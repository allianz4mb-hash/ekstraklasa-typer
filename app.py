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

    # Wyświetlamy to, co zwróciło API na głównym ekranie i zatrzymujemy aplikację, żeby nie zniknęło
    st.write("### 🔍 DEBUG - Dane ligi z API:")
    st.json(liga_info)

    if liga_info:
      league_id = liga_info.get("id")
      seasons = liga_info.get("seasons", [])
      current_season = seasons[-1]["season"] if seasons else 2026
      st.write(
          f"**Znalezione League ID:** {league_id} | **Sezon:** {current_season}"
      )

      surowe_mecze = api.pobierz_mecze_ekstraklasy(league_id, current_season)
      st.write(f"**Liczba pobranych surowych meczów:** {len(surowe_mecze)}")

      if surowe_mecze:
        st.write("Przykładowy pierwszy mecz z API:")
        st.json(surowe_mecze[0])
      else:
        st.warning(
            "API zwróciło pustą listę meczów (0 meczów). Sprawdź limit zapytań"
            " w panelu Highlightly!"
        )
    else:
      st.error(
          "Nie udało się odnaleźć polskiej Ekstraklasy w zapytaniu do API."
      )

    # Zatrzymujemy kod tutaj, żeby nic nie znikało z ekranu
    st.stop()

# --- GŁÓWNY WIDOK: MECZE I KOLEJKI ---
st.header("🎯 Nadchodząca Kolejka")

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
  kolejki = sorted(list(set(m["kolejka"] for m in wszystkie_mecze)))
  wybrana_kolejka = st.selectbox("Wybierz kolejkę:", kolejki)

  mecze_w_kolejce = [
      m for m in wszystkie_mecze if m["kolejka"] == wybrana_kolejka
  ]

  for mecz in mecze_w_kolejce:
    col1, col2, col3 = st.columns([3, 2, 3])
    with col1:
      st.write(f"**{mecz['gospodarz']}**")
    with col2:
      st.code(f"{mecz['wynik']} | {mecz['status']}", language="text")
    with col3:
      st.write(f"**{mecz['gosc']}**")
    st.markdown("---")
