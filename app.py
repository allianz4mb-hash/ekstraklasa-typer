import streamlit as st
import pandas as pd
import requests
import bcrypt
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="FIFA World Cup 2026", layout="wide")

def get_secret(key):
    try:
        return st.secrets[key]
    except:
        st.error(f"BRAKUJE SEKRETU: {key}.")
        st.stop()

# LOGOWANIE PRZEZ QUERY PARAMS
params = st.query_params
if 'nick' not in st.session_state:
    st.session_state.nick = params.get('nick', '')

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
        with st.spinner("Synchronizacja danych z API..."):
            resp = requests.get(url_api, headers=headers, timeout=10)
            if resp.status_code != 200: return False, f"Błąd API: {resp.status_code}"
            
            data = resp.json()
            matches = data.get('matches', [])
            
            for match in matches:
                try:
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
                    reg_time = score.get('regularTime')
                    if reg_time and reg_time.get('home') is not None:
                        g_g, g_go = reg_time.get('home'), reg_time.get('away')
                    else:
                        full_time = score.get('fullTime') or {}
                        g_g = full_time.get('home') if full_time.get('home') is not None else 0
                        g_go = full_time.get('away') if full_time.get('away') is not None else 0
                    
                    dane_meczu = {
                        "gospodarze": gosp, "goscie": gosc, "logo_gospodarze": logo_g, "logo_goscie": logo_go,
                        "data_meczu": data_str, "status": status, "gole_gospodarze": g_g, "gole_goscie": g_go, "kolejka": 1
                    }
                    
                    if existing: supabase.table("mecze").update(dane_meczu).eq("id", existing[0]['id']).execute()
                    else: supabase.table("mecze").insert(dane_meczu).execute()
                except: continue
            
            sync_time = datetime.now(timezone.utc).isoformat()
            supabase.table("ustawienia").upsert({"id": 1, "ostatnia_sync": sync_time}).execute()
            
            recalculate_all_points()
            return True, "Zaktualizowano!"
    except Exception as e: return False, str(e)

# Funkcja z poprawionym bezpiecznym porównywaniem dat
def check_and_sync():
    try:
        res = supabase.table("ustawienia").select("ostatnia_sync").eq("id", 1).execute()
        if not res.data:
            sync_with_api()
            return
        
        last_sync_str = res.data[0].get('ostatnia_sync')
        if not last_sync_str:
            sync_with_api()
            return

        # Bezpieczne parsowanie daty
        last_sync = datetime.fromisoformat(last_sync_str.replace('Z', '+00:00'))
        if last_sync.tzinfo is None:
            last_sync = last_sync.replace(tzinfo=timezone.utc)
            
        diff = datetime.now(timezone.utc) - last_sync
        
        # Synchronizacja co 30 minut
        if diff > timedelta(minutes=30):
            sync_with_api()
            st.rerun() # Odśwież stronę po udanej synchronizacji
    except Exception as e:
        st.sidebar.error(f"Błąd sync: {e}")

def get_last_sync_time():
    try:
        res = supabase.table("ustawienia").select("ostatnia_sync").eq("id", 1).execute()
        if res.data and res.data[0].get('ostatnia_sync'):
            dt = datetime.fromisoformat(res.data[0]['ostatnia_sync'].replace('Z', '+00:00'))
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(ZoneInfo("Europe/Warsaw")).strftime('%d.%m %H:%M')
    except: pass
    return "Brak danych"

# Uruchomienie automatycznej synchronizacji
check_and_sync()

# --- NAGŁÓWEK ---
def render_header():
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 5px;">
            <img src="https://www.markt-kom.com/wp-content/uploads/2023/07/officialLogo-600x578.png" width="50">
            <h1 style="margin: 0;">FIFA World Cup 2026</h1>
        </div>
    """, unsafe_allow_html=True)
    st.caption(f"🕒 Ostatnia automatyczna synchronizacja: **{get_last_sync_time()}**")

# --- LOGIKA GŁÓWNA ---
if st.session_state.nick == '':
    render_header()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Logowanie")
        log_nick = st.text_input("Nick:")
        log_haslo = st.text_input("Hasło:", type="password")
        if st.button("Zaloguj"):
            res = supabase.table('gracze').select('*').eq('nick', log_nick).execute()
            if res.data and check_password(log_haslo, res.data[0].get('haslo')):
                st.session_state.nick = log_nick
                st.query_params["nick"] = log_nick
                st.rerun()
            else: st.error("Błędny nick lub hasło!")
    with col2:
        st.subheader("Rejestracja")
        rej_nick = st.text_input("W
