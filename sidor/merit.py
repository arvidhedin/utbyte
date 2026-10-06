import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

from utbytesapp import kursdata, omgangar, ui

mina = ui.mina()
inst = mina["installningar"]

st.title("Meritvärde och urval")
st.caption("Räknat på din data i kursappen (läses, ändras aldrig). Det här är en uppskattning enligt UU:s "
           "publicerade regler – urvalet görs av UU.")

with st.expander("Koppling till kursappen", expanded=ui.kurs() is None):
    ny = st.text_input("Mapp för kursappen", value=inst.get("kursapp") or str(Path.home() / "kurser"))
    if ny != inst.get("kursapp"):
        dd = ui.mina()
        dd["installningar"]["kursapp"] = ny
        ui.spara(dd, "Sökvägen sparad")
        st.rerun()

kd = ui.kurs()
if kd is None:
    st.warning("Hittar ingen kursapp med `data/mina_kurser.json` i den mappen.", icon=":material/link_off:")
    st.stop()

# ---------------------------------------------------------------------------------------------
# TekNat: meritvärde och urvalsgrupp
# ---------------------------------------------------------------------------------------------
st.header("TekNat (fakultets- och institutionsavtal)")
c1, c2 = st.columns(2)
nation = c1.checkbox("Funktionär i nation eller studentkår (+0,2)", value=inst.get("extrapoang", 0) >= 0.2 - 1e-9)
mottagning = c2.checkbox("Mottagningsaktiviteter för internationella studenter (+0,1)",
                         value=round(inst.get("extrapoang", 0) * 10) % 2 == 1)
extra = (0.2 if nation else 0) + (0.1 if mottagning else 0)
if abs(extra - inst.get("extrapoang", 0)) > 1e-9:
    dd = ui.mina()
    dd["installningar"]["extrapoang"] = extra
    ui.spara(dd)
    st.rerun()

m = kursdata.meritvarde(kd, extra)
prognos = kursdata.meritvarde(kd, extra, med_planerade=True)
idag = dt.date.today()
urval = kursdata.urvalsgrupp(kd, (idag.year, idag.month))

ui.faktarutor([
    ("Meritvärde", ui.tal(m["meritvarde"], 1), "Genomsnittsbetyg (en decimal) + meriterande uppdrag (max 0,3)."),
    ("Genomsnittsbetyg (geometriskt)", f"{ui.tal(m['avrundat'], 1)} ({ui.tal(m['geometriskt'], 3)})",
     "hp-viktat geometriskt medelvärde av betyg 3–5, avrundat till en decimal."),
    ("Jämför: vanligt hp-viktat snitt", ui.tal(m["aritmetiskt"], 2), "Det som kursappen visar som merit."),
    ("Räknade hp", ui.tal(m["hp"]), "Avslutade UU-kurser med betygsskala U/3/4/5."),
    ("Urvalsgrupp (idag)", f"{urval['grupp']} ({ui.tal(urval['hp'])} hp ej avklarade)",
     "1: 0–5 hp, 2: 6–10, 3: 11–20, 4: ≥21 ej avklarade hp inom programmet."),
])
if prognos["avrundat"] is not None and prognos["hp"] > m["hp"]:
    st.info(f"Med dina **planerade betyg** i kursappen blir genomsnittsbetyget {ui.tal(prognos['avrundat'], 1)} "
            f"({ui.tal(prognos['hp'])} hp) – meritvärde {ui.tal(prognos['meritvarde'], 1)} vid ansökan "
            f"{omgangar.datum_text(omgangar.OMGANG['teknat_huvud'].slut)} om allt går som planerat.",
            icon=":material/trending_up:")
st.markdown(
    "- **Urvalsgrupp** räknas på ej avklarade hp i programkurser med rapporterade resultat (pågående kurser räknas "
    "inte). Kurserna du läser nu måste alltså vara klara senast sista ansökningsdag (15 feb 2027) för att du ska "
    "stå kvar i samma grupp.\n"
    "- Den som inte gjort utbyte tidigare via UU prioriteras. Inom samma grupp och meritvärde avgör lottning.")
if urval["rader"]:
    st.markdown("**Ej avklarade programkurser som räknas just nu:**")
    st.dataframe(pd.DataFrame(urval["rader"]).rename(columns={"kod": "Kod", "namn": "Kurs", "kvar": "Ej avklarat (hp)"}),
                 hide_index=True)
with st.expander(f"Kurser i genomsnittsbetyget ({len(m['kurser'])})"):
    st.dataframe(pd.DataFrame(m["kurser"]).rename(columns={"kod": "Kod", "namn": "Kurs", "hp": "hp", "betyg": "Betyg",
                                                           "planerat": "Planerat"}), hide_index=True, width="stretch")

# ---------------------------------------------------------------------------------------------
# Centrala avtal: toppbetyg
# ---------------------------------------------------------------------------------------------
st.header("Centrala avtal (vårrundan)")
t = kursdata.toppbetyg(kd)
ui.faktarutor([
    ("hp med högsta betyg", ui.tal(t["hp"]), "Fyll i detta under \"Grade Report\" i ansökan (som VG-poäng)."),
    ("Varav hela kurser", ui.tal(sum(r["hp"] for r in t["rader"] if r["niva"] == "kurs")), None),
    ("Varav delkurser", ui.tal(sum(r["hp"] for r in t["rader"] if r["niva"] == "delkurs")),
     "Delkurser med 5 räknas när slutbetyget är lägre – de måste synas i resultatintyget."),
])
st.markdown(
    "- Ansökningarna sorteras efter **urvalsgrupp** (prioritet: utbytet ingår i din examen och ska tillgodoräknas, "
    "inget tidigare utbyte, inget annat accepterat utbyte), sedan **antal hp med högsta betyg**, **meriterande "
    "uppdrag** och sist **lottnummer**.\n"
    "- Ett toppbetyg räknas bara en gång – inte både kurs och delkurs.\n"
    "- Tackar du ja till en TekNat-plats i mars kan det påverka prioriteringen i vårrundan.")
if t["rader"]:
    with st.expander(f"Kurser och delkurser med högsta betyg ({len(t['rader'])})"):
        st.dataframe(pd.DataFrame(t["rader"]).rename(columns={"kod": "Kod", "namn": "Kurs", "hp": "hp", "niva": "Räknas som"}),
                     hide_index=True, width="stretch")
st.caption("Källor: TekNats ansökningsguide och UU:s sida om utbytesstudier via centrala avtal.")
