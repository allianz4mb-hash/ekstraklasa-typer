import streamlit as st
import api
import database

st.set_page_config(page_title="Ekstraklasa Typer", page_icon="⚽", layout="wide")

# Inicjalizacja klienta bazy danych
db = database.init_supabase()

st.title("⚽ Ekstraklasa Typer 2026/2027")

# --- 1. PANEL BOCZNY: LOGOWANIE / WYBÓR UŻYTKOWNIKA ---
st.sidebar.header("👤 Panel Gracza")

# Pobieramy listę graczy z bazy
try:
  res_gracze = db.table("gracze").select("nick").execute()
  dostepni_gracze = [g["nick"] for g in res_gracze.data]
except Exception:
  dostepni_gracze = []

wybrany_gracze = st.sidebar.selectbox("Wybierz swój profil:", dostepni_gracze)

if wybrany_gracze:
  st.sidebar.success(f"Zalogowany jako: **{wybrany_gracze}**")
else:
  st.sidebar.warning(
      "Brak graczy w bazie. Dodaj kogoś w tabeli 'gracze' w Supabase!"
  )

st.sidebar.markdown("---")

# --- 2. SYNCHRONIZACIJA DANYCH Z API ---
st.sidebar.subheader("⚙️ Zarządzanie ligą")
if st.sidebar.button("🔄 Synchronizuj terminarz z API"):
  with st.spinner("Pobieranie terminarza Ekstraklasy..."):
    # Krok A: Pobieramy dane ligi (ID i aktualny sezon)
    liga_info = api.pobierz_ligę_ekstraklasa()

    if liga_info:
      league_id = liga_info.get("id")
      # Bierzemy najnowszy sezon z listy
      seasons = liga_info.get("seasons", [])
      current_season = seasons[-1]["season"] if seasons else 2026

      # Krok B: Pobieramy mecze dla tej ligi i sezonu
      surowe_mecze = api.pobierz_mecze_ekstraklasy(league_id, current_season)

      if surowe_mecze:
        # Krok C: Zapisujemy wsadowo do bazy (błyskawicznie!)
        sukces = database.synchronizuj_mecze_wsadowo(surowe_mecze)
        if sukces:
          st.sidebar.success(
              f"Zsynchronizowano {len(surowe_mecze)} meczów pomyślnie!"
          )
          st.rerun()
        else:
          st.sidebar.error("Błąd zapisu meczów do bazy.")
      else:
        st.sidebar.warning(
            "Nie znaleziono meczów w API dla tego sezonu lub limit"
            " wyczerpany."
        )
    else:
      st.sidebar.error(
          "Nie udało się odnaleźć polskiej Ekstraklasy w zapytaniu do API."
      )

# --- 3. GŁÓWNY WIDOK: MECZE I KOLEJKI ---
st.header("🎯 Nadchodząca Kolejka")

# Pobieramy mecze zapisane w naszej bazie
try:
  res_mecze = (
      db.table("mecze").select("*").order("data_mecz", desc=False).execute()
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

  # Wybór aktywnej kolejki (domyślnie pierwsza z brzegu lub z nierozegranymi meczami)
  wybrana_kolejka = st.selectbox("Wybierz kolejkę:", kolejki)

  # Filtrujemy mecze dla wybranej kolejki
  mecze_w_kolejce = [
      m for m in wszystkie_mecze if m["kolejka"] == wybrana_kolejka
  ]

  for mecz in mecze_w_kolejce:
    col1, col2, col3 = st.columns([3, 2, 3])
    with col1:
      st.write(f"**{mecz['gospodarz']}**")
    with col2:
      st.code(
          f"{mecz['wynik']} | {mecz['status']}", language="text"
      )  # tymczasowe wyświetlenie statusu
    with col3:
      st.write(f"**{mecz['gosc']}**")
    st.markdown("---")
