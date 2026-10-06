"""Laddar ner utbytesrapporterna (PDF) från UU:s avtalsdatabas och bygger sökindexet data/rapporter.json.

Rapporterna är publicerade av UU för blivande utbytesstudenter. De sparas i static/rapporter/ så att
appen kan visa dem lokalt. Redan nedladdade rapporter hämtas inte igen.

Kör (efter verktyg/hamta_avtal.py):
    python verktyg/hamta_rapporter.py            hämtar nya rapporter och bygger indexet
    python verktyg/hamta_rapporter.py --index    bygger bara om indexet från redan hämtade PDF:er
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from utbytesapp import bygg, moveon, rapporter  # noqa: E402


def skriv(text: str) -> None:
    print(text, flush=True)


def pdf_fil(pub: str, fil_id: str) -> Path:
    return rapporter.PDF_MAPP / f"{pub}_{fil_id}.pdf"


SAKNAS_PA_SERVERN = ROT / "data" / "radata" / "rapporter_saknas.json"


def ladda_ner(avtal: list[dict], forsok_igen: bool = False) -> None:
    trasiga = set() if forsok_igen or not SAKNAS_PA_SERVERN.exists() else set(
        json.loads(SAKNAS_PA_SERVERN.read_text(encoding="utf-8")))
    saknas = [(a, r) for a in avtal for r in a["rapporter"]
              if not pdf_fil(a["pub"], r["fil_id"]).exists() and f"{a['pub']}_{r['fil_id']}" not in trasiga]
    if not saknas:
        skriv("Alla rapporter är redan nedladdade" + (f" ({len(trasiga)} finns inte på UU:s server)." if trasiga else "."))
        return
    skriv(f"Laddar ner {len(saknas)} rapporter …")
    klient = moveon.Klient(paus=0.3)
    upplast: set[str] = set()
    for i, (a, r) in enumerate(saknas, 1):
        try:
            if a["id"] not in upplast:  # detaljanropet låser upp avtalets rapporter i sessionen
                klient.detalj(a["pub"], a["core_id"], a["relation_id"])
                upplast.add(a["id"])
            data = klient.rapport_pdf(a["pub"], r["fil_id"])
            fil = pdf_fil(a["pub"], r["fil_id"])
            fil.parent.mkdir(parents=True, exist_ok=True)
            fil.write_bytes(data)
            skriv(f"  [{i}/{len(saknas)}] {r['ar']} {a['id']}")
        except Exception as fel:
            skriv(f"  [{i}/{len(saknas)}] MISSLYCKADES {a['id']} rapport {r['fil_id']}: {fel}")
            if "ingen PDF" in str(fel):  # UU:s server saknar filen – försök inte igen nästa gång
                trasiga.add(f"{a['pub']}_{r['fil_id']}")
    SAKNAS_PA_SERVERN.parent.mkdir(parents=True, exist_ok=True)
    SAKNAS_PA_SERVERN.write_text(json.dumps(sorted(trasiga)), encoding="utf-8")


def bygg_index(avtal: list[dict], universitet: dict) -> dict:
    gammalt = {}
    if rapporter.INDEX.exists():
        for r in json.loads(rapporter.INDEX.read_text(encoding="utf-8")).get("rapporter", []):
            gammalt[r["id"]] = r
    ut = []
    misslyckade = 0
    for a in avtal:
        for r in a["rapporter"]:
            fil = pdf_fil(a["pub"], r["fil_id"])
            if not fil.exists():
                continue
            rid = f"{a['pub']}_{r['fil_id']}"
            andrad = fil.stat().st_mtime
            if rid in gammalt and gammalt[rid].get("_mtime") == andrad:
                post = gammalt[rid]
                falt = post.get("falt", {})
                post.update({"avtal_id": a["id"], "core_id": a["core_id"],
                             "termin": rapporter.termin_ur(falt.get("start")),
                             "program_kategori": rapporter.kategori_program(
                                 falt.get("program_uu", ""), falt.get("examen", ""), falt.get("profil", ""))})
                ut.append(post)
                continue
            try:
                tolkad = rapporter.tolka_pdf(fil)
            except Exception as fel:
                misslyckade += 1
                skriv(f"  Kunde inte läsa {fil.name}: {fel}")
                continue
            falt = rapporter.nyckelfalt(tolkad)
            namn = " ".join(x for x in (falt.get("fornamn"), falt.get("efternamn")) if x) or r.get("namn", "")
            ut.append({
                "id": rid, "pub": a["pub"], "fil_id": r["fil_id"], "avtal_id": a["id"], "core_id": a["core_id"],
                "ar": r.get("ar") or falt.get("lasar"), "namn": namn, "falt": falt,
                "termin": rapporter.termin_ur(falt.get("start")),
                "program_kategori": rapporter.kategori_program(falt.get("program_uu", ""), falt.get("examen", ""),
                                                               falt.get("profil", "")),
                "titel": tolkad["titel"], "avsnitt": tolkad["avsnitt"], "text": tolkad["text"],
                "kurser": rapporter.kursavsnitt(tolkad),
                "pdf": str(fil.relative_to(ROT)), "_mtime": andrad,
            })
    skriv(f"Index: {len(ut)} rapporter" + (f", {misslyckade} gick inte att läsa" if misslyckade else ""))
    return {"format": 1, "byggd": dt.datetime.now().isoformat(timespec="seconds"), "rapporter": ut}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--index", action="store_true", help="bygg bara om indexet")
    p.add_argument("--forsok-igen", action="store_true", help="försök igen med rapporter som saknades på servern")
    args = p.parse_args()
    if not bygg.AVTAL.exists():
        sys.exit("Kör först: python verktyg/hamta_avtal.py")
    data = json.loads(bygg.AVTAL.read_text(encoding="utf-8"))
    if not args.index:
        ladda_ner(data["avtal"], args.forsok_igen)
    skriv("Läser rapporterna …")
    index = bygg_index(data["avtal"], data["universitet"])
    tmp = rapporter.INDEX.with_suffix(".tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    tmp.replace(rapporter.INDEX)
    skriv("Klart.")


if __name__ == "__main__":
    main()
