"""Hämtar UU:s utbytesavtal och bygger om data/avtal.json.

Källor (alla publika, inga personuppgifter skickas):
  - Avtalsdatabasen i MoveON: centrala avtal och TekNats fakultets- och institutionsavtal
  - uu.se: universiteten i aktuell ansökningsomgång för centrala avtal (sparas i data/platslistor/)
  - uu.se: TekNats avtalssida (anteckningar, restplatser, Nordtek)
  - uu.se: Erasmusstipendiets nivåer

Kör:
    python verktyg/hamta_avtal.py           snabbt: listor, uu.se-sidor och detaljer för nya avtal
    python verktyg/hamta_avtal.py --allt    hämtar om detaljerna för alla avtal (tar 10–20 min)
    python verktyg/hamta_avtal.py --bygg    bygger bara om data/avtal.json från sparad rådata
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from utbytesapp import bygg, moveon, uusidor  # noqa: E402

RADATA = bygg.RADATA
DETALJER = RADATA / "detaljer"
HTML = RADATA / "html"


def skriv(text: str) -> None:
    print(text, flush=True)


def spara_json(fil: Path, data) -> None:
    fil.parent.mkdir(parents=True, exist_ok=True)
    tmp = fil.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(fil)


def nu() -> str:
    return dt.datetime.now().isoformat(timespec="minutes")


def hamta_moveon(allt: bool) -> dict:
    klient = moveon.Klient()
    tider = {}
    jobb = []
    for pub, (kanal, _) in moveon.PUBLICERARE.items():
        skriv(f"Hämtar avtalslistan för {'centrala avtal' if kanal == 'central' else 'TekNat'} …")
        lista = klient.lista(pub)
        spara_json(RADATA / f"moveon_lista_{pub}.json", lista)
        poster = lista.get("labelvalue", [])
        skriv(f"  {len(poster)} avtal")
        for post in poster:
            fil = DETALJER / f"{pub}_{post['core_id']}_{post['relation_id']}.json"
            if allt or not fil.exists():
                jobb.append((pub, post, fil))
    tider["moveon"] = nu()
    if jobb:
        skriv(f"Hämtar detaljer för {len(jobb)} avtal (servern är långsam, ha tålamod) …")
    for i, (pub, post, fil) in enumerate(jobb, 1):
        try:
            spara_json(fil, klient.detalj(pub, post["core_id"], post["relation_id"]))
            skriv(f"  [{i}/{len(jobb)}] {post['universityname']}")
        except Exception as fel:  # fortsätt med resten
            skriv(f"  [{i}/{len(jobb)}] MISSLYCKADES: {post['universityname']} ({fel})")
    if jobb:
        tider["detaljer"] = nu()
    return tider


def hamta_uu() -> dict:
    tider = {}
    skriv("Hämtar listan över universitet i aktuell ansökningsomgång (centrala avtal) …")
    try:
        html = moveon.hamta_sida(uusidor.URL_PLATSER)
        (HTML / "platser.html").write_text(html, encoding="utf-8")
        lista = uusidor.tolka_platslista(html)
        if lista:
            lista["hamtad"] = dt.date.today().isoformat()
            fil = bygg.PLATSLISTOR / f"{lista['mal_termin']}.json"
            ny = not fil.exists()
            spara_json(fil, lista)
            skriv(f"  {lista['omgang']} för {lista['mal_termin']}: {len(lista['universitet'])} universitet"
                  f"{' (NY LISTA!)' if ny else ''}")
        else:
            skriv("  Ingen lista publicerad just nu (publiceras 15 april och 15 oktober).")
        tider["platser"] = nu()
    except Exception as fel:
        skriv(f"  MISSLYCKADES: {fel}")

    skriv("Hämtar TekNats avtalssida …")
    try:
        html = moveon.hamta_sida(uusidor.URL_TEKNAT)
        (HTML / "teknatsida.html").write_text(html, encoding="utf-8")
        sida = uusidor.tolka_teknatsida(html)
        spara_json(RADATA / "teknatsida.json", sida)
        rest = sum(1 for a in [*sida["avtal"].values(), *sida["utan_lank"]] if a.get("restplatser"))
        skriv(f"  {len(sida['avtal']) + len(sida['utan_lank'])} rader, {rest} markerade med restplatser")
        tider["teknatsida"] = nu()
    except Exception as fel:
        skriv(f"  MISSLYCKADES: {fel}")

    skriv("Hämtar Erasmusstipendiets nivåer …")
    try:
        html = moveon.hamta_sida(uusidor.URL_ERASMUS)
        (HTML / "erasmus.html").write_text(html, encoding="utf-8")
        erasmus = uusidor.tolka_erasmus(html)
        if erasmus["grupper"]:
            spara_json(RADATA / "erasmus.json", erasmus)
            skriv("  " + ", ".join(f"grupp {g['grupp']}: {g['euro_per_manad']} €/mån" for g in erasmus["grupper"]))
        else:
            skriv("  Kunde inte tolka sidan – behåller tidigare nivåer.")
        tider["erasmus"] = nu()
    except Exception as fel:
        skriv(f"  MISSLYCKADES: {fel}")
    return tider


def _namn(data: dict, avtal_id: str) -> str:
    a = next((x for x in data["avtal"] if x["id"] == avtal_id), None)
    if not a:
        return avtal_id
    u = data["universitet"][a["core_id"]]
    return f"{u['namn']} ({a['enhet_kort']})"


def jamfor(gammal: dict, ny: dict) -> dict:
    """Vad som ändrats sedan förra bygget – visas på Översikt."""
    rader = []
    fore = {a["id"] for a in gammal["avtal"]}
    efter = {a["id"] for a in ny["avtal"]}
    for i in sorted(efter - fore):
        rader.append(f"Nytt avtal: {_namn(ny, i)}")
    for i in sorted(fore - efter):
        rader.append(f"Avtalet finns inte längre: {_namn(gammal, i)}")
    for mal in sorted(set(ny.get("platslistor", {})) - set(gammal.get("platslistor", {}))):
        meta = ny["platslistor"][mal]
        rader.append(f"Ny platslista: {meta.get('omgang') or ''} för {mal} ({meta.get('antal')} universitet)")
    gamla_platser = {(a["id"], m): v.get("platser") for a in gammal["avtal"] for m, v in a.get("platser", {}).items()}
    for a in ny["avtal"]:
        for m, v in a.get("platser", {}).items():
            fore_p = gamla_platser.get((a["id"], m), "saknas")
            if fore_p != "saknas" and fore_p != v.get("platser"):
                rader.append(f"Ändrat antal platser {m}: {_namn(ny, a['id'])} {fore_p} → {v.get('platser')}")
    gamla_rest = {a["id"]: (a.get("teknatsida") or {}).get("restplatser") for a in gammal["avtal"]}
    for a in ny["avtal"]:
        rest = (a.get("teknatsida") or {}).get("restplatser")
        if rest and rest != gamla_rest.get(a["id"]):
            rader.append(f"Restplatser markerade: {_namn(ny, a['id'])} ({rest})")
    return {"datum": nu(), "rader": rader}


def logga(andringar: dict) -> None:
    fil = bygg.DATA / "andringar.json"
    logg = json.loads(fil.read_text(encoding="utf-8")) if fil.exists() else []
    logg.insert(0, andringar)
    spara_json(fil, logg[:30])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--allt", action="store_true", help="hämta om detaljer för alla avtal")
    p.add_argument("--bygg", action="store_true", help="bygg bara om från sparad rådata (inget nätverk)")
    args = p.parse_args()

    DETALJER.mkdir(parents=True, exist_ok=True)
    HTML.mkdir(parents=True, exist_ok=True)
    bygg.PLATSLISTOR.mkdir(parents=True, exist_ok=True)

    if not args.bygg:
        tider = json.loads((RADATA / "hamtad.json").read_text(encoding="utf-8")) if (RADATA / "hamtad.json").exists() else {}
        tider.update(hamta_moveon(args.allt))
        tider.update(hamta_uu())
        spara_json(RADATA / "hamtad.json", tider)

    skriv("Bygger data/avtal.json …")
    data = bygg.bygg()
    gammal = json.loads(bygg.AVTAL.read_text(encoding="utf-8")) if bygg.AVTAL.exists() else None
    bygg.spara(data)
    skriv(f"  {len(data['avtal'])} avtal på {len(data['universitet'])} universitet")
    if gammal:
        andringar = jamfor(gammal, data)
        for rad in andringar["rader"]:
            skriv(f"  Ändring: {rad}")
        if andringar["rader"]:
            logga(andringar)
    for typ, rader in data["omatchat"].items():
        if rader:
            skriv(f"  OBS: {len(rader)} rader i {typ} kunde inte kopplas till ett avtal: "
                  + "; ".join(r["namn"] for r in rader[:5]))
    skriv("Klart.")


if __name__ == "__main__":
    main()
