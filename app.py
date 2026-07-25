from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import api
import database
import pandas as pd
import streamlit as st
from views import formularz, podglad, profil, ranking, regulamin

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="EKSTRAKLAPA - Typer 2026/27", page_icon="⚽", layout="wide"
)


# --- AUTOMATYCZNA SYNCHRONIZACJA (CO MAX 30 MINUT) ---
def auto_synchronizacja_check():
  czas_str = database.pobierz_czas_synchro()
  wykonaj_synchro = False

  if czas_str == "Brak danych":
    wykonaj_synchro = True
  else:
    try:
      ostatnia = datetime.strptime(czas_str, "%d.%m.%Y %H:%M:%S").replace(
          tzinfo=ZoneInfo("Europe/Warsaw")
      )
      teraz = datetime.now(ZoneInfo("Europe/Warsaw"))

      # Wykonaj synchronizację tylko jeśli minęło 30 minut lub więcej
      if teraz - ostatnia >= timedelta(minutes=30):
        wykonaj_synchro = True
    except Exception:
      wykonaj_synchro = True

  if wykonaj_synchro:
    surowe = api.pobierz_mecze_ekstraklasy()
    if surowe:
      database.synchronizuj_mecze_wsadowo(surowe)


# Wywołujemy sprawdzenie auto-synchro przy każdym przeładowaniu
auto_synchronizacja_check()

# Pobieramy mecze z bazy danych Supabase dla całej aplikacji
wszystkie_mecze = []
try:
  res = database.db.table("mecze").select("*").execute()
  if res.data:
    wszystkie_mecze = res.data
except Exception as e:
  st.error(f"Błąd połączenia z bazą danych: {e}")

# BANER TYTUŁOWY
st.markdown(
    """
<div style="background-color: #0b0e14; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 25px; border: 1px solid #1f293d;">
    <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 900; letter-spacing: 2px;">⚽ EKSTRAKLAPA</h1>
    <p style="color: #00f2ff; margin: 5px 0 0 0; font-size: 13px; font-weight: 700; letter-spacing: 1px;">TYPER 2026/27</p>
</div>
""",
    unsafe_allow_html=True,
)

# --- PANEL BOCZNY (SIDEBAR) ---
st.sidebar.title("👤 Panel Gracza")

gracze_lista = database.pobierz_liste_graczy()

if "zalogowany_gracz" not in st.session_state:
  st.session_state["zalogowany_gracz"] = None

# LOGOWANIE / REJESTRACJA W SIDEBARZE
if not st.session_state["zalogowany_gracz"]:
  tab_log, tab_reg = st.sidebar.tabs(["🔑 Logowanie", "📝 Rejestracja"])

  with tab_log:
    wybrany_do_logowania = st.selectbox("Wybierz gracza:", [""] + gracze_lista)
    wpisany_pin = st.text_input(
        "Wpisz 4-cyfrowy PIN:", type="password", key="login_pin"
    )

    if st.button("🚀 Zaloguj się", use_container_width=True):
      if not wybrany_do_logowania:
        st.error("Wybierz gracza z listy!")
      elif database.weryfikuj_pin_gracza(wybrany_do_logowania, wpisany_pin):
        st.session_state["zalogowany_gracz"] = wybrany_do_logowania
        st.success(f"Witaj {wybrany_do_logowania}!")
        st.rerun()
      else:
        st.error("Niepoprawny PIN!")

  with tab_reg:
    nowy_nick = st.text_input("Nowy Nick:")
    nowy_pin = st.text_input(
        "Ustal PIN (np. 1234):", type="password", key="reg_pin"
    )
    ulubiony_klub = st.text_input("Ulubiony Klub (opcjonalnie):")

    if st.button("Zarejestruj", use_container_width=True):
      ok, msg = database.zarejestruj_gracza(
          nowy_nick, nowy_pin, ulubiony_klub
      )
      if ok:
        st.success(msg)
        st.rerun()
      else:
        st.error(msg)
else:
  st.sidebar.success(
      f"Zalogowano jako: **{st.session_state['zalogowany_gracz']}**"
  )
  if st.sidebar.button("🚪 Wyloguj", use_container_width=True):
    st.session_state["zalogowany_gracz"] = None
    st.rerun()

# --- PRZYCISK SYNCHRONIZACJI WIDOCZNY TYLKO DLA "Mateusz" ---
if st.session_state.get("zalogowany_gracz") == "Mateusz":
  st.sidebar.markdown("---")
  st.sidebar.subheader("⚙️ Zarządzanie ligą")
  if st.sidebar.button(
      "🔄 Wymuś synchronizację z API", use_container_width=True
  ):
    surowe = api.pobierz_mecze_ekstraklasy()
    if database.synchronizuj_mecze_wsadowo(surowe):
      st.sidebar.success("Zsynchronizowano pomyślnie!")
      st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(
    f"⏱️ Ostatnia synchro: {database.pobierz_czas_synchro()}"
)

# --- ZAKŁADKI GŁÓWNE ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Formularz Typowania",
    "🏆 Tabela / Ranking",
    "👁️ Podgląd Typów",
    "⚙️ Profil",
    "📜 Regulamin",
])

with tab1:
  if st.session_state["zalogowany_gracz"]:
    formularz.render_formularz(
        st.session_state["zalogowany_gracz"], wszystkie_mecze
    )
  else:
    st.info("👈 Zaloguj się w panelu bocznym, aby oddawać i edytować typy!")

with tab2:
  ranking.render_ranking(wszystkie_mecze)

with tab3:
  podglad.render_podglad(wszystkie_mecze)

with tab4:
  if st.session_state["zalogowany_gracz"]:
    profil.render_profil(st.session_state["zalogowany_gracz"])
  else:
    st.info("👈 Zaloguj się, aby zmienić PIN, nick lub ulubiony klub.")

with tab5:
  regulamin.render_regulamin()
