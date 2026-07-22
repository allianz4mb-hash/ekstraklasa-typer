from datetime import datetime
import re
from zoneinfo import ZoneInfo
import api
import database
import streamlit as st

st.set_page_config(page_title="Ekstraklasa Typer", page_icon="⚽", layout="wide")

db = database.init_supabase()

# --- ZARZĄDZANIE SESJĄ LOGOWANIA ---
if "zalogowany_gracz" not in st.session_state:
  st.session_state["zalogowany_gracz"] = None


def pobierz_czas_pl(data_str):
  if not data_str:
    return None
  try:
    val_str = str(data_str)
    if val_str.endswith("Z"):
      val_str = val_str[:-1] + "+00:00"

    dt_utc = datetime.fromisoformat(val_str)
    return dt_utc.astimezone(ZoneInfo("Europe/Warsaw"))
  except Exception:
    return None


def formatuj_date(data_str):
  dt_pl = pobierz_czas_pl(data_str)
  if dt_pl:
    return dt_pl.strftime("📅 %d.%m.%Y, godz. %H:%M")
  return f"📅 {data_str}"


def czy_mecz_zablokowany(data_str, status_meczu):
  status_clean = str(status_meczu).lower()
  if status_clean not in ["not started", "ns", "scheduled", ""]:
    return True

  dt_mecz_pl = pobierz_czas_pl(data_str)
  if dt_mecz_pl:
    teraz_pl = datetime.now(ZoneInfo("Europe/Warsaw"))
    if teraz_pl >= dt_mecz_pl:
      return True

  return False


st.title("⚽ Ekstraklasa Typer 2026/2027")

# --- PANEL BOCZNY: LOGOWANIE I REJESTRACJA ---
st.sidebar.header("👤 Panel Gracza")

dostepni_gracze = database.pobierz_liste_graczy()

if not st.session_state["zalogowany_gracz"]:
  tab_login, tab_register = st.sidebar.tabs(["🔑 Logowanie", "📝 Rejestracja"])

  # --- ZAKŁADKA 1: LOGOWANIE ---
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
      st.info("Brak graczy w bazie. Zarejestruj się w obok!")

  # --- ZAKŁADKA 2: REJESTRACJA ---
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
          # Automatyczne zalogowanie po udanej rejestracji
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

# --- GŁÓWNY WIDOK: FORMULARZ TYPOWANIA ---
st.header("🎯 Formularz Typowania")

try:
  res_mecze = (
      db.table("mecze").select("*").order("data_meczu", desc=False).execute()
  )
  wszystkie_mecze = res_mecze.data
except Exception:
  wszystkie_mecze = []

if not wszystkie_mecze:
  st.info(
      "Brak meczów w bazie. Kliknij **'Synchronizuj terminarz z API'** w panelu"
      " bocznym!"
  )
else:


  def wyciagnij_numer_kolejki(nazwa_kolejki):
    cyfry = re.findall(r"\d+", nazwa_kolejki)
    return int(cyfry[0]) if cyfry else 0


  kolejki = sorted(
      list(set(m["kolejka"] for m in wszystkie_mecze)),
      key=wyciagnij_numer_kolejki,
  )
  wybrana_kolejka = st.selectbox("Wybierz kolejkę do wytypowania:", kolejki)

  mecze_w_kolejce = [
      m for m in wszystkie_mecze if m["kolejka"] == wybrana_kolejka
  ]

  dotychczasowe_typy = (
      database.pobierz_typy_gracza(wybrany_gracz) if wybrany_gracz else {}
  )

  if not wybrany_gracz:
    st.warning(
        "🔒 Zaloguj się lub zarejestruj w panelu bocznym po lewej stronie, aby"
        " typować!"
    )

  with st.form("formularz_typowania"):
    nowe_typy = {}

    for mecz in mecze_w_kolejce:
      mecz_id = mecz["id"]
      zapisany_typ = dotychczasowe_typy.get(mecz_id, None)

      data_f = formatuj_date(mecz.get("data_meczu"))
      zablokowany = czy_mecz_zablokowany(
          mecz.get("data_meczu"), mecz.get("status")
      )

      col_header1, col_header2 = st.columns([2, 2])
      with col_header1:
        st.caption(f"⏱️ {data_f}")

      with col_header2:
        if zablokowany:
          if zapisany_typ is not None:
            st.markdown(
                f"<div style='text-align: right; color: #d32f2f; font-weight:"
                f" bold;'>🔒 Zamknięte (Twój typ: {zapisany_typ[0]} -"
                f" {zapisany_typ[1]})</div>",
                unsafe_allow_html=True,
            )
          else:
            st.markdown(
                "<div style='text-align: right; color: #d32f2f; font-weight:"
                " bold;'>🔒 Zamknięte (Brak typu)</div>",
                unsafe_allow_html=True,
            )
        else:
          if zapisany_typ is not None:
            st.markdown(
                f"<div style='text-align: right; color: #2e7d32; font-weight:"
                f" bold;'>🟢 Obstawiono: {zapisany_typ[0]} - {zapisany_typ[1]}</div>",
                unsafe_allow_html=True,
            )
          else:
            st.markdown(
                "<div style='text-align: right; color: #888888;'>⚪ Brak"
                " typu</div>",
                unsafe_allow_html=True,
            )

      col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 3])

      logo_h = mecz.get("logo_gospodarze")
      logo_a = mecz.get("logo_goscie")

      with col1:
        if logo_h:
          st.markdown(
              f"<div style='display: flex; align-items: center; gap:"
              f" 10px;'><img src='{logo_h}' width='28' height='28'/>"
              f" <b>{mecz['gospodarze']}</b></div>",
              unsafe_allow_html=True,
          )
        else:
          st.write(f"**{mecz['gospodarze']}**")

      domyslna_gosp = int(zapisany_typ[0]) if zapisany_typ is not None else 0
      domyslna_gosc = int(zapisany_typ[1]) if zapisany_typ is not None else 0

      disabled_flag = (not wybrany_gracz) or zablokowany

      with col2:
        typ_gosp = st.number_input(
            "Gospodarze",
            min_value=0,
            max_value=15,
            value=domyslna_gosp,
            key=f"gosp_{mecz_id}",
            label_visibility="collapsed",
            disabled=disabled_flag,
        )

      with col3:
        st.markdown(
            "<h4 style='text-align: center; margin: 0;'>:</h4>",
            unsafe_allow_html=True,
        )

      with col4:
        typ_gosc = st.number_input(
            "Goście",
            min_value=0,
            max_value=15,
            value=domyslna_gosc,
            key=f"gosc_{mecz_id}",
            label_visibility="collapsed",
            disabled=disabled_flag,
        )

      with col5:
        if logo_a:
          st.markdown(
              f"<div style='display: flex; align-items: center; gap:"
              f" 10px;'><img src='{logo_a}' width='28' height='28'/>"
              f" <b>{mecz['goscie']}</b></div>",
              unsafe_allow_html=True,
          )
        else:
          st.write(f"**{mecz['goscie']}**")

      st.markdown("---")

      if wybrany_gracz and not zablokowany:
        nowe_typy[mecz_id] = {
            "gracz_nick": wybrany_gracz,
            "mecz_id": mecz_id,
            "typ_gospodarze": typ_gosp,
            "typ_goscie": typ_gosc,
        }

    zapisz_button = st.form_submit_button(
        "💾 Zapisz moje typy na tę kolejkę",
        use_container_width=True,
        type="primary",
        disabled=not wybrany_gracz,
    )

    if zapisz_button and wybrany_gracz:
      paczka_do_zapisu = list(nowe_typy.values())
      if paczka_do_zapisu:
        sukces = database.zapisz_typy_gracza(paczka_do_zapisu)
        if sukces:
          st.success("✅ Pomyślnie zapisano Twoje typy!")
          st.rerun()
      else:
        st.info("Brak aktywnych meczów do zapisania w tej kolejce.")
