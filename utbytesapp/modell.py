"""Datamodellen för appen: avtal och universitet som tabeller (pandas), med härledda kolumner.

Den statiska delen (från data/avtal.json och data/rapporter.json) byggs en gång och cachas av UI-lagret.
Det som beror på dina val (favoriter, egna uppgifter, inriktning) läggs på per körning.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import amnen, geo, kurstyper, omgangar, rapporter

ROT = Path(__file__).resolve().parent.parent
AVTAL = ROT / "data" / "avtal.json"

KANAL_TEXT = {"central": "Centrala avtal", "teknat": "TekNat"}
SPRAK_STATUS_TEXT = {
    "databasen": "enligt avtalsdatabasen",
    "samma_universitet": "från ett annat avtal med samma universitet",
    "obekraftad": "obekräftat – landets språk; engelska främst på masternivå",
    "egen": "din egen uppgift",
}
NIVA_TEXT = {"grund": "Grundnivå", "avancerad": "Avancerad nivå", "forskar": "Forskarnivå"}
KT_RANG = {"öppet": 0, "begränsat": 1, "oklart": 2, "stängt": 3}  # bästa vägen till universitetet vinner


def ladda_avtal() -> dict | None:
    if not AVTAL.exists():
        return None
    return json.loads(AVTAL.read_text(encoding="utf-8"))


def ladda_rapporter() -> dict:
    if not rapporter.INDEX.exists():
        return {"rapporter": []}
    return json.loads(rapporter.INDEX.read_text(encoding="utf-8"))


def senaste_varlista(data: dict) -> str | None:
    """Senaste platslistan för en vårtermin (t.ex. "VT2027", eller "VT2028" när den publicerats)."""
    var = sorted((m for m in data.get("platslistor", {}) if m.startswith("VT")), key=lambda m: int(m[2:]))
    return var[-1] if var else None


def senaste_hostlista(data: dict) -> str | None:
    host = sorted((m for m in data.get("platslistor", {}) if m.startswith("HT")), key=lambda m: int(m[2:]))
    return host[-1] if host else None


def rapportstatistik(rapp: dict) -> dict[str, dict]:
    """Per avtal: antal rapporter, antal från teknisk fysik, och senaste år."""
    ut: dict[str, dict] = {}
    for r in rapp.get("rapporter", []):
        s = ut.setdefault(r["avtal_id"], {"antal": 0, "ttf": 0, "civing": 0, "senaste": ""})
        s["antal"] += 1
        if r.get("program_kategori") == "Teknisk fysik":
            s["ttf"] += 1
        if r.get("program_kategori") in ("Teknisk fysik", "Annat ingenjörsprogram"):
            s["civing"] += 1
        s["senaste"] = max(s["senaste"], r.get("ar") or "")
    return ut


def bygg_tabell(data: dict, rapp: dict) -> pd.DataFrame:
    """En rad per avtal med allt som behövs för sökning och visning (utan dina egna val)."""
    univ = data["universitet"]
    var = senaste_varlista(data)
    host = senaste_hostlista(data)
    stat = rapportstatistik(rapp)
    rader = []
    for a in data["avtal"]:
        u = univ[a["core_id"]]
        land = geo.land(u["land_kod"])
        varm = a.get("varmanader") or {}
        manader = varm.get("manader")
        plats_var = a["platser"].get(var) if var else None
        plats_host = a["platser"].get(host) if host else None
        rs = stat.get(a["id"], {"antal": len(a["rapporter"]), "ttf": 0, "civing": 0, "senaste": ""})
        sida = a.get("teknatsida") or {}
        stangt = sida.get("ovrigt", "") if "not open" in (sida.get("ovrigt") or "").lower() else ""
        rader.append({
            "id": a["id"], "core_id": a["core_id"], "kanal": a["kanal"], "kanal_text": KANAL_TEXT[a["kanal"]],
            "universitet": u["namn"], "universitet_en": u.get("namn_en") or "", "stad": u.get("stad") or "",
            "land_kod": u["land_kod"], "land": land.namn, "flagga": land.flagga, "varldsdel": land.varldsdel,
            "region": land.region, "lat": u.get("lat"), "lon": u.get("lon"),
            "avstand_km": geo.avstand_km(u.get("lat"), u.get("lon")),
            "enhet": a["enhet"], "enhet_sv": a["enhet_sv"], "enhet_kort": a["enhet_kort"], "kontakt": a["kontakt"],
            "delnamn": a.get("delnamn", ""),
            "typ": a["typ"], "erasmus": a["erasmus"], "icm": a["icm"], "nordtek": a["nordtek"],
            "civilingenjor": a["civilingenjor"],
            "kategorier": a["kategorier"] or [], "amnen": [i["namn"] for i in a["isced"]],
            "nivaer": a["nivaer"],
            "sprak": a["sprak"]["lista"], "sprak_status": a["sprak"]["status"],
            "sprak_engelska_master": bool(a["sprak"].get("engelska_masterniva")),
            "sprak_text": a["falt"].get("Undervisningsspråk", {}).get("text", ""),
            "sprakkrav_niva": a["sprakkrav"]["niva"], "sprakkrav_test": a["sprakkrav"]["test"],
            "test_kravs": a["sprakkrav"]["test_kravs"],
            "var_start": manader[0] if manader else None, "var_slut": manader[1] if manader else None,
            "var_status": varm.get("status"),
            "varvarning": a.get("varvarning") or "",
            "platser_var": plats_var["platser"] if plats_var else None,
            "pa_varlista": plats_var is not None,
            "pa_hostlista": plats_host is not None,
            "erasmus_euro": (a.get("erasmus_stipendium") or {}).get("euro_per_manad"),
            "antal_rapporter": rs["antal"], "ttf_rapporter": rs["ttf"], "civing_rapporter": rs["civing"],
            "senaste_rapport": rs["senaste"],
            "nordtek_text": "Nordtek" if a["nordtek"] else "",
            "teknat_ovrigt": sida.get("ovrigt", ""), "restplatser": sida.get("restplatser", ""),
            "stangt": stangt,
            "omgangar": [o.id for o in omgangar.omgangar_for(a["kanal"])],
            **{f"kt_{o}": a.get("kurstyper", {}).get(o, "oklart") for o in kurstyper.OMRADEN},
            "kt_not": a.get("kurstyper", {}).get("not", ""), "kt_kalla": a.get("kurstyper", {}).get("kalla", ""),
            "kt_andrad": a.get("kurstyper", {}).get("andrad", False),
            "bara_helar": a.get("kurstyper", {}).get("helar", False),
            "url": a["url"],
            "har_detaljer": a["detaljer_hamtade"],
        })
    return pd.DataFrame(rader)


def med_mina_val(df: pd.DataFrame, mina: dict, inriktning: str | None) -> pd.DataFrame:
    """Lägger på favoriter, egna språkuppgifter och ämnesmatchning för vald inriktning."""
    df = df.copy()
    fav = mina.get("favoriter", {})
    egna = mina.get("egna_uppgifter", {})
    df["favorit"] = df["id"].isin(fav.keys())
    df["status"] = df["id"].map(lambda i: fav.get(i, {}).get("status", ""))
    for i, rad in df.iterrows():
        eget = egna.get(rad["core_id"], {})
        if eget.get("sprak"):
            df.at[i, "sprak"] = list(eget["sprak"])
            df.at[i, "sprak_status"] = "egen"
    bas = amnen_bas(inriktning)
    matchning = []
    for _, r in df.iterrows():
        if amnen.ALLA in r["kategorier"]:
            kt = {o: r[f"kt_{o}"] for o in kurstyper.OMRADEN}
            matchning.append(amnen.match_kurstyper(kt, bas))
        else:
            matchning.append(amnen.match(r["kategorier"], bas, r["civilingenjor"]))
    df["match"] = matchning
    return df


def amnen_bas(inriktning: str | None) -> str | None:
    """"Tillämpad fysik, profil Fysik" -> "Tillämpad fysik"."""
    if not inriktning:
        return None
    bas = inriktning.split(",")[0].strip()
    return bas if bas in amnen.INRIKTNINGAR else None


def per_universitet(df: pd.DataFrame) -> pd.DataFrame:
    """En rad per universitet med sammanfattning av dess avtal (för listvy, karta och jämförelse)."""
    if df.empty:
        return df
    grupper = []
    for core, g in df.groupby("core_id", sort=False):
        f = g.iloc[0]
        sprak = list(dict.fromkeys(s for lista in g["sprak"] for s in lista))
        bekraftat = any(s in ("databasen", "egen") for s in g["sprak_status"])
        grupper.append({
            "core_id": core, "universitet": f["universitet"], "universitet_en": f["universitet_en"],
            "stad": f["stad"], "land": f["land"], "land_kod": f["land_kod"], "flagga": f["flagga"],
            "varldsdel": f["varldsdel"], "region": f["region"], "lat": f["lat"], "lon": f["lon"],
            "avstand_km": f["avstand_km"],
            "antal_avtal": len(g), "kanaler": sorted(set(g["kanal"])),
            "enheter": list(dict.fromkeys(g["enhet_kort"])), "typer": list(dict.fromkeys(g["typ"])),
            "kategorier": list(dict.fromkeys(k for lista in g["kategorier"] for k in lista)),
            "sprak": sprak, "sprak_bekraftat": bekraftat,
            "match": int(g["match"].max()) if "match" in g else 0,
            "platser_var": g["platser_var"].dropna().max() if g["platser_var"].notna().any() else None,
            "pa_varlista": bool(g["pa_varlista"].any()),
            "erasmus_euro": g["erasmus_euro"].dropna().max() if g["erasmus_euro"].notna().any() else None,
            "antal_rapporter": int(g["antal_rapporter"].sum()), "ttf_rapporter": int(g["ttf_rapporter"].sum()),
            "favorit": bool(g["favorit"].any()) if "favorit" in g else False,
            "civilingenjor": bool(g["civilingenjor"].any()),
            "avtal_ids": list(g["id"]),
            "kurstyper": {o: min(g[f"kt_{o}"], key=lambda v: KT_RANG.get(v, 9)) for o in kurstyper.OMRADEN},
        })
    return pd.DataFrame(grupper)


def sprak_visning(sprak: list[str], status: str, engelska_master: bool = False) -> str:
    if not sprak:
        return "okänt"
    namn = [s.capitalize() for s in sprak]
    if status == "obekraftad" and engelska_master and "Engelska" in namn:
        namn = ["Engelska (främst master)"] + [n for n in namn if n != "Engelska"]
    return ", ".join(namn)


def vartermin_visning(start: int | None, slut: int | None, status: str | None) -> str:
    if not start or not slut:
        return "okänt"
    text = geo.manadsintervall(int(start), int(slut))
    return text + (" (typiskt för landet)" if status == "typiskt" else "")
