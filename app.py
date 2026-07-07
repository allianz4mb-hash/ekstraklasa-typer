import streamlit as st
from supabase import create_client, Client
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="Typer Mundialu", layout="wide")

# Konfiguracja
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
API_KEY = st.secrets["FOOTBALL_API_KEY"] 
supabase: Client = create_client(url, key)

if 'nick' not in st.session_state: st.session_state.nick = ''
ADMINI = ["Mateusz Bielecki", "Admin"]

# --- FUNKCJE ---
def oblicz_punkty(typ_g, typ_go, real_g, real_go):
    if typ_g == real_g and typ_go == real_go: return 3
    elif (typ_g > typ_go and real_g > real_go) or (typ_g < typ_go and real_g < real_go) or (typ_g == typ_go and real_g == real_go): return 1
    return 0

def recalculate_all_points():
    matches = supabase.table("mecze").select("id").execute().data
    valid_match_ids = [m['id'] for m in matches]
    players = supabase.table("gracze").select("nick").execute().data
    for p in players:
        typy = supabase.table("typy").select("punkty_za_mecz, mecz_id").eq("nick", p['nick']).execute().data
        total = sum(t['punkty_za_mecz'] for t in typy if t['mecz_id'] in valid_match_ids and t['punkty_za_mecz'] is not None)
        supabase.table("gracze").update({"punkty": total}).eq("nick", p['nick']).execute()

def sync_with_api():
    # Używamy poprawnego endpointu dla Mistrzostw Świata (WC)
    url_api = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {"X-Auth-Token": API_KEY}
    
    try:
        resp = requests.get(url_api, headers=headers)
        if resp.status_code != 200:
            st.error(f"Błąd API (Kod {resp.status_code}): {resp.text}")
            return
        
        data = resp.json()
        matches = data.get('matches', [])
        
        if not matches:
            st.warning("API zwróciło odpowiedź, ale nie znaleziono żadnych meczów.")
            return

        for match in matches:
            gosp = match['homeTeam']['name']
            gosc = match['awayTeam']['name']
            data_str = match['utcDate']
            status = 'FT' if match['status'] == 'FINISHED' else 'NS'
            # Obsługa meczów, które jeszcze się nie odbyły (brak wyników)
            g_g = match['score']['fullTime']['home'] if match['score']['fullTime']['home'] is not None else 0
            g_go = match['score']['fullTime']['away'] if match['score']['fullTime']['away'] is not None else 0
            
            supabase.table("mecze").upsert({
                "gospodarze": gosp,
                "goscie": gosc,
                "data_meczu": data_str,
                "status": status,
                "gole_gospodarze": g_g,
                "gole_goscie": g_go,
                "kolejka": 1
            }).execute()
        st.success(f"Zsynchronizowano pomyślnie {len(matches)} meczów!")
    except Exception as e:
        st.error(f"Wystąpił błąd: {e}")

# --- LOGOWANIE I RESZTA KODU (BEZ ZMIAN) ---
# [Tutaj wklej resztę swojego działającego kodu z poprzedniej wersji]
