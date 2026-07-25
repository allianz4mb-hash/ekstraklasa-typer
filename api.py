import requests
import streamlit as st

BASE_URL = "https://soccer.highlightly.net"


def get_headers():
  api_key = st.secrets.get("HIGHLIGHTLY_API_KEY", "").strip()
  return {"x-rapidapi-key": api_key}


def pobierz_ligę_ekstraklasa():
  # Szybki powrót bez marnowania zapytań API
  return {
      "id": 90990,
      "name": "Ekstraklasa",
      "seasons": [
          {"season": 2026},
          {"season": 2025},
          {"season": 2024},
          {"season": 2023},
          {"season": 2022},
      ],
  }


@st.cache_data(ttl=300, show_spinner=False)
def pobierz_mecze_ekstraklasy(league_id: int = 90990, season: int = 2026):
  api_key = st.secrets.get("HIGHLIGHTLY_API_KEY", "").strip()

  if not api_key:
    st.error("❌ Brak klucza HIGHLIGHTLY_API_KEY w Streamlit Secrets!")
    return []

  url = f"{BASE_URL}/matches"
  wszystkie_mecze = []
  offset = 0
  limit = 100

  while True:
    params = {
        "leagueId": league_id,
        "season": season,
        "limit": limit,
        "offset": offset,
    }
    try:
      response = requests.get(url, headers=get_headers(), params=params)

      if response.status_code == 200:
        pobrana_paczka = response.json().get("data", [])

        if not pobrana_paczka:
          break

        for mecz in pobrana_paczka:
          home = mecz.get("homeTeam", {}).get("name")
          away = mecz.get("awayTeam", {}).get("name")
          if (
              home
              and away
              and "unknown" not in home.lower()
              and "unknown" not in away.lower()
          ):
            wszystkie_mecze.append(mecz)

        if len(pobrana_paczka) < limit:
          break

        offset += limit
      else:
        st.error(
            f"Błąd pobierania meczów ({response.status_code}): {response.text}"
        )
        break
    except Exception as e:
      st.error(f"Błąd połączenia z API: {e}")
      break

  return wszystkie_mecze
