from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import api
import database
import streamlit as st


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

      # Jeśli od ostatniej synchro minęło 30 minut lub więcej
      if teraz - ostatnia >= timedelta(minutes=30):
        wykonaj_synchro = True
    except Exception:
      wykonaj_synchro = True

  if wykonaj_synchro:
    surowe = api.pobierz_mecze_ekstraklasy()
    if surowe:
      database.synchronizuj_mecze_wsadowo(surowe)


# Wywołujemy automatyczną kontrolę przy każdym wejściu gracza lub bota
auto_synchronizacja_check()

# --- DALSZA CZĘŚĆ LOGIKI PANELU BOCZNEGO ---
# Przyjmijmy, że wybrany_gracz to zmienna z selectboxa/zalogowanego użytkownika
wybrany_gracz = st.sidebar.selectbox(
    "Wybierz gracza:", database.pobierz_liste_graczy()
)

# --- PANEL ZARZĄDZANIA WIDOCZNY TYLKO DLA NICKU "Mateusz" ---
if wybrany_gracz == "Mateusz":
  st.sidebar.markdown("---")
  st.sidebar.subheader("⚙️ Zarządzanie ligą (Admin)")

  if st.sidebar.button("🔄 Wymuś synchronizację z API"):
    surowe = api.pobierz_mecze_ekstraklasy()
    if database.synchronizuj_mecze_wsadowo(surowe):
      st.sidebar.success("Zsynchronizowano pomyślnie!")
      st.rerun()

st.sidebar.caption(
    f"⏱️ Ostatnia synchro: {database.pobierz_czas_synchro()}"
)
