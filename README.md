# Utbytesöversikt – VT2028, teknisk fysik vid UU

En lokal app som samlar **alla universitet du kan söka utbyte till** som student i teknisk fysik (TTF2Y) vid
Uppsala universitet, och visar **via vilket avtal, vilken fakultet/institution och när** du söker för våren 2028.

## Starta

Dubbelklicka på **`start.command`** i Finder. Appen öppnas på <http://localhost:8502> (kursappen ligger kvar på 8501).
Första gången hämtas avtalsdatan från UU automatiskt. Stäng med Ctrl+C i terminalfönstret.

```bash
cd ~/utbyte && streamlit run app.py
```

## Så söker du för VT2028

| Omgång | Datum | Gäller |
|---|---|---|
| **TekNat – huvudomgången** | 15 jan–15 feb 2027 | Fakultetens och institutionernas avtal (Erasmus, Nordtek, ämnesavtal). Upp till 4 val. |
| **Centrala avtal – vårrundan** | 15 apr–14 maj 2027 kl. 15 | Universitetsövergripande avtal i hela världen, plus vissa Erasmus/ICM. Bara universitet på listan som publiceras 15 april. |
| **TekNat – restplatser** | 15 aug–15 sep 2027 | Avtal med lediga platser för våren. |

Datumen för 2027 följer UU:s återkommande schema – kontrollera på uu.se när ansökan öppnar.

## Sidor

| Sida | Vad den gör |
|---|---|
| **Översikt** | Nedräkning till omgångarna, hur du söker, snabbsökningar, statistik och nyheter sedan senaste uppdateringen |
| **Sök** | Sök och filtrera på land, världsdel, omgång, kanal, institution, avtalstyp, ämne, kurstyper (teknik/fysik/matte/data), nivå, undervisningsspråk, språktest, vårterminens längd, stipendium, platslistan, rapporter, avstånd. Kort eller tabell, CSV-export |
| **Karta** | Alla universitet på en karta (fungerar offline), färgade efter kanal, ämnesmatchning eller språk |
| **Universitet** | Allt om ett universitet: varje avtal med ansökningsväg, kontakt, platser, ämnen, kurstyper, språk och språkkrav, terminsdatum, poängomräkning, stipendium och alla fält ur UU:s databas. Utbytesrapporter, egna anteckningar och egna språkuppgifter |
| **Jämför** | Upp till fyra universitet sida vid sida |
| **Mina val** | Favoriter med status och anteckningar, rangordning 1–4 per ansökningsomgång med varningar |
| **Tidslinje** | Alla datum fram till avresa, egna datum, checklista och export till Kalender (.ics) |
| **Kursplan** | Kursförslag (30 hp) per avtal med poängomräkning, koppling mot kurserna i termin 8 och vad tidigare studenter läste |
| **Meritvärde och urval** | TekNats meritvärde (geometriskt snitt), urvalsgrupp och hp med toppbetyg för centrala ansökan – räknat ur kursappen |
| **Utbytesrapporter** | Fulltextsökning i ~600 rapporter, filter på vad studenten läste (t.ex. teknisk fysik), land och termin |
| **Data och uppdatering** | Hämta ny data från UU, se källor, tolkningsregler, ändringar och säkerhetskopior |

## Uppdatera data

Tryck **Uppdatera** under *Data och uppdatering*, eller kör:

```bash
cd ~/utbyte && python verktyg/hamta_avtal.py            # snabbt: listor, platslista, TekNat-sidan, Erasmusnivåer
cd ~/utbyte && python verktyg/hamta_avtal.py --allt     # alla detaljer på nytt (10–20 min)
cd ~/utbyte && python verktyg/hamta_rapporter.py        # nya utbytesrapporter
```

Viktiga tillfällen att uppdatera: **15 april 2027** (listan och platserna för VT2028 publiceras) och
**mitten av augusti 2027** (TekNats restplatser).

## Så tolkas datan

- **Källor:** UU:s publika avtalsdatabas i MoveON (centrala avtal och TekNats avtal), listan över universitet i
  aktuell central omgång, TekNats avtalssida och sidan om Erasmusstipendiet.
- **Undervisningsspråk:** från avtalsdatabasen; annars från ett annat avtal med samma universitet; annars landets
  språk med *engelska främst på masternivå*, märkt **obekräftat**. Du kan rätta det per universitet.
- **Kurser du kan läsa:** för de 85 centrala avtalen en manuell tolkning (2026-10-06) av UU:s ämnesbegränsningar.
  Flera "alla ämnen"-avtal utesluter teknik eller naturvetenskap (t.ex. Köpenhamn, Sorbonne, Galway, UT Austin).
  Ändrar UU texten visar appen det. Tolkningen finns i `utbytesapp/kurstyper.py`.
- **Ämnesmatchning** är bara ett sorteringsförslag och säger inget om behörighet.
- Det här är en sammanställning, inte ett beslut. Kontrollera alltid med UU och avtalets koordinator.

## Integritet – allt är lokalt

- Dina val sparas i `data/mina_val.json`, med en säkerhetskopia i `data/backups/` vid varje ändring.
- Kursappens data (`~/kurser/data/`) läses bara – för meritvärde, urvalsgrupp och termin 8 – och skrivs aldrig.
- Servern lyssnar bara på `localhost` och telemetri är avstängd. Kartunderlaget ligger lokalt i `static/karta/`.
- Mappen är ett eget git-repo. `.gitignore` håller dina val, säkerhetskopior, rådata och utbytesrapporterna
  (andra studenters namn och kontaktuppgifter) utanför git – de hämtas lokalt med verktygen.
- Bara verktygen i `verktyg/` gör nätverksanrop, och bara mot UU:s publika sidor.

## Tester

```bash
cd ~/utbyte && python -m pytest -q
```

## Filer

```
app.py                     startpunkt och navigering
sidor/                     en fil per sida
utbytesapp/bygg.py         bygger data/avtal.json av rådatan (namnmatchning, språk, terminer, platser)
utbytesapp/kurstyper.py    tolkningen av vilka kurstyper som är öppna per avtal
utbytesapp/tolka.py        tolkning av fritext: språk, språkkrav, poängomräkning, terminsdatum
utbytesapp/omgangar.py     ansökningsomgångar och datum för VT2028
utbytesapp/kursdata.py     läser kursappen: meritvärde, toppbetyg, urvalsgrupp, termin 8
utbytesapp/rapporter.py    tolkning av utbytesrapporternas PDF:er
verktyg/                   hämtning från UU (avtal, platslistor, rapporter)
data/                      avtal.json, rapporter.json, platslistor, rådata och dina val
static/                    kartunderlag och rapport-PDF:er (serveras bara lokalt)
```
