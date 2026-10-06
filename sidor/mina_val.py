import datetime as dt

import pandas as pd
import streamlit as st

from utbytesapp import lagring, modell, omgangar, ui

d = ui.krav_data()
df = ui.tabell()
mina = ui.mina()
fav = mina["favoriter"]
varlista = modell.senaste_varlista(d)

st.title("Mina val")
st.caption("Dina sparade avtal, rangordnade per ansökningsomgång. I varje omgång får du ange upp till fyra val i "
           "prioritetsordning. Allt sparas lokalt i `data/mina_val.json`.")

if not fav:
    st.info("Du har inga favoriter än. Klicka på stjärnan vid ett avtal under **Sök** eller på ett universitet.",
            icon=":material/star_border:")
    st.page_link("sidor/sok.py", label="Till Sök", icon=":material/search:")
    st.stop()

favdf = df[df["id"].isin(fav)].copy()
favdf["tillagd"] = favdf["id"].map(lambda i: fav[i].get("tillagd", ""))
favdf = favdf.sort_values(["tillagd", "universitet"])

# Statusöversikt
per_status = favdf["status"].value_counts()
st.markdown(" ".join(ui.badge(f"{s}: {per_status.get(s, 0)}", "blue" if per_status.get(s, 0) else "gray")
                     for s in lagring.STATUSAR))


def spara_tabell(omgang_id: str, nyckel: str, ids: list[str]) -> None:
    andringar = st.session_state[nyckel]["edited_rows"]
    dd = ui.mina()
    rang = {i: pos + 1 for pos, i in enumerate(dd["rangordning"].get(omgang_id, []))}
    for rad_nr, falt in andringar.items():
        aid = ids[int(rad_nr)]
        if aid not in dd["favoriter"]:
            continue
        if "Rang" in falt:
            rang.pop(aid, None)
            if falt["Rang"] and str(falt["Rang"]).isdigit():
                ny = int(falt["Rang"])
                for annan, r in list(rang.items()):  # den som hade rangen flyttas undan
                    if r == ny:
                        rang.pop(annan)
                rang[aid] = ny
        if "Status" in falt and falt["Status"]:
            dd["favoriter"][aid]["status"] = falt["Status"]
        if "Anteckning" in falt:
            dd["favoriter"][aid]["anteckning"] = falt["Anteckning"] or ""
    dd["rangordning"][omgang_id] = [i for i, _ in sorted(rang.items(), key=lambda x: x[1])][:4]
    ui.spara(dd, "Sparat")


idag = dt.date.today()
for o in omgangar.OMGANGAR:
    kandidater = favdf[favdf["kanal"] == o.kanal]
    st.subheader(f"{o.namn}")
    status = o.status(idag)
    st.caption(f"{o.kort_datum()} · {o.galler} · "
               + {"kommande": f"öppnar om {omgangar.dagar_kvar(o.start)} dagar",
                  "öppen": f"**öppen – {omgangar.dagar_kvar(o.slut)} dagar kvar**", "stängd": "stängd"}[status])
    if kandidater.empty:
        st.caption("Inga favoriter i den här kanalen ännu.")
        continue
    rangordning = [i for i in mina["rangordning"].get(o.id, []) if i in fav]
    ids = list(kandidater["id"])
    tabell = pd.DataFrame({
        "Rang": [str(rangordning.index(i) + 1) if i in rangordning else "–" for i in ids],
        "Universitet": (kandidater["flagga"] + " " + kandidater["universitet"]).tolist(),
        "Avtal": [ui.vag(r) for _, r in kandidater.iterrows()],
        "Land": kandidater["land"].tolist(),
        "Språk": [modell.sprak_visning(r["sprak"], r["sprak_status"], r["sprak_engelska_master"]) for _, r in kandidater.iterrows()],
        "Status": [fav[i].get("status", lagring.STATUSAR[0]) for i in ids],
        "Anteckning": [fav[i].get("anteckning", "") for i in ids],
    })
    nyckel = f"mv_{o.id}"
    st.data_editor(
        tabell, key=nyckel, hide_index=True, width="stretch",
        column_config={
            "Rang": st.column_config.SelectboxColumn(options=["–", "1", "2", "3", "4"], width="small", required=True,
                                                     help="1 = förstahandsval. Max fyra per omgång. – = inte med."),
            "Status": st.column_config.SelectboxColumn(options=lagring.STATUSAR, width="medium"),
            "Anteckning": st.column_config.TextColumn(width="large"),
        },
        disabled=["Universitet", "Avtal", "Land", "Språk"],
        on_change=spara_tabell, args=(o.id, nyckel, ids),
    )
    if rangordning:
        rader = []
        for pos, aid in enumerate(rangordning, 1):
            r = df[df["id"] == aid].iloc[0]
            varningar = []
            if o.bara_lista and not r["pa_varlista"]:
                varningar.append(f"fanns inte på senaste vårlistan ({varlista})" if varlista else "ingen vårlista ännu")
            if r["stangt"]:
                varningar.append(r["stangt"])
            if r["varvarning"]:
                varningar.append("villkor för vårterminen")
            if r["sprak_status"] == "obekraftad":
                varningar.append("språk obekräftat")
            hp_plan = sum(k.get("hp") or 0 for k in mina["kursplaner"].get(aid, {}).get("kurser", []))
            rader.append(f"**{pos}.** {r['flagga']} {ui.md_escape(r['universitet'])} – {ui.vag(r)}"
                         + (f" · kursplan {ui.tal(hp_plan)} hp" if hp_plan else " · ingen kursplan än")
                         + (" · :orange[" + "; ".join(varningar) + "]" if varningar else ""))
        st.markdown("  \n".join(rader))
    elif status != "stängd":
        st.caption("Välj rang 1–4 i tabellen för att bygga din ansökan.")

st.divider()
st.subheader("Exportera")
export = favdf[["universitet", "stad", "land", "kanal_text", "enhet_sv", "typ", "kontakt", "url"]].copy()
export["sprak"] = favdf.apply(lambda r: modell.sprak_visning(r["sprak"], r["sprak_status"]), axis=1)
export["status"] = favdf["id"].map(lambda i: fav[i].get("status"))
export["anteckning"] = favdf["id"].map(lambda i: fav[i].get("anteckning"))
for o in omgangar.OMGANGAR:
    lista = mina["rangordning"].get(o.id, [])
    export[f"rang_{o.id}"] = favdf["id"].map(lambda i: lista.index(i) + 1 if i in lista else None)
st.download_button("Ladda ner Mina val (CSV)", export.to_csv(index=False).encode("utf-8-sig"),
                   file_name="mina_utbytesval.csv", mime="text/csv", icon=":material/download:")
