"""Vilka sorters kurser du kan läsa via ett avtal: teknik, fysik/naturvetenskap, matematik och data.

- Centrala avtal gäller formellt "alla ämnen", men ämnesbegränsningarna utesluter ibland just teknik eller
  naturvetenskap (t.ex. Köpenhamn, Sorbonne, UT Austin). Tabellen nedan är en manuell tolkning av UU:s text
  för varje centralt avtal, gjord 2026-10-06. Kontrollsumman visar om UU har ändrat texten sedan dess.
- TekNat-avtal är ämnesavtal: statusen härleds ur avtalets ämnesområden (ISCED).

Status: öppet, begränsat (få platser, villkor, hård konkurrens), stängt, oklart.
"""

from __future__ import annotations

import hashlib

from . import amnen

TOLKAD = "2026-10-06"
OMRADEN = ["teknik", "fysik", "matematik", "data"]
OMRADE_NAMN = {"teknik": "Teknik", "fysik": "Fysik/naturvet.", "matematik": "Matematik", "data": "Data/IT"}
STATUS = {"ö": "öppet", "b": "begränsat", "s": "stängt", "?": "oklart"}

# id: (teknik, fysik, matematik, data, bara_helar, kontrollsumma av ämnesbegränsningen, notering)
CENTRALA: dict[str, tuple] = {
    "9-1771-5628": ("?", "?", "?", "?", False, "77b6fa6a6b17", "Avtalet anger inga ämnen."),
    "9-4212-780": ("ö", "ö", "ö", "ö", False, "0efbf24e1212", ""),
    "9-475-781": ("ö", "ö", "ö", "ö", False, "6d601c310d79", ""),
    "9-481-787": ("ö", "ö", "ö", "ö", False, "b7ee46d4bc15", "Kräver snittbetyg motsvarande minst C (ECTS)."),
    "9-484-790": ("ö", "ö", "ö", "ö", False, "19e5f24f9d01", ""),
    "9-480-786": ("ö", "ö", "ö", "ö", False, "f5a8cea53367", ""),
    "9-483-789": ("ö", "ö", "ö", "ö", False, "0f4aa1d87d66", "Grundnivåstudenter kan normalt inte läsa avancerade kurser, med vissa undantag inom teknik och naturvetenskap. UNSW inför en ny terminskalender 2028."),
    "9-485-791": ("ö", "ö", "ö", "ö", False, "d1e50e7de8a3", ""),
    "9-486-792": ("ö", "ö", "ö", "ö", False, "14b6a0d5dd07", ""),
    "9-488-794": ("ö", "ö", "ö", "ö", False, "2ad9f67ad80a", ""),
    "9-490-796": ("ö", "ö", "ö", "ö", False, "0d12ee756d5f", ""),
    "9-122-1885": ("ö", "ö", "ö", "ö", False, "ade33e0d2ddf", "Minst hälften av kurserna ska ligga inom ämnet för ditt utbyte. Kurser på engelska finns främst på masternivå."),
    "9-933-4213": ("ö", "ö", "ö", "ö", False, "1096ce8e68e6", "Inga kurser på engelska på avancerad nivå."),
    "9-1220-5180": ("s", "ö", "?", "s", False, "da39a3ee5e6b", "Avtalet gäller fysik."),
    "9-501-807": ("ö", "ö", "ö", "b", False, "e2f97c6cf8f7", "Teknik kräver ett akademiskt referensbrev. Datavetenskap har begränsat med platser."),
    "9-497-803": ("ö", "ö", "ö", "b", False, "0ff83eac3c9e", "Datavetenskap kan ha begränsat med platser."),
    "9-498-5182": ("ö", "ö", "ö", "ö", False, "a93e421fd79c", ""),
    "9-498-804": ("b", "ö", "ö", "ö", False, "f7dfa5bac08c", "Begränsat med platser inom Engineering, och du måste läsa en ingenjörsexamen hemma."),
    "9-505-811": ("s", "ö", "ö", "?", False, "96a0c70ed51f", "Avtalet omfattar Faculty of Science, Humanities och Social Sciences – inte Engineering. Kontrollera om datavetenskap räknas till Engineering."),
    "9-506-812": ("b", "ö", "ö", "s", False, "8ed6855980fc", "Lassonde School of Engineering bara på grundnivå, utom elektroteknik och datavetenskap. Datavetenskap tog inte emot studenter 2024."),
    "9-429-735": ("ö", "ö", "ö", "ö", False, "3d0fefcc2574", ""),
    "9-700-1213": ("ö", "ö", "ö", "ö", False, "d996fb1f6bc1", "Masterstudenter tas inte emot – kontrollera vad som gäller dig i årskurs 4."),
    "9-452-758": ("ö", "ö", "ö", "ö", False, "9fe151ee420f", ""),
    "9-457-763": ("ö", "ö", "ö", "b", False, "4d045077f191", "School of Software and Microelectronics ingår inte."),
    "9-453-759": ("b", "ö", "ö", "b", False, "93ea427a3e1d", "Faculty of Engineering och School of Computing and Data Science har extremt få platser och kräver höga betyg."),
    "9-957-9878": ("s", "s", "s", "s", False, "da39a3ee5e6b", "Avtalet gäller freds- och konfliktstudier."),
    "9-195-8069": ("s", "ö", "ö", "ö", False, "11fe8657969a", "Engineering erbjuds inte."),
    "9-224-273": ("ö", "ö", "ö", "ö", False, "1f141a04da05", ""),
    "9-362-8058": ("ö", "ö", "ö", "ö", False, "dec374fce8f1", ""),
    "9-356-8056": ("ö", "ö", "ö", "ö", False, "8c3dff0d77ee", "De flesta kurserna ska läsas vid en och samma fakultet."),
    "9-2262-6029": ("s", "s", "s", "s", False, "329d5ee9dc50", "Avtalet gäller humaniora och samhällsvetenskap. Se även TekNat-avtalen med samma universitet."),
    "9-1622-6459": ("ö", "ö", "ö", "ö", False, "6067ff6d95b7", ""),
    "9-1047-4797": ("ö", "b", "?", "ö", False, "15f98c00f62e", "Grundnivå: bl.a. civil-, data- och elektroteknik. Avancerad nivå: bl.a. life sciences."),
    "9-163-136": ("ö", "ö", "s", "s", False, "1165d53335bb", "Matematik och informatik ingår inte."),
    "9-313-8060": ("ö", "ö", "ö", "ö", False, "2c993815b177", ""),
    "9-311-415": ("s", "s", "s", "s", False, "deb078c2a329", "College of Science and Engineering är inte öppet för utbytesstudenter via det här avtalet."),
    "9-441-747": ("ö", "ö", "ö", "ö", False, "1844375a6b49", ""),
    "9-443-749": ("ö", "ö", "ö", "ö", False, "f0b08c909bdf", ""),
    "9-445-751": ("ö", "ö", "?", "?", False, "960dcdafa4a7", "Engelskspråkiga program finns bl.a. inom Green Science och Green Engineering."),
    "9-447-753": ("ö", "ö", "ö", "ö", False, "6e07f8c3a20c", "Bara grundnivå (USTEP Type U)."),
    "9-446-752": ("ö", "ö", "?", "?", False, "9de9d490e029", "Programbaserat: JYPE (naturvetenskap och teknik, bara åk 3) samt COLABS på avancerad nivå."),
    "9-1052-5439": ("s", "s", "b", "ö", False, "98c44a97f8c5", "Samhällsvetenskap, lingvistik samt datavetenskap och matematik (bara grundnivå)."),
    "9-874-1911": ("b", "ö", "ö", "b", False, "f7277facce41", "Begränsningar kan gälla ELTEC Engineering."),
    "9-463-769": ("b", "ö", "ö", "ö", False, "e5ae0597307f", "Communication Engineering och Smart Mobility är stängda."),
    "9-464-770": ("b", "ö", "ö", "s", False, "0e1c55299e0d", "Computer Science and Engineering och Electrical and Computer Engineering tar inte emot utbytesstudenter."),
    "9-465-771": ("ö", "ö", "ö", "ö", False, "37556438b185", "Naturvetenskap ligger på ett eget campus en timme från humaniora/samhällsvetenskap."),
    "9-666-1175": ("ö", "ö", "ö", "b", False, "fe21ae24658b", "Datavetenskap är mycket konkurrensutsatt."),
    "9-432-738": ("ö", "ö", "ö", "ö", False, "a5c9464dbeb8", "Inga kurser på avancerad nivå."),
    "9-3406-7723": ("ö", "ö", "ö", "ö", False, "45f198abefe8", ""),
    "9-330-5495": ("ö", "ö", "ö", "ö", False, "e8ded649bc9e", "De flesta kurserna ska läsas vid en fakultet."),
    "9-495-801": ("ö", "ö", "ö", "ö", False, "635e3519f6b9", ""),
    "9-496-802": ("ö", "ö", "ö", "ö", False, "aa3554c28044", ""),
    "9-4217-9601": ("?", "?", "?", "?", False, "da39a3ee5e6b", "Avtalet anger inga ämnen."),
    "9-650-1018": ("ö", "ö", "ö", "s", False, "711214c71252", "Kurser vid College of Computing and Data Science är inte öppna."),
    "9-467-773": ("b", "ö", "ö", "b", False, "e94e48faf1f9", "Civil Engineering och Computer Science har hög efterfrågan och få platser. Kräver minst B i snitt; gäller grundnivå."),
    "9-1766-5615": ("ö", "b", "b", "ö", False, "1770374e2f29", "Bara EPD, ESD, ISTD, HASS och DAI är öppna."),
    "9-365-6457": ("ö", "ö", "ö", "ö", False, "51762fb62d48", ""),
    "9-1049-4804": ("ö", "ö", "ö", "ö", False, "1f869639bd9f", ""),
    "9-423-7726": ("ö", "ö", "ö", "ö", False, "53a7e2545a0f", ""),
    "9-2802-6455": ("ö", "ö", "ö", "ö", False, "2b3a7dd7ab67", "Våren 2027 gällde bara vissa fakulteter, bl.a. Faculty of Engineering (Vitoria) och Science & Technology (Bilbao)."),
    "9-132-8073": ("ö", "ö", "ö", "ö", False, "30d6c31a9a1e", "De flesta kurser på engelska är på masternivå."),
    "9-667-5669": ("ö", "ö", "ö", "ö", False, "20ccd46d92d7", ""),
    "9-469-775": ("ö", "ö", "ö", "ö", False, "885ae5d29ea7", ""),
    "9-925-5176": ("ö", "ö", "ö", "ö", False, "fb0542992a7f", ""),
    "9-2591-6359": ("s", "s", "ö", "ö", False, "ed668b33491d", "Kurser på engelska finns i tillämpad matematik och informatik, geografi, ekonomi m.fl."),
    "9-1214-5130": ("s", "s", "s", "s", False, "02a6ec466b58", "Filologi, juridik, internationella relationer m.m."),
    "9-392-5032": ("ö", "ö", "ö", "ö", True, "8b2ebfb8d18c", "Bara helårsutbyten – fungerar inte för enbart VT2028."),
    "9-405-561": ("b", "b", "b", "s", False, "10924fdf3e8d", "Minst hälften av kurserna ska läsas vid SELCS (språk och kultur); datavetenskap ingår inte. Studenter på integrerade program får söka på grundnivå."),
    "9-393-891": ("s", "s", "s", "s", False, "34f8547a5831", "Bara College of Humanities and Social Science."),
    "9-393-4186": ("ö", "ö", "ö", "ö", False, "40d41af6fb37", "Minst två tredjedelar av kurserna inom ett college, t.ex. Science and Engineering."),
    "9-384-538": ("b", "ö", "ö", "b", False, "097e675ef355", "Engineering & Informatics har mycket få platser."),
    "9-510-816": ("ö", "ö", "ö", "ö", False, "6e29552d4575", "Bara grundnivå. Campus tilldelas; San Diego, Long Beach och Los Angeles är svåra att få."),
    "9-516-822": ("ö", "ö", "ö", "ö", False, "caecd6b923ed", "Bara grundnivå."),
    "9-536-842": ("ö", "ö", "ö", "ö", False, "1f77bf8ac412", ""),
    "9-507-813": ("ö", "ö", "ö", "b", False, "578e30dd755f", "Högst tre kurser i datavetenskap."),
    "9-512-818": ("ö", "ö", "ö", "ö", False, "83fd8e21b525", ""),
    "9-599-1200": ("ö", "ö", "ö", "ö", False, "9d5f8259428e", ""),
    "9-519-825": ("ö", "b", "ö", "b", False, "a3f1f884498e", "Högst 3 fysikkurser (PHYS) och 2 datavetenskapskurser (CS) per termin."),
    "9-523-829": ("ö", "ö", "ö", "b", False, "07a01fc456a6", "Datavetenskap är mycket begränsat; Engineering Management ingår inte."),
    "9-534-840": ("s", "b", "b", "ö", False, "ba1da15c3846", "Avtalet gäller School of Information; kurser vid andra skolor bara med tillstånd. Teknik rekommenderas inte."),
    "9-525-831": ("ö", "ö", "ö", "ö", False, "9264ecfd7c6c", ""),
    "9-526-832": ("ö", "ö", "ö", "ö", False, "58370b2e49d5", ""),
    "9-531-837": ("s", "ö", "ö", "b", False, "072f3d962f78", "Cockrell School of Engineering ingår inte; vissa begränsningar i datavetenskap."),
    "9-533-839": ("b", "b", "b", "b", False, "8eeb252f0133", "Mycket svårt att komma in på bl.a. Engineering, Computer Science och Math; hård konkurrens även i naturvetenskap."),
    "9-2233-5986": ("ö", "ö", "ö", "ö", False, "cdbfd83fabb5", ""),
}


def kontrollsumma(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:12]


def _harled(kategorier: list[str], civilingenjor: bool) -> dict[str, str]:
    k = set(kategorier)
    if amnen.ALLA in k:
        return {o: "öppet" for o in OMRADEN}
    if not k:
        return {o: "oklart" for o in OMRADEN}
    bred_teknik = bool(k & {"Teknik (brett)"})
    ut = {
        "teknik": "öppet" if k & {"Teknik (brett)", "El, energi och elektronik", "Maskin och material", "Bygg",
                                  "Kemi och kemiteknik"} and not k <= {"Kemi och kemiteknik"} else "stängt",
        "fysik": "öppet" if k & {"Fysik", "Naturvetenskap (brett)"} else "stängt",
        "matematik": "öppet" if k & {"Matematik och statistik", "Naturvetenskap (brett)"} else "stängt",
        "data": "öppet" if "Data och IT" in k else "stängt",
    }
    if bred_teknik or civilingenjor:  # breda teknikavtal: fysik/matte/data kan ofta ingå – kontrollera
        for o in ("fysik", "matematik", "data"):
            if ut[o] == "stängt":
                ut[o] = "oklart"
    return ut


def bedom(avtal: dict) -> dict:
    """{"teknik": "öppet", …, "helar": bool, "not": str, "kalla": "tolkad"/"härledd", "andrad": bool}"""
    text = avtal["falt"].get("Ämnesbegränsningar", {}).get("text", "")
    if avtal["id"] in CENTRALA:
        t, f, m, d, helar, summa, not_ = CENTRALA[avtal["id"]]
        return {"teknik": STATUS[t], "fysik": STATUS[f], "matematik": STATUS[m], "data": STATUS[d],
                "helar": helar, "not": not_, "kalla": "tolkad", "andrad": summa != kontrollsumma(text)}
    if avtal["kanal"] == "central":  # nytt centralt avtal som inte tolkats än
        return {**{o: "oklart" for o in OMRADEN}, "helar": False, "not": "Nytt avtal – läs ämnesbegränsningen.",
                "kalla": "otolkad", "andrad": False}
    return {**_harled(avtal["kategorier"], avtal["civilingenjor"]), "helar": False, "not": "",
            "kalla": "härledd", "andrad": False}
