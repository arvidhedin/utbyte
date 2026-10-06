import plotly.graph_objects as go
import streamlit as st

from utbytesapp import geo, modell, ui

d = ui.krav_data()
df = ui.tabell()
varlista = modell.senaste_varlista(d)
f = ui.filterpanel(df, varlista)
traffar = ui.filtrera(df, f, ui.sokbar())
uni = modell.per_universitet(traffar)

st.title("Karta")
st.caption("Samma filter som på Sök. Färgen visar vilken kanal du söker via. Klicka på en prick för att se "
           "universitetets avtal nedanför kartan.")

if uni.empty:
    st.info("Inga universitet matchar filtren.", icon=":material/search_off:")
    st.stop()

VYER = {
    "Urvalet": None,
    "Världen": dict(lataxis_range=[-50, 75], lonaxis_range=[-170, 180]),
    "Europa": dict(lataxis_range=[34, 71], lonaxis_range=[-25, 45]),
    "Asien": dict(lataxis_range=[-12, 55], lonaxis_range=[60, 150]),
    "Nordamerika": dict(lataxis_range=[10, 62], lonaxis_range=[-135, -55]),
    "Sydamerika": dict(lataxis_range=[-56, 15], lonaxis_range=[-90, -30]),
    "Oceanien": dict(lataxis_range=[-48, -8], lonaxis_range=[110, 180]),
}
c1, c2 = st.columns([4, 2], vertical_alignment="bottom")
vy = c1.segmented_control("Visa", list(VYER), default="Urvalet", key="k_vy") or "Urvalet"
farg_efter = c2.selectbox("Färg efter", ["Kanal", "Ämnesmatchning", "Undervisningsspråk bekräftat"], key="k_farg")

uni = uni[uni["lat"].notna()].copy()
uni["grupp"] = uni["kanaler"].map(lambda k: "Både centralt och TekNat" if len(k) > 1 else modell.KANAL_TEXT[k[0]])
GRUPPFARG = {"Centrala avtal": ui.KANALFARG["central"], "TekNat": ui.KANALFARG["teknat"],
             "Både centralt och TekNat": "#d6662a"}
if farg_efter == "Ämnesmatchning":
    from utbytesapp import amnen
    uni["grupp"] = uni["match"].map(lambda m: f"Ämnesmatch: {amnen.MATCH_TEXT[int(m)]}")
    GRUPPFARG = {"Ämnesmatch: Mycket bra": "#0ca30c", "Ämnesmatch: Bra": "#2a78d6",
                 "Ämnesmatch: Möjlig": "#898781", "Ämnesmatch: Svag": "#c3c2b7"}
elif farg_efter == "Undervisningsspråk bekräftat":
    uni["grupp"] = uni["sprak_bekraftat"].map(lambda b: "Språk bekräftat" if b else "Språk obekräftat")
    GRUPPFARG = {"Språk bekräftat": "#2a78d6", "Språk obekräftat": "#898781"}


def hovertext(r) -> str:
    rader = [f"<b>{ui.e(r['flagga'])} {ui.e(r['universitet'])}</b>",
             f"{ui.e(r['stad'] + ', ' if r['stad'] else '')}{ui.e(r['land'])}",
             "Avtal: " + ui.e(", ".join(r["enheter"])),
             "Språk: " + ui.e(modell.sprak_visning(r["sprak"], "databasen" if r["sprak_bekraftat"] else "obekraftad"))
             + ("" if r["sprak_bekraftat"] else " (obekräftat)")]
    if r["pa_varlista"]:
        rader.append(f"Vårlistan: {ui.heltal(r['platser_var'])} platser" if not ui.ar_nan(r["platser_var"]) else "På vårlistan")
    if r["antal_rapporter"]:
        rader.append(f"{r['antal_rapporter']} rapporter" + (f" ({r['ttf_rapporter']} TTF)" if r["ttf_rapporter"] else ""))
    return "<br>".join(rader)


fig = go.Figure()
for grupp, g in uni.groupby("grupp"):
    fig.add_trace(go.Scattergeo(
        lat=g["lat"], lon=g["lon"], mode="markers", name=f"{grupp} ({len(g)})",
        marker=dict(size=(7 + 2.2 * g["antal_avtal"].clip(upper=5)).tolist(), color=GRUPPFARG.get(grupp, ui.GRA),
                    line=dict(width=g["favorit"].map(lambda f: 2.5 if f else 0.6).tolist(), color="#ffd23f"),
                    opacity=0.9),
        customdata=g["core_id"], hovertext=[hovertext(r) for _, r in g.iterrows()], hoverinfo="text",
    ))
fig.add_trace(go.Scattergeo(lat=[geo.UPPSALA[0]], lon=[geo.UPPSALA[1]], mode="markers+text", text=["Uppsala"],
                            textposition="top center", marker=dict(size=9, color=ui.GRA, symbol="star"),
                            name="Uppsala", hoverinfo="skip", showlegend=False))
geo_inst = dict(projection_type="natural earth", showcountries=True, countrycolor="rgba(137,135,129,0.45)",
                showland=True, landcolor="rgba(137,135,129,0.12)", showocean=False, bgcolor="rgba(0,0,0,0)",
                showframe=False, coastlinecolor="rgba(137,135,129,0.55)", resolution=50 if vy not in ("Världen",) else 110)
if VYER[vy] is None:
    geo_inst["fitbounds"] = "locations"
else:
    geo_inst.update(VYER[vy])
fig.update_geos(**geo_inst)
st.caption("Större prick = fler avtal. Gul ring = favorit.")
ev = ui.visa_plotly(ui.plotly_layout(fig, hojd=560), on_select="rerun", selection_mode=("points",), key="k_karta")

valda = []
if ev and ev.selection and ev.selection.get("points"):
    valda = [p.get("customdata") for p in ev.selection["points"] if p.get("customdata")]
if valda:
    for core in dict.fromkeys(valda):
        rad = uni[uni["core_id"] == core]
        if len(rad):
            ui.universitetskort(rad.iloc[0], traffar[traffar["core_id"] == core], varlista, nyckel="k_")
else:
    st.info("Klicka på en prick för att visa universitetet här. Dra för att panorera, scrolla för att zooma.", icon=":material/touch_app:")

with st.expander(f"Länder i urvalet ({uni['land'].nunique()})"):
    per_land = uni.groupby(["varldsdel", "land", "flagga"]).size().reset_index(name="Universitet")
    per_land = per_land.sort_values(["varldsdel", "Universitet"], ascending=[True, False])
    st.dataframe(per_land.rename(columns={"varldsdel": "Världsdel", "land": "Land", "flagga": ""}),
                 hide_index=True, width="stretch")
