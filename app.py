import streamlit as st
import pandas as pd
import requests
import bcrypt
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client
from streamlit_cookies_controller import CookieController

# 1. TO MUSI BYĆ ABSOLUTNIE PIERWSZA KOMENDA STREAMLIT
st.set_page_config(page_title="Typer Mundialu", layout="wide")

# 2. DOPIERO TERAZ INICJALIZACJA RESZTY
controller = CookieController()

def get_secret(key):
    try:
        return st.secrets[key]
    except:
        st.error(f"BRAKUJE SEKRETU: {key}.")
        st.stop()

# Inicjalizacja sesji z ciasteczka (zapamiętanie logowania)
if 'nick' not in st.session_state:
    saved_nick = controller.get('user_nick')
    st.session_state.nick = saved_nick if saved_nick else ''

url = get_secret("SUPABASE_URL")
key = get_secret("SUPABASE_KEY")
API_KEY = get_secret("FOOTBALL_API_KEY") 
supabase: Client = create_client(url, key)

ADMINI = ["Mateusz Bielecki", "Admin"]

# --- FUNKCJE ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def oblicz_punkty(typ_g, typ_go, real_g, real_go):
    if typ_g == real_g and typ_go == real_go: return 3
    elif (typ_g > typ_go and real_g > real_go) or (typ_g < typ_go and real_g < real_go) or (typ_g == typ_go and real_g == real_go): return 1
    return 0

def recalculate_all_points():
    matches = supabase.table("mecze").select("*").execute().data
    matches_dict = {m['id']: m for m in matches}
    players = supabase.table("gracze").select("nick").execute().data
    
    for p in players:
        nick = p['nick']
        total_points = 0
        typy = supabase.table("typy").select("*").eq("nick", nick).execute().data
        
        for t in typy:
            mecz = matches_dict.get(t['mecz_id'])
            if mecz and mecz['status'] == 'FT':
                pkt = oblicz_punkty(t['typ_gospodarze'], t['typ_goscie'], mecz['gole_gospodarze'], mecz['gole_goscie'])
                supabase.table("typy").update({"punkty_za_mecz": pkt}).eq("id", t['id']).execute()
                total_points += pkt
            else:
                supabase.table("typy").update({"punkty_za_mecz": 0}).eq("id", t['id']).execute()
        
        supabase.table("gracze").update({"punkty": total_points}).eq("nick", nick).execute()

def sync_with_api():
    url_api = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {"X-Auth-Token": API_KEY}
    try:
        resp = requests.get(url_api, headers=headers)
        if resp.status_code != 200: 
            return False, f"Błąd serwera API (Kod {resp.status_code}): {resp.text}"
        
        data = resp.json()
        matches = data.get('matches', [])
        
        for match in matches:
            try:
                # Bezpieczne pobieranie danych
                home_team = match.get('homeTeam') or {}
                away_team = match.get('awayTeam') or {}
                
                gosp = home_team.get('name') or "Nieznany"
                gosc = away_team.get('name') or "Nieznany"
                
                logo_g = home_team.get('crest')
                logo_go = away_team.get('crest')
                data_str = match.get('utcDate')
                
                existing = supabase.table("mecze").select("id").eq("gospodarze", gosp).eq("goscie", gosc).eq("data_meczu", data_str).execute().data
                
                status = 'FT' if match.get('status') == 'FINISHED' else 'NS'
                
                score = match.get('score') or {}
                
                # --- Wymuszanie pobrania tylko z 90 minut ---
                reg_time = score.get('regularTime')
                if reg_time and reg_time.get('home') is not None:
                    g_g = reg_time.get('home')
                    g_go = reg_time.get('away')
                else:
                    full_time = score.get('fullTime') or {}
                    g_g = full_time.get('home') if full_time.get('home') is not None else 0
                    g_go = full_time.get('away') if full_time.get('away') is not None else 0
                
                dane_meczu = {
                    "gospodarze": gosp, "goscie": gosc, "logo_gospodarze": logo_g, "logo_goscie": logo_go,
                    "data_meczu": data_str, "status": status, "gole_gospodarze": g_g, "gole_goscie": g_go, "kolejka": 1
                }
