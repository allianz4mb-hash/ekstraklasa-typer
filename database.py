import os
import streamlit as st
from supabase import create_client, Client

# Połączenie z bazą Supabase (pobierane ze Streamlit secrets)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

def synchronizuj_mecze_wsadowo(mecze_z_api):
    """
    Optymalizacja wsadowa: zamiast dziesiątek pojedynczych zapytań, 
    przetwarza i aktualizuje mecze w bazie błyskawicznie.
    """
    if not mecze_z_api:
        return False

    try:
        # Przygotowujemy dane do wgrania/aktualizacji paczką
        paczka_danych = []
        for mecz in mecze_z_api:
            match_id = mecz.get("id")
            round_name = mecz.get("round", "Kolejka")
            date = mecz.get("date")
            home_team = mecz.get("homeTeam", {}).get("name")
            away_team = mecz.get("awayTeam", {}).get("name")
            
            # Stan meczu i wyniki
            state_info = mecz.get("state", {})
            status = state_info.get("description", "Not started")
            score = state_info.get("score", {}).get("current", "0 - 0")

            paczka_danych.append({
                "match_id": match_id,
                "kolejka": round_name,
                "data_mecz": date,
                "gospodarz": home_team,
                "gosc": away_team,
                "status": status,
                "wynik": score
            })

        # Wysłanie całej paczki do Supabase naraz (upsert po match_id)
        # Dzięki temu cała operacja trwa ułamek sekundy zamiast 2 minut!
        response = supabase.table("mecze").upsert(paczka_danych, on_conflict="match_id").execute()
        return True

    except Exception as e:
        st.error(f"Błąd synchronizacji wsadowej z bazą: {e}")
        return False
