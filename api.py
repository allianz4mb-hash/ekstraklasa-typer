import os
import requests
import streamlit as st

# Bazowy adres URL dla Highlightly API
BASE_URL = "https://soccer.highlightly.net"

# Klucz API (najlepiej pobierać go ze Streamlit secrets, ale na start możesz wpisać go w cudzysłowie)
API_KEY = st.secrets.get("HIGHLIGHTLY_API_KEY", "2fa78843-86c1-4651-a285-c05db06da545")


def get_headers():
  return {"x-rapidapi-key": API_KEY}


@st.cache_data(ttl=3600)  # Cache na 1 godzinę, żeby oszczędzać darmowy limit 100 zapytań/dzień
def pobierz_ligę_ekstraklasa():
  """Szuka ID polskiej Ekstraklasy w API"""
  url = f"{BASE_URL}/leagues"
  params = {"countryName": "Poland", "leagueName": "Ekstraklasa"}

  try:
    response = requests.get(url, headers=get_headers(), params=params)
    if response.status_code == 200:
      data = response.json().get("data", [])
      if data:
        return data[0]  # Zwraca obiekt ligi z jej ID i sezonami
    return None
  except Exception as e:
    st.error(f"Błąd pobierania ligi: {e}")
    return None


@st.cache_data(ttl=1800)  # Cache na 30 minut
def pobierz_mecze_ekstraklasy(league_id: int, season: int):
  """Pobiera mecze dla danej ligi i sezonu, zabezpieczając się przed 'Nieznanymi' drużynami"""
  url = f"{BASE_URL}/matches"
  params = {"leagueId": league_id, "season": season, "limit": 100}

  try:
    response = requests.get(url, headers=get_headers(), params=params)
    if response.status_code == 200:
      surowe_mecze = response.json().get("data", [])

      # Zabezpieczenie (Punkt 3 z naszej listy): Filtr odrzucający mecze z "Nieznanymi" drużynami
      czyste_mecze = []
      for mecz in surowe_mecze:
        home = mecz.get("homeTeam", {}).get("name")
        away = mecz.get("awayTeam", {}).get("name")

        # Jeśli nazwa drużyny istnieje, nie jest pusta i nie zawiera słowa "Unknown" / "Nieznany"
        if (
            home
            and away
            and "unknown" not in home.lower()
            and "unknown" not in away.lower()
        ):
          czyste_mecze.append(mecz)

      return czyste_mecze
    else:
      st.error(f"Błąd pobierania meczów: {response.status_code}")
      return []
  except Exception as e:
    st.error(f"Błąd połączenia: {e}")
    return []
