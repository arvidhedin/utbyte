"""Utbytesöversikt – utbytesstudier VT2028 för teknisk fysik vid Uppsala universitet.

Starta med:  streamlit run app.py   (eller dubbelklicka på start.command)
"""

import streamlit as st

from utbytesapp import ui

st.set_page_config(page_title="Utbytesöversikt", page_icon=":material/flight_takeoff:", layout="wide")
ui.injicera_css()
ui.behall_filter()

sidor = {
    "Start": [
        st.Page("sidor/oversikt.py", title="Översikt", icon=":material/dashboard:", default=True),
    ],
    "Hitta": [
        st.Page("sidor/sok.py", title="Sök", icon=":material/search:"),
        st.Page("sidor/karta.py", title="Karta", icon=":material/map:"),
        st.Page("sidor/universitet.py", title="Universitet", icon=":material/account_balance:"),
        st.Page("sidor/jamfor.py", title="Jämför", icon=":material/compare_arrows:"),
    ],
    "Planera": [
        st.Page("sidor/mina_val.py", title="Mina val", icon=":material/star:"),
        st.Page("sidor/tidslinje.py", title="Tidslinje", icon=":material/event:"),
        st.Page("sidor/kursplan.py", title="Kursplan", icon=":material/menu_book:"),
        st.Page("sidor/merit.py", title="Meritvärde och urval", icon=":material/leaderboard:"),
    ],
    "Läs": [
        st.Page("sidor/rapporter.py", title="Utbytesrapporter", icon=":material/description:"),
    ],
    "Data": [
        st.Page("sidor/data.py", title="Data och uppdatering", icon=":material/sync:"),
    ],
}
sida = st.navigation(sidor, position="top")
ui.sidomeny()
sida.run()
