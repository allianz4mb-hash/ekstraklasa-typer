import requests
import streamlit as st

BASE_URL = "https://soccer.highlightly.net"
API_KEY = st.secrets.get("HIGHLIGHTLY_API_KEY", "2fa78843-86c1-4651-a285-c05db06da545")


def get_headers():
  return {"x-rapidapi-key": API_KEY}


@st.cache_data(ttl=3600)
def pobierz_ligę_ekstraklasa():
  url = f"{BASE_URL}/leagues"
  params = {"countryName": "Poland", "leagueName": "Ekstraklasa"}
  try:
    response = requests.get(url, headers=get_headers(), params=params)
    if response.status_code == 200:
      data = response.json().get("data", [])
      if data:
        return data[0]
    return None
  except Exception as e:
    st.error(f"Błąd pobierania ligi: {e}")
    return None


@st.cache_data(ttl=1800)
def pobierz_mecze_ekstraklasy(league_id: int, season: int):
  url = f"{BASE_URL}/matches"
  params = {"leagueId": league_id, "season": season, "limit": 100}
  try:
    response = requests.get(url, headers=get_headers(), params=params)
    if response.status_code == 200:
      surowe_mecze = response.json().get("data", [])
      czyste_mecze = []
      for mecz in surowe_mecze:
        home = mecz.get("homeTeam", {}).get("name")
        away = mecz.get("awayTeam", {}).get("name")
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
