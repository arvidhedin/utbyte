"""Tolkning av fritextfält i avtalsdatabasen: undervisningsspråk, språkkrav, poängomräkning,
terminsdatum och varningar för vårterminen.

Allt här är heuristik på UU:s egna texter. Originaltexten visas alltid bredvid i appen.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------------------------
# Språk
# ---------------------------------------------------------------------------------------------

SPRAK_MONSTER = [
    ("engelska", r"english|engelska|anglais|englisch|ingl[eé]s"),
    ("tyska", r"german\b|deutsch|tyska"),
    ("franska", r"french|fran[cç]ais|franska"),
    ("spanska", r"spanish|espa[nñ]ol|castellano|castilian|spanska"),
    ("italienska", r"italian|italiano|italienska"),
    ("nederländska", r"dutch|nederlands|flemish|nederländska"),
    ("portugisiska", r"portugu[eê]s|portuguese|portugisiska"),
    ("katalanska", r"catalan|catal[aà]"),
    ("baskiska", r"basque|euskara"),
    ("svenska", r"swedish|svenska"),
    ("finska", r"finnish|suomi|finska"),
    ("danska", r"danish|danska"),
    ("norska", r"norwegian|norska"),
    ("isländska", r"icelandic"),
    ("estniska", r"estonian"),
    ("lettiska", r"latvian"),
    ("litauiska", r"lithuanian"),
    ("polska", r"polish\b"),
    ("tjeckiska", r"czech"),
    ("slovakiska", r"slovak\b"),
    ("slovenska", r"sloven(e|ian)\b"),
    ("kroatiska", r"croatian"),
    ("grekiska", r"greek"),
    ("turkiska", r"turkish"),
    ("ungerska", r"hungarian"),
    ("japanska", r"japanese"),
    ("koreanska", r"korean"),
    ("kinesiska", r"chinese|mandarin|cantonese"),
    ("ryska", r"russian"),
    ("arabiska", r"arabic"),
    ("thailändska", r"\bthai\b"),
    ("vietnamesiska", r"vietnamese"),
    ("indonesiska", r"indonesian|bahasa"),
    ("kazakiska", r"kazakh"),
    ("georgiska", r"georgian"),
    ("albanska", r"albanian"),
    ("ukrainska", r"ukrainian"),
]
_SPRAK_RE = [(namn, re.compile(m, re.I)) for namn, m in SPRAK_MONSTER]


def sprak_i_text(text: str | None) -> list[str]:
    """Alla språk som nämns i en text, i visningsordning (engelska först)."""
    if not text:
        return []
    hittade = [namn for namn, rx in _SPRAK_RE if rx.search(text)]
    return hittade


_VAR = re.compile(r"spring|vår|sommersemester|summer semester|\b(fall|autumn) semester\b", re.I)
_BARA = re.compile(r"\bonly\b|endast|\bbara\b|cannot|can not|can't|not possible|no courses in english|uniquement", re.I)
_IRRELEVANT = re.compile(r"business|\bMBA\b|\blaw\b|medicine|BNAD|special terms", re.I)


def varvarning(*texter: str | None) -> str | None:
    """Hittar meningar som begränsar vårterminen, t.ex. "During the spring semester you can only
    take courses in French" eller "For the spring semester 2027, students can ONLY study at …"."""
    for text in texter:
        if not text:
            continue
        for mening in re.split(r"(?<=[.!?])\s+|\n", text):
            m = mening.strip()
            if m and _VAR.search(m) and _BARA.search(m) and not _IRRELEVANT.search(m):
                return m if len(m) <= 320 else m[:319].rstrip() + "…"
    return None


# ---------------------------------------------------------------------------------------------
# Språkkrav
# ---------------------------------------------------------------------------------------------

_CEFR = re.compile(r"\b([ABC][12])\b")
_TEST = re.compile(
    r"\b(TOEFL|IELTS|Cambridge|DELF|DALF|TCF|TestDaF|DSH|Goethe|DELE|SIELE|CELI|CILS|JLPT|TOPIK|HSK|TOEIC|"
    r"Duolingo|PTE|CAE|FCE|Anglia|Linguaskill)\b", re.I)
_INGET_TEST = re.compile(
    r"no (official )?(language )?(test|certificate|certification|proof)[^.]{0,40}(needed|required|necessary)|"
    r"(test|certificate)s? (is|are)? ?not (needed|required|necessary)|no language test|"
    r"there is no language (test|requirement)|without (a )?(language )?(test|certificate)|"
    r"inget språktest|no formal (language )?(test|requirement)", re.I)
_GYMNASIE = re.compile(r"upper secondary|gymnasi|English 6|Engelska 6|grade 4|\bVG\b|secondary school", re.I)


def sprakkrav(text: str | None) -> dict:
    """Sammanfattar ett språkkrav: högsta CEFR-nivå, nämnda test och om test krävs.
    test_kravs: False = uttryckligen inget test, True = test nämns som krav, None = oklart."""
    if not text or not text.strip():
        return {"niva": None, "test": [], "test_kravs": None, "gymnasiebetyg": False}
    nivaer = sorted(set(_CEFR.findall(text)))
    test = sorted({t.upper() if t.isupper() or len(t) <= 5 else t.capitalize() for t in _TEST.findall(text)})
    inget = bool(_INGET_TEST.search(text))
    gymn = bool(_GYMNASIE.search(text))
    if inget:
        kravs: bool | None = False
    elif test:
        # "If no such results, a language test may be required" -> kan krävas
        kravs = None if gymn or re.search(r"\bmay\b|\bmight\b|if (you )?(do not|don't|no)", text, re.I) else True
    else:
        kravs = None
    return {"niva": nivaer[-1] if nivaer else None, "test": test, "test_kravs": kravs, "gymnasiebetyg": gymn}


# ---------------------------------------------------------------------------------------------
# Poängomräkning
# ---------------------------------------------------------------------------------------------

_TAL = r"(\d+(?:[.,]\d+)?)"
_HP = r"(?:hp|högskolepoäng|swedish credits|swedish higher education credits|ects|credits at (?:uu|uppsala))"
_LIKA = r"(?:=|equals?(?: to)?|is equal to|corresponds? to|is equivalent(?: to)?|equivalent to|motsvarar|→|->|gives)"
# Talet, upp till 60 tecken text (t.ex. "Graduate/Master credit units per semester"), likhet, tal, hp.
_OMR = re.compile(rf"{_TAL}(?![.,]?\d)([^=\d\n]{{0,60}}?){_LIKA}\s*{_TAL}\s*{_HP}\b", re.I)
_GRAD = re.compile(r"graduate|master|postgraduate", re.I)
_UNDERGRAD = re.compile(r"undergrad|bachelor", re.I)


def _tal(s: str) -> float:
    return float(s.replace(",", "."))


def omrakningar(text: str | None) -> list[dict]:
    """Alla omräkningar i en text: [{"faktor": hp per värdpoäng, "niva": "grund"/"avancerad"/None, "text": …}].

    "Undergraduate/Bachelor: 15 credits = 30 hp Graduate/Master: 12 credits = 30 hp"
    -> faktor 2,0 (grund) och 2,5 (avancerad)."""
    if not text:
        return []
    # Parenteser som "(about 5 courses)" förstör annars talparet; prova utan dem först.
    utan_parentes = re.sub(r"\([^)]*\)", " ", text)
    ut = _hitta_omrakningar(utan_parentes) or _hitta_omrakningar(text)
    if not ut and re.search(r"\bECTS\b", text):
        ut.append({"faktor": 1.0, "niva": None, "text": "ECTS"})
    return ut


def _hitta_omrakningar(text: str) -> list[dict]:
    ut: list[dict] = []
    for m in _OMR.finditer(text):
        a, b = _tal(m[1]), _tal(m[3])
        if a <= 0 or not 0.05 <= b / a <= 10:
            continue
        fore = text[max(0, m.start() - 45): m.start()] + m[2]
        niva = None
        if _UNDERGRAD.search(fore):
            niva = "grund"
        elif _GRAD.search(fore):
            niva = "avancerad"
        ut.append({"faktor": round(b / a, 4), "niva": niva, "text": m.group(0).strip()})
    return ut


def omrakning(text: str | None) -> float | None:
    """Första (oftast grundnivå) omräkningsfaktorn, hp per värdpoäng."""
    alla = omrakningar(text)
    return alla[0]["faktor"] if alla else None


# ---------------------------------------------------------------------------------------------
# Terminsdatum
# ---------------------------------------------------------------------------------------------

_MANAD = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "maj": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12,
    "januari": 1, "februari": 2, "mars": 3, "april": 4, "juni": 6, "juli": 7, "augusti": 8,
    "january": 1, "february": 2, "march": 3, "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}
_MANAD_RE = r"(jan|feb|mar|apr|ma[yj]|jun|jul|aug|sep|o[ck]t|nov|dec)[a-z]*"
_PREFIX = r"(?:(?:early|mid|late|end|beginning|start|the|of|in)[\s/\-]*)*"
_VAR_INTERVALL = re.compile(
    rf"(?:spring|semester 1\b|semester 2 \(spring\)|sommersemester|summer (?:semester|term)|term 1\b|trimester 1\b|"
    rf"first semester|winter (?:semester|term)|vårtermin)[^.\n]{{0,40}}?"
    rf"\b{_MANAD_RE}\b[^.\n]{{0,25}}?(?:-|–|—|\bto\b|till|until|through|ends in|ends)\s*"
    rf"(?:\d{{1,2}}\.?\s*)?{_PREFIX}\b{_MANAD_RE}\b",
    re.I)


def _manad(s: str) -> int | None:
    s = s.lower()
    return _MANAD.get(s) or _MANAD.get(s[:3])


def varmanader(text: str | None) -> tuple[int, int] | None:
    """Vårterminens månader ur t.ex. "Spring semester: January to May" -> (1, 5).
    Tar första tolkningen som ligger på våren (start jan–jun)."""
    if not text:
        return None
    for m in _VAR_INTERVALL.finditer(text):
        a, b = _manad(m[1]), _manad(m[2])
        if a and b and 1 <= a <= 6 and a <= b <= 9:
            return a, b
    return None
