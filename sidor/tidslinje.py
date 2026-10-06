import datetime as dt

import streamlit as st

from utbytesapp import omgangar, ui

mina = ui.mina()
idag = dt.date.today()

st.title("Tidslinje mot VT2028")
st.caption("Alla viktiga datum från nu till avresa. Datumen för 2027 följer UU:s återkommande schema – "
           "kontrollera på uu.se när ansökan öppnar. Händelser markerade *ungefär* har inget exakt datum.")

# Nedräkning till de tre ansökningsomgångarna
kol = st.columns(3)
for k, o in zip(kol, omgangar.OMGANGAR):
    status = o.status(idag)
    with k.container(border=True):
        st.markdown(f"**{o.namn}**")
        st.markdown(f"{o.kort_datum()}  \n:small[{o.galler}]")
        if status == "kommande":
            st.markdown(f"### {omgangar.dagar_kvar(o.start)} dagar kvar")
            st.caption("tills den öppnar")
        elif status == "öppen":
            st.markdown(f"### :green[Öppen – {omgangar.dagar_kvar(o.slut)} dagar kvar]")
        else:
            st.markdown("### :gray[Stängd]")
        antal = len(mina["rangordning"].get(o.id, []))
        st.caption(f"{antal} av 4 val rangordnade i Mina val")

visa_alla = st.toggle("Visa även händelser som inte gäller VT2028", value=False)
TYPFARG = {"ansokan": "#2a78d6", "besked": "#0ca30c", "info": "#898781", "stipendium": "#d6a12a",
           "resa": "#8a5cd6", "ovrigt": "#898781", "egen": "#d6662a"}

poster = []
for h in omgangar.HANDELSER:
    if h.galler_vt2028 or visa_alla:
        poster.append({"datum": h.datum, "slut": h.slut, "titel": h.titel, "text": h.text, "typ": h.typ,
                       "url": h.url, "ungefar": h.ungefarlig, "egen": False})
for i, e_ in enumerate(mina["handelser"]):
    try:
        poster.append({"datum": dt.date.fromisoformat(e_["datum"]), "slut": None, "titel": e_["text"],
                       "text": e_.get("anteckning", ""), "typ": "egen", "url": None, "ungefar": False, "egen": True,
                       "klar": e_.get("klar", False), "index": i})
    except (KeyError, ValueError):
        continue
poster.sort(key=lambda p: p["datum"])

rader = []
for p in poster:
    slut = p["slut"] or p["datum"]
    klass = "ut-forbi" if slut < idag else ("ut-nu" if p["datum"] <= idag <= slut else "")
    if slut < idag:
        kvar = "passerat"
    elif p["datum"] <= idag:
        kvar = f"pågår · {omgangar.dagar_kvar(slut)} d kvar"
    else:
        kvar = f"om {omgangar.dagar_kvar(p['datum'])} d"
    datum = omgangar.datum_text(p["datum"])
    if p["slut"]:
        datum = omgangar.intervall_text(p["datum"], p["slut"])
    titel = ui.e(p["titel"]) + (" <small>(ungefär)</small>" if p["ungefar"] else "") + (" ✓" if p.get("klar") else "")
    lank = f' <a href="{ui.e(p["url"])}" target="_blank">läs mer</a>' if p["url"] else ""
    rader.append(
        f'<div class="ut-tl-rad {klass}"><div class="ut-tl-datum">{ui.e(datum)}</div>'
        f'<div><div class="ut-tl-titel"><span class="ut-prick" style="background:{TYPFARG.get(p["typ"], "#898781")}"></span>'
        f'{titel}</div><div class="ut-tl-text">{ui.e(p["text"])}{lank}</div></div>'
        f'<div class="ut-tl-kvar">{ui.e(kvar)}</div></div>')
st.markdown(f'<div class="ut-tl">{"".join(rader)}</div>', unsafe_allow_html=True)
st.markdown(" ".join(f'<span class="ut-liten"><span class="ut-prick" style="background:{f}"></span>{t}</span>&nbsp;&nbsp;'
                     for t, f in (("Ansökan", TYPFARG["ansokan"]), ("Besked", TYPFARG["besked"]),
                                  ("Information", TYPFARG["info"]), ("Stipendium", TYPFARG["stipendium"]),
                                  ("Resa", TYPFARG["resa"]), ("Egen", TYPFARG["egen"]))), unsafe_allow_html=True)

st.download_button("Lägg in i kalendern (.ics)", omgangar.ics(
    [h for h in omgangar.HANDELSER if h.galler_vt2028 and (h.slut or h.datum) >= idag], mina["handelser"]),
    file_name="utbyte_vt2028.ics", mime="text/calendar", icon=":material/calendar_add_on:",
    help="Öppna filen så läggs datumen in i Kalender (heldagshändelser).")

st.divider()
v, h = st.columns(2)
with v:
    st.subheader("Egna datum")
    with st.form("ny_handelse", clear_on_submit=True):
        datum = st.date_input("Datum", value=idag + dt.timedelta(days=7), format="YYYY-MM-DD")
        text = st.text_input("Vad", placeholder="t.ex. Möte med studievägledare om tillgodoräknande")
        anteckning = st.text_input("Anteckning (valfri)")
        if st.form_submit_button("Lägg till", icon=":material/add:") and text.strip():
            dd = ui.mina()
            dd["handelser"].append({"datum": datum.isoformat(), "text": text.strip(), "anteckning": anteckning,
                                    "klar": False})
            ui.spara(dd, "Tillagd")
            st.rerun()
    for i, e_ in enumerate(mina["handelser"]):
        c1, c2, c3 = st.columns([1, 6, 1], vertical_alignment="center")
        klar = c1.checkbox("Klar", value=e_.get("klar", False), key=f"h_klar_{i}", label_visibility="collapsed")
        c2.markdown(f"**{ui.md_escape(e_['datum'])}** {ui.md_escape(e_['text'])}")
        if klar != e_.get("klar", False):
            dd = ui.mina()
            dd["handelser"][i]["klar"] = klar
            ui.spara(dd)
            st.rerun()
        if c3.button("", key=f"h_bort_{i}", icon=":material/delete:", type="tertiary", help="Ta bort"):
            dd = ui.mina()
            dd["handelser"].pop(i)
            ui.spara(dd, "Borttagen")
            st.rerun()

with h:
    st.subheader("Checklista inför ansökan")
    PUNKTER = [
        ("massa", "Gå på TekNats utbytesmässa (2 nov, Ångström)"),
        ("vagledare", "Prata med studievägledningen om tillgodoräknande och termin 8"),
        ("inriktning", "Bestäm (preliminär) inriktning för årskurs 4"),
        ("valj", "Välj upp till fyra avtal per omgång i Mina val"),
        ("kurser", "Gör kursförslag på 30 hp för varje val (Kursplan)"),
        ("prereq", "Kontrollera förkunskapskrav för kurserna"),
        ("sprak", "Kontrollera språkkrav – boka språktest i tid om det behövs"),
        ("motivering", "Svara på de tre frågorna (akademisk motivering) på engelska"),
        ("intyg", "Ladda ner resultatintyg och registreringsintyg från Ladok"),
        ("merit", "Intyg för meriterande uppdrag (nation/kår, mottagning) om du har"),
        ("pass", "Kontrollera passets giltighet och visumregler"),
        ("erasmus", "Erasmusstipendiet: ansök 1–15 nov 2027 (om Erasmusavtal)"),
    ]
    lista = mina.get("checklista", {})
    klara = sum(1 for p, _ in PUNKTER if lista.get(p))
    st.markdown(ui.meter(klara / len(PUNKTER), full=klara == len(PUNKTER)) + f'<div class="ut-liten">{klara} av {len(PUNKTER)} klara</div>',
                unsafe_allow_html=True)
    for pid, text in PUNKTER:
        varde = st.checkbox(text, value=bool(lista.get(pid)), key=f"cl_{pid}")
        if varde != bool(lista.get(pid)):
            dd = ui.mina()
            dd.setdefault("checklista", {})[pid] = varde
            ui.spara(dd)
            st.rerun()
