from utbytesapp import amnen, bygg, kurstyper, uusidor


def kandidat(namn, land="Australia"):
    return {"namn": [namn], "land": land, "avtal": {"id": namn}}


def test_matchning_valjer_ratt_universitet():
    kandidater = [kandidat("University of Sydney"), kandidat("University of Technology Sydney (UTS)")]
    traff = bygg.matcha("University of Technology Sydney", "Australia", kandidater)
    assert traff["avtal"]["id"] == "University of Technology Sydney (UTS)"
    hk = [kandidat("City University of Hong Kong", "China"), kandidat("The University of Hong Kong", "China")]
    assert bygg.matcha("University of Hong Kong", "China", hk)["avtal"]["id"] == "The University of Hong Kong"


def test_tilldela_ger_varje_kandidat_en_rad():
    kandidater = [kandidat("University of British Columbia - Okanagan Campus", "Canada"),
                  kandidat("University of British Columbia - Vancouver Campus", "Canada")]
    rader = [{"namn": "University of British Columbia - Vancouver Campus", "land": "Canada"},
             {"namn": "University of British Columbia - Okanagan Campus", "land": "Canada"}]
    par = bygg.tilldela(rader, kandidater)
    assert [k["avtal"]["id"] for _, k in par] == [r["namn"] for r in rader]


def test_annat_land_matchas_inte():
    assert bygg.matcha("University of Sydney", "Canada", [kandidat("University of Sydney")]) is None


def test_enhet_och_delnamn():
    namn = "Erasmus SMS - Technische Universität München - Electricity and energy - TEKNAT - Faculty of Science and Technology"
    enhet = bygg.enhet_ur_avtalsnamn(namn, "teknat")
    assert enhet == "Faculty of Science and Technology"
    assert bygg.delnamn(namn, enhet, "Technische Universität München (TUM)") == "Electricity and energy"
    galway = "General university-wide exchange - Ollscoil na Gaillimhe - University of Galway - All fields of study"
    assert bygg.delnamn(galway, "Unit for International Mobility", "Ollscoil na Gaillimhe - University of Galway") == ""
    assert bygg.enhet_ur_avtalsnamn("Erasmus SMS - X - TEKNAT - Department of Chemistry BMC", "teknat") == "Chemistry"


def test_typ():
    assert bygg._typ("ICM student exchange|| International Office co-ordinated", "", "central") == ("Erasmus ICM", False, True)
    assert bygg._typ("Department co-ordinated|| Erasmus SMS", "Erasmus SMS - X - NORDTEK Network", "teknat")[0] == "Erasmus (Nordtek)"


def test_platslista_med_rowspan():
    html = """<main><h2>Application round for the spring semester 2026</h2>
    <p>The application applies to outgoing students for the spring semester 2027.</p>
    <table><tr><th>Country</th><th>University</th><th>Number of seats</th><th>Grant opportunities</th></tr>
    <tr><td rowspan="2">Australia</td><td>Monash University</td><td>6</td><td></td></tr>
    <tr><td>University of Melbourne</td><td>6</td><td></td></tr>
    <tr><td>Netherlands</td><td>Rijksuniversiteit Groningen (RuG)</td><td>17 (Divided per faculty)</td><td>Erasmus</td></tr>
    </table><p>Last modified: 2026-04-14</p></main>"""
    lista = uusidor.tolka_platslista(html)
    assert lista["mal_termin"] == "VT2027" and lista["omgang"] == "Vårrundan 2026"
    assert [(u["land"], u["platser"]) for u in lista["universitet"]] == [("Australia", 6), ("Australia", 6), ("Netherlands", 17)]
    assert lista["senast_andrad"] == "2026-04-14"
    assert uusidor.tolka_platslista("<main><p>No list yet</p></main>") is None


def test_erasmusgrupper():
    html = "<main><p>Grupp 1</p><p>Stipendiet uppgår till 580 euro i månaden.</p><p>Belgien</p><p>Tyskland</p>" \
           "<p>Grupp 3</p><p>Stipendiet uppgår till 580 euro i månaden.</p><p>Schweiz (gäller endast University of Bern)</p></main>"
    e = uusidor.tolka_erasmus(html)
    assert e["grupper"][0]["lander"] == {"BE": "Belgien", "DE": "Tyskland"}
    assert e["grupper"][1]["noter"]["CH"] == "gäller endast University of Bern"


def test_kurstyper():
    central = {"id": "9-195-8069", "kanal": "central", "falt": {}, "kategorier": [amnen.ALLA], "civilingenjor": False}
    kt = kurstyper.bedom(central)
    assert kt["teknik"] == "stängt" and kt["fysik"] == "öppet" and kt["kalla"] == "tolkad"
    assert kt["andrad"]  # tom text skiljer sig från den tolkade
    ny = {"id": "9-0-0", "kanal": "central", "falt": {}, "kategorier": [amnen.ALLA], "civilingenjor": False}
    assert kurstyper.bedom(ny)["kalla"] == "otolkad"
    fysik = {"id": "5-1-1", "kanal": "teknat", "falt": {}, "kategorier": ["Fysik"], "civilingenjor": False}
    assert kurstyper.bedom(fysik)["fysik"] == "öppet" and kurstyper.bedom(fysik)["teknik"] == "stängt"


def test_matchning():
    assert amnen.match(["Fysik"], "Tillämpad fysik") == 3
    assert amnen.match(["Biologi och biokemi"], None) == 0
    assert amnen.match(["Teknik (brett)"], None, civilingenjor=True) == 3
    kopenhamn = {"teknik": "stängt", "fysik": "öppet", "matematik": "öppet", "data": "öppet"}
    assert amnen.match_kurstyper(kopenhamn, "Tillämpad fysik") == 3
    assert amnen.match_kurstyper(kopenhamn, None) == 2
    assert amnen.match_kurstyper({o: "stängt" for o in kurstyper.OMRADEN}, None) == 0
