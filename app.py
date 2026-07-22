import api
import database
import streamlit as st
from views.matryca import render_matryca
from views.ranking import render_ranking
from views.typowanie import render_typowanie

st.set_page_config(page_title="Ekstraklasa Typer", page_icon="⚽", layout="wide")

db = database.init_supabase()

# --- ZARZĄDZANIE SESJĄ LOGOWANIA ---
if "zalogowany_gracz" not in st.session_state:
  st.session_state["zalogowany_gracz"] = None

st.title("⚽ Ekstraklasa Typer 2026/2027")

# --- PANEL BOCZNY: LOGOWANIE I REJESTRACJA ---
st.sidebar.header("👤 Panel Gracza")

dostepni_gracze = database.pobierz_liste_graczy()

if not st.session_state["zalogowany_gracz"]:
  tab_login, tab_register = st.sidebar.tabs(["🔑 Logowanie", "📝 Rejestracja"])

  with tab_login:
    if dostepni_gracze:
      wybrany_gracz_do_logowania = st.selectbox(
          "Wybierz gracza:", dostepni_gracze, key="login_select"
      )
      wpisany_pin = st.text_input("Wpisz PIN:", type="password", key="login_pin")

      if st.button("🔑 Zaloguj się", use_container_width=True):
        if database.weryfikuj_pin_gracza(
            wybrany_gracz_do_logowania, wpisany_pin
        ):
          st.session_state["zalogowany_gracz"] = wybrany_gracz_do_logowania
          st.success("Zalogowano pomyślnie!")
          st.rerun()
        else:
          st.error("❌ Nieprawidłowy PIN!")
    else:
      st.info("Brak graczy w bazie. Zarejestruj się obok!")

  with tab_register:
    nowy_nick = st.text_input("Nick / Imię:", key="reg_nick")
    nowy_pin = st.text_input("Ustal PIN:", type="password", key="reg_pin")
    powtorz_pin = st.text_input(
        "Powtórz PIN:", type="password", key="reg_pin_repeat"
    )

    if st.button("✨ Zarejestruj się", use_container_width=True):
      if not nowy_nick.strip():
        st.error("Podaj swój nick!")
      elif not nowy_pin.strip():
        st.error("Ustal PIN!")
      elif nowy_pin != powtorz_pin:
        st.error("Wpisane PIN-y nie są identyczne!")
      else:
        sukces, komunikat = database.zarejestruj_gracza(nowy_nick, nowy_pin)
        if sukces:
          st.success(komunikat)
          st.session_state["zalogowany_gracz"] = nowy_nick.strip()
          st.rerun()
        else:
          st.error(komunikat)

else:
  wybrany_gracz = st.session_state["zalogowany_gracz"]
  st.sidebar.success(f"Zalogowany jako: **{wybrany_gracz}**")

  if st.sidebar.button("🚪 Wyloguj się", use_container_width=True):
    st.session_state["zalogowany_gracz"] = None
    st.rerun()

wybrany_gracz = st.session_state["zalogowany_gracz"]

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Zarządzanie ligą")

if st.sidebar.button("🔄 Synchronizuj terminarz z API"):
  with st.spinner("Pobieranie terminarza Ekstraklasy..."):
    liga_info = api.pobierz_ligę_ekstraklasa()

    if liga_info:
      seasons = liga_info.get("seasons", [])
      current_season = (
          max([s["season"] for s in seasons]) if seasons else 2026
      )
      league_id = liga_info.get("id")

      surowe_mecze = api.pobierz_mecze_ekstraklasy(league_id, current_season)

      if surowe_mecze:
        sukces = database.synchronizuj_mecze_wsadowo(surowe_mecze)
        if sukces:
          st.sidebar.success("Zsynchronizowano mecze i herby pomyślnie!")
          st.rerun()
        else:
          st.sidebar.error("Błąd zapisu meczów do bazy.")
      else:
        st.sidebar.warning("API zwróciło pustą listę meczów.")
    else:
      st.sidebar.error("Nie udało się odnaleźć polskiej Ekstraklasy w API.")

# --- WCHODZENIE W ZAKŁADKI ---
tab_typowanie, tab_ranking, tab_matryca = st.tabs(
    ["🎯 Formularz Typowania", "🏆 Tabela / Ranking", "👁️ Podgląd Typów"]
)

try:
  res_mecze = (
      db.table("mecze").select("*").order("data_meczu", desc=False).execute()
  )
  wszystkie_mecze = res_mecze.data
except Exception:
  wszystkie_mecze = []

with tab_typowanie:
  render_typowanie(wszystkie_mecze, wybrany_gracz)

with tab_ranking:
  render_ranking(wszystkie_mecze)

with tab_matryca:
  render_matryca(wszystkie_mecze, wybrany_gracz)
