"""Läser (bara läser) din data i kursappen (~/kurser) för meritvärde, urvalsgrupp och termin 8.

Kursappen ändras aldrig härifrån. Saknas kursappen fungerar resten av utbytesappen ändå.

Urvalsreglerna (TekNat, ansökningsguiden):
- Meritvärde = genomsnittsbetyg + meriterande uppdrag (max 0,3).
- Genomsnittsbetyget räknas på alla kurser vid UU med betygsskala U, 3, 4, 5 som är rapporterade som
  avslutade i Ladok vid sista ansökningsdag, viktade med hp, som geometriskt medelvärde med en decimal.
- Urvalsgrupp efter antal ej avklarade hp inom programmet (bara kurser med rapporterade resultat):
  1: 0–5 hp, 2: 6–10 hp, 3: 11–20 hp, 4: ≥ 21 hp.
Centrala avtal: antal hp med högsta betyg (5, VG, A) – även delkurser med högsta betyg när slutbetyget
är lägre – används för rangordning tillsammans med urvalsgrupp, uppdrag och lottnummer.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

TOPPBETYG = {"5", "VG", "A"}
GODKANDA = {"3", "4", "5", "G", "VG", "A", "B", "C", "D", "E", "P"}


@dataclass
class Kursdata:
    mapp: Path
    kurser: list[dict]
    katalog: dict
    studieplaner: dict
    installningar: dict

    @property
    def inriktning(self) -> str | None:
        return self.installningar.get("inriktning")

    @property
    def profil(self) -> str | None:
        return self.installningar.get("profil")


def las(mapp: str | Path | None) -> Kursdata | None:
    if not mapp:
        return None
    mapp = Path(mapp).expanduser()
    data = mapp / "data"
    try:
        mina = json.loads((data / "mina_kurser.json").read_text(encoding="utf-8"))
        katalog = json.loads((data / "katalog.json").read_text(encoding="utf-8")) if (data / "katalog.json").exists() else {}
        planer = json.loads((data / "studieplaner.json").read_text(encoding="utf-8")) if (data / "studieplaner.json").exists() else {}
    except (OSError, json.JSONDecodeError):
        return None
    return Kursdata(mapp, mina.get("kurser", []), katalog, planer, mina.get("installningar", {}))


def _hp(k: dict, katalog: dict) -> float:
    return float(k.get("hp") or katalog.get(k.get("kod") or "", {}).get("hp") or 0)


def _skala(k: dict, katalog: dict) -> str | None:
    return k.get("skala") or katalog.get(k.get("kod") or "", {}).get("betygsskala")


def _vid_uu(k: dict) -> bool:
    larosate = (k.get("larosate") or "").lower()
    return k.get("status") != "tillgodoräknad" and (not larosate or "uppsala" in larosate)


# ---------------------------------------------------------------------------------------------
# Meritvärde (TekNat)
# ---------------------------------------------------------------------------------------------

def meritvarde(kd: Kursdata, extrapoang: float = 0.0, med_planerade: bool = False) -> dict:
    """Geometriskt hp-viktat snitt över avslutade UU-kurser med skala U/3/4/5.
    med_planerade=True tar också med pågående/planerade kurser som har ett planerat betyg."""
    rader = []
    for k in kd.kurser:
        if not _vid_uu(k):
            continue
        skala = _skala(k, kd.katalog)
        if skala not in (None, "TH"):
            continue
        betyg = k.get("betyg") if k.get("status") == "klar" else (k.get("planerat_betyg") if med_planerade else None)
        if betyg not in ("3", "4", "5"):
            continue
        hp = _hp(k, kd.katalog)
        if hp > 0:
            rader.append({"kod": k.get("kod"), "namn": k.get("namn") or kd.katalog.get(k.get("kod") or "", {}).get("namn"),
                          "hp": hp, "betyg": int(betyg), "planerat": k.get("status") != "klar"})
    hp_sum = sum(r["hp"] for r in rader)
    if not hp_sum:
        return {"geometriskt": None, "avrundat": None, "aritmetiskt": None, "hp": 0, "kurser": rader,
                "extrapoang": extrapoang, "meritvarde": None}
    geo = math.exp(sum(r["hp"] * math.log(r["betyg"]) for r in rader) / hp_sum)
    ari = sum(r["hp"] * r["betyg"] for r in rader) / hp_sum
    avr = math.floor(geo * 10 + 0.5) / 10  # en decimal, avrundat uppåt vid ,x5
    extra = min(max(extrapoang, 0.0), 0.3)
    return {"geometriskt": geo, "avrundat": avr, "aritmetiskt": ari, "hp": hp_sum, "kurser": rader,
            "extrapoang": extra, "meritvarde": round(avr + extra, 1)}


# ---------------------------------------------------------------------------------------------
# Toppbetyg (centrala avtal)
# ---------------------------------------------------------------------------------------------

def toppbetyg(kd: Kursdata) -> dict:
    """hp med högsta betyg. Slutbetyg 5/VG/A ger kursens hp; annars räknas delkurser med högsta betyg.
    Ett toppbetyg räknas bara en gång (inte både kurs och delkurs)."""
    rader = []
    for k in kd.kurser:
        if k.get("status") != "klar" or not _vid_uu(k):
            continue
        if k.get("betyg") in TOPPBETYG:
            rader.append({"kod": k.get("kod"), "namn": k.get("namn"), "hp": _hp(k, kd.katalog), "niva": "kurs"})
            continue
        moment_hp = sum(float(m.get("hp") or 0) for m in k.get("moment", []) if m.get("betyg") in TOPPBETYG)
        if moment_hp > 0:
            rader.append({"kod": k.get("kod"), "namn": k.get("namn"), "hp": moment_hp, "niva": "delkurs"})
    return {"hp": sum(r["hp"] for r in rader), "rader": rader}


# ---------------------------------------------------------------------------------------------
# Urvalsgrupp (TekNat)
# ---------------------------------------------------------------------------------------------

_TERMIN = re.compile(r"^(HT|VT|SO)(\d{4})$")


def _termin_slut(etikett: str) -> tuple[int, int]:
    """Ungefärligt slut (år, månad) för en termin vid UU."""
    m = _TERMIN.match(etikett or "")
    if not m:
        return (9999, 12)
    typ, ar = m[1], int(m[2])
    return {"HT": (ar + 1, 1), "VT": (ar, 6), "SO": (ar, 8)}[typ]


def urvalsgrupp(kd: Kursdata, per: tuple[int, int]) -> dict:
    """Uppskattar ej avklarade hp inom programmet vid en tidpunkt (år, månad).
    Räknar programkurser som borde vara avslutade (sista termin slut före tidpunkten) men inte är klara,
    minus delkurser som är godkända. Pågående kurser som inte är slut räknas inte."""
    i_plan = set()
    for plan in kd.studieplaner.values():
        i_plan |= {r["kod"] for r in plan.get("kurser", [])}
    rader = []
    for k in kd.kurser:
        if k.get("status") in ("klar", "tillgodoräknad", "planerad") or k.get("kod") not in i_plan:
            continue
        terminer = [p.get("termin") for p in k.get("placering") or [] if p.get("termin")] or [k.get("termin")]
        slut = max((_termin_slut(t) for t in terminer if t), default=(9999, 12))
        if slut >= per:
            continue
        klart = sum(float(m.get("hp") or 0) for m in k.get("moment", []) if m.get("betyg") in GODKANDA)
        kvar = max(_hp(k, kd.katalog) - klart, 0)
        if kvar > 0:
            rader.append({"kod": k.get("kod"), "namn": k.get("namn"), "kvar": kvar})
    summa = sum(r["kvar"] for r in rader)
    grupp = 1 if summa <= 5 else 2 if summa <= 10 else 3 if summa <= 20 else 4
    return {"hp": summa, "grupp": grupp, "rader": rader}


# ---------------------------------------------------------------------------------------------
# Termin 8 (vårterminen i årskurs 4 = VT2028)
# ---------------------------------------------------------------------------------------------

def inriktningar(kd: Kursdata, version: str) -> list[str]:
    plan = kd.studieplaner.get(version, {})
    return sorted({r["inriktning"] for r in plan.get("kurser", []) if r.get("inriktning")})


def termin_kurser(kd: Kursdata, version: str, termin: int, inriktning: str | None, profil: str | None) -> list[dict]:
    """Kurserna i en programtermin för vald inriktning/profil (plus gemensamma), en rad per kurs."""
    plan = kd.studieplaner.get(version, {})

    def hor_till(rinr: str | None) -> bool:
        if not rinr:
            return True  # gemensam kurs
        if not inriktning:
            return False
        if profil:
            return rinr in (inriktning, f"{inriktning}, profil {profil}")
        return rinr == inriktning or rinr.startswith(f"{inriktning}, profil ")

    ut: dict[str, dict] = {}
    for r in plan.get("kurser", []):
        rinr = r.get("inriktning")
        if r.get("termin") != termin or not hor_till(rinr):
            continue
        post = ut.setdefault(r["kod"], {
            "kod": r["kod"], "namn": r["namn"], "hp": r["hp"], "perioder": [], "obligatorisk": False,
            "noter": [], "inriktning": rinr,
        })
        if r.get("period") and r["period"] not in post["perioder"]:
            post["perioder"].append(r["period"])
        post["obligatorisk"] = post["obligatorisk"] or bool(r.get("obligatorisk"))
        for n in r.get("noter") or []:
            if n not in post["noter"]:
                post["noter"].append(n)
    return sorted(ut.values(), key=lambda k: (not k["obligatorisk"], min(k["perioder"] or [9]), k["namn"]))
