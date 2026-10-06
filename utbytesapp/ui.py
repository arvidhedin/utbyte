"""Delade delar för Streamlit-sidorna: data med cache, format, färger, sidomeny, filter och kort."""

from __future__ import annotations

import datetime as dt
import html
import math
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import amnen, geo, kursdata, kurstyper, lagring, modell, omgangar, rapporter

# ---------------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------------


def _mtime(fil) -> float:
    return fil.stat().st_mtime if fil.exists() else 0.0


@st.cache_data(show_spinner=False)
def _data(_m: float) -> dict | None:
    return modell.ladda_avtal()


@st.cache_data(show_spinner=False)
def _rapp(_m: float) -> dict:
    return modell.ladda_rapporter()


@st.cache_data(show_spinner=False)
def _tabell(_m1: float, _m2: float) -> pd.DataFrame:
    d = _data(_m1)
    return modell.bygg_tabell(d, _rapp(_m2)) if d else pd.DataFrame()


def data() -> dict | None:
    return _data(_mtime(modell.AVTAL))


def rapp() -> dict:
    return _rapp(_mtime(rapporter.INDEX))


def bastabell() -> pd.DataFrame:
    # Modulernas ändringstid ingår i nyckeln, så att tabellen byggs om när koden uppdateras.
    kod = max(_mtime(Path(modell.__file__)), _mtime(Path(__file__)))
    return _tabell(_mtime(modell.AVTAL), _mtime(rapporter.INDEX) + kod)


def mina() -> dict:
    return lagring.ladda()


def spara(d: dict, meddelande: str | None = None) -> None:
    lagring.spara(d)
    if meddelande:
        st.toast(meddelande, icon=":material/check:")


@st.cache_data(show_spinner=False)
def _kursdata(mapp: str, _m: float) -> kursdata.Kursdata | None:
    return kursdata.las(mapp)


def kurs() -> kursdata.Kursdata | None:
    mapp = mina()["installningar"].get("kursapp") or ""
    fil = Path(mapp).expanduser() / "data" / "mina_kurser.json"
    return _kursdata(mapp, _mtime(fil))


def inriktning() -> tuple[str | None, str | None]:
    """(inriktning, profil): eget val i utbytesappen, annars kursappens."""
    inst = mina()["installningar"]
    if inst.get("inriktning"):
        return inst["inriktning"], inst.get("profil")
    kd = kurs()
    if kd and kd.inriktning:
        return kd.inriktning, kd.profil
    return None, None


def tabell() -> pd.DataFrame:
    df = bastabell()
    if df.empty:
        return df
    inr, _ = inriktning()
    return modell.med_mina_val(df, mina(), inr)


def krav_data() -> dict:
    """Stoppar sidan med en instruktion om ingen avtalsdata finns."""
    d = data()
    if d is None:
        st.warning("Ingen avtalsdata ännu. Gå till **Data och uppdatering** och hämta, eller kör "
                   "`python verktyg/hamta_avtal.py` i terminalen.", icon=":material/cloud_download:")
        st.page_link("sidor/data.py", label="Data och uppdatering", icon=":material/sync:")
        st.stop()
    return d


# ---------------------------------------------------------------------------------------------
# Format (svenska)
# ---------------------------------------------------------------------------------------------

def tal(x: float | None, decimaler: int | None = None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    s = f"{x:.{decimaler}f}" if decimaler is not None else f"{round(x, 1):g}"
    return s.replace(".", ",").replace("-", "−")


def heltal(x: float | None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    return f"{int(round(x)):,}".replace(",", " ")


def km(x: float | None) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{heltal(round(x, -1))} km"


def e(text) -> str:
    return html.escape(str(text))


def md_escape(text: str) -> str:
    """För text i Markdown-strängar (t.ex. universitetsnamn)."""
    text = str(text)
    for tecken in "\\$*_`[]":
        text = text.replace(tecken, "\\" + tecken)
    return text


def badge(text: str, farg: str = "gray", ikon: str | None = None) -> str:
    t = str(text).replace("[", "(").replace("]", ")").replace("$", "\\$")
    return f":{farg}-badge[{ikon + ' ' if ikon else ''}{t}]"


def ar_nan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


# ---------------------------------------------------------------------------------------------
# Stil
# ---------------------------------------------------------------------------------------------

CSS_VARIABLER = """
  --ut-ink: light-dark(#0b0b0b, #ffffff);
  --ut-ink2: light-dark(#52514e, #c3c2b7);
  --ut-muted: #898781;
  --ut-grid: light-dark(#e1e0d9, #2c2c2a);
  --ut-kant: light-dark(rgba(11,11,11,0.10), rgba(255,255,255,0.12));
  --ut-spar: light-dark(#ecebe6, #2c2c2a);
  --ut-accent: light-dark(#2a78d6, #3987e5);
  --ut-accent-svag: light-dark(rgba(42,120,214,0.10), rgba(57,135,229,0.16));
  --ut-bra: light-dark(#006300, #0ca30c);
  --ut-varning: light-dark(#a15c00, #e8a33d);
"""


def injicera_css() -> None:
    st.html(f"""<style>
:root, .stApp {{ {CSS_VARIABLER} }}
.ut-rubrik {{ font-size:1.12rem; font-weight:650; color:var(--ut-ink); line-height:1.3; margin:0; }}
.ut-under {{ color:var(--ut-ink2); font-size:0.88rem; margin:2px 0 0 0; }}
.ut-tl {{ display:flex; flex-direction:column; }}
.ut-tl-rad {{ display:grid; grid-template-columns: 116px 1fr 110px; gap:12px; padding:10px 0;
  border-top:1px solid var(--ut-grid); align-items:start; }}
.ut-tl-rad.ut-forbi {{ opacity:0.55; }}
.ut-tl-rad.ut-nu {{ background: linear-gradient(90deg, var(--ut-accent-svag), transparent 70%); }}
.ut-tl-datum {{ font-weight:650; color:var(--ut-ink); font-variant-numeric: tabular-nums; line-height:1.25; }}
.ut-tl-datum small {{ display:block; font-weight:400; color:var(--ut-muted); font-size:0.78rem; }}
.ut-tl-titel {{ font-weight:600; color:var(--ut-ink); }}
.ut-tl-text {{ color:var(--ut-ink2); font-size:0.9rem; margin-top:2px; }}
.ut-tl-kvar {{ text-align:right; color:var(--ut-ink2); font-size:0.85rem; font-variant-numeric: tabular-nums; }}
.ut-prick {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; vertical-align:1px; }}
.ut-meter {{ height:10px; border-radius:5px; background:var(--ut-spar); overflow:hidden; margin:6px 0 4px 0; }}
.ut-meter > span {{ display:block; height:100%; background:var(--ut-accent); border-radius:5px; }}
.ut-meter.ut-full > span {{ background:var(--ut-bra); }}
.ut-liten {{ color:var(--ut-ink2); font-size:0.85rem; }}
.ut-jamfor td {{ vertical-align:top; }}
.ut-faktarad {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:10px; margin:6px 0 14px 0; }}
.ut-fakta {{ border:1px solid var(--ut-kant); border-radius:8px; padding:10px 12px; }}
.ut-fakta-etikett {{ color:var(--ut-ink2); font-size:0.8rem; margin-bottom:4px; }}
.ut-fakta-varde {{ color:var(--ut-ink); font-size:1.05rem; font-weight:600; line-height:1.3; }}
mark.ut-traff {{ background: color-mix(in srgb, var(--ut-accent) 22%, transparent); color:inherit; padding:0 2px; border-radius:3px; }}
</style>""")


# Plotly-färger som fungerar i både ljust och mörkt läge.
KANALFARG = {"central": "#8a5cd6", "teknat": "#2a78d6"}
GRA = "#898781"


def plotly_layout(fig: go.Figure, hojd: int = 420, **extra) -> go.Figure:
    fig.update_layout(height=hojd, margin=dict(l=4, r=4, t=8, b=4), separators=", ",
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0), **extra)
    return fig


def visa_plotly(fig: go.Figure, **kw):
    """Kartunderlaget (topojson) läses från static/karta så att kartan fungerar offline."""
    config = {"displayModeBar": False, "topojsonURL": "app/static/karta/", "scrollZoom": True}
    return st.plotly_chart(fig, width="stretch", theme="streamlit", config=config, **kw)


# ---------------------------------------------------------------------------------------------
# Sidomeny (alla sidor)
# ---------------------------------------------------------------------------------------------

def sidomeny() -> None:
    d = mina()
    inst = d["installningar"]
    kd = kurs()
    with st.sidebar:
        st.markdown("### Inställningar")
        val_lista = sorted({
            *(kursdata.inriktningar(kd, inst.get("studieplan_t8") or "HT2024") if kd else []),
        }) or [f"{i}" for i in amnen.INRIKTNINGAR]
        alternativ = [None] + val_lista
        eget = f"{inst['inriktning']}, profil {inst['profil']}" if inst.get("inriktning") and inst.get("profil") else inst.get("inriktning")
        kursappens = None
        if kd and kd.inriktning:
            kursappens = f"{kd.inriktning}, profil {kd.profil}" if kd.profil else kd.inriktning
        nu = eget or None
        etikett_none = f"Som i kursappen ({kursappens})" if kursappens else "Inte vald ännu"
        val = st.selectbox(
            "Inriktning i årskurs 4", alternativ,
            index=alternativ.index(nu) if nu in alternativ else 0,
            format_func=lambda x: etikett_none if x is None else x,
            help="Styr ämnesmatchningen och vilka kurser i termin 8 (VT2028) som visas. Ändrar inget i kursappen.",
        )
        if val != nu:
            if val is None:
                inst["inriktning"], inst["profil"] = None, None
            elif ", profil " in val:
                inst["inriktning"], inst["profil"] = val.split(", profil ", 1)
            else:
                inst["inriktning"], inst["profil"] = val, None
            spara(d)
            st.rerun()

        nasta = omgangar.nasta_omgang()
        if nasta:
            idag = dt.date.today()
            if nasta.status(idag) == "öppen":
                st.success(f"**{nasta.namn}** är öppen – sista dag {omgangar.datum_text(nasta.slut)} "
                           f"({omgangar.dagar_kvar(nasta.slut)} dagar kvar).", icon=":material/edit_note:")
            else:
                st.info(f"Nästa ansökan: **{nasta.namn}**, öppnar {omgangar.datum_text(nasta.start)} "
                        f"(om {omgangar.dagar_kvar(nasta.start)} dagar).", icon=":material/event:")
        dd = data()
        if dd:
            st.caption(f"Avtalsdata hämtad {(dd.get('hamtad') or {}).get('moveon', '?').replace('T', ' ')} · "
                       f"{len(dd['avtal'])} avtal · allt sparas lokalt.")


# ---------------------------------------------------------------------------------------------
# Filter (delas av Sök, Karta och Jämför)
# ---------------------------------------------------------------------------------------------

SORTERING = {
    "Ämnesmatchning": ("match", False),
    "Namn": ("universitet", True),
    "Land": ("land", True),
    "Avstånd från Uppsala": ("avstand_km", True),
    "Antal utbytesrapporter": ("antal_rapporter", False),
    "Rapporter från teknisk fysik": ("ttf_rapporter", False),
    "Platser på senaste vårlistan": ("platser_var", False),
}
MATCHNIVAER = {"Alla": 0, "Minst möjlig": 1, "Minst bra": 2, "Mycket bra": 3}
TERMINSLUT = {"Spelar ingen roll": 12, "Senast juni": 6, "Senast juli": 7, "Senast augusti": 8}


def behall_filter() -> None:
    """Streamlit glömmer widgetvärden på sidor som inte visas; detta behåller filtren mellan sidor."""
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith("f_"):
            st.session_state[k] = st.session_state[k]


def nollstall_filter() -> None:
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith("f_"):
            del st.session_state[k]


def filterpanel(df: pd.DataFrame, varlista: str | None) -> dict:
    """Ritar filtren i sidomenyn och returnerar deras värden."""
    alla_sprak = sorted({s for lista in df["sprak"] for s in lista}, key=lambda s: (s != "engelska", s))
    with st.sidebar:
        st.markdown("### Filter")
        f = {}
        f["text"] = st.text_input("Sök fritt", key="f_text", placeholder="t.ex. quantum, Zürich, robotics",
                                  help="Söker i namn, ort, land, ämnen och alla avtalsfält (kurskatalog, ämnesbegränsningar …).")
        f["varldsdel"] = st.multiselect("Världsdel", geo.VARLDSDELAR, key="f_varldsdel", placeholder="Alla världsdelar")
        landval = df if not f["varldsdel"] else df[df["varldsdel"].isin(f["varldsdel"])]
        f["land"] = st.multiselect("Land", sorted(landval["land"].unique()), key="f_land", placeholder="Alla länder")
        f["omgang"] = st.multiselect(
            "Ansökningsomgång för VT2028", [o.id for o in omgangar.OMGANGAR], key="f_omgang", placeholder="Alla omgångar",
            format_func=lambda i: f"{omgangar.OMGANG[i].namn} ({omgangar.OMGANG[i].kort_datum()})")
        with st.expander("Avtal och ämnen", expanded=False):
            f["kanal"] = st.multiselect("Kanal", ["Centrala avtal", "TekNat"], key="f_kanal", placeholder="Båda")
            f["enhet"] = st.multiselect("Samordnas av", sorted(df["enhet_kort"].unique()), key="f_enhet", placeholder="Alla")
            f["typ"] = st.multiselect("Avtalstyp", sorted(df["typ"].unique()), key="f_typ", placeholder="Alla typer")
            f["amnen"] = st.multiselect("Ämnesområde", [k for k in amnen.KATEGORIER
                                                        if any(k in l for l in df["kategorier"])], key="f_amnen",
                                        placeholder="Alla ämnen",
                                        help="\"Alla ämnen\" = universitetsövergripande avtal där du väljer kurser fritt.")
            f["match"] = st.select_slider("Ämnesmatchning mot din inriktning", list(MATCHNIVAER), key="f_match")
            f["niva"] = st.multiselect("Nivå", ["grund", "avancerad"], key="f_niva", placeholder="Alla nivåer",
                                       format_func=lambda n: modell.NIVA_TEXT[n])
            f["civing"] = st.checkbox("Bara avtal för civilingenjörsprogram", key="f_civing",
                                      help="Avtal märkta \"Master of Science in Engineering\" i databasen.")
            f["kurstyper"] = st.multiselect(
                "Måste gå att läsa", kurstyper.OMRADEN, key="f_kurstyper", placeholder="Inga krav",
                format_func=kurstyper.OMRADE_NAMN.get,
                help="Döljer avtal där kurstypen är stängd enligt ämnesbegränsningen (tolkning – se universitetssidan).")
            f["kt_strikt"] = st.checkbox("Räkna \"begränsat\" och \"oklart\" som nej", key="f_ktstrikt")
        with st.expander("Språk", expanded=False):
            f["sprak"] = st.multiselect("Undervisningsspråk", alla_sprak, key="f_sprak", placeholder="Alla språk",
                                        format_func=str.capitalize,
                                        help="Visar avtal där något av språken finns med.")
            f["bara_bekraftat"] = st.checkbox("Bara bekräftade språkuppgifter", key="f_bekraftat",
                                              help="Döljer avtal där språket bara är uppskattat utifrån landet.")
            f["inget_test"] = st.checkbox("Dölj avtal som kräver språktest", key="f_test")
        with st.expander("Termin, pengar och erfarenheter", expanded=False):
            f["terminslut"] = st.selectbox("Vårterminen hos värden slutar", list(TERMINSLUT), key="f_terminslut",
                                           help="Uppsalas HT2028 börjar i slutet av augusti.")
            f["erasmus"] = st.checkbox("Bara med Erasmus- eller ICM-stipendium", key="f_erasmus")
            if varlista:
                f["varlista"] = st.checkbox(f"Bara på senaste vårlistan ({varlista})", key="f_varlista",
                                            help="Centrala avtal som gick att söka i senaste vårrundan.")
            f["rapporter"] = st.checkbox("Har utbytesrapporter", key="f_rapporter")
            f["ttf"] = st.checkbox("Teknisk fysik-studenter har åkt hit", key="f_ttf")
            f["max_km"] = st.slider("Max avstånd från Uppsala (km)", 0, 20000, 20000, step=250, key="f_km")
        f["favoriter"] = st.checkbox("Bara mina favoriter", key="f_favoriter")
        f["dolj_stangda"] = st.checkbox("Dölj avtal som inte går att söka för VT2028", key="f_stangda",
                                        help="Avtal markerade \"Not open for application\" och avtal som bara tar emot helårsutbyten.")
        st.button("Nollställ filter", on_click=nollstall_filter, icon=":material/filter_alt_off:", width="stretch")
    return f


def filtrera(df: pd.DataFrame, f: dict, sokbar: dict[str, str] | None = None) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    if f.get("text"):
        ord_ = [o for o in re.split(r"\s+", f["text"].lower().strip()) if o]
        text = df["id"].map(lambda i: (sokbar or {}).get(i, ""))
        bas = (df["universitet"] + " " + df["universitet_en"] + " " + df["stad"] + " " + df["land"] + " "
               + df["enhet_sv"] + " " + df["typ"]).str.lower() + " " + text
        for o in ord_:
            m &= bas.str.contains(re.escape(o), regex=True)
    if f.get("varldsdel"):
        m &= df["varldsdel"].isin(f["varldsdel"])
    if f.get("land"):
        m &= df["land"].isin(f["land"])
    if f.get("omgang"):
        m &= df["omgangar"].map(lambda l: bool(set(l) & set(f["omgang"])))
    if f.get("kanal"):
        m &= df["kanal_text"].isin(f["kanal"])
    if f.get("enhet"):
        m &= df["enhet_kort"].isin(f["enhet"])
    if f.get("typ"):
        m &= df["typ"].isin(f["typ"])
    if f.get("amnen"):
        m &= df["kategorier"].map(lambda l: bool(set(l) & set(f["amnen"])))
    if f.get("match") and MATCHNIVAER.get(f["match"], 0):
        m &= df["match"] >= MATCHNIVAER[f["match"]]
    if f.get("niva"):
        m &= df["nivaer"].map(lambda l: bool(set(l) & set(f["niva"])))
    if f.get("civing"):
        m &= df["civilingenjor"]
    for omrade in f.get("kurstyper") or []:
        tillatna = {"öppet"} if f.get("kt_strikt") else {"öppet", "begränsat", "oklart"}
        m &= df[f"kt_{omrade}"].isin(tillatna)
    if f.get("sprak"):
        m &= df["sprak"].map(lambda l: bool(set(l) & set(f["sprak"])))
    if f.get("bara_bekraftat"):
        m &= df["sprak_status"].isin(["databasen", "samma_universitet", "egen"])
    if f.get("inget_test"):
        m &= df["test_kravs"].map(lambda v: v is not True)
    slut = TERMINSLUT.get(f.get("terminslut") or "", 12)
    if slut < 12:
        m &= df["var_slut"].map(lambda v: ar_nan(v) or v <= slut)
    if f.get("erasmus"):
        m &= df["erasmus"] | df["icm"]
    if f.get("varlista"):
        m &= df["pa_varlista"]
    if f.get("rapporter"):
        m &= df["antal_rapporter"] > 0
    if f.get("ttf"):
        m &= df["ttf_rapporter"] > 0
    if f.get("max_km") is not None and f["max_km"] < 20000:
        m &= df["avstand_km"].map(lambda v: ar_nan(v) or v <= f["max_km"])
    if f.get("favoriter"):
        m &= df["favorit"]
    if f.get("dolj_stangda"):
        m &= (df["stangt"] == "") & ~df["bara_helar"]
    return df[m]


@st.cache_data(show_spinner=False)
def _sokbar(_m: float) -> dict[str, str]:
    d = _data(_m)
    if not d:
        return {}
    ut = {}
    for a in d["avtal"]:
        delar = [a["avtalsnamn"], " ".join(i["namn"] + " " + i["engelska"] for i in a["isced"]),
                 " ".join(a["kategorier"]), (a.get("teknatsida") or {}).get("ovrigt", "")]
        delar += [f["text"] for f in a["falt"].values()]
        ut[a["id"]] = " ".join(delar).lower()
    return ut


def sokbar() -> dict[str, str]:
    return _sokbar(_mtime(modell.AVTAL))


# ---------------------------------------------------------------------------------------------
# Märken och kort
# ---------------------------------------------------------------------------------------------

def vag(rad) -> str:
    """Kort namn på avtalet/vägen: "Centralt avtal", "TekNat · fakulteten", "TekNat · Fysik och astronomi"."""
    tillagg = f" · {rad['delnamn']}" if rad.get("delnamn") else ""
    if rad["kanal"] == "central":
        return "Centralt avtal" + tillagg
    return "TekNat · " + rad["enhet_kort"].replace("TekNat (fakulteten)", "fakulteten") + tillagg


def sok_via(rad) -> str:
    """"Sök via TekNat (15 jan–15 feb 2027)" osv."""
    delar = [f"{o.namn.split(' – ')[-1]} {o.kort_datum()}" for o in omgangar.omgangar_for(rad["kanal"])]
    if rad["kanal"] == "central":
        return "Centrala ansökan: " + " · ".join(delar)
    return "TekNats ansökan: " + " · ".join(delar)


def avtalsmarken(rad, kort: bool = False) -> str:
    b = []
    if rad["kanal"] == "central":
        b.append(badge(vag(rad), "violet", ":material/public:"))
    else:
        b.append(badge(vag(rad), "blue", ":material/school:"))
    if rad["erasmus"] and not ar_nan(rad["erasmus_euro"]):
        b.append(badge(f"{'Nordtek · ' if rad['nordtek'] else ''}Erasmus {heltal(rad['erasmus_euro'])} €/mån", "green",
                       ":material/euro:"))
    elif rad["erasmus"]:
        b.append(badge("Erasmus", "green"))
    elif rad["icm"]:
        b.append(badge("ICM-stipendium", "green", ":material/euro:"))
    elif rad["typ"] == "Ämnesspecifikt":
        b.append(badge("Ämnesspecifikt avtal", "gray"))
    if rad["civilingenjor"]:
        b.append(badge("Civ.ing.-avtal", "primary", ":material/engineering:"))
    if not kort:
        amn = rad["amnen"] or ([amnen.ALLA] if amnen.ALLA in rad["kategorier"] else [])
        if amnen.ALLA in rad["kategorier"]:
            amn = [amnen.ALLA]
        if amn:
            b.append(badge(", ".join(dict.fromkeys(amn))[:60], "gray", ":material/category:"))
    if not kort:
        b.append(kurstypmarke(rad))
    if rad["bara_helar"]:
        b.append(badge("Bara helårsutbyte", "red", ":material/block:"))
    if rad["stangt"]:
        b.append(badge(rad["stangt"], "red", ":material/block:"))
    if rad["varvarning"]:
        b.append(badge("Obs: villkor för vårterminen", "orange", ":material/warning:"))
    if rad["restplatser"]:
        b.append(badge(f"Restplatser: {rad['restplatser']}", "orange", ":material/event_seat:"))
    return " ".join(b)


KT_SYMBOL = {"öppet": "✓", "begränsat": "≈", "stängt": "✗", "oklart": "?"}
KT_KORT = {"teknik": "Teknik", "fysik": "Fysik", "matematik": "Matte", "data": "Data"}


def kurstypmarke(rad) -> str:
    """"Teknik ✓ · Fysik ✓ · Matte ✓ · Data ✗" – grå om allt är öppet, annars orange."""
    delar = [f"{KT_KORT[o]} {KT_SYMBOL[rad[f'kt_{o}']]}" for o in kurstyper.OMRADEN]
    farg = "gray" if all(rad[f"kt_{o}"] == "öppet" for o in ("teknik", "fysik")) else "orange"
    return badge(" · ".join(delar), farg, ":material/menu_book:")


def sprakmarke(sprak: list[str], status: str, engelska_master: bool = False) -> str:
    text = modell.sprak_visning(sprak, status, engelska_master)
    if status in ("databasen", "egen"):
        return badge(text, "blue", ":material/translate:")
    if status == "samma_universitet":
        return badge(text, "blue", ":material/translate:")
    return badge(text + " (obekräftat)", "gray", ":material/translate:")


MATCHFARG = {3: "green", 2: "blue", 1: "gray", 0: "gray"}


def universitetsmarken(u, varlista: str | None) -> str:
    b = [badge(f"Ämnesmatch: {amnen.MATCH_TEXT[int(u['match'])]}", MATCHFARG[int(u["match"])], ":material/target:")]
    b.append(sprakmarke(u["sprak"], "databasen" if u["sprak_bekraftat"] else "obekraftad"))
    if u["pa_varlista"]:
        pl = u["platser_var"]
        b.append(badge(f"Vårlistan {varlista[2:] if varlista else ''}: "
                       f"{heltal(pl) + ' platser' if not ar_nan(pl) else 'fanns med'}", "orange", ":material/event_seat:"))
    if u["antal_rapporter"]:
        b.append(badge(f"{u['antal_rapporter']} {'rapport' if u['antal_rapporter'] == 1 else 'rapporter'}"
                       + (f" · {u['ttf_rapporter']} från TTF" if u["ttf_rapporter"] else ""),
                       "gray", ":material/description:"))
    return " ".join(b)


def vaxla_favorit(avtal_id: str) -> None:
    d = mina()
    ar = lagring.vaxla_favorit(d, avtal_id)
    spara(d, "Sparad i Mina val" if ar else "Borttagen ur Mina val")


def oppna_universitet(core_id: str) -> None:
    st.session_state["vald_uni"] = core_id


def universitetskort(u, avtal: pd.DataFrame, varlista: str | None, nyckel: str = "") -> None:
    with st.container(border=True):
        v, h = st.columns([6, 1], vertical_alignment="top")
        with v:
            namn_en = f" · {u['universitet_en']}" if u["universitet_en"] and u["universitet_en"] != u["universitet"] else ""
            st.markdown(f'<p class="ut-rubrik">{e(u["flagga"])} {e(u["universitet"])}</p>'
                        f'<p class="ut-under">{e(u["stad"] + ", " if u["stad"] else "")}{e(u["land"])} · '
                        f'{e(u["region"])} · {e(km(u["avstand_km"]))} från Uppsala{e(namn_en)}</p>',
                        unsafe_allow_html=True)
        with h:
            if st.button("Öppna", key=f"oppna_{nyckel}{u['core_id']}", icon=":material/open_in_new:",
                         width="stretch", help="Visa alla detaljer om universitetet"):
                oppna_universitet(u["core_id"])
                st.switch_page("sidor/universitet.py")
        st.markdown(universitetsmarken(u, varlista))
        for _, rad in avtal.iterrows():
            a, b = st.columns([14, 1], vertical_alignment="center")
            with a:
                st.markdown(avtalsmarken(rad) + "  \n" + f":small[{md_escape(sok_via(rad))} · "
                            f"kontakt {md_escape(rad['kontakt'])}]")
            with b:
                fav = bool(rad["favorit"])
                st.button("", key=f"fav_{nyckel}{rad['id']}", icon=":material/star:" if fav else ":material/star_border:",
                          type="tertiary", on_click=vaxla_favorit, args=(rad["id"],),
                          help="Ta bort ur Mina val" if fav else "Spara i Mina val")


def faktarutor(rutor: list[tuple[str, str, str | None]]) -> None:
    """Nyckeltal där värdet får radbrytas (st.metric kortar av långa texter)."""
    celler = "".join(
        f'<div class="ut-fakta"{f" title={chr(34)}{e(hjalp)}{chr(34)}" if hjalp else ""}>'
        f'<div class="ut-fakta-etikett">{e(etikett)}{" ⓘ" if hjalp else ""}</div>'
        f'<div class="ut-fakta-varde">{e(varde)}</div></div>'
        for etikett, varde, hjalp in rutor)
    st.markdown(f'<div class="ut-faktarad">{celler}</div>', unsafe_allow_html=True)


def meter(andel: float, full: bool = False) -> str:
    andel = max(0.0, min(andel, 1.0))
    return f'<div class="ut-meter{" ut-full" if full else ""}"><span style="width:{andel * 100:.1f}%"></span></div>'


def markera(text: str, ord_: list[str], bredd: int = 220) -> str:
    """Utdrag kring första träffen med träffarna markerade (HTML)."""
    if not text:
        return ""
    lagre = text.lower()
    pos = min((lagre.find(o) for o in ord_ if o and lagre.find(o) >= 0), default=-1)
    if pos < 0:
        utdrag = text[:bredd]
        return e(utdrag) + ("…" if len(text) > bredd else "")
    start = max(0, pos - bredd // 3)
    utdrag = text[start:start + bredd]
    ut = e(utdrag)
    for o in sorted({o for o in ord_ if o}, key=len, reverse=True):
        ut = re.sub(re.escape(e(o)), lambda m: f'<mark class="ut-traff">{m.group(0)}</mark>', ut, flags=re.I)
    return ("…" if start else "") + ut + ("…" if start + bredd < len(text) else "")
