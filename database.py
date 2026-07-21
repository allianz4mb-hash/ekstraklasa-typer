import os
import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

def synchronizuj_mecze_wsadowo(mecze_z_api):
    if not mecze_z_api:
        return False

    try:
        paczka_danych = []
        for mecz in mecze_z_api:
            match_id = mecz.get("id")
            round_name = mecz.get("round", "Kolejka")
            date = mecz.get("date")
            home_team = mecz.get("homeTeam", {}).get("name")
            away_team = mecz.get("awayTeam", {}).get("name")
            
            state_info = mecz.get("state", {})
            status = state_info.get("description", "Not started")
            score = state_info.get("score", {}).get("current") or "- : -"

            paczka_danych.append({
                "id": match_id,
                "kolejka": round_name,
                "data_meczu": date,
                "gospodarze": home_team,
                "goscie": away_team,
                "status": status,
                "gole_gospodarze": 0,
                "gole_goscie": 0,
                "wynik": score
            })

        response = supabase.table("mecze").upsert(paczka_danych, on_conflict="id").execute()
        return True

    except Exception as e:
        st.error(f"Błąd synchronizacji wsadowej z bazą: {e}")
        return False
