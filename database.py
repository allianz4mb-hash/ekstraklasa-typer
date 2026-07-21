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
            
            home_info = mecz.get("homeTeam", {})
            away_info = mecz.get("awayTeam", {})
            
            home_team = home_info.get("name")
            away_team = away_info.get("name")
            home_logo = home_info.get("logo") or home_info.get("logoUrl") or ""
            away_logo = away_info.get("logo") or away_info.get("logoUrl") or ""
            
            state_info = mecz.get("state", {})
            status = state_info.get("description", "Not started")
            score = state_info.get("score", {}).get("current") or "- : -"

            paczka_danych.append({
                "id": match_id,
                "kolejka": round_name,
                "data_meczu": date,
                "gospodarze": home_team,
                "goscie": away_team,
                "logo_gospodarze": home_logo,
                "logo_goscie": away_logo,
                "status": status,
                "gole_gospodarze": 0,
                "gole_goscie": 0,
                "wynik": score
            })

        supabase.table("mecze").upsert(paczka_danych, on_conflict="id").execute()
        return True

    except Exception as e:
        st.error(f"Błąd synchronizacji wsadowej z bazą: {e}")
        return False

def pobierz_typy_gracza(gracz_nick: str):
    try:
        res = supabase.table("typy").select("*").eq("gracz_nick", gracz_nick).execute()
        return {item["mecz_id"]: (item["typ_gospodarze"], item["typ_goscie"]) for item in res.data}
    except Exception as e:
        st.error(f"Błąd pobierania typów: {e}")
        return {}

def zapisz_typy_gracza(paczka_typow):
    try:
        supabase.table("typy").upsert(paczka_typow, on_conflict="gracz_nick,mecz_id").execute()
        return True
    except Exception as e:
        st.error(f"Błąd zapisu typów: {e}")
        return False
