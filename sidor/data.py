import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from utbytesapp import amnen, bygg, kurstyper, lagring, rapporter, ui

ROT = Path(__file__).resolve().parent.parent
d = ui.data()

st.title("Data och uppdatering")
st.caption("Allt hämtas från UU:s publika sidor och lagras lokalt i `data/`. Appen själv gör inga nätverksanrop – "
           "bara knapparna nedan gör det.")


def kor(argument: list[str], rubrik: str) -> None:
    with st.status(rubrik, expanded=True) as status:
        ruta = st.empty()
        rader: list[str] = []
        proc = subprocess.Popen([sys.executable, *argument], cwd=ROT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
        for rad in proc.stdout:
            rader.append(rad.rstrip())
            ruta.code("\n".join(rader[-25:]), language=None)
        proc.wait()
        st.cache_data.clear()
        if proc.returncode == 0:
            status.update(label=f"{rubrik} – klart", state="complete", expanded=False)
        else:
            status.update(label=f"{rubrik} – misslyckades (se loggen)", state="error", expanded=True)
    st.session_state["data_logg"] = "\n".join(rader)


c1, c2, c3 = st.columns(3)
with c1.container(border=True):
    st.markdown("**Snabb uppdatering**")
    st.caption("Avtalslistor, platslistan för aktuell omgång, TekNats sida (restplatser) och Erasmusnivåer. "
               "Detaljer hämtas bara för nya avtal. Tar under en minut.")
    if st.button("Uppdatera", type="primary", icon=":material/sync:", width="stretch"):
        kor(["verktyg/hamta_avtal.py"], "Uppdaterar avtalsdata")
with c2.container(border=True):
    st.markdown("**Hämta alla detaljer på nytt**")
    st.caption("Hämtar om alla fält för alla avtal (språk, terminsdatum, kurskataloger …). "
               "Servern är långsam – räkna med 10–20 minuter.")
    if st.button("Hämta allt", icon=":material/cloud_sync:", width="stretch"):
        kor(["verktyg/hamta_avtal.py", "--allt"], "Hämtar alla avtalsdetaljer")
with c3.container(border=True):
    st.markdown("**Utbytesrapporter**")
    st.caption("Laddar ner nya rapporter (PDF) och bygger sökindexet. Första gången tar det 20–30 minuter.")
    if st.button("Hämta rapporter", icon=":material/description:", width="stretch"):
        kor(["verktyg/hamta_rapporter.py"], "Hämtar utbytesrapporter")

if st.session_state.get("data_logg"):
    with st.expander("Logg från senaste körningen"):
        st.code(st.session_state["data_logg"], language=None)

if d is None:
    st.warning("Ingen avtalsdata ännu – tryck på **Uppdatera**.", icon=":material/cloud_download:")
    st.stop()

# ---------------------------------------------------------------------------------------------
st.subheader("Det här finns lokalt")
hamtad = d.get("hamtad") or {}
rapp = ui.rapp()
pdf_antal = len(list(rapporter.PDF_MAPP.glob("*.pdf"))) if rapporter.PDF_MAPP.exists() else 0
totalt_rapporter = sum(len(a["rapporter"]) for a in d["avtal"])
st.dataframe(pd.DataFrame([
    {"Källa": "Avtalsdatabasen (MoveON): listor", "Hämtad": hamtad.get("moveon", "–"),
     "Innehåll": f"{len(d['avtal'])} avtal, {len(d['universitet'])} universitet"},
    {"Källa": "Avtalsdatabasen: detaljer", "Hämtad": hamtad.get("detaljer", "–"),
     "Innehåll": f"{sum(1 for a in d['avtal'] if a['detaljer_hamtade'])} av {len(d['avtal'])} avtal"},
    *[{"Källa": f"Platslista {meta.get('omgang') or ''} ({mal})", "Hämtad": meta.get("hamtad", "–"),
       "Innehåll": f"{meta.get('antal')} universitet · senast ändrad på uu.se {meta.get('senast_andrad') or '?'}"}
      for mal, meta in sorted(d.get("platslistor", {}).items())],
    {"Källa": "TekNats avtalssida", "Hämtad": hamtad.get("teknatsida", "–"),
     "Innehåll": f"senast ändrad på uu.se {(d.get('teknatsida') or {}).get('senast_andrad') or '?'}"},
    {"Källa": "Erasmusstipendiets nivåer", "Hämtad": hamtad.get("erasmus", "–"),
     "Innehåll": ", ".join(f"grupp {g['grupp']}: {g['euro_per_manad']} €" for g in d["erasmus"].get("grupper", []))},
    {"Källa": "Utbytesrapporter", "Hämtad": (rapp.get("byggd") or "–").replace("T", " ")[:16],
     "Innehåll": f"{len(rapp.get('rapporter', []))} indexerade, {pdf_antal} av {totalt_rapporter} PDF:er nedladdade"},
]), hide_index=True, width="stretch")

# ---------------------------------------------------------------------------------------------
st.subheader("Så tolkas datan")
st.markdown("""
- **Kanaler.** *Centrala avtal* söks i UU:s centrala ansökan (vårrundan 15 april–14 maj för VT2028) och bara
  universitet på den omgångens lista kan väljas. *TekNat* omfattar fakultetens avtal och institutionernas avtal
  (fysik, matematik, IT, elektroteknik, kemi, biologi, geovetenskaper, samhällsbyggnad och industriell teknik);
  alla söks i TekNats formulär 15 jan–15 feb 2027, med restplatser 15 aug–15 sep 2027. Institutionsavtal kräver
  att dina kurser ligger inom avtalets ämne (*Subject area restrictions*).
- **Undervisningsspråk** tas i första hand från avtalets fält i databasen. Saknas det används uppgiften från ett
  annat avtal med samma universitet. Annars visas landets språk med *engelska främst på masternivå* (TekNats egen
  tumregel) och märks **obekräftat**. Du kan rätta språket per universitet under *Egna uppgifter* på
  universitetssidan.
- **Vårterminens månader** tolkas ur fältet *Semester dates*; saknas det visas ett typiskt intervall för landet,
  märkt *typiskt för landet*.
- **Platser** kommer från UU:s lista över universitet i respektive centrala omgång och matchas mot avtalen på namn.
  Listan för VT2028 publiceras 15 april 2027 – uppdatera då.
- **Kurser du kan läsa** (teknik, fysik/naturvetenskap, matematik, data) är för de 85 centrala avtalen en
  manuell tolkning av UU:s ämnesbegränsningar ({kurstyper.TOLKAD}). Flera "alla ämnen"-avtal utesluter nämligen
  teknik eller naturvetenskap. Ändrar UU texten visar appen det. För TekNat-avtal härleds det ur avtalets
  ämnesområden. Tolkningen finns i `utbytesapp/kurstyper.py`.
- **Ämnesmatchning** är ett förslag för sortering. TekNat-avtal matchas på ämnesområde (ISCED) och din inriktning,
  med +1 för avtal riktade till civilingenjörsprogram. Avtal med alla ämnen matchas på vilka kurstyper som är
  öppna. Matchningen säger inget om behörighet.
""".replace("{kurstyper.TOLKAD}", kurstyper.TOLKAD))
st.dataframe(pd.DataFrame(amnen.regeltabell()), hide_index=True, width="stretch")
with st.expander("Tolkningen av de centrala avtalens ämnesbegränsningar"):
    rader = []
    for a in d["avtal"]:
        kt = a.get("kurstyper") or {}
        if kt.get("kalla") != "tolkad":
            continue
        rader.append({"Universitet": d["universitet"][a["core_id"]]["namn"], **{
            kurstyper.OMRADE_NAMN[o]: kt.get(o) for o in kurstyper.OMRADEN},
            "Bara helår": kt.get("helar"), "Notering": kt.get("not"), "Texten ändrad": kt.get("andrad")})
    st.dataframe(pd.DataFrame(rader).sort_values("Universitet"), hide_index=True, width="stretch")
st.markdown("- **Utbytesrapporter** kategoriseras på svaret på *What are you studying at Uppsala University?* "
            "(t.ex. *Engineering physics* → teknisk fysik).\n"
            "- Det här är en sammanställning, inte ett beslut. Kontrollera alltid uppgifter på uu.se och med "
            "koordinatorn för avtalet innan du söker.")

omatchat = d.get("omatchat", {})
if any(omatchat.values()):
    with st.expander("Rader som inte kunde kopplas till ett avtal"):
        for typ, rader in omatchat.items():
            for r in rader:
                st.markdown(f"- {typ}: {ui.md_escape(r.get('namn', ''))} ({ui.md_escape(r.get('land', ''))})")

andringsfil = bygg.DATA / "andringar.json"
if andringsfil.exists():
    with st.expander("Ändringar vid tidigare uppdateringar"):
        for post in json.loads(andringsfil.read_text(encoding="utf-8")):
            st.markdown(f"**{post['datum'].replace('T', ' ')}**")
            st.markdown("\n".join(f"- {ui.md_escape(r)}" for r in post["rader"]))

# ---------------------------------------------------------------------------------------------
st.subheader("Dina sparade val")
mina = ui.mina()
st.markdown(f"{len(mina['favoriter'])} favoriter · {sum(len(p.get('kurser', [])) for p in mina['kursplaner'].values())} "
            f"planerade kurser · {len(mina['egna_uppgifter'])} universitet med egna uppgifter. "
            f"Sparas i `data/mina_val.json`, med automatisk säkerhetskopia i `data/backups/` vid varje ändring.")
backups = lagring.lista_backups()
if backups:
    with st.expander(f"Säkerhetskopior ({len(backups)})"):
        val = st.selectbox("Återställ till", backups, format_func=lambda p: p.stem.replace("mina_val-", ""))
        if st.button("Återställ", icon=":material/restore:"):
            lagring.aterstall(val)
            st.success("Återställt. Den tidigare versionen sparades också som säkerhetskopia.")
            st.rerun()

st.subheader("Integritet")
st.markdown("- Servern lyssnar bara på `localhost` och telemetri är avstängd (`.streamlit/config.toml`).\n"
            "- Hela mappen ignoreras av git (`.gitignore` med `*`), eftersom hemkatalogen är ett git-repo med "
            "GitHub-remote.\n"
            "- Kursappens data läses bara (för meritvärde och termin 8) och skrivs aldrig.")
