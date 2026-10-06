import streamlit as st

from utbytesapp import amnen, modell, omgangar, ui

d = ui.krav_data()
df = ui.tabell()
mina = ui.mina()
alla = modell.per_universitet(df).sort_values("universitet")
etiketter = {r["core_id"]: f"{r['flagga']} {r['universitet']} ({r['land']})" for _, r in alla.iterrows()}

st.title("Jämför universitet")
favoriter = list(dict.fromkeys(df[df["favorit"]]["core_id"]))
if "j_valda" not in st.session_state:
    st.session_state["j_valda"] = favoriter[:4]
valda = st.multiselect("Välj upp till fyra universitet", list(etiketter), key="j_valda", max_selections=4,
                       format_func=etiketter.get, placeholder="Sök universitet …",
                       help="Förvalt: universitet bland dina favoriter.")
if not valda:
    st.info("Välj universitet ovan – dina favoriter förväljs automatiskt.", icon=":material/compare_arrows:")
    st.stop()

ra = {a["id"]: a for a in d["avtal"]}
varlista = modell.senaste_varlista(d)


def lista(rader: list[str]) -> str:
    return "<br>".join(rader) if rader else "–"


def kolumn(core: str) -> dict[str, str]:
    u = d["universitet"][core]
    av = df[df["core_id"] == core]
    f = av.iloc[0]
    sprak = list(dict.fromkeys(s for l in av["sprak"] for s in l))
    bekr = any(s in ("databasen", "egen", "samma_universitet") for s in av["sprak_status"])
    krav = []
    for _, r in av.iterrows():
        sk = ra[r["id"]]["sprakkrav"]
        delar = [x for x in (sk["niva"], ", ".join(sk["test"]) if sk["test"] else None) if x]
        if delar or sk["test_kravs"] is not None:
            krav.append(" · ".join(delar + [{True: "test krävs", False: "inget test", None: "test kan krävas"}[sk["test_kravs"]]]))
    omr = []
    for _, r in av.iterrows():
        for o in ra[r["id"]].get("omrakningar") or []:
            t = f"1 poäng = {ui.tal(o['faktor'], 2)} hp" + ({"grund": " (grund)", "avancerad": " (avancerad)"}.get(o["niva"] or "", ""))
            if t not in omr:
                omr.append(t)
    plan_hp = [sum(k.get("hp") or 0 for k in mina["kursplaner"].get(i, {}).get("kurser", [])) for i in av["id"]]
    status = [f"{ui.e(r['enhet_kort'])}: {ui.e(mina['favoriter'][r['id']]['status'])}" for _, r in av.iterrows()
              if r["id"] in mina["favoriter"]]
    lankar = [f'<a href="{ui.e(url)}" target="_blank">{t}</a>' for t, url in
              (("Webbplats", u.get("webb")), ("Internationellt", u.get("webb_int")), ("Kurskatalog", u.get("kurskatalog")))
              if url]
    return {
        "Ort": ui.e(f"{u.get('stad') or '–'}, {f['land']} ({f['region']})"),
        "Avstånd från Uppsala": ui.km(f["avstand_km"]),
        "Avtal": lista([ui.e(("Centralt · " if r["kanal"] == "central" else "TekNat · ") + r["enhet_kort"] + " · " + r["typ"])
                        for _, r in av.iterrows()]),
        "Sök för VT2028": lista(sorted({ui.e(o.namn + ": " + o.kort_datum()) for k in av["kanal"] for o in omgangar.omgangar_for(k)})),
        "Senaste vårlistan": lista([f"{ui.heltal(r['platser_var'])} platser" if not ui.ar_nan(r["platser_var"]) else "fanns med"
                                    for _, r in av.iterrows() if r["pa_varlista"]]) if av["pa_varlista"].any()
        else ("finns inte med" if (av["kanal"] == "central").any() else "gäller inte (TekNat)"),
        "Ämnen": ui.e(", ".join(dict.fromkeys(a for l in av["amnen"] for a in l)) or
                      (amnen.ALLA if any(amnen.ALLA in k for k in av["kategorier"]) else "–")),
        "Ämnesmatchning": amnen.MATCH_TEXT[int(av["match"].max())],
        "Kurser du kan läsa": lista([ui.e(ui.vag(r) + ": " + " · ".join(
            f"{ui.KT_KORT[o]} {ui.KT_SYMBOL[r[f'kt_{o}']]}" for o in ("teknik", "fysik", "matematik", "data")))
            for _, r in av.iterrows()]),
        "Nivå": ui.e(", ".join(modell.NIVA_TEXT[n] for n in dict.fromkeys(n for l in av["nivaer"] for n in l)) or "–"),
        "Civ.ing.-avtal": "Ja" if av["civilingenjor"].any() else "Nej",
        "Undervisningsspråk": ui.e(modell.sprak_visning(sprak, "databasen" if bekr else "obekraftad",
                                                         bool(av["sprak_engelska_master"].any()))
                                   + ("" if bekr else " (obekräftat)")),
        "Språkkrav": lista([ui.e(k) for k in dict.fromkeys(krav)]),
        "Vårtermin hos värden": ui.e(modell.vartermin_visning(f["var_start"], f["var_slut"], f["var_status"])),
        "Villkor för våren": lista([ui.e(v) for v in dict.fromkeys(av["varvarning"]) if v]
                                   + (["Bara helårsutbyte"] if av["bara_helar"].any() else [])),
        "Poängomräkning": lista([ui.e(o) for o in omr]) if omr else ("ECTS (1:1)" if av["erasmus"].any() else "–"),
        "Stipendium": (f"Erasmus {ui.heltal(av['erasmus_euro'].dropna().max())} €/mån" if av["erasmus_euro"].notna().any()
                       else "Erasmus ICM" if av["icm"].any() else "–"),
        "Utbytesrapporter": f"{int(av['antal_rapporter'].sum())} ({int(av['ttf_rapporter'].sum())} från TTF)",
        "Din status": lista(status) if status else "–",
        "Din kursplan": lista([f"{ui.tal(h)} hp" for h in plan_hp if h]) if any(plan_hp) else "–",
        "Länkar": " · ".join(lankar) or "–",
    }


kolumner = {core: kolumn(core) for core in valda}
rubriker = "".join(f'<th>{ui.e(d["universitet"][c]["namn"])}</th>' for c in valda)
rader = []
for falt in next(iter(kolumner.values())):
    celler = "".join(f"<td>{kolumner[c][falt]}</td>" for c in valda)
    rader.append(f'<tr><th scope="row">{ui.e(falt)}</th>{celler}</tr>')
st.markdown(f"""<style>
.ut-jamfor {{ width:100%; border-collapse:collapse; font-size:0.9rem; }}
.ut-jamfor th, .ut-jamfor td {{ border-top:1px solid var(--ut-grid); padding:8px 10px; text-align:left; vertical-align:top; }}
.ut-jamfor thead th {{ font-size:1rem; border-top:none; }}
.ut-jamfor tbody th {{ color:var(--ut-ink2); font-weight:500; width:170px; }}
</style><div style="overflow-x:auto"><table class="ut-jamfor"><thead><tr><th></th>{rubriker}</tr></thead>
<tbody>{''.join(rader)}</tbody></table></div>""", unsafe_allow_html=True)

st.caption("Obekräftat språk = landets språk; engelska finns oftast på masternivå. Kontrollera i kurskatalogen.")
c = st.columns(len(valda))
for kol, core in zip(c, valda):
    if kol.button(f"Öppna {d['universitet'][core]['namn'][:30]}", key=f"j_oppna_{core}", icon=":material/open_in_new:",
                  width="stretch"):
        ui.oppna_universitet(core)
        st.switch_page("sidor/universitet.py")
