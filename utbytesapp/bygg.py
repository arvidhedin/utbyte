"""Bygger data/avtal.json av rådatan i data/radata/ och platslistorna i data/platslistor/.

Rena funktioner utan nätverk – körs av verktyg/hamta_avtal.py efter hämtning, eller fristående
med `python verktyg/hamta_avtal.py --bygg`.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from rapidfuzz import fuzz

from . import amnen, geo, kurstyper, moveon, text, tolka

ROT = Path(__file__).resolve().parent.parent
DATA = ROT / "data"
RADATA = DATA / "radata"
PLATSLISTOR = DATA / "platslistor"
AVTAL = DATA / "avtal.json"

# ---------------------------------------------------------------------------------------------
# Samordnande enheter
# ---------------------------------------------------------------------------------------------

ENHETER = {
    # nyckelord i avtalsnamnet -> (svenskt namn, kort namn, e-post)
    "Faculty of Science and Technology": ("Teknisk-naturvetenskapliga fakulteten", "TekNat (fakulteten)", "exchange-teknat@uu.se"),
    "Department of Physics and Astronomy": ("Institutionen för fysik och astronomi", "Fysik och astronomi", "erasmus@physics.uu.se"),
    "Department of Mathematics": ("Matematiska institutionen", "Matematik", "exchange@math.uu.se"),
    "Department of Information Technology": ("Institutionen för informationsteknologi", "Informationsteknologi", "ulrika.jaresund@it.uu.se"),
    "Department of Electrical Engineering": ("Institutionen för elektroteknik", "Elektroteknik", "anke.bender@angstrom.uu.se"),
    "Department of Civil and Industrial Engineering": ("Institutionen för samhällsbyggnad och industriell teknik", "Samhällsbyggnad och industriell teknik", "exchange-samint@angstrom.uu.se"),
    "Chemistry": ("Sektionen för kemi", "Kemi", "exchangechemistry@uu.se"),
    "Biology Education Centre": ("Biologiskt utbildningscentrum", "Biologi", "exchange@ibg.uu.se"),
    "Department of Earth Sciences": ("Institutionen för geovetenskaper", "Geovetenskaper", "exchange.students@geo.uu.se"),
    "Unit for International Mobility": ("Enheten för internationell mobilitet (centrala avtal)", "Centrala avtal", "mobility@uu.se"),
}

# Rubriker på TekNat-sidan -> nyckel ovan
_SIDRUBRIK = {
    "the faculty of science and technology": "Faculty of Science and Technology",
    "biology education centre": "Biology Education Centre",
    "section of chemistry": "Chemistry",
    "department of civil and industrial engineering": "Department of Civil and Industrial Engineering",
    "department of earth sciences": "Department of Earth Sciences",
    "department of electrical engineering": "Department of Electrical Engineering",
    "department of information technology": "Department of Information Technology",
    "department of mathematics": "Department of Mathematics",
    "department of physics and astronomy": "Department of Physics and Astronomy",
}


_GENERISKT = re.compile(r"^(teknat|all fields( of study)?|university-wide|nordtek network|erasmus sms|erasmus|icm|"
                        r"general university-wide exchange|subject-specific exchange)$", re.I)


def delnamn(avtalsnamn: str, enhet: str, *uninamn: str) -> str:
    """Det som skiljer avtalet från andra med samma universitet, t.ex. "Electricity and energy" eller
    "Okanagan Campus" ur "Erasmus SMS - TUM - Electricity and energy - TEKNAT - Faculty of …".
    Delar som bara är en bit av universitetets namn ("University of Galway") tas bort."""
    delar = [d.strip() for d in avtalsnamn.split(" - ")][2:]
    namn = " ".join(text.normalisera_namn(n) for n in uninamn if n)
    kvar = []
    for d in delar:
        if not d or _GENERISKT.match(d) or d.lower() in enhet.lower() or enhet.lower() in d.lower():
            continue
        nd = text.normalisera_namn(d)
        if nd and (nd in namn or set(nd.split()) <= set(namn.split())):
            continue
        if any(n.lower() in d.lower() for n in ENHETER) or d.lower().startswith(("department", "faculty", "section")):
            continue
        kvar.append(d)
    return " · ".join(kvar)


def enhet_ur_avtalsnamn(avtalsnamn: str, kanal: str) -> str:
    if kanal == "central":
        return "Unit for International Mobility"
    efter = avtalsnamn.split("TEKNAT", 1)[1] if "TEKNAT" in avtalsnamn else avtalsnamn
    for nyckel in ENHETER:
        if nyckel.lower() in efter.lower():
            return nyckel
    if "chemistry" in efter.lower():
        return "Chemistry"
    return "Faculty of Science and Technology"


# ---------------------------------------------------------------------------------------------
# Fält
# ---------------------------------------------------------------------------------------------

FALT = {
    "subject area restrictions": "Ämnesbegränsningar",
    "subject area": "Ämnesområde",
    "course catalogue": "Kurskatalog",
    "teaching language": "Undervisningsspråk",
    "general language requirements": "Språkkrav",
    "language preparation": "Språkförberedelser",
    "credit point conversion": "Poängomräkning",
    "semester dates": "Terminsdatum",
    "deadline at uppsala to apply for this exchange": "Sista ansökningsdag vid UU",
    "application deadlines at the host university for students chosen for this exchange": "Ansökningsdatum hos värduniversitetet",
    "application formalities": "Ansökningsformalia",
    "important documents for this university": "Viktiga dokument",
    "important information": "Viktig information",
    "publisher - important information": "Viktig information",
    "content": "Avtalet omfattar",
    "accommodation": "Boende",
    "fees": "Avgifter",
    "insurance": "Försäkring",
    "visa and residence permits": "Visum och uppehållstillstånd",
    "vaccinations/health requirements": "Vaccinationer och hälsa",
    "scholarships": "Stipendier",
    "grants/scholarships": "Stipendier",
    "disability support": "Stöd vid funktionsnedsättning",
    "description": "Om universitetet",
    "location": "Om orten",
    "more information": "Mer information",
    "website": "Webbplats",
    "contact for more information": "Kontakt",
    "coordinator email": "Koordinatorns e-post",
    "document": "Dokument",
}
FALTORDNING = list(dict.fromkeys(FALT.values()))

_HOPPA_FALT = {"photos", "exchange programme", "type of agreement", "partner institution",
               "subject area (isced code)", "level", "degree-specific exchange programme"}


def _falt(relationer: list[dict]) -> tuple[dict[str, str], dict[str, dict]]:
    """Råa fält (engelska nycklar, HTML) och visningsfält (svenska nycklar, Markdown + text)."""
    ra: dict[str, str] = {}
    for e in relationer:
        nyckel = (e.get("shortname") or "").strip().lower()
        varde = (e.get("fullname") or "").strip()
        if nyckel and varde:
            ra[nyckel] = (ra[nyckel] + "<br>" + varde) if nyckel in ra else varde
    visning: dict[str, dict] = {}
    for nyckel, varde in ra.items():
        if nyckel in _HOPPA_FALT:
            continue
        etikett = FALT.get(nyckel, nyckel.capitalize())
        md = text.html_till_md(varde)
        if not md:
            continue
        if etikett in visning:  # t.ex. två varianter av "Viktig information"
            visning[etikett]["md"] += "\n\n" + md
            visning[etikett]["text"] += " " + text.html_till_text(varde)
        else:
            visning[etikett] = {"md": md, "text": text.html_till_text(varde), "lankar": text.lankar(varde)}
    return ra, visning


def _nivaer(s: str) -> list[str]:
    s = s.lower()
    ut = []
    if "bachelor" in s or "undergraduate" in s:
        ut.append("grund")
    if "master" in s or "postgraduate" in s:
        ut.append("avancerad")
    if "doctor" in s or "phd" in s:
        ut.append("forskar")
    return ut


def _typ(program: str, avtalsnamn: str, kanal: str) -> tuple[str, bool, bool]:
    """(typ, erasmus, icm)"""
    p = program.lower()
    icm = "icm" in p
    erasmus = "erasmus sms" in p
    if icm:
        return "Erasmus ICM", False, True
    if erasmus and "nordtek" in avtalsnamn.lower():
        return "Erasmus (Nordtek)", True, False
    if erasmus:
        return "Erasmus", True, False
    if "subject-specific" in p:
        return "Ämnesspecifikt", False, False
    if "university-wide" in p:
        return "Universitetsövergripande", False, False
    return "Övrigt", False, False


# ---------------------------------------------------------------------------------------------
# Namnmatchning (platslistor och TekNat-sidans olänkade rader)
# ---------------------------------------------------------------------------------------------

_LANDALIAS = {
    "united states of america": "united states", "usa": "united states", "south korea": "korea, republic of",
    "korea": "korea, republic of", "the netherlands": "netherlands", "scotland": "united kingdom",
    "turkey": "türkiye", "czechia": "czech republic", "hong kong": "china",
}


def _land_norm(s: str) -> str:
    s = (s or "").strip().lower()
    return _LANDALIAS.get(s, s)


def _varianter(namn: str) -> list[str]:
    """"Helsingin Yliopisto (University of Helsinki)" -> [hela, utan parentes, parentesens innehåll]."""
    ut = [namn]
    utan = re.sub(r"\([^)]*\)", " ", namn).strip()
    if utan and utan != namn:
        ut.append(utan)
    ut += [m for m in re.findall(r"\(([^)]{6,})\)", namn)]
    return ut


def _likhet(a: str, b: str) -> float:
    """0–100. Medel av token_set (tål extra ord) och token_sort (straffar extra ord), så att
    "University of Sydney" inte vinner över "University of Technology Sydney"."""
    bast = 0.0
    for va in _varianter(a):
        for vb in _varianter(b):
            na, nb = text.normalisera_namn(va), text.normalisera_namn(vb)
            if not na or not nb:
                continue
            poang = (fuzz.token_set_ratio(na, nb) + fuzz.token_sort_ratio(na, nb)) / 2
            ta, tb = text.namntoken(va), text.namntoken(vb)
            if ta and tb and not ta & tb:
                poang = min(poang, 60)  # inga gemensamma särskiljande ord (t.ex. bara "University of")
            bast = max(bast, poang)
    fa, fb = text.forkortning(a), text.forkortning(b)
    if (fa and fa in text.normalisera_namn(b).split()) or (fb and fb in text.normalisera_namn(a).split()):
        bast = max(bast, 95)
    return bast


def basta_kandidat(namn: str, land: str, kandidater: list[dict]) -> tuple[dict | None, float]:
    """Bästa kandidat i samma land och dess poäng. Kandidat: {"namn": [namnvarianter…], "land": …}"""
    bast, bast_poang = None, 0.0
    for k in kandidater:
        if land and _land_norm(k["land"]) != _land_norm(land):
            continue
        poang = max((_likhet(namn, v) for v in k["namn"] if v), default=0.0)
        if poang > bast_poang:
            bast, bast_poang = k, poang
    return bast, bast_poang


def matcha(namn: str, land: str, kandidater: list[dict], troskel: float = 82) -> dict | None:
    bast, poang = basta_kandidat(namn, land, kandidater)
    return bast if poang >= troskel else None


def tilldela(rader: list[dict], kandidater: list[dict], troskel: float = 82) -> list[tuple[dict, dict | None]]:
    """Matchar varje rad mot högst en kandidat och varje kandidat mot högst en rad (bästa först)."""
    forslag = []
    for i, rad in enumerate(rader):
        k, poang = basta_kandidat(rad["namn"], rad.get("land", ""), kandidater)
        forslag.append((poang, i, k))
    tagna: set[int] = set()
    resultat: dict[int, dict | None] = {}
    for poang, i, k in sorted(forslag, key=lambda f: -f[0]):
        if k is not None and poang >= troskel and id(k) not in tagna:
            tagna.add(id(k))
            resultat[i] = k
        else:
            resultat[i] = None
    return [(rad, resultat[i]) for i, rad in enumerate(rader)]


# ---------------------------------------------------------------------------------------------
# Bygg
# ---------------------------------------------------------------------------------------------

def _las(fil: Path, standard=None):
    return json.loads(fil.read_text(encoding="utf-8")) if fil.exists() else standard


def _institution(post: dict, detalj: dict | None) -> dict:
    inst = {}
    if detalj:
        for e in detalj.get("institutions", []):
            inst[(e.get("shortname") or "").strip().lower()] = (e.get("fullname") or "").strip()

    def url(nyckel: str) -> str | None:
        lankar = text.lankar(inst.get(nyckel))
        return lankar[0][1] if lankar else text.laga_url(text.html_till_text(inst.get(nyckel)) or None)

    try:
        lat, lon = float(post.get("latitude") or ""), float(post.get("longitude") or "")
    except ValueError:
        lat = lon = None
    return {
        "id": post["core_id"],
        "namn": post["universityname"].strip(),
        "namn_en": inst.get("name (english)") or None,
        "land_kod": post.get("country"),
        "land_en": post.get("country_fullname"),
        "stad": inst.get("city") or None,
        "lat": lat, "lon": lon,
        "webb": url("url"),
        "webb_int": url("website for international students"),
        "kurskatalog": url("course catalogue"),
        "erasmuskod": inst.get("erasmus code") or None,
    }


def _rapporter(detalj: dict | None) -> list[dict]:
    ut = []
    for rad in (detalj or {}).get("travelreports", []) or []:
        falt = {(e.get("shortname") or "").strip().lower(): (e.get("fullname") or "") for e in rad}
        lank = falt.get("exchange report", "")
        m = re.search(r"data-id='(\d+)'", lank)
        if not m:
            continue
        # Rapportskrivarens namn sparas inte här (avtal.json kan delas); det finns i rapporten själv.
        ut.append({"fil_id": m.group(1), "ar": (falt.get("academic year") or falt.get("year") or "").strip()})
    return ut


def bygg(radata: Path = RADATA, platslistor: Path = PLATSLISTOR) -> dict:
    listor = {pub: _las(radata / f"moveon_lista_{pub}.json", {}) for pub in moveon.PUBLICERARE}
    teknatsida = _las(radata / "teknatsida.json", {"avtal": {}, "utan_lank": []})
    erasmus = _las(radata / "erasmus.json", {"grupper": []})
    hamtad = _las(radata / "hamtad.json", {})

    universitet: dict[str, dict] = {}
    avtal: list[dict] = []
    for pub, (kanal, _) in moveon.PUBLICERARE.items():
        for post in listor[pub].get("labelvalue", []):
            core, rel = post["core_id"], post["relation_id"]
            d = _las(radata / "detaljer" / f"{pub}_{core}_{rel}.json")
            detalj = None
            if d:
                detalj = next((x["informatics"][0] for x in d.get("labelvalue", []) if x.get("core_id") == core), None)
            relationer = (detalj or {}).get("relations") or post.get("informatics", [{}])[0].get("relations", [])
            ra, falt = _falt(relationer)
            program = ra.get("exchange programme", "")
            if "erasmus sms" not in program.lower() and "sta" in re.split(r"\W+", program.lower()):
                continue  # Erasmus STA = lärarutbyte, inte för studenter
            avtalsnamn = text.html_till_text(ra.get("type of agreement", ""))
            typ, ar_erasmus, icm = _typ(program, avtalsnamn, kanal)
            enhet = enhet_ur_avtalsnamn(avtalsnamn, kanal)
            uni = universitet.get(core) or _institution(post, detalj)
            if not uni.get("stad") and detalj:
                uni.update({k: v for k, v in _institution(post, detalj).items() if v})
            universitet[core] = uni

            isced = amnen.tolka_isced(text.html_till_text(ra.get("subject area (isced code)", "")))
            kategorier = list(dict.fromkeys(i["kategori"] for i in isced))
            if kanal == "central" and ("all fields" in avtalsnamn.lower() or "university-wide" in program.lower()):
                kategorier = [amnen.ALLA] + [k for k in kategorier if k != amnen.ALLA]

            sprak_text = falt.get("Undervisningsspråk", {}).get("text", "")
            sprakkrav_text = falt.get("Språkkrav", {}).get("text", "")
            omr_text = falt.get("Poängomräkning", {}).get("text", "")
            termin_text = falt.get("Terminsdatum", {}).get("text", "")
            begr_text = falt.get("Ämnesbegränsningar", {}).get("text", "")
            sista_text = falt.get("Sista ansökningsdag vid UU", {}).get("text", "")
            examensprogram = text.html_till_text(ra.get("degree-specific exchange programme", ""))

            avtal.append({
                "id": f"{pub}-{core}-{rel}",
                "pub": pub, "core_id": core, "relation_id": rel, "kanal": kanal,
                "typ": typ, "erasmus": ar_erasmus, "icm": icm,
                "program": program, "avtalsnamn": avtalsnamn,
                "enhet": enhet, "enhet_sv": ENHETER[enhet][0], "enhet_kort": ENHETER[enhet][1],
                "delnamn": delnamn(avtalsnamn, enhet, uni["namn"], uni.get("namn_en") or "", post["universityname"]),
                "kontakt": ENHETER[enhet][2],
                "nordtek": "nordtek" in avtalsnamn.lower(),
                "civilingenjor": "master of science in engineering" in examensprogram.lower(),
                "examensprogram": examensprogram or None,
                "isced": isced, "kategorier": kategorier,
                "nivaer": _nivaer(text.html_till_text(ra.get("level", ""))),
                "falt": falt,
                "sprak_db": tolka.sprak_i_text(sprak_text),
                "sprakkrav": tolka.sprakkrav(sprakkrav_text),
                "omrakningar": tolka.omrakningar(omr_text),
                "varmanader_db": tolka.varmanader(termin_text),
                "varvarning": tolka.varvarning(sprak_text, begr_text, sista_text, sprakkrav_text,
                                               falt.get("Viktig information", {}).get("text", "")),
                "rapporter": _rapporter(detalj),
                "detaljer_hamtade": detalj is not None,
                "url": moveon.avtalslank(pub, core, rel),
                "teknatsida": None, "platser": {},
            })

    for a in avtal:
        a["kurstyper"] = kurstyper.bedom(a)
    _fyll_sprak(avtal, universitet)
    _fyll_terminer(avtal, universitet)
    _erasmus(avtal, universitet, erasmus)
    omatchat_teknat = _koppla_teknatsida(avtal, universitet, teknatsida)
    listor_meta, omatchat_platser = _koppla_platser(avtal, universitet, platslistor)

    return {
        "format": 1,
        "byggd": dt.datetime.now().isoformat(timespec="seconds"),
        "hamtad": hamtad,
        "erasmus": erasmus,
        "platslistor": listor_meta,
        "teknatsida": {k: teknatsida.get(k) for k in ("senast_andrad", "omgang_text", "kalla")},
        "universitet": universitet,
        "avtal": avtal,
        "omatchat": {"platser": omatchat_platser, "teknatsida": omatchat_teknat},
    }


def _fyll_sprak(avtal: list[dict], universitet: dict) -> None:
    """Undervisningsspråk: databasen > annat avtal med samma universitet > landets språk (obekräftat)."""
    per_uni: dict[str, dict] = {}
    for a in avtal:
        if a["sprak_db"]:
            per_uni.setdefault(a["core_id"], a)
    for a in avtal:
        uni = universitet[a["core_id"]]
        if a["sprak_db"]:
            a["sprak"] = {"lista": a["sprak_db"], "status": "databasen", "fran": None}
        elif a["core_id"] in per_uni:
            kalla = per_uni[a["core_id"]]
            a["sprak"] = {"lista": kalla["sprak_db"], "status": "samma_universitet", "fran": kalla["id"]}
        else:
            lokala, eng = geo.lokala_sprak(uni["land_kod"], uni.get("stad") or "", uni["namn"], uni.get("namn_en") or "")
            lista = list(dict.fromkeys(["engelska", *lokala])) if not eng else list(dict.fromkeys(["engelska", *lokala]))
            a["sprak"] = {"lista": lista, "status": "obekraftad", "fran": None,
                          "engelska_masterniva": not eng}


def _fyll_terminer(avtal: list[dict], universitet: dict) -> None:
    per_uni: dict[str, tuple[int, int]] = {}
    for a in avtal:
        if a["varmanader_db"]:
            per_uni.setdefault(a["core_id"], tuple(a["varmanader_db"]))
    for a in avtal:
        uni = universitet[a["core_id"]]
        if a["varmanader_db"]:
            a["varmanader"] = {"manader": list(a["varmanader_db"]), "status": "databasen"}
        elif a["core_id"] in per_uni:
            a["varmanader"] = {"manader": list(per_uni[a["core_id"]]), "status": "samma_universitet"}
        else:
            kod = uni["land_kod"]
            if "hong kong" in f"{uni.get('stad') or ''} {uni['namn']}".lower():
                manader = (1, 5)
            else:
                manader = geo.TYPISK_VARTERMIN.get(kod)
            a["varmanader"] = {"manader": list(manader) if manader else None, "status": "typiskt"}


def _erasmus(avtal: list[dict], universitet: dict, erasmus: dict) -> None:
    belopp: dict[str, tuple[int, int, str]] = {}
    for g in erasmus.get("grupper", []):
        for kod in g["lander"]:
            belopp[kod] = (g["grupp"], g["euro_per_manad"], g["noter"].get(kod, ""))
    for a in avtal:
        a["erasmus_stipendium"] = None
        if not a["erasmus"]:
            continue
        kod = universitet[a["core_id"]]["land_kod"]
        if kod in belopp:
            grupp, euro, not_ = belopp[kod]
            if not_ and "bern" in not_.lower() and "bern" not in universitet[a["core_id"]]["namn"].lower():
                continue
            a["erasmus_stipendium"] = {"grupp": grupp, "euro_per_manad": euro}


def _koppla_teknatsida(avtal: list[dict], universitet: dict, sida: dict) -> list[dict]:
    per_rel = {a["relation_id"]: a for a in avtal if a["kanal"] == "teknat"}
    for rel, info in sida.get("avtal", {}).items():
        if rel in per_rel:
            per_rel[rel]["teknatsida"] = info
    omatchat = []
    per_enhet: dict[str | None, list[dict]] = {}
    for rad in sida.get("utan_lank", []):
        per_enhet.setdefault(_SIDRUBRIK.get((rad.get("enhet") or "").strip().lower()), []).append(rad)
    for enhet, rader in per_enhet.items():
        kandidater = [
            {"namn": [universitet[a["core_id"]]["namn"], universitet[a["core_id"]].get("namn_en") or "",
                      f'{universitet[a["core_id"]]["namn"]} {universitet[a["core_id"]].get("stad") or ""}'],
             "land": universitet[a["core_id"]]["land_en"], "avtal": a}
            for a in avtal if a["kanal"] == "teknat" and a["teknatsida"] is None and (enhet is None or a["enhet"] == enhet)
        ]
        kvar = []
        for rad, traff in tilldela([{**r, "namn": _SIDALIAS.get(r["namn"], r["namn"])} for r in rader],
                                   kandidater, troskel=72):
            if traff:
                traff["avtal"]["teknatsida"] = {**rad, "core_id": traff["avtal"]["core_id"], "matchad_pa_namn": True}
            else:
                kvar.append(rad)
        # Reserv: unik stad i namnet, t.ex. "University of Kiel" -> universitetet i Kiel.
        for rad in kvar:
            ord_ = set(text.normalisera_namn(rad["namn"]).split())
            traffar = [k for k in kandidater if k["avtal"]["teknatsida"] is None
                       and _land_norm(k["land"]) == _land_norm(rad["land"])
                       and text.normalisera_namn(universitet[k["avtal"]["core_id"]].get("stad") or "-") in ord_]
            if len(traffar) == 1:
                traffar[0]["avtal"]["teknatsida"] = {**rad, "core_id": traffar[0]["avtal"]["core_id"], "matchad_pa_namn": True}
            else:
                omatchat.append(rad)
    return omatchat


# Namn på TekNat-sidan som inte går att matcha automatiskt (universitet som bytt namn).
_SIDALIAS = {
    "Université Pierre et Marie Curie": "Sorbonne Université",
}


def _koppla_platser(avtal: list[dict], universitet: dict, mapp: Path) -> tuple[dict, list[dict]]:
    meta: dict[str, dict] = {}
    omatchat: list[dict] = []
    centrala = [
        {"namn": [universitet[a["core_id"]]["namn"], universitet[a["core_id"]].get("namn_en") or "",
                  a["avtalsnamn"].split(" - ", 1)[-1]],
         "land": universitet[a["core_id"]]["land_en"], "avtal": a}
        for a in avtal if a["kanal"] == "central"
    ]
    for fil in sorted(mapp.glob("*.json")):
        lista = json.loads(fil.read_text(encoding="utf-8"))
        mal = lista["mal_termin"]
        meta[mal] = {k: v for k, v in lista.items() if k != "universitet"} | {"antal": len(lista["universitet"])}
        for rad, traff in tilldela(lista["universitet"], centrala):
            if traff:
                traff["avtal"]["platser"][mal] = {
                    "platser": rad.get("platser"), "platser_text": rad.get("platser_text"),
                    "stipendium": rad.get("stipendium"), "namn_pa_listan": rad["namn"],
                }
            else:
                omatchat.append({"mal_termin": mal, **rad})
    return meta, omatchat


def spara(data: dict, fil: Path = AVTAL) -> None:
    fil.parent.mkdir(parents=True, exist_ok=True)
    tmp = fil.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(fil)
