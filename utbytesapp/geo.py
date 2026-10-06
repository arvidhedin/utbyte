"""Länder: svenska namn, världsdel, region och lokala språk – plus avstånd från Uppsala.

Tabellen är statisk (fakta om länderna, inte om avtalen). Språken används bara som
*obekräftad* reserv när UU:s avtalsdatabas saknar uppgift om undervisningsspråk.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Land:
    kod: str
    namn: str
    varldsdel: str
    region: str
    sprak: tuple[str, ...]  # språk som universitet i landet normalt undervisar på
    engelsktalande: bool = False  # engelska är huvudspråk i högre utbildning
    flagga: str = ""


def _flagga(kod: str) -> str:
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in kod.upper())


_RADER = [
    # kod, namn, världsdel, region, språk, engelsktalande
    ("AL", "Albanien", "Europa", "Sydosteuropa", ("albanska",), False),
    ("AT", "Österrike", "Europa", "Centraleuropa", ("tyska",), False),
    ("AU", "Australien", "Oceanien", "Oceanien", ("engelska",), True),
    ("BE", "Belgien", "Europa", "Västeuropa", ("nederländska", "franska"), False),
    ("BR", "Brasilien", "Sydamerika", "Latinamerika", ("portugisiska",), False),
    ("BT", "Bhutan", "Asien", "Sydasien", ("engelska",), True),
    ("CA", "Kanada", "Nordamerika", "Nordamerika", ("engelska", "franska"), True),
    ("CH", "Schweiz", "Europa", "Centraleuropa", ("tyska", "franska", "italienska"), False),
    ("CL", "Chile", "Sydamerika", "Latinamerika", ("spanska",), False),
    ("CN", "Kina", "Asien", "Östasien", ("kinesiska",), False),
    ("CO", "Colombia", "Sydamerika", "Latinamerika", ("spanska",), False),
    ("CY", "Cypern", "Europa", "Sydeuropa", ("grekiska", "engelska"), False),
    ("CZ", "Tjeckien", "Europa", "Centraleuropa", ("tjeckiska",), False),
    ("DE", "Tyskland", "Europa", "Centraleuropa", ("tyska",), False),
    ("DK", "Danmark", "Europa", "Norden", ("danska",), False),
    ("EE", "Estland", "Europa", "Baltikum", ("estniska",), False),
    ("ES", "Spanien", "Europa", "Sydeuropa", ("spanska",), False),
    ("FI", "Finland", "Europa", "Norden", ("finska", "svenska"), False),
    ("FR", "Frankrike", "Europa", "Västeuropa", ("franska",), False),
    ("GB", "Storbritannien", "Europa", "Västeuropa", ("engelska",), True),
    ("GE", "Georgien", "Asien", "Kaukasus", ("georgiska",), False),
    ("GH", "Ghana", "Afrika", "Afrika söder om Sahara", ("engelska",), True),
    ("GR", "Grekland", "Europa", "Sydeuropa", ("grekiska",), False),
    ("HR", "Kroatien", "Europa", "Sydosteuropa", ("kroatiska",), False),
    ("HU", "Ungern", "Europa", "Centraleuropa", ("ungerska",), False),
    ("ID", "Indonesien", "Asien", "Sydostasien", ("indonesiska",), False),
    ("IE", "Irland", "Europa", "Västeuropa", ("engelska",), True),
    ("IN", "Indien", "Asien", "Sydasien", ("engelska",), True),
    ("IS", "Island", "Europa", "Norden", ("isländska",), False),
    ("IT", "Italien", "Europa", "Sydeuropa", ("italienska",), False),
    ("JO", "Jordanien", "Asien", "Mellanöstern", ("arabiska",), False),
    ("JP", "Japan", "Asien", "Östasien", ("japanska",), False),
    ("KR", "Sydkorea", "Asien", "Östasien", ("koreanska",), False),
    ("KZ", "Kazakstan", "Asien", "Centralasien", ("kazakiska", "ryska"), False),
    ("LT", "Litauen", "Europa", "Baltikum", ("litauiska",), False),
    ("LV", "Lettland", "Europa", "Baltikum", ("lettiska",), False),
    ("MA", "Marocko", "Afrika", "Nordafrika", ("arabiska", "franska"), False),
    ("MT", "Malta", "Europa", "Sydeuropa", ("engelska",), True),
    ("MX", "Mexiko", "Nordamerika", "Latinamerika", ("spanska",), False),
    ("NL", "Nederländerna", "Europa", "Västeuropa", ("nederländska",), False),
    ("NO", "Norge", "Europa", "Norden", ("norska",), False),
    ("NZ", "Nya Zeeland", "Oceanien", "Oceanien", ("engelska",), True),
    ("PL", "Polen", "Europa", "Centraleuropa", ("polska",), False),
    ("PS", "Palestina", "Asien", "Mellanöstern", ("arabiska",), False),
    ("PT", "Portugal", "Europa", "Sydeuropa", ("portugisiska",), False),
    ("RU", "Ryssland", "Europa", "Östeuropa", ("ryska",), False),
    ("SG", "Singapore", "Asien", "Sydostasien", ("engelska",), True),
    ("SI", "Slovenien", "Europa", "Centraleuropa", ("slovenska",), False),
    ("SK", "Slovakien", "Europa", "Centraleuropa", ("slovakiska",), False),
    ("TH", "Thailand", "Asien", "Sydostasien", ("thailändska",), False),
    ("TR", "Turkiet", "Europa", "Sydosteuropa", ("turkiska",), False),
    ("TW", "Taiwan", "Asien", "Östasien", ("kinesiska",), False),
    ("TZ", "Tanzania", "Afrika", "Afrika söder om Sahara", ("engelska",), True),
    ("UA", "Ukraina", "Europa", "Östeuropa", ("ukrainska",), False),
    ("UG", "Uganda", "Afrika", "Afrika söder om Sahara", ("engelska",), True),
    ("US", "USA", "Nordamerika", "Nordamerika", ("engelska",), True),
    ("UY", "Uruguay", "Sydamerika", "Latinamerika", ("spanska",), False),
    ("VN", "Vietnam", "Asien", "Sydostasien", ("vietnamesiska",), False),
    ("ZA", "Sydafrika", "Afrika", "Afrika söder om Sahara", ("engelska",), True),
]

LANDER: dict[str, Land] = {
    kod: Land(kod, namn, vd, reg, sprak, eng, _flagga(kod)) for kod, namn, vd, reg, sprak, eng in _RADER
}

VARLDSDELAR = ["Europa", "Nordamerika", "Sydamerika", "Asien", "Oceanien", "Afrika"]
REGIONER = [
    "Norden", "Baltikum", "Västeuropa", "Centraleuropa", "Sydeuropa", "Sydosteuropa", "Östeuropa",
    "Nordamerika", "Latinamerika", "Östasien", "Sydostasien", "Sydasien", "Centralasien", "Kaukasus",
    "Mellanöstern", "Oceanien", "Nordafrika", "Afrika söder om Sahara",
]

# Städer/universitet där undervisningsspråket skiljer sig från resten av landet.
_SPRAK_UNDANTAG = [
    ("hong kong", ("engelska",), True),
    ("montréal", ("franska",), False),
    ("montreal", ("franska",), False),
    ("québec", ("franska",), False),
    ("åbo akademi", ("svenska",), False),
    ("louvain", ("franska",), False),
    ("namur", ("franska",), False),
    ("bruxelles", ("franska",), False),
    ("leuven", ("nederländska",), False),
    ("gent", ("nederländska",), False),
    ("antwerp", ("nederländska",), False),
    ("odisee", ("nederländska",), False),
    ("lausanne", ("franska",), False),
    ("genève", ("franska",), False),
    ("barcelona", ("spanska", "katalanska"), False),
    ("catalunya", ("spanska", "katalanska"), False),
    ("país vasco", ("spanska", "baskiska"), False),
    ("pais vasco", ("spanska", "baskiska"), False),
]


def land(kod: str | None) -> Land:
    if kod and kod in LANDER:
        return LANDER[kod]
    return Land(kod or "??", kod or "Okänt land", "Okänd", "Okänd", (), False, "")


def lokala_sprak(landkod: str, *texter: str) -> tuple[tuple[str, ...], bool]:
    """Troliga undervisningsspråk (utöver engelska på masternivå) för ett universitet.
    Returnerar (språk, engelsktalande)."""
    lagre = " ".join(t.lower() for t in texter if t)
    for nyckel, sprak, eng in _SPRAK_UNDANTAG:
        if nyckel in lagre:
            return sprak, eng
    l = land(landkod)
    return l.sprak, l.engelsktalande


# Uppsala (Ångströmlaboratoriet) för avståndsberäkning.
UPPSALA = (59.8395, 17.6476)


def avstand_km(lat: float | None, lon: float | None, fran: tuple[float, float] = UPPSALA) -> float | None:
    """Fågelvägen enligt haversine-formeln."""
    if lat is None or lon is None:
        return None
    r = 6371.0
    p1, p2 = math.radians(fran[0]), math.radians(lat)
    dp, dl = p2 - p1, math.radians(lon - fran[1])
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# Typisk vårtermin per land (månad 1–12). Gäller som *obekräftad* fingervisning när databasen
# saknar terminsdatum – universitetens egna kalendrar går före.
TYPISK_VARTERMIN: dict[str, tuple[int, int]] = {
    "US": (1, 5), "CA": (1, 4), "MX": (1, 5), "BR": (3, 7), "CL": (3, 7), "CO": (2, 6), "UY": (3, 7),
    "AU": (2, 6), "NZ": (2, 6),
    "JP": (4, 8), "KR": (3, 6), "CN": (2, 7), "TW": (2, 6), "SG": (1, 5), "TH": (1, 5), "VN": (2, 6),
    "ID": (2, 6), "IN": (1, 5), "BT": (2, 6), "KZ": (1, 5), "GE": (2, 6), "JO": (2, 6), "PS": (2, 6),
    "DE": (4, 7), "AT": (3, 6), "CH": (2, 6), "FR": (1, 6), "BE": (2, 6), "NL": (2, 7), "GB": (1, 6),
    "IE": (1, 5), "ES": (2, 6), "PT": (2, 7), "IT": (2, 7), "GR": (2, 6), "MT": (2, 6), "CY": (1, 5),
    "DK": (2, 6), "NO": (1, 6), "FI": (1, 5), "IS": (1, 5), "EE": (2, 6), "LV": (2, 6), "LT": (2, 6),
    "PL": (2, 6), "CZ": (2, 6), "SK": (2, 6), "SI": (2, 6), "HR": (3, 6), "HU": (2, 6), "AL": (2, 6),
    "TR": (2, 6), "UA": (2, 6), "RU": (2, 6), "MA": (2, 6), "ZA": (2, 6), "TZ": (3, 7), "UG": (2, 6),
    "GH": (1, 5),
}

MANADER = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]


def manadsintervall(start: int, slut: int) -> str:
    return f"{MANADER[start - 1]}–{MANADER[slut - 1]}"
