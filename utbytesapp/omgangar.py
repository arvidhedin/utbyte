"""Ansökningsomgångar och viktiga datum för ett utbyte vårterminen 2028.

Datumen för 2027 följer UU:s återkommande schema (samma datum varje år) och bekräftas när
UU publicerar ansökan. Källor finns på varje rad och visas i appen.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from . import uusidor

UTBYTESTERMIN = "VT2028"


@dataclass(frozen=True)
class Omgang:
    id: str
    namn: str
    kanal: str  # "teknat" eller "central"
    start: dt.date
    slut: dt.date
    slut_klocka: str | None
    galler: str
    beskrivning: str
    url: str
    max_val: int = 4
    bara_lista: bool = False  # bara universitet på omgångens lista kan väljas

    def status(self, idag: dt.date) -> str:
        if idag < self.start:
            return "kommande"
        if idag <= self.slut:
            return "öppen"
        return "stängd"

    def kort_datum(self) -> str:
        return intervall_text(self.start, self.slut) + (f" kl. {self.slut_klocka}" if self.slut_klocka else "")


OMGANGAR = [
    Omgang(
        id="teknat_huvud", namn="TekNat – huvudomgången", kanal="teknat",
        start=dt.date(2027, 1, 15), slut=dt.date(2027, 2, 15), slut_klocka=None,
        galler="Utbyten hösten 2027 och våren 2028",
        beskrivning=("Ansökan till fakultetens och institutionernas avtal i ett och samma formulär i MoveON. "
                     "Upp till fyra val i prioritetsordning, både fakultets- och institutionsavtal. "
                     "Urval: urvalsgrupp (ej klarade hp i programmet) och meritvärde."),
        url=uusidor.URL_TEKNAT_GUIDE,
    ),
    Omgang(
        id="central_var", namn="Centrala avtal – vårrundan", kanal="central",
        start=dt.date(2027, 4, 15), slut=dt.date(2027, 5, 14), slut_klocka="15:00",
        galler="Utbyten som startar våren 2028",
        beskrivning=("Universitetsövergripande avtal, Erasmus och ICM via Enheten för internationell mobilitet. "
                     "Bara universitet på listan som publiceras 15 april kan väljas. Upp till fyra val. "
                     "Urval: prioritetsgrupp, antal hp med högsta betyg, meriterande uppdrag och lottning."),
        url=uusidor.URL_CENTRAL, bara_lista=True,
    ),
    Omgang(
        id="teknat_rest", namn="TekNat – restplatser", kanal="teknat",
        start=dt.date(2027, 8, 15), slut=dt.date(2027, 9, 15), slut_klocka=None,
        galler="Lediga platser våren 2028",
        beskrivning=("Avtal som fortfarande har platser kvar för våren. Markeras med \"Has remaining seats\" "
                     "på TekNats avtalssida när omgången öppnar."),
        url=uusidor.URL_TEKNAT_GUIDE,
    ),
]
OMGANG = {o.id: o for o in OMGANGAR}


def omgangar_for(kanal: str) -> list[Omgang]:
    return [o for o in OMGANGAR if o.kanal == kanal]


@dataclass(frozen=True)
class Handelse:
    datum: dt.date
    titel: str
    text: str = ""
    slut: dt.date | None = None
    typ: str = "info"  # ansokan, besked, info, stipendium, resa, ovrigt
    url: str | None = None
    ungefarlig: bool = False
    galler_vt2028: bool = True
    taggar: tuple[str, ...] = field(default_factory=tuple)


HANDELSER = [
    Handelse(dt.date(2026, 10, 15), "Centrala höstrundan",
             "Gäller utbyten som startar hösten 2027 – inte ett utbyte bara våren 2028. Listan visar vilka "
             "universitet som brukar erbjudas.", slut=dt.date(2026, 11, 16), typ="info", url=uusidor.URL_CENTRAL,
             galler_vt2028=False),
    Handelse(dt.date(2026, 10, 19), "Webbinarium: Applying for Exchange Studies – del 1: välja universitet",
             "Kl. 12–13, på svenska. UU:s enhet för internationell mobilitet.", typ="info", url=uusidor.URL_CENTRAL),
    Handelse(dt.date(2026, 11, 2), "TekNats utbytesmässa",
             "Kl. 11.30–13.30 på Ångströmlaboratoriet. Träffa fakultetens och institutionernas koordinatorer och "
             "studentambassadörer.", typ="info",
             url="https://www.uu.se/en/students/faculty/science-and-technology/events/archive/2026-11-02-exchange-studies-fair"),
    Handelse(dt.date(2027, 1, 15), "TekNats huvudomgång",
             "Fakultets- och institutionsavtal. Förbered kursförslag (30 hp) för varje val och svaren på de tre "
             "frågorna i akademisk motivering (på engelska) för förstahandsvalet.", slut=dt.date(2027, 2, 15),
             typ="ansokan", url=uusidor.URL_TEKNAT_GUIDE, taggar=("teknat_huvud",)),
    Handelse(dt.date(2027, 3, 15), "Besked från TekNat (ungefär)",
             "UU anger inget exakt datum. Om du tackar ja till en TekNat-plats räknas det in i prioriteringen "
             "i den centrala vårrundan (studenter utan annat utbyte prioriteras).", typ="besked", ungefarlig=True),
    Handelse(dt.date(2027, 4, 15), "Centrala vårrundan (listan publiceras 15 april)",
             "Kör \"Uppdatera data\" i appen samma dag så hämtas listan och antalet platser för VT2028.",
             slut=dt.date(2027, 5, 14), typ="ansokan", url=uusidor.URL_CENTRAL, taggar=("central_var",)),
    Handelse(dt.date(2027, 6, 11), "Besked från centrala ansökan (ungefär)",
             "Cirka fyra veckor efter sista ansökningsdag. Du har ungefär en vecka på dig att svara.",
             typ="besked", ungefarlig=True),
    Handelse(dt.date(2027, 8, 15), "TekNats restplatser för våren",
             "Kolla TekNats avtalssida (\"Has remaining seats\") – appen visar det efter en uppdatering.",
             slut=dt.date(2027, 9, 15), typ="ansokan", url=uusidor.URL_TEKNAT, taggar=("teknat_rest",)),
    Handelse(dt.date(2027, 9, 15), "Ansökan till värduniversitetet (ofta sep–nov)",
             "Efter nomineringen söker du till värduniversitetet enligt deras instruktioner och deadline. "
             "Kolla fältet \"Ansökningsdatum hos värduniversitetet\" för ditt avtal.", typ="ovrigt", ungefarlig=True),
    Handelse(dt.date(2027, 11, 1), "Ansökan om Erasmusstipendiet",
             "1–15 november för utbyten som startar på våren (gäller Erasmusavtal). Du får instruktioner via e-post.",
             slut=dt.date(2027, 11, 15), typ="stipendium", url=uusidor.URL_ERASMUS),
    Handelse(dt.date(2028, 1, 20), "Vårterminen 2028 börjar",
             "Värduniversitetets terminsstart kan ligga allt från januari (USA, Asien) till april (Tyskland, Japan).",
             typ="resa", ungefarlig=True),
]

MANADER_LANG = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september",
                "oktober", "november", "december"]


def datum_text(d: dt.date, ar: bool = True) -> str:
    return f"{d.day} {MANADER_LANG[d.month - 1][:3]}{' ' + str(d.year) if ar else ''}"


def intervall_text(start: dt.date, slut: dt.date) -> str:
    """"15 jan–15 feb 2027" (året bara en gång när det är samma)."""
    if start.year == slut.year:
        return f"{datum_text(start, ar=False)}–{datum_text(slut)}"
    return f"{datum_text(start)}–{datum_text(slut)}"


def dagar_kvar(d: dt.date, idag: dt.date | None = None) -> int:
    return (d - (idag or dt.date.today())).days


def nasta_omgang(kanal: str | None = None, idag: dt.date | None = None) -> Omgang | None:
    idag = idag or dt.date.today()
    for o in OMGANGAR:
        if (kanal is None or o.kanal == kanal) and o.slut >= idag:
            return o
    return None


def ics(handelser: list[Handelse], egna: list[dict] | None = None) -> str:
    """Kalenderfil (iCalendar) med heldagshändelser."""
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    rader = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//utbytesoversikt//SV", "CALSCALE:GREGORIAN"]
    stampel = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    poster: list[tuple[dt.date, str, str]] = []
    for h in handelser:
        beskr = h.text + (f"\n{h.url}" if h.url else "")
        if h.slut:  # perioder blir två händelser: start och sista dag
            poster.append((h.datum, f"{h.titel} – öppnar", beskr))
            poster.append((h.slut, f"Sista dag: {h.titel}", beskr))
        else:
            poster.append((h.datum, h.titel, beskr))
    for e in egna or []:
        try:
            poster.append((dt.date.fromisoformat(e["datum"]), e["text"], e.get("anteckning", "")))
        except (KeyError, ValueError):
            continue
    for i, (dag, titel, text) in enumerate(poster):
        rader += [
            "BEGIN:VEVENT",
            f"UID:utbyte-{dag.isoformat()}-{i}@localhost",
            f"DTSTAMP:{stampel}",
            f"DTSTART;VALUE=DATE:{dag.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(dag + dt.timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{esc(titel)}",
            f"DESCRIPTION:{esc(text)}",
            "END:VEVENT",
        ]
    rader.append("END:VCALENDAR")
    return "\r\n".join(rader) + "\r\n"
