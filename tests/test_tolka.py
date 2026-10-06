from utbytesapp import text, tolka


def test_sprak_i_text():
    assert tolka.sprak_i_text("Danish and English") == ["engelska", "danska"]
    assert tolka.sprak_i_text("English, German") == ["engelska", "tyska"]
    assert tolka.sprak_i_text("") == []


def test_sprakkrav():
    inget = tolka.sprakkrav("Proficiency in English (no official certificate is needed).")
    assert inget["test_kravs"] is False
    krav = tolka.sprakkrav("TOEFL iBT 90 or IELTS 6.5 is required.")
    assert krav["test_kravs"] is True and krav["test"] == ["IELTS", "TOEFL"]
    kanske = tolka.sprakkrav("At least grade 4 in English. If no such results, a language test such as TOEFL or IELTS may be required.")
    assert kanske["test_kravs"] is None and kanske["gymnasiebetyg"]
    assert tolka.sprakkrav("B2 English")["niva"] == "B2"


def test_omrakning():
    assert tolka.omrakning("50 credits=30 hp") == 0.6
    assert tolka.omrakning("1 credit equals 2 hp") == 2.0
    assert tolka.omrakning("15 credits (about 5 courses) / semester = 30hp.") == 2.0
    assert tolka.omrakning("30 ECTS per semester at TSNUK equals 30 credits at UU.") == 1.0
    assert tolka.omrakning("ECTS grading system") == 1.0
    nivaer = tolka.omrakningar("Undergraduate/Bachelor: 15 credits = 30 hp Graduate/Master: 12 credits = 30 hp")
    assert [(o["faktor"], o["niva"]) for o in nivaer] == [(2.0, "grund"), (2.5, "avancerad")]


def test_varmanader():
    assert tolka.varmanader("Autumn semester: Sept–Dec Spring semester: January to May") == (1, 5)
    assert tolka.varmanader("Spring Semester: early February – mid/late May") == (2, 5)
    assert tolka.varmanader("Winter semester: mid October to mid February Summer term starts in April and ends in August") == (4, 8)
    assert tolka.varmanader("Trimester 1*: February - June Trimester 2*: July - November") == (2, 6)
    assert tolka.varmanader("Academic calendar") is None


def test_varvarning():
    assert "French" in tolka.varvarning("During the spring semester you can only take courses in French.")
    assert tolka.varvarning("Graduate School of Business (MBA program) is only offered for the Spring semester.") is None


def test_html_till_md():
    md = text.html_till_md('<p>Cost: $500 per <b>month</b></p><a href="http://https://www.kth.se/x">länk</a>')
    assert "\\$500" in md and "**month**" in md and "[länk](https://www.kth.se/x)" in md
    assert text.laga_url("www.uu.se") == "https://www.uu.se"
    assert text.laga_url("javascript:alert(1)") is None


def test_normalisera_namn():
    assert "milano" in text.normalisera_namn("University of Milan-Bicocca")
    assert text.forkortning("Rijksuniversiteit Groningen (RuG)") == "rug"
