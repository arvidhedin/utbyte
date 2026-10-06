"""Textverktyg: HTML från avtalsdatabasen till säker Markdown, ren text och namnnormalisering."""

from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup, NavigableString, Tag

_WS = re.compile(r"[ \t\r\f\v\xa0​]+")
_URL = re.compile(r"(?<![(\[])\b((?:https?://|www\.)[^\s<>()\[\]]+[^\s<>()\[\].,;:!?'\"])")


def laga_url(url: str | None) -> str | None:
    """Rättar vanliga fel i databasens länkar (t.ex. "http://https://…")."""
    if not url:
        return None
    u = url.strip().replace(" ", "%20")
    u = re.sub(r"^https?://(https?://)", r"\1", u)
    if u.startswith("www."):
        u = "https://" + u
    if u.startswith("//"):
        u = "https:" + u
    if not re.match(r"^(https?|mailto):", u):
        return None
    return u


def _escape_md(text: str) -> str:
    # $ startar LaTeX i Streamlit; * _ ` kan ge oavsiktlig formatering.
    text = text.replace("\\", "\\\\")
    for tecken in "$*_`[]":
        text = text.replace(tecken, "\\" + tecken)
    return text.replace("<", "&lt;").replace(">", "&gt;")


def _lankifiera(text: str) -> str:
    """Gör nakna webbadresser i (redan escapad) text klickbara."""
    def ersatt(m: re.Match) -> str:
        url = laga_url(m.group(1).replace("\\_", "_"))
        return f"[{m.group(1)}]({url})" if url else m.group(1)
    return _URL.sub(ersatt, text)


_BLOCK = {"p", "div", "ul", "ol", "table", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "section"}


def html_till_md(html: str | None) -> str:
    """Konverterar ett HTML-fält till Markdown med bara länkar, fetstil, radbrytningar och listor."""
    if not html or not html.strip():
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "img", "iframe"]):
        t.decompose()

    delar: list[str] = []

    def gå(nod) -> None:
        for barn in nod.children:
            if isinstance(barn, NavigableString):
                if barn.__class__.__name__ == "Comment":
                    continue
                delar.append(_lankifiera(_escape_md(_WS.sub(" ", str(barn)))))
            elif isinstance(barn, Tag):
                namn = barn.name.lower()
                if namn == "br":
                    delar.append("\n")
                elif namn == "a":
                    url = laga_url(barn.get("href"))
                    text = _WS.sub(" ", barn.get_text(" ")).strip() or (url or "")
                    if url and text:
                        delar.append(f"[{_escape_md(text)}]({url})")
                    elif text:
                        delar.append(_escape_md(text))
                elif namn in ("b", "strong"):
                    text = _WS.sub(" ", barn.get_text(" ")).strip()
                    if barn.find("a"):  # behåll länkar inuti fetstil
                        gå(barn)
                    elif text:
                        delar.append(f" **{_escape_md(text)}** ")
                elif namn == "li":
                    delar.append("\n- ")
                    gå(barn)
                    delar.append("\n")
                elif namn in ("td", "th"):
                    gå(barn)
                    delar.append(" · ")
                elif namn in _BLOCK:
                    delar.append("\n\n")
                    gå(barn)
                    delar.append("\n\n")
                else:
                    gå(barn)

    gå(soup)
    rader = [_WS.sub(" ", r).strip(" ·") for r in "".join(delar).split("\n")]
    # Tom rad = nytt stycke, annars hård radbrytning. Listpunkter får egen rad.
    ut: list[str] = []
    tomma = 0
    for r in rader:
        if not r or r == "-":
            tomma += 1
            continue
        if ut:
            if r.startswith("- "):
                ut.append("\n")
            else:
                ut.append("\n\n" if tomma else "  \n")
        ut.append(r)
        tomma = 0
    return "".join(ut).strip()


def html_till_text(html: str | None) -> str:
    """Ren text (för sökning och tolkning)."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    text = soup.get_text(" ")
    return _WS.sub(" ", text).strip()


def lankar(html: str | None) -> list[tuple[str, str]]:
    """Alla länkar i ett HTML-fält som (text, url)."""
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    ut = []
    for a in soup.find_all("a", href=True):
        url = laga_url(a["href"])
        if url:
            ut.append((_WS.sub(" ", a.get_text(" ")).strip() or url, url))
    return ut


def utan_accenter(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


_FYLLORD = {
    "the", "of", "at", "de", "di", "du", "del", "der", "des", "la", "le", "zu", "i", "u", "v", "in", "and", "y",
    "university", "universiteit", "universitat", "universitaet", "universidad", "universidade", "universite",
    "universita", "universitet", "universitetet", "universitetin", "univerzita", "univerza", "uniwersytet",
    "yliopisto", "ulikool", "hochschule", "college", "campus", "degli", "studi", "london",
}


# Svenska/engelska exonymer -> lokala namn, så att "University of Milan-Bicocca" hittar "Milano-Bicocca".
_EXONYMER = {
    "milan": "milano", "turin": "torino", "vienna": "wien", "munich": "munchen", "muenchen": "munchen",
    "cologne": "koln", "rome": "roma", "florence": "firenze", "naples": "napoli", "lisbon": "lisboa",
    "lissabon": "lisboa", "prague": "praha", "warsaw": "warszawa", "cracow": "krakow", "copenhagen": "kobenhavn",
    "gothenburg": "goteborg", "zurich": "zurich", "geneva": "geneve", "louvain": "leuven", "brussels": "bruxelles",
    "free": "freie", "technical": "technische",
}


def normalisera_namn(namn: str) -> str:
    s = utan_accenter(namn).lower()
    s = s.replace("&", " and ").replace("’", "'")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return " ".join(_EXONYMER.get(t, t) for t in s.split())


def namntoken(namn: str) -> set[str]:
    return {t for t in normalisera_namn(namn).split() if t not in _FYLLORD and len(t) > 1}


def forkortning(namn: str) -> str | None:
    """"Rijksuniversiteit Groningen (RuG)" -> "rug"."""
    m = re.search(r"\(([A-Za-z]{2,8})\)", namn)
    return m.group(1).lower() if m else None


def kort(text: str, n: int = 160) -> str:
    text = _WS.sub(" ", text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"
