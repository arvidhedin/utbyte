import datetime as dt

import plotly.graph_objects as go
import streamlit as st

from utbytesapp import amnen, bygg, geo, kurstyper, lagring, modell, omgangar, tolka, ui

d = ui.krav_data()
df = ui.tabell()
alla = modell.per_universitet(df).sort_values("universitet")
ordning = list(alla["core_id"])
etiketter = {r["core_id"]: f"{r['flagga']} {r['universitet']} – {r['stad'] + ', ' if r['stad'] else ''}{r['land']}"
             for _, r in alla.iterrows()}

vald = st.session_state.get("vald_uni") or st.query_params.get("uni")
if vald not in etiketter:
    vald = ordning[0]
core = st.selectbox("Universitet", ordning, index=ordning.index(vald), format_func=etiketter.get,
                    label_visibility="collapsed")
if core != st.session_state.get("vald_uni"):
    st.session_state["vald_uni"] = core
st.query_params["uni"] = core

u = d["universitet"][core]
land = geo.land(u["land_kod"])
avtal = df[df["core_id"] == core]
ra = {a["id"]: a for a in d["avtal"] if a["core_id"] == core}
varlista = modell.senaste_varlista(d)
hostlista = modell.senaste_hostlista(d)
mina = ui.mina()

st.title(f"{land.flagga} {u['namn']}")
under = [x for x in (u.get("namn_en") if u.get("namn_en") != u["namn"] else None, u.get("stad"), land.namn,
                     land.region, f"{ui.km(geo.avstand_km(u.get('lat'), u.get('lon')))} från Uppsala") if x]
st.caption(" · ".join(under))
lankar = [("Webbplats", u.get("webb")), ("För internationella studenter", u.get("webb_int")),
          ("Kurskatalog", u.get("kurskatalog"))]
lanktext = " · ".join(f"[{t}]({url})" for t, url in lankar if url)
if lanktext:
    st.markdown(":material/link: " + lanktext)

# Nyckeltal
f = avtal.iloc[0]
sprak = list(dict.fromkeys(s for l in avtal["sprak"] for s in l))
bekr = any(s in ("databasen", "egen", "samma_universitet") for s in avtal["sprak_status"])
eur = avtal["erasmus_euro"].dropna()
antal_r = int(avtal["antal_rapporter"].sum())
ttf_r = int(avtal["ttf_rapporter"].sum())
ui.faktarutor([
    ("Avtal hit", str(len(avtal)), None),
    ("Undervisningsspråk", modell.sprak_visning(sprak, "databasen" if bekr else "obekraftad",
                                                bool(avtal["sprak_engelska_master"].any())) + ("" if bekr else " (obekräftat)"),
     None if bekr else "Uppskattat utifrån landet. Engelska finns oftast på masternivå."),
    ("Vårtermin hos värden", modell.vartermin_visning(f["var_start"], f["var_slut"], f["var_status"]), None),
    ("Stipendium", f"{ui.heltal(eur.max())} €/mån (Erasmus)" if len(eur) else ("Erasmus ICM" if avtal["icm"].any() else "Inget"),
     "Erasmusstipendiet per månad enligt UU:s nivåer."),
    ("Utbytesrapporter", f"{antal_r}" + (f" ({ttf_r} från teknisk fysik)" if ttf_r else ""), None),
])

# ---------------------------------------------------------------------------------------------
# Ett avtal per flik
# ---------------------------------------------------------------------------------------------


def fliknamn(rad) -> str:
    if rad["kanal"] == "central":
        return f"Centralt · {rad['typ']}" + (f" · {rad.get('delnamn')}" if rad.get("delnamn") else "")
    return ui.vag(rad)


def spara_status(avtal_id: str) -> None:
    dd = ui.mina()
    if avtal_id in dd["favoriter"]:
        dd["favoriter"][avtal_id]["status"] = st.session_state[f"st_{avtal_id}"]
        dd["favoriter"][avtal_id]["anteckning"] = st.session_state.get(f"an_{avtal_id}", "")
        ui.spara(dd)


def falt_md(a: dict, etikett: str) -> str:
    return a["falt"].get(etikett, {}).get("md", "")


flikar = st.tabs([fliknamn(r) for _, r in avtal.iterrows()])
for flik, (_, rad) in zip(flikar, avtal.iterrows()):
    a = ra[rad["id"]]
    with flik:
        v, h = st.columns([5, 2], vertical_alignment="top")
        with v:
            st.markdown(ui.avtalsmarken(rad))
            st.caption(f"Avtal i databasen: *{ui.md_escape(a['avtalsnamn'])}* · [öppna i UU:s avtalsdatabas]({a['url']})")
        with h:
            fav = bool(rad["favorit"])
            st.button("Ta bort ur Mina val" if fav else "Spara i Mina val", key=f"ufav_{rad['id']}",
                      icon=":material/star:" if fav else ":material/star_border:", on_click=ui.vaxla_favorit,
                      args=(rad["id"],), type="secondary" if fav else "primary", width="stretch")
            if fav:
                post = mina["favoriter"][rad["id"]]
                st.selectbox("Status", lagring.STATUSAR, index=lagring.STATUSAR.index(post.get("status", lagring.STATUSAR[0]))
                             if post.get("status") in lagring.STATUSAR else 0, key=f"st_{rad['id']}",
                             on_change=spara_status, args=(rad["id"],))
                st.text_area("Anteckning", value=post.get("anteckning", ""), key=f"an_{rad['id']}",
                             on_change=spara_status, args=(rad["id"],), height=80)

        # Så söker du
        with st.container(border=True):
            st.markdown("##### :material/how_to_reg: Så söker du för VT2028")
            idag = dt.date.today()
            for o in omgangar.omgangar_for(rad["kanal"]):
                status = o.status(idag)
                ikon = {"öppen": ":green[:material/radio_button_checked:]", "kommande": ":material/schedule:",
                        "stängd": ":gray[:material/block:]"}[status]
                st.markdown(f"{ikon} **{o.namn}**: {o.kort_datum()} – {o.galler.lower()}. "
                            f":small[[instruktioner]({o.url})]")
            st.markdown(f"**Samordnas av:** {rad['enhet_sv']} – [{rad['kontakt']}](mailto:{rad['kontakt']})")
            if rad["kanal"] == "central":
                rader_pl = []
                for mal, info in sorted(a["platser"].items(), key=lambda x: (x[0][2:], x[0][:2])):
                    meta = d["platslistor"].get(mal, {})
                    rader_pl.append(f"{meta.get('omgang', mal)} (för {mal}): "
                                    + (f"**{info['platser']} platser**" if info.get("platser") else "fanns med")
                                    + (f", {info['stipendium']}" if info.get("stipendium") else ""))
                if rader_pl:
                    st.markdown("**På UU:s listor:** " + " · ".join(rader_pl))
                else:
                    st.markdown(f"**På UU:s listor:** fanns inte med på listorna för "
                                f"{', '.join(sorted(d['platslistor']))}. Bara universitet på vårlistan som "
                                f"publiceras 15 april 2027 kan väljas för VT2028.")
            sida = a.get("teknatsida") or {}
            if sida.get("ovrigt"):
                st.markdown(f"**Enligt TekNats avtalssida:** {ui.md_escape(sida['ovrigt'])}")
            if sida.get("restplatser"):
                st.markdown(f"**Restplatser:** {ui.md_escape(sida['restplatser'])}")
            if a.get("varvarning"):
                st.warning(f"Villkor som rör vårterminen: *{ui.md_escape(a['varvarning'])}*", icon=":material/warning:")
            sista = falt_md(a, "Sista ansökningsdag vid UU")
            if sista:
                st.markdown(f"**Sista ansökningsdag enligt avtalet:** {sista}")
            vard = falt_md(a, "Ansökningsdatum hos värduniversitetet")
            if vard:
                st.markdown(f"**Ansökan hos värduniversitetet:** {vard}")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### :material/category: Ämnen och nivå")
            if a["isced"]:
                st.markdown(" ".join(ui.badge(f"{i['kod']} {i['namn']}", "gray") for i in a["isced"]))
            elif amnen.ALLA in a["kategorier"]:
                st.markdown(ui.badge("Alla ämnen (universitetsövergripande)", "gray"))
            st.markdown("**Nivå:** " + (", ".join(modell.NIVA_TEXT[n] for n in a["nivaer"]) or "ej angiven")
                        + (" · **Program:** " + a["examensprogram"] if a.get("examensprogram") else ""))
            st.markdown(f"**Ämnesmatchning mot din inriktning:** {amnen.MATCH_TEXT[int(rad['match'])]}")
            kt = a.get("kurstyper") or {}
            KT_FARG = {"öppet": "green", "begränsat": "orange", "stängt": "red", "oklart": "gray"}
            st.markdown("**Kurser du kan läsa:** " + " ".join(
                ui.badge(f"{kurstyper.OMRADE_NAMN[o]}: {kt.get(o, 'oklart')}", KT_FARG[kt.get(o, "oklart")])
                for o in kurstyper.OMRADEN))
            kalltext = {"tolkad": f"Tolkning av ämnesbegränsningen ({kurstyper.TOLKAD}).",
                        "härledd": "Härlett ur avtalets ämnesområden.",
                        "otolkad": "Nytt avtal – inte tolkat än."}.get(kt.get("kalla"), "")
            st.caption(" ".join(x for x in (kt.get("not"), kalltext) if x))
            if kt.get("andrad"):
                st.warning("UU har ändrat ämnesbegränsningen sedan tolkningen gjordes – läs texten nedan.",
                           icon=":material/update:")
            if kt.get("helar"):
                st.error("Det här avtalet tar bara emot helårsutbyten – det fungerar inte för enbart VT2028.",
                         icon=":material/block:")
            begr = falt_md(a, "Ämnesbegränsningar")
            if begr:
                with st.expander("Ämnesbegränsningar", expanded=True):
                    st.markdown(begr)
            kat = falt_md(a, "Kurskatalog")
            if kat:
                with st.expander("Kurskatalog"):
                    st.markdown(kat)

            st.markdown("##### :material/calculate: Poäng")
            omr = a.get("omrakningar") or []
            if omr:
                for o in omr:
                    niva = {"grund": " (grundnivå)", "avancerad": " (avancerad nivå)"}.get(o["niva"] or "", "")
                    st.markdown(f"1 poäng hos värden = **{ui.tal(o['faktor'], 2)} hp**{niva} – *{ui.md_escape(o['text'])}*")
            elif rad["erasmus"]:
                st.markdown("ECTS: 1 poäng = 1 hp (Erasmus).")
            else:
                st.markdown("Ingen omräkning angiven i databasen.")
        with c2:
            st.markdown("##### :material/translate: Språk")
            st.markdown(ui.sprakmarke(rad["sprak"], rad["sprak_status"], rad["sprak_engelska_master"])
                        + f"  \n:small[{modell.SPRAK_STATUS_TEXT[rad['sprak_status']]}]")
            if a["sprak"]["status"] == "samma_universitet" and a["sprak"].get("fran") in ra:
                st.caption(f"Hämtat från avtalet {fliknamn(avtal[avtal['id'] == a['sprak']['fran']].iloc[0])}.")
            sp = falt_md(a, "Undervisningsspråk")
            if sp:
                st.markdown(sp)
            krav = falt_md(a, "Språkkrav")
            if krav:
                sk = a["sprakkrav"]
                sammanfattning = []
                if sk["niva"]:
                    sammanfattning.append(f"nivå {sk['niva']}")
                if sk["test"]:
                    sammanfattning.append("test: " + ", ".join(sk["test"]))
                sammanfattning.append({True: "test krävs", False: "inget test krävs", None: "test kan krävas"}[sk["test_kravs"]])
                st.markdown(f"**Språkkrav** ({', '.join(sammanfattning)}):")
                st.markdown(krav)
            st.markdown("##### :material/date_range: Termin")
            st.markdown(f"**Vårtermin hos värden:** {modell.vartermin_visning(rad['var_start'], rad['var_slut'], rad['var_status'])}")
            if not ui.ar_nan(rad["var_slut"]) and rad["var_slut"] >= 8:
                st.caption("Slutar sent – kan krocka med HT2028 i Uppsala (start i slutet av augusti).")
            term = falt_md(a, "Terminsdatum")
            if term:
                st.markdown(term)
            st.markdown("##### :material/payments: Pengar")
            if a.get("erasmus_stipendium"):
                es = a["erasmus_stipendium"]
                st.markdown(f"Erasmusstipendium grupp {es['grupp']}: **{es['euro_per_manad']} €/månad** "
                            f"(ansök 1–15 nov 2027). Lägsta krav: 22,5 hp per termin.")
            elif rad["icm"]:
                st.markdown("Erasmus ICM-stipendium (belopp enligt UU:s ICM-sida).")
            else:
                st.markdown("Inget Erasmusstipendium. Inga studieavgifter (utbytesavtal); CSN gäller som vanligt.")
            for etikett in ("Avgifter", "Stipendier", "Försäkring", "Visum och uppehållstillstånd"):
                if falt_md(a, etikett):
                    with st.expander(etikett):
                        st.markdown(falt_md(a, etikett))

        ovriga = [e_ for e_ in bygg.FALTORDNING if e_ in a["falt"] and e_ not in (
            "Ämnesbegränsningar", "Kurskatalog", "Undervisningsspråk", "Språkkrav", "Terminsdatum", "Avgifter",
            "Stipendier", "Försäkring", "Visum och uppehållstillstånd", "Sista ansökningsdag vid UU",
            "Ansökningsdatum hos värduniversitetet", "Poängomräkning")]
        if ovriga:
            with st.expander(f"Övrigt i avtalsdatabasen ({', '.join(ovriga).lower()})"):
                for etikett in ovriga:
                    st.markdown(f"**{etikett}**")
                    st.markdown(a["falt"][etikett]["md"])
        if st.button("Planera kurser för det här avtalet", key=f"kp_{rad['id']}", icon=":material/menu_book:"):
            st.session_state["kp_avtal"] = rad["id"]
            st.switch_page("sidor/kursplan.py")

# ---------------------------------------------------------------------------------------------
# Egna uppgifter, rapporter och karta
# ---------------------------------------------------------------------------------------------

st.divider()
v, h = st.columns([3, 2])
with v:
    st.subheader("Utbytesrapporter")
    rapp = [r for r in ui.rapp().get("rapporter", []) if r["core_id"] == core]
    if not rapp:
        antal = sum(len(ra[i]["rapporter"]) for i in ra)
        st.caption("Inga rapporter." if not antal else
                   f"{antal} {'rapport finns' if antal == 1 else 'rapporter finns'} i databasen men är inte "
                   "nedladdade än – se **Data och uppdatering**.")
    rapp = sorted(sorted(rapp, key=lambda r: r.get("ar") or "", reverse=True),
                  key=lambda r: r["program_kategori"] != "Teknisk fysik")
    for r in rapp:
        falt = r.get("falt", {})
        rubrik = " · ".join(x for x in (r.get("ar"), r.get("termin"), falt.get("program_uu"), falt.get("niva"),
                                         falt.get("amne")) if x)
        ikon = ":material/star:" if r["program_kategori"] == "Teknisk fysik" else ":material/description:"
        with st.expander(rubrik or r["id"], icon=ikon):
            st.markdown(f"[Öppna PDF](app/{r['pdf']}) · {ui.md_escape(r.get('namn') or '')}")
            if r.get("kurser"):
                st.markdown("**Om kurserna och tillgodoräknande**")
                st.markdown(ui.md_escape(r["kurser"]))
            for avs in r["avsnitt"]:
                if avs["rubrik"].lower() in ("basic information", "data handling", "submit report", "photos", "studies"):
                    continue
                svar = [p for p in avs["poster"] if p["svar"] and len(p["svar"]) > 3]
                if svar:
                    st.markdown(f"**{ui.md_escape(avs['rubrik'])}**")
                    for p in svar:
                        st.markdown(ui.md_escape(p["svar"]))
with h:
    st.subheader("Egna uppgifter")
    eget = mina["egna_uppgifter"].get(core, {})
    alla_sprak = [s for s, _ in tolka.SPRAK_MONSTER]
    with st.form(f"eget_{core}"):
        nya_sprak = st.multiselect("Undervisningsspråk (ersätter databasen/uppskattningen)", alla_sprak,
                                   default=[s for s in eget.get("sprak", []) if s in alla_sprak],
                                   format_func=str.capitalize, placeholder="Välj språk")
        kalla = st.text_input("Källa (t.ex. länk till kurskatalogen)", value=eget.get("sprak_kalla", ""))
        anteckning = st.text_area("Anteckningar om universitetet", value=eget.get("anteckning", ""), height=100)
        if st.form_submit_button("Spara", icon=":material/save:"):
            dd = ui.mina()
            if nya_sprak or kalla or anteckning:
                dd["egna_uppgifter"][core] = {"sprak": nya_sprak, "sprak_kalla": kalla, "anteckning": anteckning}
            else:
                dd["egna_uppgifter"].pop(core, None)
            ui.spara(dd, "Sparat")
            st.rerun()

    if u.get("lat") is not None:
        fig = go.Figure()
        fig.add_trace(go.Scattergeo(lat=[geo.UPPSALA[0], u["lat"]], lon=[geo.UPPSALA[1], u["lon"]], mode="lines",
                                    line=dict(width=1.5, color=ui.GRA, dash="dot"), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scattergeo(lat=[geo.UPPSALA[0]], lon=[geo.UPPSALA[1]], mode="markers+text", text=["Uppsala"],
                                    textposition="top center", marker=dict(size=7, color=ui.GRA), showlegend=False,
                                    hoverinfo="skip"))
        fig.add_trace(go.Scattergeo(lat=[u["lat"]], lon=[u["lon"]], mode="markers+text", text=[u.get("stad") or u["namn"]],
                                    textposition="top center", marker=dict(size=11, color=ui.KANALFARG["teknat"]),
                                    showlegend=False, hoverinfo="skip"))
        fig.update_geos(projection_type="natural earth", showcountries=True, countrycolor="rgba(137,135,129,0.5)",
                        showland=True, landcolor="rgba(137,135,129,0.12)", showocean=False, bgcolor="rgba(0,0,0,0)",
                        fitbounds="locations", showframe=False, coastlinecolor="rgba(137,135,129,0.6)")
        ui.visa_plotly(ui.plotly_layout(fig, hojd=260))
