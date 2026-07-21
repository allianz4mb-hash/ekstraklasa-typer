import api
import database
import streamlit as st

st.set_page_config(page_title="Ekstraklasa Typer", page_icon="⚽", layout="wide")

db = database.init_supabase()

st.title("⚽ Ekstraklasa Typer 2026/2027")

# --- PANEL BOCZNY: LOGOWANIE I SYNCHRONIZACJA ---
st.sidebar.header("👤 Panel Gracza")

try:
  res_gracze = db.table("gracze").select("nick").execute()
  dostepni_gracze = [g["nick"] for g in res_gracze.data]
except Exception:
  dostepni_gracze = []

wybrany_gracze = st.sidebar.selectbox("Wybierz swój profil:", dostepni_gracze)

if wybrany_gracze:
  st.sidebar.success(f"Zalogowany jako: **{wybrany_gracze}**")
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

      # Pobieramy mecze dla najnowszego sezonu
      surowe_mecze = api.pobierz_mecze_ekstraklasy(league_id, current_season)

      if surowe_mecze:
        # Zapisujemy paczkę do bazy Supabase
        sukces = database.synchronizuj_mecze_wsadowo(surowe_mecze)
        if sukces:
          st.sidebar.success(
              f"Zsynchronizowano {len(surowe_mecze)} meczów pomyślnie!"
          )
          st.rerun()
        else:
          st.sidebar.error("Błąd zapisu meczów do bazy.")
      else:
        st.sidebar.warning("API zwróciło pustą listę meczów.")
    else:
      st.sidebar.error("Nie udało się odnaleźć polskiej Ekstraklasy w API.")

# --- GŁÓWNY WIDOK: MECZE I KOLEJKI ---
st.header("🎯 Nadchodząca Kolejka")

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
  # Wyciągamy unikalne kolejki
  kolejki = sorted(list(set(m["kolejka"] for m in wszystkie_mecze)))
  wybrana_kolejka = st.selectbox("Wybierz kolejkę:", kolejki)

  mecze_w_kolejce = [
      m for m in wszystkie_mecze if m["kolejka"] == wybrana_kolejka
  ]

  for mecz in mecze_w_kolejce:
    col1, col2, col3 = st.columns([3, 2, 3])
    with col1:
      st.write(f"**{mecz['gospodarze']}**")
    with col2:
      st.code(
          f"{mecz.get('wynik', '0 - 0')} | {mecz.get('status', 'Not started')}",
          language="text",
      )
    with col3:
      st.write(f"**{mecz['goscie']}**")
    st.markdown("---")
