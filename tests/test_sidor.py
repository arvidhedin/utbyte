"""Röktest: varje sida körs utan fel mot den riktiga avtalsdatan och en tom kopia av dina val."""

import json

import pytest
from streamlit.testing.v1 import AppTest

from utbytesapp import lagring, modell

SIDOR = ["oversikt", "sok", "karta", "universitet", "jamfor", "mina_val", "tidslinje", "kursplan", "merit",
         "rapporter", "data"]

pytestmark = pytest.mark.skipif(not modell.AVTAL.exists(), reason="ingen data/avtal.json – kör verktyg/hamta_avtal.py")


@pytest.fixture
def mina(tmp_path, monkeypatch):
    fil = tmp_path / "mina_val.json"
    monkeypatch.setenv("UTBYTE_MINA", str(fil))
    monkeypatch.setattr(lagring, "MINA", fil)
    monkeypatch.setattr(lagring, "BACKUPS", tmp_path / "backups")
    return fil


def kor(sida: str) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=120)
    at.switch_page(f"sidor/{sida}.py")
    at.run()
    return at


@pytest.mark.parametrize("sida", SIDOR)
def test_sida_utan_val(mina, sida):
    at = kor(sida)
    assert not at.exception, at.exception[0].value


@pytest.mark.parametrize("sida", ["oversikt", "sok", "mina_val", "jamfor", "kursplan", "universitet"])
def test_sida_med_favoriter(mina, sida):
    data = json.loads(modell.AVTAL.read_text(encoding="utf-8"))
    d = lagring.tom()
    for a in data["avtal"][:4]:
        lagring.vaxla_favorit(d, a["id"])
    forsta = data["avtal"][0]["id"]
    d["rangordning"]["teknat_huvud"] = [forsta]
    d["kursplaner"][forsta] = {"faktor": 1.0, "kurser": [{"namn": "Test", "poang": 7.5, "hp": 7.5}]}
    mina.write_text(json.dumps(d), encoding="utf-8")
    at = kor(sida)
    assert not at.exception, at.exception[0].value
