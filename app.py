from datetime import datetime
import re
from zoneinfo import ZoneInfo
import api
import database
import streamlit as st

st.set_page_config(page_title="Ekstraklasa Typer", page_icon="⚽", layout="wide")

db = database.init_supabase()


def formatuj_date(data_str):
  """Przelicza czas UTC z API na czas polski (Europe/Warsaw) i formatuje czytelnie."""
  if not data_str:
    return ""
  try:
    # Zamiana ISO UTC (np. '2026-07-24T17:00:00Z') na obiekt datetime z UTC
    val_str = str(data_str)
    if val_str.endswith("Z"):
      val_str = val_str[:-1] + "+00:00"

    dt_utc = datetime.fromisoformat(val_str)
    # Konwersja na strefę czasową Polski (Europe/Warsaw)
    dt_pl = dt_utc.astimezone(ZoneInfo("Europe/Warsaw"))

    return dt_pl.strftime("📅 %d.%m.%Y, godz. %H:%M")
  except Exception:
    return f"📅 {data_str}"


st.title("⚽ Ekstraklasa Typer 2026/2027")

# --- PANEL BOCZNY ---
st.sidebar.header("👤 Panel Gracza")

try:
  res_gracze = db.table("gracze").select("nick").execute()
  dostepni_gracze = [g["nick"] for g in res_gracze.data]
except Exception:
  dostepni_gracze = []

wybrany_gracz = st.sidebar.selectbox("Wybierz swój profil:", dostepni_gracze)

if wybrany_gracz:
  st.sidebar.success(f"Zalogowany jako: **{wybrany_gracz}**")
else:
  st.sidebar.warning("Brak graczy w bazie. Dodaj kogoś w tabeli 'gracze'!")

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
          st.sidebar.success("Zsynchronizowano mecze pomyślnie!")
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
    st.warning("⚠️ Wybierz swój profil w panelu bocznym, aby móc typować mecze!")

  with st.form("formularz_typowania"):
    nowe_typy = {}

    for mecz in mecze_w_kolejce:
      mecz_id = mecz["id"]
      zapisany_typ = dotychczasowe_typy.get(mecz_id, None)

      # Nagłówek meczu: Polskojęzyczna data oraz status obstawienia
      data_f = formatuj_date(mecz.get("data_meczu"))

      col_header1, col_header2 = st.columns([2, 2])
      with col_header1:
        st.caption(f"⏱️ {data_f}")
      with col_header2:
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

      # Wiersz zespołu i pól do wpisywania wyników
      col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 3])

      with col1:
        logo_h = mecz.get("logo_gospodarze")
        if logo_h:
          col_img, col_txt = st.columns([1, 4])
          with col_img:
            st.image(logo_h, width=30)
          with col_txt:
            st.write(f"**{mecz['gospodarze']}**")
        else:
          st.write(f"**{mecz['gospodarze']}**")

      domyslna_gosp = int(zapisany_typ[0]) if zapisany_typ is not None else 0
      domyslna_gosc = int(zapisany_typ[1]) if zapisany_typ is not None else 0

      with col2:
        typ_gosp = st.number_input(
            "Gospodarze",
            min_value=0,
            max_value=15,
            value=domyslna_gosp,
            key=f"gosp_{mecz_id}",
            label_visibility="collapsed",
            disabled=not wybrany_gracz,
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
            disabled=not wybrany_gracz,
        )

      with col5:
        logo_a = mecz.get("logo_goscie")
        if logo_a:
          col_img, col_txt = st.columns([1, 4])
          with col_img:
            st.image(logo_a, width=30)
          with col_txt:
            st.write(f"**{mecz['goscie']}**")
        else:
          st.write(f"**{mecz['goscie']}**")

      st.markdown("---")

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

    if zapisz_button:
      paczka_do_zapisu = list(nowe_typy.values())
      sukces = database.zapisz_typy_gracza(paczka_do_zapisu)
      if sukces:
        st.success("✅ Pomyślnie zapisano Twoje typy!")
        st.rerun()
