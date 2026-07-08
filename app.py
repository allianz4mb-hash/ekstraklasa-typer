import streamlit as st
import pandas as pd
import requests
import bcrypt
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client

# --- KONFIGURACJA ---
def get_secret(key):
    try:
        return st.secrets[key]
    except:
        st.error(f"BRAKUJE SEKRETU: {key}. Sprawdź ustawienia w Streamlit.")
        st.stop()

st.set_page_config(page_title="Typer Mundialu", layout="wide")

# --- TRYB SERWISOWY ---
st.error("⚠️ Uwaga! Strona w trakcie prac technicznych.")
st.write("Wystąpił problem z aktualizacją wyników meczów. Zajmę się tym w wolnej chwili. Przepraszam za utrudnienia!")
st.stop()

# Poniżej znajduje się reszta kodu, która nie uruchomi się dopóki nie usuniesz powyższego st.stop()
url = get_secret("SUPABASE_URL")
key = get_secret("SUPABASE_KEY")
API_KEY = get_secret("FOOTBALL_API_KEY") 
supabase: Client = create_client(url, key)

if 'nick' not in st.session_state: st.session_state.nick = ''
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
        if resp.status_code != 200: return False
        data = resp.json()
        matches = data.get('matches', [])
        
        for match in matches:
            gosp = match['homeTeam']['name']
            gosc = match['awayTeam']['name']
            logo_g = match['homeTeam'].get('crest')
            logo_go = match['awayTeam'].get('crest')
            data_str = match['utcDate']
            existing = supabase.table("mecze").select("id").eq("gospodarze", gosp).eq("goscie", gosc).eq("data_meczu", data_str).execute().data
            
            status = 'FT' if match['status'] == 'FINISHED' else 'NS'
            
            score = match.get('score', {})
            full_time = score.get('fullTime', {})
            g_g = full_time.get('home') if full_time.get('home') is not None else 0
            g_go = full_time.get('away') if full_time.get('away') is not None else 0
            
            dane_meczu = {
                "gospodarze": gosp, "goscie": gosc, "logo_gospodarze": logo_g, "logo_goscie": logo_go,
                "data_meczu": data_str, "status": status, "gole_gospodarze": g_g, "gole_goscie": g_go, "kolejka": 1
            }
            if existing: supabase.table("mecze").update(dane_meczu).eq("id", existing[0]['id']).execute()
            else: supabase.table("mecze").insert(dane_meczu).execute()
        
        recalculate_all_points()
        return True
    except: return False

def check_and_sync():
    try:
        res = supabase.table("ustawienia").select("ostatnia_sync").eq("id", 1).execute()
        if not res.data: return
        last_sync = datetime.fromisoformat(res.data[0]['ostatnia_sync'].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) - last_sync > timedelta(minutes=10):
            if sync_with_api():
                supabase.table("ustawienia").update({"ostatnia_sync": datetime.now(timezone.utc).isoformat()}).eq("id", 1).execute()
    except: pass
