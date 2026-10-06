"""Tolkar UU:s webbsidor om utbytesstudier (sparad HTML in, strukturerad data ut).

- Listan över universitet i en ansökningsomgång för centrala avtal (med antal platser)
- TekNats sida över fakultets- och institutionsavtal (anteckningar, restplatser, Nordtek)
- Erasmusstipendiets nivåer per land
"""

from __future__ import annotations

import re
import urllib.parse

from bs4 import BeautifulSoup

from . import geo

URL_PLATSER = ("https://www.uu.se/en/students/international-opportunities/"
               "exchange-studies-via-university-wide-agreements/available-universities")
URL_TEKNAT = ("https://www.uu.se/en/students/faculty/science-and-technology/exchange-studies/"
              "exchange-studies-in-science-and-technology")
URL_ERASMUS = "https://www.uu.se/student/internationella-mojligheter/erasmusstipendiet/erasmusstudier"
URL_CENTRAL = "https://www.uu.se/student/internationella-mojligheter/utbytesstudier-via-centrala-avtal"
URL_CENTRAL_EN = "https://www.uu.se/en/students/international-opportunities/exchange-studies-via-university-wide-agreements"
URL_TEKNAT_GUIDE = "https://www.uu.se/en/students/faculty/science-and-technology/exchange-studies/application-guide"

_WS = re.compile(r"\s+")


def _text(el) -> str:
    return _WS.sub(" ", el.get_text(" ")).strip() if el is not None else ""


def _main(html: str):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    for t in main(["script", "style", "nav"]):
        t.decompose()
    return main


def _senast_andrad(main) -> str | None:
    m = re.search(r"(?:Last modified|Senast ändrad):?\s*(\d{4}-\d{2}-\d{2})", _text(main))
    return m.group(1) if m else None


# ---------------------------------------------------------------------------------------------
# Platslista (centrala avtal)
# ---------------------------------------------------------------------------------------------

def _termin(ord_: str, ar: str) -> str:
    return ("VT" if ord_.lower() == "spring" else "HT") + ar


def tolka_platslista(html: str) -> dict | None:
    """Universitet, platser och stipendium i den omgång som just nu är publicerad.
    Returnerar None om sidan inte har någon lista (mellan omgångarna)."""
    main = _main(html)
    hel = _text(main)
    omgang = mal = None
    if m := re.search(r"Application round for the (spring|autumn|fall) semester (\d{4})", hel, re.I):
        omgang = ("Vårrundan " if m[1].lower() == "spring" else "Höstrundan ") + m[2]
    if m := re.search(r"outgoing students for the (spring|autumn|fall) semester (\d{4})", hel, re.I):
        mal = _termin(m[1], m[2])
    elif m := re.search(r"exchanges starting in (spring|autumn|fall) of (\d{4})", hel, re.I):
        mal = _termin(m[1], m[2])
    beskrivning = ""
    if m := re.search(r"(The application applies to[^.]*\.(?:[^.]*\.)?)", hel):
        beskrivning = m.group(1).strip()

    universitet = []
    tabell = main.find("table")
    if tabell:
        land = ""
        for rad in tabell.find_all("tr"):
            celler = [_text(c) for c in rad.find_all(["td", "th"])]
            if not celler or celler[0] == "Country":
                continue
            if len(celler) >= 4:
                land, namn, platser, stip = celler[:4]
            elif len(celler) == 3:
                namn, platser, stip = celler
            else:
                continue
            if not namn:
                continue
            m_tal = re.match(r"\s*(\d+)", platser)
            universitet.append({
                "land": land, "namn": namn, "platser": int(m_tal[1]) if m_tal else None,
                "platser_text": platser, "stipendium": stip,
            })
    if not universitet or not mal:
        return None
    return {
        "omgang": omgang, "mal_termin": mal, "beskrivning": beskrivning,
        "senast_andrad": _senast_andrad(main), "kalla": URL_PLATSER, "universitet": universitet,
    }


# ---------------------------------------------------------------------------------------------
# TekNats avtalssida
# ---------------------------------------------------------------------------------------------

_HOPPA = re.compile(r"^(contact|contakt|kontakt|subject area restrictions|view all)", re.I)


def tolka_teknatsida(html: str) -> dict:
    """{relation_id: {"enhet", "land", "namn", "ovrigt", "restplatser", "nordtek", "core_id"}} plus
    sidans senaste ändringsdatum. Enheten är rubriken (fakulteten eller institutionen) ovanför tabellen.
    Rader utan länk till databasen (vissa institutioner) hamnar i "utan_lank" och matchas på namn."""
    main = _main(html)
    avtal: dict[str, dict] = {}
    utan_lank: list[dict] = []
    enhet = None
    for el in main.find_all(["h2", "h3", "table"]):
        if el.name in ("h2", "h3"):
            rubrik = _text(el)
            if rubrik and not _HOPPA.match(rubrik):
                enhet = rubrik
            continue
        rader = el.find_all("tr")
        if not rader:
            continue
        land = _text(rader[0].find(["th", "td"]))
        for rad in rader[1:]:
            celler = rad.find_all(["td", "th"])
            if not celler or not _text(celler[0]):
                continue
            ovrigt = _text(celler[1]) if len(celler) > 1 else ""
            rest = _text(celler[2]) if len(celler) > 2 else ""
            a = celler[0].find("a", href=True)
            q = urllib.parse.parse_qs(urllib.parse.urlparse(a["href"].replace("&amp;", "&")).query) if a else {}
            rel = (q.get("relation_id") or [None])[0]
            core = (q.get("core_id") or [None])[0]
            if not rel:
                utan_lank.append({"enhet": enhet, "land": land, "namn": _text(celler[0]), "ovrigt": ovrigt,
                                  "restplatser": rest, "nordtek": "nordtek" in ovrigt.lower()})
                continue
            post = avtal.setdefault(rel, {
                "core_id": core, "enhet": enhet, "land": land, "namn": _text(a),
                "ovrigt": ovrigt, "restplatser": rest, "nordtek": "nordtek" in ovrigt.lower(),
            })
            # Samma avtal kan stå under flera rubriker (t.ex. ENS Lyon) – behåll första enheten.
            if ovrigt and ovrigt not in post["ovrigt"]:
                post["ovrigt"] = (post["ovrigt"] + " · " + ovrigt).strip(" ·")
    oppen_omgang = None
    if m := re.search(r"application round from\s+(\d{1,2} \w+) to (\d{1,2} \w+)", _text(main), re.I):
        oppen_omgang = f"{m[1]}–{m[2]}"
    return {"avtal": avtal, "utan_lank": utan_lank, "senast_andrad": _senast_andrad(main),
            "omgang_text": oppen_omgang, "kalla": URL_TEKNAT}


# ---------------------------------------------------------------------------------------------
# Erasmusstipendiet
# ---------------------------------------------------------------------------------------------

_SV_TILL_KOD = {l.namn.lower(): kod for kod, l in geo.LANDER.items()}
_SV_TILL_KOD.update({"luxemburg": "LU", "liechtenstein": "LI", "bulgarien": "BG", "rumänien": "RO",
                     "nordmakedonien": "MK", "serbien": "RS", "malta": "MT", "cypern": "CY"})


def tolka_erasmus(html: str) -> dict:
    """{"grupper": [{"grupp": 1, "euro_per_manad": 580, "lander": {"BE": "Belgien", …}, "noter": {…}}],
    "ansokan": "1–15 november för utbytesstudier som påbörjas vårterminen", …}"""
    main = _main(html)
    rader = [r.strip() for r in main.get_text("\n").split("\n") if r.strip()]
    grupper: list[dict] = []
    aktuell = None
    for rad in rader:
        if m := re.match(r"^Grupp (\d)$", rad):
            aktuell = {"grupp": int(m[1]), "euro_per_manad": None, "lander": {}, "noter": {}}
            grupper.append(aktuell)
            continue
        if aktuell is None:
            continue
        if m := re.search(r"uppgår till (\d+) euro", rad):
            aktuell["euro_per_manad"] = int(m[1])
            continue
        if rad.startswith(("Inkluderingsstöd", "Resebidrag", "Språkkurs")):
            aktuell = None
            continue
        namn = re.sub(r"\s*\(.*\)\s*$", "", rad).strip()
        kod = _SV_TILL_KOD.get(namn.lower())
        if kod:
            aktuell["lander"][kod] = namn
            if "(" in rad:
                aktuell["noter"][kod] = rad[rad.index("(") + 1: rad.rindex(")")] if ")" in rad else ""
    hel = "\n".join(rader)
    var = re.search(r"(\d{1,2}–\d{1,2} \w+) för utbytesstudier som påbörjas vårterminen", hel)
    return {
        "grupper": [g for g in grupper if g["lander"]],
        "ansokan_var": var.group(1) if var else None,
        "senast_andrad": _senast_andrad(main),
        "kalla": URL_ERASMUS,
    }
