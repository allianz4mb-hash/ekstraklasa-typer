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

url = get_secret("SUPABASE_URL")
key = get_secret("SUPABASE_KEY")
API_KEY = get_secret("FOOTBALL_API_KEY") 
supabase: Client = create_client(url, key)

if 'nick' not in st.session_state: st.session_state.nick = ''
ADMINI = ["Mateusz Bielecki", "Admin"]

# --- FUNKCJE BEZPIECZEŃSTWA ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# --- FUNKCJE LOGIKI ---
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
    url_api = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {"X-Auth-Token": API_KEY}
    
    try:
        resp = requests.get(url_api, headers=headers)
        if resp.status_code != 200:
            st.error(f"Błąd API: {resp.status_code}")
            return
        
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
            g_g = match['score']['fullTime']['home'] if match['score']['fullTime']['home'] is not None else 0
            g_go = match['score']['fullTime']['away'] if match['score']['fullTime']['away'] is not None else 0
            
            dane_meczu = {
                "gospodarze": gosp,
                "goscie": gosc,
                "logo_gospodarze": logo_g,
                "logo_goscie": logo_go,
                "data_meczu": data_str,
                "status": status,
                "gole_gospodarze": g_g,
                "gole_goscie": g_go,
                "kolejka": 1
            }
            
            if existing:
                supabase.table("mecze").update(dane_meczu).eq("id", existing[0]['id']).execute()
            else:
                supabase.table("mecze").insert(dane_meczu).execute()
        st.success(f"Zsynchronizowano {len(matches)} meczów!")
    except Exception as e:
        st.error(f"Błąd: {e}")

# --- INTERFEJS ---
if st.session_state.nick == '':
    st.title("⚽ Typer Mundialu")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Logowanie")
        log_nick = st.text_input("Nick:")
        log_haslo = st.text_input("Hasło:", type="password")
        if st.button("Zaloguj"):
            res = supabase.table('gracze').select('*').eq('nick', log_nick).execute()
            if res.data and check_password(log_haslo, res.data[0].get('haslo')):
                st.session_state.nick = log_nick
                st.rerun()
            else: st.error("Błędny nick lub hasło!")
    with col2:
        st.subheader("Rejestracja")
        rej_nick = st.text_input("Wymyśl nick:")
        rej_haslo = st.text_input("Wymyśl hasło:", type="password")
        if st.button("Zarejestruj"):
            # WALIDACJA: Min 3 znaki
            clean_nick = rej_nick.strip()
            if len(clean_nick) < 3:
                st.error("Nick musi składać się przynajmniej z 3 znaków!")
            elif supabase.table('gracze').select('*').eq('nick', clean_nick).execute().data:
                st.error("Nick zajęty!")
            else:
                hashed_pw = hash_password(rej_haslo)
                supabase.table('gracze').insert({'nick': clean_nick, 'haslo': hashed_pw, 'punkty': 0}).execute()
                st.session_state.nick = clean_nick
                st.rerun()

else:
    with st.sidebar:
        st.write(f"Zalogowany: **{st.session_state.nick}**")
        if st.button("Wyloguj się"):
            st.session_state.nick = ''
            st.rerun()

    st.title("⚽ Typer Mundialu")
    opcje = ["🎯 Typer", "🏆 Ranking"]
    if st.session_state.nick in ADMINI: opcje.append("⚙️ Panel Admina")
    wybor = st.radio("Nawigacja:", opcje, horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    if wybor == "🎯 Typer":
        st.subheader("Obstaw mecze")
        st.info("ℹ️ Typy można zapisywać i edytować do 5 minut przed rozpoczęciem meczu.")
        
        all_mecze = supabase.table("mecze").select("*").order("data_meczu").execute().data
        now = datetime.now(timezone.utc)
        
        aktywne = [m for m in all_mecze if m['status'] != 'FT']
        zakonczone = [m for m in all_mecze if m['status'] == 'FT']

        if aktywne:
            for m in aktywne:
                mecz_time = datetime.fromisoformat(m['data_meczu'].replace('Z', '+00:00'))
                lock_time = mecz_time - timedelta(minutes=5)
                is_locked = now >= lock_time
                pl_time = mecz_time.astimezone(ZoneInfo("Europe/Warsaw"))
                
                # HTML z logo
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
                    <img src="{m['logo_gospodarze']}" width="30">
                    <span style="font-size: 18px;"><strong>{m['gospodarze']} vs {m['goscie']}</strong></span>
                    <img src="{m['logo_goscie']}" width="30">
                </div>
                """, unsafe_allow_html=True)
                
                st.write(f"📅 Start (PL): {pl_time.strftime('%d.%m, %H:%M')}")
                
                time_diff = lock_time - now
                if not is_locked:
                    if time_diff <= timedelta(
