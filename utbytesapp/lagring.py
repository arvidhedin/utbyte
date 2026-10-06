"""Dina egna uppgifter: favoriter, rangordning, kursplaner, anteckningar och inställningar.

Allt sparas lokalt i data/mina_val.json. Före varje ändring av innehållet läggs en kopia av den
gamla versionen i data/backups/ (de 60 senaste behålls), precis som i kursappen.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
import shutil
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
DATA = ROT / "data"
# UTBYTE_MINA låter dig köra appen mot en kopia (t.ex. vid test).
MINA = Path(os.environ.get("UTBYTE_MINA", DATA / "mina_val.json"))
BACKUPS = MINA.parent / "backups"
MAX_BACKUPS = 60

STATUSAR = ["Intresserad", "Undersöker", "Kursplan klar", "Ska söka", "Sökt", "Erbjuden plats", "Tackat ja", "Avstår"]

STANDARD = {
    "format": 1,
    "installningar": {
        "inriktning": None,       # None = hämta från kursappen
        "profil": None,
        "kursapp": str(Path.home() / "kurser"),
        "extrapoang": 0.0,        # meriterande uppdrag (TekNat: 0,2 nation/kår, 0,1 mottagning; max 0,3)
        "studieplan_t8": "HT2024",
    },
    "favoriter": {},     # avtal_id -> {"status", "anteckning", "tillagd"}
    "rangordning": {},   # omgångs-id -> [avtal_id, …] (max 4)
    "kursplaner": {},    # avtal_id -> {"faktor": float|None, "kurser": [ {…} ]}
    "egna_uppgifter": {},  # core_id -> {"sprak": [...], "sprak_kalla": "", "anteckning": ""}
    "handelser": [],     # egna datum: {"datum", "text", "anteckning", "klar"}
    "checklista": {},    # punkt-id -> True när den är avbockad
    "lasta_rapporter": [],
}


def tom() -> dict:
    return copy.deepcopy(STANDARD)


def ladda() -> dict:
    if not MINA.exists():
        return tom()
    data = json.loads(MINA.read_text(encoding="utf-8"))
    for nyckel, varde in STANDARD.items():
        data.setdefault(nyckel, copy.deepcopy(varde))
    for nyckel, varde in STANDARD["installningar"].items():
        data["installningar"].setdefault(nyckel, varde)
    return data


def spara(data: dict) -> None:
    MINA.parent.mkdir(parents=True, exist_ok=True)
    if MINA.exists():
        gammal = json.loads(MINA.read_text(encoding="utf-8"))
        if gammal == data:
            return
        BACKUPS.mkdir(exist_ok=True)
        stampel = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        shutil.copy2(MINA, BACKUPS / f"mina_val-{stampel}.json")
        for fil in sorted(BACKUPS.glob("mina_val-*.json"))[:-MAX_BACKUPS]:
            fil.unlink()
    tmp = MINA.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, MINA)  # atomiskt


def lista_backups() -> list[Path]:
    return sorted(BACKUPS.glob("mina_val-*.json"), reverse=True)


def aterstall(fil: Path) -> None:
    spara(json.loads(fil.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------------------------
# Små hjälpare som ändrar en laddad struktur (sparas av anroparen)
# ---------------------------------------------------------------------------------------------

def vaxla_favorit(data: dict, avtal_id: str) -> bool:
    """Lägger till eller tar bort en favorit. Returnerar True om den nu är favorit."""
    fav = data["favoriter"]
    if avtal_id in fav:
        del fav[avtal_id]
        for lista in data["rangordning"].values():
            if avtal_id in lista:
                lista.remove(avtal_id)
        return False
    fav[avtal_id] = {"status": STATUSAR[0], "anteckning": "", "tillagd": dt.date.today().isoformat()}
    return True
