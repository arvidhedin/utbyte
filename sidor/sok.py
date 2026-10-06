import json

import pandas as pd
import streamlit as st

from utbytesapp import modell, ui

d = ui.krav_data()
df = ui.tabell()
varlista = modell.senaste_varlista(d)
f = ui.filterpanel(df, varlista)
traffar = ui.filtrera(df, f, ui.sokbar())
uni = modell.per_universitet(traffar)

st.title("Sök utbytesuniversitet")
st.caption("Varje kort är ett universitet. Under namnet står alla avtal (vägar) dit: vilken kanal, vem som "
           "samordnar och när du söker för VT2028. Stjärnan sparar avtalet i **Mina val**.")

if uni.empty:
    st.info("Inga universitet matchar filtren.", icon=":material/search_off:")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Universitet", len(uni), border=True)
k2.metric("Avtal", len(traffar), border=True)
k3.metric("Länder", traffar["land"].nunique(), border=True)
k4.metric("TekNat / centralt", f"{(traffar['kanal'] == 'teknat').sum()} / {(traffar['kanal'] == 'central').sum()}",
          border=True)

c1, c2, c3 = st.columns([2, 2, 3], vertical_alignment="bottom")
sortering = c1.selectbox("Sortera efter", list(ui.SORTERING), key="s_sort")
vy = c2.segmented_control("Visa som", ["Kort", "Tabell"], default="Kort", key="s_vy") or "Kort"
kol, stigande = ui.SORTERING[sortering]
uni = uni.sort_values([kol, "universitet"], ascending=[stigande, True], na_position="last")

with c3:
    export = traffar.drop(columns=["lat", "lon", "omgangar"]).copy()
    for kolumn in ("kategorier", "amnen", "nivaer", "sprak", "sprakkrav_test"):
        export[kolumn] = export[kolumn].map(lambda v: ", ".join(v) if isinstance(v, list) else v)
    st.download_button("Ladda ner urvalet (CSV)", export.to_csv(index=False).encode("utf-8-sig"),
                       file_name="utbytesavtal.csv", mime="text/csv", icon=":material/download:")

if vy == "Tabell":
    tab = pd.DataFrame({
        "⭐": uni["favorit"],
        "Universitet": uni["flagga"] + " " + uni["universitet"],
        "Ort": uni["stad"],
        "Land": uni["land"],
        "Världsdel": uni["varldsdel"],
        "Kanal": uni["kanaler"].map(lambda k: " + ".join(modell.KANAL_TEXT[x] for x in k)),
        "Samordnas av": uni["enheter"].map(", ".join),
        "Språk": [modell.sprak_visning(s, "databasen" if b else "obekraftad") + ("" if b else " ?")
                  for s, b in zip(uni["sprak"], uni["sprak_bekraftat"])],
        "Ämnesmatch": uni["match"],
        "Kurser": [" · ".join(f"{ui.KT_KORT[o]} {ui.KT_SYMBOL[bast]}" for o, bast in kt.items())
                   for kt in uni["kurstyper"]],
        "Platser vårlistan": uni["platser_var"],
        "Erasmus €/mån": uni["erasmus_euro"],
        "Rapporter": uni["antal_rapporter"],
        "TTF-rapporter": uni["ttf_rapporter"],
        "Avstånd (km)": uni["avstand_km"].round(-1),
    })
    val = st.dataframe(
        tab, hide_index=True, width="stretch", height=min(38 * len(tab) + 40, 700),
        on_select="rerun", selection_mode="single-row", key="s_tabell",
        column_config={
            "⭐": st.column_config.CheckboxColumn(width="small"),
            "Ämnesmatch": st.column_config.ProgressColumn(min_value=0, max_value=3, format="%d av 3", width="small"),
            "Platser vårlistan": st.column_config.NumberColumn(format="%d"),
            "Erasmus €/mån": st.column_config.NumberColumn(format="%d €"),
            "Avstånd (km)": st.column_config.NumberColumn(format="%d"),
            "Språk": st.column_config.TextColumn(help="? = obekräftat (landets språk)"),
        },
    )
    rader = val.selection.rows if val and val.selection else []
    if rader:
        u = uni.iloc[rader[0]]
        st.markdown(f"#### {u['flagga']} {ui.md_escape(u['universitet'])}")
        ui.universitetskort(u, traffar[traffar["core_id"] == u["core_id"]], varlista, nyckel="t_")
    else:
        st.caption("Markera en rad för att se avtalen och spara favoriter.")
else:
    PER_SIDA = 12
    nyckel = json.dumps({k: v for k, v in f.items()}, sort_keys=True, default=str) + sortering
    if st.session_state.get("s_filternyckel") != nyckel:
        st.session_state["s_filternyckel"] = nyckel
        st.session_state["s_sida"] = 1
    antal_sidor = max(1, -(-len(uni) // PER_SIDA))
    sida = min(st.session_state.get("s_sida", 1), antal_sidor)
    visas = uni.iloc[(sida - 1) * PER_SIDA: sida * PER_SIDA]
    for _, u in visas.iterrows():
        ui.universitetskort(u, traffar[traffar["core_id"] == u["core_id"]], varlista)
    if antal_sidor > 1:
        v, m, h = st.columns([1, 2, 1], vertical_alignment="center")
        if v.button("Föregående", disabled=sida <= 1, icon=":material/chevron_left:", width="stretch"):
            st.session_state["s_sida"] = sida - 1
            st.rerun()
        m.markdown(f"<div style='text-align:center'>Sida {sida} av {antal_sidor} · "
                   f"{len(uni)} universitet</div>", unsafe_allow_html=True)
        if h.button("Nästa", disabled=sida >= antal_sidor, icon=":material/chevron_right:", width="stretch"):
            st.session_state["s_sida"] = sida + 1
            st.rerun()
