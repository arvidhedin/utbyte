import pandas as pd
import streamlit as st

from utbytesapp import kursdata, ui

d = ui.krav_data()
df = ui.tabell()
mina = ui.mina()
kd = ui.kurs()
inr, profil = ui.inriktning()
ra = {a["id"]: a for a in d["avtal"]}

st.title("Kursplan för utbytet")
st.caption("Planera 30 hp per val – det krävs ett kursförslag för varje avtal du söker. Planen sparas per avtal "
           "och visas i Mina val och Jämför.")

fav = [i for i in mina["favoriter"] if i in ra]
ovriga = [i for i in df.sort_values(["universitet", "enhet_kort"])["id"] if i not in fav]
alla = fav + ovriga
rad_av = df.set_index("id")


def etikett(i: str) -> str:
    r = rad_av.loc[i]
    vag = ui.vag(r)
    plan_hp = sum(k.get("hp") or 0 for k in mina["kursplaner"].get(i, {}).get("kurser", []))
    return f"{'⭐ ' if i in fav else ''}{r['flagga']} {r['universitet']} – {vag}" + (f" ({ui.tal(plan_hp)} hp planerat)" if plan_hp else "")


forval = st.session_state.get("kp_avtal")
if forval not in alla:
    forval = fav[0] if fav else alla[0]
aid = st.selectbox("Avtal", alla, index=alla.index(forval), format_func=etikett,
                   help="Favoriter först. Spara avtal med stjärnan under Sök.")
st.session_state["kp_avtal"] = aid
rad = rad_av.loc[aid]
a = ra[aid]
plan = mina["kursplaner"].get(aid, {"faktor": None, "kurser": []})

# ---------------------------------------------------------------------------------------------
# Poängomräkning
# ---------------------------------------------------------------------------------------------
alternativ: list[tuple[str, float | None]] = []
for o in a.get("omrakningar") or []:
    niva = {"grund": ", grundnivå", "avancerad": ", avancerad nivå"}.get(o["niva"] or "", "")
    alternativ.append((f"{o['text']}{niva} → {ui.tal(o['faktor'], 3)} hp/poäng", o["faktor"]))
alternativ.append(("ECTS (1 poäng = 1 hp)", 1.0))
alternativ.append(("Eget värde", None))
etiketter_omr = [t for t, _ in alternativ]
sparad = plan.get("faktor")
index = 0
if sparad is not None:
    index = next((i for i, (_, f) in enumerate(alternativ) if f is not None and abs(f - sparad) < 1e-6),
                 len(alternativ) - 1)
c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
val = c1.selectbox("Poängomräkning", etiketter_omr, index=index,
                   help="Från avtalets fält \"Credit point conversion\". Välj nivå om värden skiljer sig mellan grund och master.")
faktor = dict(alternativ)[val]
if faktor is None:
    faktor = c2.number_input("hp per poäng", min_value=0.05, max_value=10.0, value=float(sparad or 1.0), step=0.05,
                             format="%.3f")
else:
    c2.metric("hp per poäng", ui.tal(faktor, 3))
if faktor != plan.get("faktor"):
    dd = ui.mina()
    dd["kursplaner"].setdefault(aid, {"faktor": None, "kurser": []})["faktor"] = faktor
    for k in dd["kursplaner"][aid]["kurser"]:
        k["hp"] = round((k.get("poang") or 0) * faktor, 2)
    ui.spara(dd)
    plan = dd["kursplaner"][aid]

# ---------------------------------------------------------------------------------------------
# Termin 8 enligt studieplanen
# ---------------------------------------------------------------------------------------------
version = mina["installningar"].get("studieplan_t8") or "HT2024"
t8: list[dict] = []
if kd:
    versioner = sorted(kd.studieplaner)
    if version not in versioner and versioner:
        version = versioner[0]
    t8 = kursdata.termin_kurser(kd, version, 8, inr, profil)
UU_VAL = ([f"{k['kod']} {k['namn']} ({ui.tal(k['hp'])} hp{', obligatorisk' if k['obligatorisk'] else ''})" for k in t8]
          + ["Valfri kurs inom examen", "Annan UU-kurs (skriv i anteckning)", "Extra (räknas inte in)"])

# ---------------------------------------------------------------------------------------------
# Kurser
# ---------------------------------------------------------------------------------------------
st.subheader(f"Kurser vid {rad['universitet']}")
if a["falt"].get("Kurskatalog"):
    with st.expander("Kurskatalog och ämnesbegränsningar enligt avtalet"):
        st.markdown(a["falt"]["Kurskatalog"]["md"])
        if a["falt"].get("Ämnesbegränsningar"):
            st.markdown("**Ämnesbegränsningar**")
            st.markdown(a["falt"]["Ämnesbegränsningar"]["md"])

kurser = plan.get("kurser", [])
tabell = pd.DataFrame([{
    "Kurs": k.get("namn", ""), "Kod": k.get("kod", ""), "Poäng": k.get("poang"),
    "Nivå": k.get("niva") or None, "Länk": k.get("lank", ""), "Ersätter": k.get("ersatter") or None,
    "Anteckning": k.get("anteckning", ""),
} for k in kurser], columns=["Kurs", "Kod", "Poäng", "Nivå", "Länk", "Ersätter", "Anteckning"])
tabell["Poäng"] = pd.to_numeric(tabell["Poäng"], errors="coerce")

with st.form(f"kp_form_{aid}"):
    redigerad = st.data_editor(
        tabell, num_rows="dynamic", width="stretch", hide_index=True, key=f"kp_tab_{aid}",
        column_config={
            "Kurs": st.column_config.TextColumn(required=True, width="large"),
            "Kod": st.column_config.TextColumn(width="small"),
            "Poäng": st.column_config.NumberColumn(help="Poäng i värduniversitetets system", min_value=0, step=0.5,
                                                   width="small"),
            "Nivå": st.column_config.SelectboxColumn(options=["Grundnivå", "Avancerad nivå"], width="small"),
            "Länk": st.column_config.LinkColumn(help="Länk till kursbeskrivningen (krävs i ansökan)", width="medium"),
            "Ersätter": st.column_config.SelectboxColumn(options=UU_VAL, width="large",
                                                         help="Vilken kurs i termin 8 kursen ska tillgodoräknas mot"),
            "Anteckning": st.column_config.TextColumn(width="medium"),
        },
    )
    if st.form_submit_button("Spara kursplan", icon=":material/save:", type="primary"):
        nya = []
        for _, r in redigerad.iterrows():
            if not str(r["Kurs"] or "").strip():
                continue
            poang = None if pd.isna(r["Poäng"]) else float(r["Poäng"])
            nya.append({"namn": str(r["Kurs"]).strip(), "kod": str(r["Kod"] or "").strip(), "poang": poang,
                        "hp": round((poang or 0) * faktor, 2), "niva": r["Nivå"] if isinstance(r["Nivå"], str) else None,
                        "lank": str(r["Länk"] or "").strip(), "ersatter": r["Ersätter"] if isinstance(r["Ersätter"], str) else None,
                        "anteckning": str(r["Anteckning"] or "").strip()})
        dd = ui.mina()
        dd["kursplaner"].setdefault(aid, {"faktor": faktor, "kurser": []})["kurser"] = nya
        dd["kursplaner"][aid]["faktor"] = faktor
        ui.spara(dd, "Kursplanen sparad")
        st.session_state.pop(f"kp_tab_{aid}", None)
        st.rerun()

summa = sum((k.get("poang") or 0) * faktor for k in kurser if k.get("ersatter") != "Extra (räknas inte in)")
v, h = st.columns([2, 3])
with v:
    st.markdown(f"**{ui.tal(summa)} hp av 30 hp**" + (" ✓" if summa >= 30 else f" – {ui.tal(30 - summa)} hp kvar"))
    st.markdown(ui.meter(summa / 30, full=summa >= 30), unsafe_allow_html=True)
    if rad["erasmus"] or rad["icm"]:
        st.caption("Erasmus: du måste klara minst 22,5 hp under terminen för att behålla stipendiet.")
    avancerad = sum((k.get("poang") or 0) * faktor for k in kurser if k.get("niva") == "Avancerad nivå")
    if kurser:
        st.caption(f"Varav avancerad nivå: {ui.tal(avancerad)} hp.")
with h:
    if t8:
        tackta = {k.get("ersatter") for k in kurser}
        saknas = [k for k, etik in zip(t8, UU_VAL) if k["obligatorisk"] and etik not in tackta]
        if saknas:
            st.warning("Obligatoriska kurser i termin 8 som inte ersätts: "
                       + ", ".join(f"{k['kod']} {k['namn']}" for k in saknas)
                       + ". Läs dem en annan termin eller planera tillgodoräknande med studievägledningen.",
                       icon=":material/warning:")
        else:
            st.success("Alla obligatoriska kurser i termin 8 är täckta (eller så finns inga).", icon=":material/check:")

if kurser:
    rader = [f"- {k['namn']}{' (' + k['kod'] + ')' if k.get('kod') else ''}, {ui.tal(k.get('poang'))} poäng"
             f" = {ui.tal((k.get('poang') or 0) * faktor)} hp{' – ' + k['lank'] if k.get('lank') else ''}" for k in kurser]
    text = f"Kursförslag – {rad['universitet']} ({ui.vag(rad)})\n" + "\n".join(rader)
    st.download_button("Ladda ner kursförslaget (text)", text.encode("utf-8"), file_name="kursforslag.txt",
                       icon=":material/download:", help="Klistra in i MoveON-ansökan.")

# ---------------------------------------------------------------------------------------------
# Termin 8 och tidigare studenter
# ---------------------------------------------------------------------------------------------
st.divider()
v, h = st.columns(2)
with v:
    st.subheader("Termin 8 (VT2028) enligt studieplanen")
    if not kd:
        st.info("Kursappen hittades inte – ange sökvägen under **Meritvärde och urval**.", icon=":material/link_off:")
    else:
        versioner = sorted(kd.studieplaner)
        ny_version = st.segmented_control("Studieplan", versioner, default=version, key="kp_version",
                                          help="Årskurs 4 får följa valfri studieplan mellan din start och examen.")
        if ny_version and ny_version != mina["installningar"].get("studieplan_t8"):
            dd = ui.mina()
            dd["installningar"]["studieplan_t8"] = ny_version
            ui.spara(dd)
            st.rerun()
        if not inr:
            st.info("Välj inriktning i sidomenyn för att se kurserna i termin 8.", icon=":material/tune:")
        elif not t8:
            st.caption("Inga kurser i termin 8 för den inriktningen i den här studieplanen.")
        else:
            st.dataframe(pd.DataFrame([{
                "Kod": k["kod"], "Kurs": k["namn"], "hp": k["hp"], "Period": ", ".join(str(p) for p in k["perioder"]),
                "Obligatorisk": k["obligatorisk"], "Profil": (k["inriktning"] or "").split("profil ")[-1] if k["inriktning"] else "",
            } for k in t8]), hide_index=True, width="stretch",
                column_config={"Obligatorisk": st.column_config.CheckboxColumn(), "hp": st.column_config.NumberColumn(format="%.1f")})
            noter = [n for k in t8 for n in k["noter"]]
            if noter:
                with st.expander("Noter i studieplanen"):
                    for n in dict.fromkeys(noter):
                        st.markdown(f"- {ui.md_escape(n)}")
with h:
    st.subheader("Så gjorde tidigare studenter")
    rapp = [r for r in ui.rapp().get("rapporter", []) if r["core_id"] == rad["core_id"] and r.get("kurser")]
    if not rapp:
        st.caption("Inga rapporter med kursinformation för det här universitetet.")
    rapp = sorted(rapp, key=lambda r: r.get("ar") or "", reverse=True)  # nyast först …
    rapp = sorted(rapp, key=lambda r: r["program_kategori"] != "Teknisk fysik")  # … men teknisk fysik överst
    for r in rapp[:12]:
        falt = r.get("falt", {})
        rubrik = " · ".join(x for x in (r.get("ar"), falt.get("program_uu"), falt.get("niva")) if x)
        with st.expander(rubrik, icon=":material/star:" if r["program_kategori"] == "Teknisk fysik" else ":material/description:"):
            st.markdown(ui.md_escape(r["kurser"]))
            st.markdown(f"[Hela rapporten (PDF)](app/{r['pdf']})")
