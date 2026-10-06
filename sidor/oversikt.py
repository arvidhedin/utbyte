import datetime as dt
import json

import plotly.graph_objects as go
import streamlit as st

from utbytesapp import bygg, geo, modell, omgangar, ui

d = ui.krav_data()
df = ui.tabell()
mina = ui.mina()
idag = dt.date.today()
varlista = modell.senaste_varlista(d)

st.title("Utbyte våren 2028")
st.caption("Alla universitet du kan söka som student i teknisk fysik vid UU – via centrala avtal och via TekNats "
           "fakultets- och institutionsavtal – med var och när du söker.")

# Ansökningsomgångar
kol = st.columns(3)
for k, o in zip(kol, omgangar.OMGANGAR):
    with k.container(border=True):
        status = o.status(idag)
        st.markdown(f"**{o.namn}**  \n{o.kort_datum()}")
        if status == "kommande":
            st.markdown(f"### {omgangar.dagar_kvar(o.start)} dagar")
            st.caption(f"tills den öppnar · {o.galler.lower()}")
        elif status == "öppen":
            st.markdown("### :green[Öppen]")
            st.caption(f"{omgangar.dagar_kvar(o.slut)} dagar kvar")
        else:
            st.markdown("### :gray[Stängd]")
        n = len(df[(df["kanal"] == o.kanal)])
        st.caption(f"{n} avtal · {len(mina['rangordning'].get(o.id, []))} av 4 val rangordnade")

with st.expander("Så söker du för VT2028", expanded=not mina["favoriter"], icon=":material/info:"):
    st.markdown(f"""
1. **TekNat, 15 jan–15 feb 2027.** Fakultetens och institutionernas avtal (främst Europa via Erasmus, Nordtek med
   nordiska tekniska universitet, och några ämnesavtal som ETH, Polytechnique Montréal, Tokyo och POSTECH).
   Upp till fyra val i samma ansökan, även blandat fakultet/institution. Urval på urvalsgrupp och meritvärde.
2. **Centrala avtal, vårrundan 15 april–14 maj 2027.** Universitetsövergripande avtal över hela världen (USA, Kanada,
   Australien, Asien, Latinamerika) samt vissa Erasmus- och ICM-avtal. Bara universitet på listan som publiceras
   15 april kan väljas. Förra vårrundans lista ({varlista or '–'}) visas som fingervisning.
3. **Restplatser via TekNat, 15 aug–15 sep 2027**, om du inte fått plats eller vill komplettera.

Du kan söka i flera omgångar. Har du tackat ja till en plats prioriteras andra före dig i nästa omgång.
""")

# Snabbsök
st.subheader("Snabbsök")
PRESET = {
    "Europa via TekNat": {"f_varldsdel": ["Europa"], "f_kanal": ["TekNat"]},
    "Utanför Europa": {"f_varldsdel": [v for v in geo.VARLDSDELAR if v != "Europa"]},
    "Fysikavtal": {"f_amnen": ["Fysik"]},
    "Civilingenjörsavtal": {"f_civing": True},
    "Undervisning på engelska (bekräftat)": {"f_sprak": ["engelska"], "f_bekraftat": True},
    "Där teknisk fysik-studenter varit": {"f_ttf": True},
    f"På senaste vårlistan ({varlista})": {"f_varlista": True},
    "Mina favoriter": {"f_favoriter": True},
}
knappar = st.columns(4)
for i, (namn, varden) in enumerate(PRESET.items()):
    if knappar[i % 4].button(namn, key=f"preset_{i}", width="stretch"):
        ui.nollstall_filter()
        for nyckel, varde in varden.items():
            st.session_state[nyckel] = varde
        st.switch_page("sidor/sok.py")

# Statistik
st.subheader("Utbudet")
v, h = st.columns([3, 2])
with v:
    uni = modell.per_universitet(df)
    uni["kanalgrupp"] = uni["kanaler"].map(lambda k: "Båda" if len(k) > 1 else modell.KANAL_TEXT[k[0]])
    fig = go.Figure()
    for grupp, farg in (("TekNat", ui.KANALFARG["teknat"]), ("Centrala avtal", ui.KANALFARG["central"]),
                        ("Båda", "#d6662a")):
        g = uni[uni["kanalgrupp"] == grupp].groupby("varldsdel").size().reindex(geo.VARLDSDELAR, fill_value=0)
        fig.add_trace(go.Bar(y=g.index, x=g.values, name=grupp, orientation="h", marker_color=farg,
                             hovertemplate="%{y}: %{x} universitet<extra>" + grupp + "</extra>"))
    fig.update_layout(barmode="stack", yaxis=dict(autorange="reversed"), xaxis_title="Universitet")
    ui.visa_plotly(ui.plotly_layout(fig, hojd=300))
with h:
    ui.faktarutor([
        ("Universitet", str(df["core_id"].nunique()), None),
        ("Avtal", str(len(df)), None),
        ("Länder", str(df["land"].nunique()), None),
        ("Bekräftat engelska", str(df[df["sprak"].map(lambda l: "engelska" in l) &
                                      df["sprak_status"].isin(["databasen", "samma_universitet", "egen"])]["core_id"].nunique()),
         "Universitet där databasen anger engelska som undervisningsspråk."),
        ("Med Erasmus/ICM", str(df[df["erasmus"] | df["icm"]]["core_id"].nunique()), None),
        ("TTF-rapporter", str(int(df["ttf_rapporter"].sum())), "Rapporter från studenter som läste teknisk fysik."),
    ])

# Favoriter och kommande datum
v, h = st.columns(2)
with v:
    st.subheader("Mina val")
    if not mina["favoriter"]:
        st.caption("Inga favoriter än – spara avtal med stjärnan under Sök.")
    else:
        fav = df[df["favorit"]]
        for _, r in fav.head(8).iterrows():
            st.markdown(f"{r['flagga']} **{ui.md_escape(r['universitet'])}** – {ui.vag(r)} · {r['status']}")
        if len(fav) > 8:
            st.caption(f"… och {len(fav) - 8} till.")
        st.page_link("sidor/mina_val.py", label="Rangordna i Mina val", icon=":material/star:")
with h:
    st.subheader("Kommande datum")
    kommande = [x for x in omgangar.HANDELSER if (x.slut or x.datum) >= idag and x.galler_vt2028][:4]
    for x in kommande:
        nar = f"om {omgangar.dagar_kvar(x.datum)} dagar" if x.datum > idag else "pågår"
        st.markdown(f"**{omgangar.datum_text(x.datum)}** – {x.titel} :small[({nar})]")
    st.page_link("sidor/tidslinje.py", label="Hela tidslinjen", icon=":material/event:")

fil = bygg.DATA / "andringar.json"
if fil.exists():
    logg = json.loads(fil.read_text(encoding="utf-8"))
    if logg:
        senaste = logg[0]
        with st.expander(f"Nytt vid senaste uppdateringen ({senaste['datum'].replace('T', ' ')})",
                         icon=":material/new_releases:"):
            st.markdown("\n".join(f"- {ui.md_escape(r)}" for r in senaste["rader"][:30]))
