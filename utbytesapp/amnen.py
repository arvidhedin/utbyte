"""Ämnesområden: ISCED-koderna i avtalsdatabasen översatta till svenska kategorier, och en
genomskinlig regel för hur väl varje kategori passar teknisk fysik och dess inriktningar.

Matchningen är ett *förslag* för sortering – den säger inget om behörighet. Det gör avtalets
ämnesbegränsningar ("Subject area restrictions").
"""

from __future__ import annotations

import re

# Svenska namn på ISCED-F 2013-koder som förekommer i databasen (och närliggande).
ISCED_NAMN = {
    "03": "Samhällsvetenskap", "0311": "Nationalekonomi",
    "04": "Ekonomi och administration", "041": "Företagsekonomi", "0410": "Företagsekonomi",
    "0413": "Ledarskap och administration",
    "05": "Naturvetenskap, matematik och statistik",
    "051": "Biologi", "0510": "Biologi", "0511": "Biologi", "0512": "Biokemi",
    "052": "Miljövetenskap", "0521": "Miljövetenskap", "0522": "Naturmiljö",
    "053": "Fysikaliska vetenskaper", "0531": "Kemi", "0532": "Geovetenskap", "0533": "Fysik",
    "054": "Matematik och statistik", "0540": "Matematik och statistik", "0541": "Matematik",
    "0542": "Statistik",
    "06": "Informations- och kommunikationsteknik", "061": "Informations- och kommunikationsteknik",
    "0600": "Informations- och kommunikationsteknik", "0610": "Informations- och kommunikationsteknik",
    "0611": "Datoranvändning", "0612": "Databaser och nätverk", "0613": "Mjukvaruutveckling",
    "0619": "Informations- och kommunikationsteknik",
    "07": "Teknik, tillverkning och byggande", "071": "Teknik", "0710": "Teknik",
    "0711": "Kemiteknik", "0712": "Miljöteknik", "0713": "El- och energiteknik",
    "0714": "Elektronik och automation", "0715": "Maskinteknik", "0716": "Fordonsteknik",
    "072": "Tillverkning och processteknik", "0720": "Tillverkning och processteknik",
    "0722": "Material", "073": "Arkitektur och byggande", "0731": "Arkitektur", "0732": "Byggteknik",
    "10": "Tjänster", "1015": "Turism",
}

# Kategorier för filtret, i visningsordning.
ALLA = "Alla ämnen"
KATEGORIER = [
    ALLA, "Fysik", "Matematik och statistik", "Data och IT", "Teknik (brett)",
    "El, energi och elektronik", "Maskin och material", "Kemi och kemiteknik",
    "Geo- och miljövetenskap", "Biologi och biokemi", "Naturvetenskap (brett)", "Bygg", "Ekonomi och övrigt",
]


def kategori(kod: str) -> str:
    k = kod.strip()
    if k == "0533":
        return "Fysik"
    if k.startswith("054"):
        return "Matematik och statistik"
    if k.startswith("06"):
        return "Data och IT"
    if k in ("0713", "0714"):
        return "El, energi och elektronik"
    if k in ("0715", "0716", "0722", "072", "0720"):
        return "Maskin och material"
    if k in ("0531", "0711"):
        return "Kemi och kemiteknik"
    if k in ("0532", "0712") or k.startswith("052"):
        return "Geo- och miljövetenskap"
    if k.startswith("051"):
        return "Biologi och biokemi"
    if k.startswith("073"):
        return "Bygg"
    if k in ("07", "071", "0710"):
        return "Teknik (brett)"
    if k in ("05", "053"):
        return "Naturvetenskap (brett)"
    return "Ekonomi och övrigt"


_KOD = re.compile(r"^\s*(\d{2,4})\s*-\s*(.+?)\s*$")


def tolka_isced(text: str | None) -> list[dict]:
    """"0533 - Physics|| 0541 - Mathematics" -> [{"kod": "0533", "namn": "Fysik", "kategori": "Fysik"}, …]"""
    ut = []
    for del_ in (text or "").split("||"):
        m = _KOD.match(del_)
        if not m:
            continue
        kod = m[1]
        ut.append({"kod": kod, "namn": ISCED_NAMN.get(kod, m[2]), "engelska": m[2], "kategori": kategori(kod)})
    return ut


# ---------------------------------------------------------------------------------------------
# Matchning mot teknisk fysik (0–3). Nyckel None = ingen inriktning vald.
# ---------------------------------------------------------------------------------------------

INRIKTNINGAR = [
    "Tillämpad fysik", "Beräkningsteknik", "Hållbar energiteknik", "Inbyggda system", "Elektrifiering",
]

_MATCH: dict[str, dict[str | None, int]] = {
    ALLA: {None: 3},
    "Fysik": {None: 3, "Tillämpad fysik": 3, "Beräkningsteknik": 2, "Hållbar energiteknik": 2, "Inbyggda system": 2},
    "Matematik och statistik": {None: 2, "Beräkningsteknik": 3},
    "Data och IT": {None: 2, "Beräkningsteknik": 3, "Inbyggda system": 3, "Tillämpad fysik": 1, "Hållbar energiteknik": 1},
    "Teknik (brett)": {None: 2, "Hållbar energiteknik": 3, "Inbyggda system": 2, "Elektrifiering": 3},
    "El, energi och elektronik": {None: 2, "Inbyggda system": 3, "Hållbar energiteknik": 3, "Elektrifiering": 3,
                                  "Beräkningsteknik": 1},
    "Maskin och material": {None: 2, "Beräkningsteknik": 1, "Inbyggda system": 1},
    "Kemi och kemiteknik": {None: 1},
    "Geo- och miljövetenskap": {None: 1},
    "Biologi och biokemi": {None: 0},
    "Naturvetenskap (brett)": {None: 2},
    "Bygg": {None: 1},
    "Ekonomi och övrigt": {None: 0},
}

MATCH_TEXT = {3: "Mycket bra", 2: "Bra", 1: "Möjlig", 0: "Svag"}

# För avtal med "alla ämnen": vilka kurstyper som är viktigast (primära) och näst viktigast per inriktning.
KURSTYP_VIKT: dict[str | None, tuple[tuple[str, ...], tuple[str, ...]]] = {
    None: (("teknik", "fysik"), ("matematik", "data")),
    "Tillämpad fysik": (("fysik",), ("teknik", "matematik")),
    "Beräkningsteknik": (("data", "matematik"), ("fysik", "teknik")),
    "Hållbar energiteknik": (("teknik",), ("fysik",)),
    "Inbyggda system": (("teknik", "data"), ("fysik",)),
    "Elektrifiering": (("teknik",), ("fysik",)),
}
_KT_POANG = {"öppet": 3, "begränsat": 2, "oklart": 2, "stängt": 0}


def match_kurstyper(kt: dict, inriktning: str | None) -> int:
    """Matchning för avtal med alla ämnen, utifrån vilka kurstyper som är öppna enligt ämnesbegränsningen."""
    primara, sekundara = KURSTYP_VIKT.get(inriktning, KURSTYP_VIKT[None])
    poang = [_KT_POANG.get(kt.get(o, "oklart"), 2) for o in primara]
    # Utan inriktning väger teknik och fysik lika (medel); med inriktning räcker bästa primära kurstyp.
    p = int(sum(poang) / len(poang) + 0.5) if inriktning is None else max(poang)
    if p >= 2:
        return p
    s = max((_KT_POANG.get(kt.get(o, "oklart"), 2) for o in sekundara), default=0)
    return 2 if s == 3 else 1 if s == 2 else 0


def match(kategorier: list[str], inriktning: str | None, civilingenjor: bool = False) -> int:
    """Bästa matchning bland avtalets kategorier, +1 (max 3) för avtal riktade till
    civilingenjörsprogram ("Master of Science in Engineering")."""
    if not kategorier:
        return 1
    bast = 0
    for k in kategorier:
        tabell = _MATCH.get(k, {None: 0})
        bast = max(bast, tabell.get(inriktning, tabell[None]) if inriktning else tabell[None])
    if civilingenjor:
        bast = min(3, bast + 1)
    return bast


def regeltabell() -> list[dict]:
    """För sidan Om datan: hela matchningsregeln som tabell."""
    rader = []
    for kat in KATEGORIER:
        t = _MATCH[kat]
        rad = {"Ämneskategori": kat, "Ingen inriktning vald": MATCH_TEXT[t[None]]}
        for inr in INRIKTNINGAR:
            rad[inr] = MATCH_TEXT[t.get(inr, t[None])]
        rader.append(rad)
    return rader
