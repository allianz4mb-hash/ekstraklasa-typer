import api
import database
import streamlit as st
from views.matryca import render_matryca
from views.profil import render_profil
from views.ranking import render_ranking
from views.typowanie import render_typowanie

st.set_page_config(page_title="Ekstraklasa Typer", page_icon="⚽", layout="wide")

db = database.init_supabase()


# --- AUTOMATYCZNA SYNCHRONIZACJA W TLE (MAX RAZ NA 30 MINUT) ---
@st.cache_data(ttl=1800, show_spinner=False)
def automatyczna_synchronizacja():
  try:
    liga_info = api.pobierz_ligę_ekstraklasa()
    if liga_info:
      seasons = liga_info.get("seasons", [])
      current_season = max([s["season"] for s in seasons]) if seasons else 2026
      league_id = liga_info.get("id")
      surowe_mecze = api.pobierz_mecze_ekstraklasy(league_id, current_season)
      if surowe_mecze:
        database.synchronizuj_mecze_wsadowo(surowe_mecze)
  except Exception:
    pass


automatyczna_synchronizacja()

# --- ZARZĄDZANIE SESJĄ ---
if "zalogowany_gracz" not in st.session_state:
  st.session_state["zalogowany_gracz"] = None

# Pobieramy nick domyślny zapamiętany na tym urządzeniu
zapamietany_nick = st.query_params.get("gracz", "")

st.title("⚽ Ekstraklasa Typer 2026/2027")

# --- PANEL BOCZNY ---
st.sidebar.header("👤 Panel Gracza")

dostepni_gracze = database.pobierz_liste_graczy()

if not st.session_state["zalogowany_gracz"]:
  tab_login, tab_register = st.sidebar.tabs(["🔑 Logowanie", "📝 Rejestracja"])

  with tab_login:
    if dostepni_gracze:
      with st.form("form_logowania"):
        # Standardowe pole tekstowe aktywuje wykrywanie formularza logowania przez iOS Safari (FaceID)
        wpisany_nick = st.text_input(
            "Nick / Imię:",
            value=zapamietany_nick,
            key="login_nick_input",
            placeholder="Wpisz swój nick",
        )
        wpisany_pin = st.text_input(
            "4-cyfrowy PIN:",
            type="password",
            max_chars=4,
            key="login_pin_input",
        )

        btn_login = st.form_submit_button(
            "🔑 Zaloguj się", use_container_width=True, type="primary"
        )

        if btn_login:
          nick_clean = wpisany_nick.strip()
          if not nick_clean:
            st.error("Wpisz swój nick!")
          elif database.weryfikuj_pin_gracza(nick_clean, wpisany_pin):
            st.session_state["zalogowany_gracz"] = nick_clean
            # Zapamiętujemy Twój nick na Twoim urządzeniu
            st.query_params["gracz"] = nick_clean
            st.success("Zalogowano pomyślnie!")
            st.rerun()
          else:
            st.error("❌ Nieprawidłowy nick lub PIN!")

      # Ściągawka z listą graczy na wypadek gdyby ktoś zapomniał jak dokładnie zapisał swój nick
      with st.expander("📋 Lista zarejestrowanych graczy"):
        st.write(", ".join(dostepni_gracze))
    else:
      st.info("Brak graczy w bazie. Zarejestruj się obok!")

  with tab_register:
    with st.form("form_rejestracji"):
      nowy_nick = st.text_input("Nick / Imię:", key="reg_nick")
      nowy_pin = st.text_input(
          "Ustal 4-cyfrowy PIN:",
          type="password",
          max_chars=4,
          key="reg_pin",
          help="PIN musi składać się z 4 cyfr (np. 1234)",
      )
      powtorz_pin = st.text_input(
          "Powtórz 4-cyfrowy PIN:",
          type="password",
          max_chars=4,
          key="reg_pin_repeat",
      )

      btn_reg = st.form_submit_button(
          "✨ Zarejestruj się", use_container_width=True, type="primary"
      )

      if btn_reg:
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
            st.query_params["gracz"] = nowy_nick.strip()
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

if st.sidebar.button("🔄 Wymuś synchronizację z API", use_container_width=True):
  st.cache_data.clear()
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

# Podgląd czasu ostatniej synchronizacji z bazy Supabase
czas_synchro = database.pobierz_czas_synchro()
st.sidebar.caption(f"⏱️ **Ostatnia synchro:** {czas_synchro}")

# --- WCHODZENIE W ZAKŁADKI ---
tab_typowanie, tab_ranking, tab_matryca, tab_profil = st.tabs([
    "🎯 Formularz Typowania",
    "🏆 Tabela / Ranking",
    "👁️ Podgląd Typów",
    "⚙️ Profil",
])

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

with tab_profil:
  render_profil(wybrany_gracz)
