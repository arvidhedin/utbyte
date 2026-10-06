import re

import pandas as pd
import streamlit as st

from utbytesapp import geo, ui

d = ui.krav_data()
df = ui.tabell()
rapp = ui.rapp().get("rapporter", [])

st.title("Utbytesrapporter")
st.caption("Rapporter som tidigare UU-studenter skrivit efter sitt utbyte, hämtade från UU:s avtalsdatabas. "
           "Sök fritt i texten, t.ex. *housing*, *quantum*, *tillgodoräkna* eller en kurskod.")

if not rapp:
    st.info("Inga rapporter hämtade ännu. Gå till **Data och uppdatering** och hämta utbytesrapporterna.",
            icon=":material/cloud_download:")
    st.page_link("sidor/data.py", label="Data och uppdatering", icon=":material/sync:")
    st.stop()

univ = d["universitet"]
kanal_for = {a["id"]: a["kanal"] for a in d["avtal"]}
favoriter = set(df[df["favorit"]]["core_id"])

rader = []
for r in rapp:
    u = univ.get(r["core_id"], {})
    land = geo.land(u.get("land_kod"))
    termin = r.get("termin") or ""
    rader.append({**r, "universitet": u.get("namn", "?"), "land": land.namn, "flagga": land.flagga,
                  "varldsdel": land.varldsdel, "kanal": kanal_for.get(r["avtal_id"], ""),
                  "termintyp": "Vår" if termin.startswith("VT") else "Höst" if termin.startswith("HT") else "Okänd"})
tab = pd.DataFrame(rader)

with st.sidebar:
    st.markdown("### Filter för rapporter")
    text = st.text_input("Sök i rapporterna", key="r_text", placeholder="t.ex. accommodation, ECTS, robotics")
    program = st.multiselect("Vad studenten läste i Uppsala", ["Teknisk fysik", "Annat ingenjörsprogram", "Fysik", "Annat"],
                             key="r_program", placeholder="Alla program")
    varldsdel = st.multiselect("Världsdel", geo.VARLDSDELAR, key="r_varldsdel", placeholder="Alla")
    land = st.multiselect("Land", sorted(tab["land"].unique()), key="r_land", placeholder="Alla länder")
    termintyp = st.segmented_control("Termin", ["Vår", "Höst"], key="r_termin", selection_mode="multi")
    bara_fav = st.checkbox("Bara universitet bland mina favoriter", key="r_fav")
    sortering = st.selectbox("Sortera", ["Nyast först", "Teknisk fysik först", "Universitet"], key="r_sort")

m = pd.Series(True, index=tab.index)
ord_ = [o for o in re.split(r"\s+", (text or "").lower().strip()) if o]
for o in ord_:
    m &= (tab["text"].str.lower().str.contains(re.escape(o)) | tab["universitet"].str.lower().str.contains(re.escape(o))
          | tab["land"].str.lower().str.contains(re.escape(o)))
if program:
    m &= tab["program_kategori"].isin(program)
if varldsdel:
    m &= tab["varldsdel"].isin(varldsdel)
if land:
    m &= tab["land"].isin(land)
if termintyp:
    m &= tab["termintyp"].isin(termintyp)
if bara_fav:
    m &= tab["core_id"].isin(favoriter)
urval = tab[m].copy()
if sortering == "Nyast först":
    urval = urval.sort_values(["ar", "universitet"], ascending=[False, True])
elif sortering == "Teknisk fysik först":
    urval = urval.assign(_t=urval["program_kategori"] != "Teknisk fysik").sort_values(["_t", "ar"], ascending=[True, False])
else:
    urval = urval.sort_values(["universitet", "ar"])

k = st.columns(4)
k[0].metric("Rapporter", len(urval), border=True)
k[1].metric("Universitet", urval["core_id"].nunique(), border=True)
k[2].metric("Från teknisk fysik", int((urval["program_kategori"] == "Teknisk fysik").sum()), border=True)
k[3].metric("Vårtermin", int((urval["termintyp"] == "Vår").sum()), border=True)

if not program and not text:
    ttf = tab[tab["program_kategori"] == "Teknisk fysik"]
    if len(ttf):
        with st.expander(f"Hit har teknisk fysik-studenter åkt ({len(ttf)} rapporter)", expanded=False):
            topp = ttf.groupby(["flagga", "universitet", "land"]).size().reset_index(name="Rapporter")
            st.dataframe(topp.sort_values("Rapporter", ascending=False).rename(
                columns={"flagga": "", "universitet": "Universitet", "land": "Land"}), hide_index=True, width="stretch")

PER_SIDA = 25
nyckel = f"{text}|{program}|{varldsdel}|{land}|{termintyp}|{bara_fav}|{sortering}"
if st.session_state.get("r_nyckel") != nyckel:
    st.session_state["r_nyckel"] = nyckel
    st.session_state["r_sida"] = 1
antal_sidor = max(1, -(-len(urval) // PER_SIDA))
sida = min(st.session_state.get("r_sida", 1), antal_sidor)

for _, r in urval.iloc[(sida - 1) * PER_SIDA: sida * PER_SIDA].iterrows():
    falt = r["falt"] if isinstance(r["falt"], dict) else {}
    rubrik = " · ".join(x for x in (f"{r['flagga']} {r['universitet']}", r.get("ar"), r.get("termin"),
                                     falt.get("program_uu")) if x)
    ikon = ":material/star:" if r["program_kategori"] == "Teknisk fysik" else ":material/description:"
    with st.expander(rubrik, icon=ikon):
        info = [x for x in (falt.get("niva"), falt.get("amne"), falt.get("samordnare"),
                            f"{falt.get('terminer')} termin(er)" if falt.get("terminer") else None) if x]
        st.markdown(" · ".join(ui.md_escape(x) for x in info) + f"  \n[Öppna PDF](app/{r['pdf']})")
        if ord_:
            st.markdown(f'<div class="ut-liten">{ui.markera(r["text"], ord_, 320)}</div>', unsafe_allow_html=True)
        for avs in r["avsnitt"]:
            if avs["rubrik"].lower() in ("basic information", "data handling", "submit report", "photos"):
                continue
            svar = [p for p in avs["poster"] if p["svar"] and len(p["svar"]) > 3]
            if not svar:
                continue
            st.markdown(f"**{ui.md_escape(avs['rubrik'])}**")
            for p in svar:
                st.markdown(f":small[{ui.md_escape(p['fraga'])}]  \n{ui.md_escape(p['svar'])}")
        if falt.get("kontakt") and "@" in falt.get("kontakt", ""):
            st.caption(f"Studenten vill gärna bli kontaktad av blivande utbytesstudenter: {falt['kontakt']}")
        if st.button("Visa universitetet", key=f"r_uni_{r['id']}", icon=":material/account_balance:"):
            ui.oppna_universitet(r["core_id"])
            st.switch_page("sidor/universitet.py")

if antal_sidor > 1:
    v, mitt, h = st.columns([1, 2, 1], vertical_alignment="center")
    if v.button("Föregående", disabled=sida <= 1, icon=":material/chevron_left:", width="stretch"):
        st.session_state["r_sida"] = sida - 1
        st.rerun()
    mitt.markdown(f"<div style='text-align:center'>Sida {sida} av {antal_sidor}</div>", unsafe_allow_html=True)
    if h.button("Nästa", disabled=sida >= antal_sidor, icon=":material/chevron_right:", width="stretch"):
        st.session_state["r_sida"] = sida + 1
        st.rerun()
