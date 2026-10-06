import datetime as dt
import math
from pathlib import Path

from utbytesapp import kursdata, omgangar, rapporter


def kd(kurser, planer=None):
    return kursdata.Kursdata(Path("."), kurser, {}, planer or {}, {})


def test_meritvarde_geometriskt():
    k = kd([
        {"kod": "A", "hp": 10, "status": "klar", "betyg": "5", "skala": "TH"},
        {"kod": "B", "hp": 5, "status": "klar", "betyg": "3", "skala": "TH"},
        {"kod": "C", "hp": 5, "status": "klar", "betyg": "G", "skala": "UG"},       # räknas inte
        {"kod": "D", "hp": 5, "status": "tillgodoräknad", "betyg": "5"},            # inte vid UU
        {"kod": "E", "hp": 5, "status": "pågående", "planerat_betyg": "4"},         # bara i prognos
    ])
    m = kursdata.meritvarde(k, extrapoang=0.5)
    vantat = math.exp((10 * math.log(5) + 5 * math.log(3)) / 15)
    assert abs(m["geometriskt"] - vantat) < 1e-9
    assert m["avrundat"] == round(vantat, 1)
    assert m["extrapoang"] == 0.3  # max 0,3
    assert m["meritvarde"] == round(m["avrundat"] + 0.3, 1)
    assert kursdata.meritvarde(k, med_planerade=True)["hp"] == 20


def test_toppbetyg_med_delkurser():
    k = kd([
        {"kod": "A", "hp": 10, "status": "klar", "betyg": "5", "moment": [{"hp": 5, "betyg": "5"}]},
        {"kod": "B", "hp": 10, "status": "klar", "betyg": "4", "moment": [{"hp": 3, "betyg": "5"}, {"hp": 7, "betyg": "3"}]},
        {"kod": "C", "hp": 5, "status": "klar", "betyg": "VG"},
    ])
    t = kursdata.toppbetyg(k)
    assert t["hp"] == 10 + 3 + 5


def test_urvalsgrupp():
    planer = {"HT2024": {"kurser": [{"kod": "A"}, {"kod": "B"}, {"kod": "C"}]}}
    k = kd([
        {"kod": "A", "hp": 10, "status": "pågående", "termin": "VT2026",
         "moment": [{"hp": 3, "betyg": "G"}]},                          # 7 hp kvar
        {"kod": "B", "hp": 5, "status": "pågående", "termin": "HT2026"},   # pågår fortfarande
        {"kod": "C", "hp": 5, "status": "klar", "termin": "HT2025", "betyg": "4"},
        {"kod": "X", "hp": 5, "status": "pågående", "termin": "VT2025"},   # inte i programmet
    ], planer)
    u = kursdata.urvalsgrupp(k, (2026, 10))
    assert u["hp"] == 7 and u["grupp"] == 2


def test_termin_kurser():
    planer = {"HT2024": {"kurser": [
        {"kod": "F1", "namn": "Fasta", "hp": 5, "termin": 8, "period": 3, "inriktning": "Tillämpad fysik, profil Fysik", "obligatorisk": True},
        {"kod": "K1", "namn": "Kvant", "hp": 5, "termin": 8, "period": 4, "inriktning": "Tillämpad fysik, profil Kvantteknologi", "obligatorisk": False},
        {"kod": "B1", "namn": "Annan", "hp": 5, "termin": 8, "period": 3, "inriktning": "Beräkningsteknik, profil Artificiell intelligens", "obligatorisk": False},
    ]}}
    k = kd([], planer)
    assert [x["kod"] for x in kursdata.termin_kurser(k, "HT2024", 8, "Tillämpad fysik", "Fysik")] == ["F1"]
    assert {x["kod"] for x in kursdata.termin_kurser(k, "HT2024", 8, "Tillämpad fysik", None)} == {"F1", "K1"}
    assert kursdata.termin_kurser(k, "HT2024", 8, None, None) == []


def test_omgangar_och_kalender():
    o = omgangar.OMGANG["central_var"]
    assert o.kort_datum() == "15 apr–14 maj 2027 kl. 15:00"
    assert o.status(dt.date(2027, 5, 1)) == "öppen" and o.status(dt.date(2026, 10, 6)) == "kommande"
    ics = omgangar.ics(omgangar.HANDELSER, [{"datum": "2027-01-10", "text": "Möte"}])
    perioder = sum(1 for h in omgangar.HANDELSER if h.slut)
    assert ics.count("BEGIN:VEVENT") == len(omgangar.HANDELSER) + perioder + 1


def test_rapportfalt():
    assert rapporter.termin_ur("Autumn Semester 2025/26") == "HT2025"
    assert rapporter.termin_ur("Spring semester 2024/25") == "VT2025"
    assert rapporter.kategori_program("Engineering physics") == "Teknisk fysik"
    assert rapporter.kategori_program("Civilingenjörsprogrammet i system i teknik och samhälle") == "Annat ingenjörsprogram"
    assert rapporter.kategori_program("Masters program in Earth science, physical geography") == "Annat"
