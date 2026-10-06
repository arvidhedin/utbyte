"""Utbytesrapporter: tolkning av rapport-PDF:erna från MoveON och sökning i dem.

Rapporterna är formulär i två kolumner: frågan (fetstil) till vänster och svaret till höger.
Vi läser ord med position och typsnitt via pdfplumber och bygger upp fråga–svar per avsnitt.
"""

from __future__ import annotations

import re
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
PDF_MAPP = ROT / "static" / "rapporter"
INDEX = ROT / "data" / "rapporter.json"

_KOLUMN = 256  # x-koordinat mellan fråga och svar (A4, 595 pt bred)


def _rader(sida) -> list[dict]:
    """Ord grupperade till visuella rader och klassade som titel, rubrik, underrubrik, fråga eller svar."""
    ord_ = sorted(sida.extract_words(extra_attrs=["fontname", "size"]), key=lambda w: (w["top"], w["x0"]))
    linjer: list[list[dict]] = []
    for w in ord_:
        if linjer and abs(linjer[-1][0]["top"] - w["top"]) < 3:
            linjer[-1].append(w)
        else:
            linjer.append([w])
    rader: list[dict] = []
    for linje in linjer:
        linje.sort(key=lambda w: w["x0"])
        forsta = linje[0]
        storlek = max(round(w["size"], 1) for w in linje)
        top = forsta["top"]
        hel = " ".join(w["text"] for w in linje)
        if storlek >= 11:
            rader.append({"typ": "rubrik" if forsta["x0"] < 60 else "titel", "top": top, "text": hel})
            continue
        if storlek >= 8.5 and forsta["x0"] < 60:
            rader.append({"typ": "underrubrik", "top": top, "text": hel})
            continue
        vanster = [w for w in linje if w["x0"] < _KOLUMN and "bold" in w["fontname"].lower()]
        hoger = [w for w in linje if w not in vanster]
        if vanster:
            rader.append({"typ": "fraga", "top": top, "text": " ".join(w["text"] for w in vanster)})
        if hoger:
            rader.append({"typ": "svar", "top": top, "text": " ".join(w["text"] for w in hoger)})
    return rader


def tolka_pdf(fil: Path) -> dict:
    """{"titel", "avsnitt": [{"rubrik", "poster": [{"fraga", "svar"}]}], "text"}"""
    import pdfplumber  # importeras här: bara verktyget behöver det

    avsnitt: list[dict] = []
    titel = ""
    aktuell: dict | None = None
    post: dict | None = None
    senaste_fraga_top = -100.0
    with pdfplumber.open(fil) as pdf:
        for sidnr, sida in enumerate(pdf.pages):
            senaste_fraga_top = -100.0
            for rad in _rader(sida):
                typ, txt = rad["typ"], rad["text"].strip()
                if typ == "titel":
                    titel = (titel + " " + txt).strip() if sidnr == 0 else titel
                    continue
                if typ in ("rubrik", "underrubrik"):
                    if typ == "rubrik" or aktuell is None:
                        aktuell = {"rubrik": txt.title() if txt.isupper() else txt, "poster": []}
                        avsnitt.append(aktuell)
                    post = None
                    continue
                if aktuell is None:
                    aktuell = {"rubrik": "", "poster": []}
                    avsnitt.append(aktuell)
                if typ == "fraga":
                    # Frågor står med minst en tom rad emellan; en frågerad inom en radhöjd
                    # (≈9,5 pt) från förra är en fortsättning på samma fråga.
                    if post is None or rad["top"] - senaste_fraga_top > 12:
                        post = {"fraga": txt, "svar": ""}
                        aktuell["poster"].append(post)
                    else:
                        post["fraga"] += " " + txt
                    senaste_fraga_top = rad["top"]
                else:  # svar
                    if post is None:
                        post = {"fraga": "", "svar": ""}
                        aktuell["poster"].append(post)
                    post["svar"] = (post["svar"] + " " + txt).strip()
    for a in avsnitt:
        a["poster"] = [p for p in a["poster"] if p["fraga"] or p["svar"]]
    avsnitt = [a for a in avsnitt if a["poster"]]
    text = "\n".join(f"{p['fraga']}: {p['svar']}" for a in avsnitt for p in a["poster"])
    return {"titel": titel, "avsnitt": avsnitt, "text": text}


# ---------------------------------------------------------------------------------------------
# Nyckelfält
# ---------------------------------------------------------------------------------------------

_FALT = {
    "efternamn": r"^surname$",
    "fornamn": r"^first name$",
    "land": r"^exchange country$",
    "stad": r"^exchange city$",
    "universitet": r"^exchange university$",
    "samordnare": r"co-?ordinated by",
    "lasar": r"academic year$",
    "start": r"start semester",
    "terminer": r"duration in semesters",
    "niva": r"level of studies at the exchange",
    "amne": r"^subject area$",
    "program_uu": r"what are you studying at uppsala",
    "examen": r"^degree programme$",
    "profil": r"what profile within your program",
    "ar_innan": r"how many years of study",
    "kontakt": r"leave an email address|contact you about this exchange",
}

TTF = re.compile(r"engineering physics|teknisk fysik|technical physics|engineering\s+phys|\bTTF\b|"
                 r"physics engineering|applied physics and electrical", re.I)
CIVING = re.compile(r"engineer|ingenjör|civilingen|master of science in engineering|integrated bachelor and master", re.I)
FYSIK = re.compile(r"\bphysics\b|fysik|astronom", re.I)


def nyckelfalt(tolkad: dict) -> dict:
    ut: dict[str, str] = {}
    for a in tolkad["avsnitt"]:
        for p in a["poster"]:
            fraga = p["fraga"].strip().rstrip(":").lower()
            for nyckel, monster in _FALT.items():
                if nyckel not in ut and re.search(monster, fraga):
                    ut[nyckel] = p["svar"].strip()
    return ut


def termin_ur(start: str | None) -> str | None:
    """"Autumn Semester 2025/26" -> "HT2025", "Spring semester 2024/25" -> "VT2025"."""
    if not start:
        return None
    m = re.search(r"(autumn|fall|spring)\D*(\d{4})(?:/(\d{2}))?", start, re.I)
    if not m:
        return None
    ar = int(m[2])
    if m[1].lower() == "spring":
        return f"VT{ar + 1 if m[3] else ar}"
    return f"HT{ar}"


def kategori_program(program: str, examen: str = "", profil: str = "") -> str:
    hel = " ".join(x for x in (program, examen, profil) if x)
    if TTF.search(hel):
        return "Teknisk fysik"
    if CIVING.search(hel):
        return "Annat ingenjörsprogram"
    if FYSIK.search(hel):
        return "Fysik"
    return "Annat"


def kursavsnitt(tolkad: dict) -> str:
    """Allt rapportskrivaren skrev under "Studies" (kurser, tillgodoräknande, undervisning)."""
    delar = []
    for a in tolkad["avsnitt"]:
        if a["rubrik"].lower().startswith("studies"):
            delar += [p["svar"] for p in a["poster"] if p["svar"] and len(p["svar"]) > 3]
    return "\n\n".join(delar)
