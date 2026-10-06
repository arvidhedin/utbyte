"""Klient för UU:s publika avtalsdatabas i MoveON (uu.adv-pub.moveon4.de).

Används bara av verktygen i verktyg/ – själva appen gör inga nätverksanrop.
Databasen är samma som studenter söker i via uu.se; vi hämtar samma JSON som sidan själv laddar.
"""

from __future__ import annotations

import http.cookiejar
import json
import time
import urllib.parse
import urllib.request

BAS = "https://uu.adv-pub.moveon4.de"
AJAX = f"{BAS}/ap-dashboard/admin-ajax.php"
ANVANDARAGENT = "Mozilla/5.0 (utbytesoversikt; privat studieverktyg)"

# publisher_id -> (kanal, rapportsida för länkar)
PUBLICERARE = {
    "9": ("central", f"{BAS}/report-page-1799/"),
    "5": ("teknat", f"{BAS}/report-page-1643/"),
}


def avtalslank(publisher: str, core_id: str, relation_id: str) -> str:
    sida = PUBLICERARE[str(publisher)][1]
    return f"{sida}?core_id={core_id}&relation_id={relation_id}&openwhichtab=relations&hide_elements=true&whichtab=all"


class Klient:
    """Håller en session (cookie) – behövs för att få ladda ner utbytesrapporter."""

    def __init__(self, paus: float = 0.4, forsok: int = 3):
        self.paus = paus
        self.forsok = forsok
        self._oppnare = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self._oppnare.addheaders = [("User-Agent", ANVANDARAGENT)]

    def _post(self, data: dict, timeout: int = 120) -> bytes:
        kodad = urllib.parse.urlencode(data).encode()
        senaste: Exception | None = None
        for forsok in range(self.forsok):
            try:
                with self._oppnare.open(AJAX, data=kodad, timeout=timeout) as svar:
                    innehall = svar.read()
                time.sleep(self.paus)  # var snäll mot servern
                return innehall
            except Exception as fel:  # nätverksfel, 5xx, timeout
                senaste = fel
                if getattr(fel, "code", None) == 403:
                    raise
                time.sleep(2 + 3 * forsok)
        raise RuntimeError(f"MoveON svarade inte: {senaste}")

    def lista(self, publisher: str) -> dict:
        """Alla avtal hos en publicerare (utan detaljer)."""
        raw = self._post({
            "action": "load_report_data_on_ajax_load",
            "searched_data[publisher_id]": str(publisher),
            "ajaxload": "0",
        })
        return json.loads(raw.decode("utf-8"))

    def detalj(self, publisher: str, core_id: str, relation_id: str) -> dict:
        """Alla fält för ett avtal, institutionsuppgifter och listan över utbytesrapporter.
        Anropet låser också upp avtalets rapporter för nedladdning i sessionen."""
        raw = self._post({
            "action": "load_report_data_on_ajax_load",
            "searched_data[core_id]": str(core_id),
            "searched_data[relation_id]": str(relation_id),
            "searched_data[publisher_id]": str(publisher),
        })
        return json.loads(raw.decode("utf-8"))

    def rapport_pdf(self, publisher: str, fil_id: str) -> bytes:
        """En utbytesrapport som PDF. Kräver att detalj() för avtalet anropats i samma session."""
        raw = self._post({"action": "fetch_pdf_data", "fileId": str(fil_id), "publisherId": str(publisher)})
        start = raw.find(b"%PDF")
        if start < 0:
            raise RuntimeError("Svaret var ingen PDF")
        return raw[start:]


def hamta_sida(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": ANVANDARAGENT, "Accept-Language": "sv,en"})
    with urllib.request.urlopen(req, timeout=timeout) as svar:
        return svar.read().decode("utf-8", errors="replace")
