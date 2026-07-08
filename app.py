import streamlit as st
import pandas as pd
import requests
import bcrypt
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client
from streamlit_cookies_controller import CookieController

# --- KONFIGURACJA ---
controller = CookieController()

def get_secret(key):
    try:
        return st.secrets[key]
    except:
        st.error(f"BRAKUJE SEKRETU: {key}.")
        st.stop()

st.set_page_config(page_title="Typer Mundialu", layout="wide")

# Inicjalizacja sesji z ciasteczka
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

def recalculate_all_points():
    try:
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
                    # Logika: 3pkt dokładny, 1pkt 1X2
                    pkt = 0
                    if t['typ_gospodarze'] == mecz['gole_gospodarze'] and t['typ_goscie'] == mecz['gole_goscie']: pkt = 3
                    elif (t['typ_gospodarze'] > t['typ_goscie'] and mecz['gole_gospodarze'] > mecz['gole_goscie']) or \
                         (t['typ_gospodarze'] < t['typ_goscie'] and mecz['gole_gospodarze'] < mecz['gole_goscie']) or \
                         (t['typ_gospodarze'] == t['typ_goscie'] and mecz['gole_gospodarze'] == mecz['gole_goscie']): pkt = 1
                    
                    supabase.table("typy").update({"punkty_za_mecz": pkt}).eq("id", t['id']).execute()
                    total_points += pkt
            supabase.table("gracze").update({"punkty": total_points}).eq("nick", nick).execute()
    except Exception as e:
        st.error(f"Błąd przeliczania: {e}")

def sync_with_api():
    url_api = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {"X-Auth-Token": API_KEY}
    try:
        resp = requests.get(url_api, headers=headers)
        if resp.status_code != 200: return False
        data = resp.json()
        matches = data.get('matches', [])
        for match in matches:
            gosp, gosc = match['homeTeam']['name'], match['awayTeam']['name']
            data_str = match['utcDate']
            existing = supabase.table("mecze").select("id").eq("gospodarze", gosp).eq("goscie", gosc).eq("data_meczu", data_str).execute().data
            
            # Wymuszenie tylko 90 minut
            full_time = match.get('score', {}).get('fullTime', {})
            dane_meczu = {
                "gospodarze": gosp, "goscie": gosc, 
                "logo_gospodarze": match['homeTeam'].get('crest'),
                "logo_goscie": match['awayTeam'].get('crest'), 
                "data_meczu": data_str,
                "status": 'FT' if match['status'] == 'FINISHED' else 'NS',
                "gole_gospodarze": full_time.get('home', 0) if full_time.get('home') is not None else 0, 
                "gole_goscie": full_time.get('away', 0) if full_time.get('away') is not None else 0, 
                "kolejka": 1
            }
            if existing: supabase.table("mecze").update(dane_meczu).eq("id", existing[0]['id']).execute()
            else: supabase.table("mecze").insert(dane_meczu).execute()
        recalculate_all_points()
        return True
    except Exception as e:
        st.error(f"Błąd API: {e}")
        return False

# --- LOGIKA GŁÓWNA ---

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
                controller.set('user_nick', log_nick, max_age=3600*24*30)
                st.rerun()
            else: st.error("Błędny nick lub hasło!")
    with col2:
        st.subheader("Rejestracja")
        rej_nick = st.text_input("Wymyśl nick:")
        rej_haslo = st.text_input("Wymyśl hasło:", type="password")
        if st.button("Zarejestruj"):
            clean_nick = rej_nick.strip()
            if len(clean_nick) < 3: st.error("Nick min. 3 znaki!")
            elif supabase.table('gracze').select('*').eq('nick', clean_nick).execute().data: st.error("Nick zajęty!")
            else:
                hashed_pw = hash_password(rej_haslo)
                supabase.table('gracze').insert({'nick': clean_nick, 'haslo': hashed_pw, 'punkty': 0}).execute()
                st.session_state.nick = clean_nick
                controller.set('user_nick', clean_nick, max_age=3600*24*30)
                st.rerun()
else:
    with st.sidebar:
        st.write(f"Zalogowany: **{st.session_state.nick}**")
        if st.button("Wyloguj się"):
            controller.remove('user_nick')
            st.session_state.nick = ''
            st.rerun()

    st.title("⚽ Typer Mundialu")
    
    opcje = ["🎯 Typer", "🏆 Ranking"]
    if st.session_state.nick in ADMINI: opcje.append("⚙️ Panel Admina")
    wybor = st.radio("Nawigacja:", opcje, horizontal=True, label_visibility="collapsed", key="nav")
    st.markdown("---")

    if wybor == "🎯 Typer":
        try:
            st.subheader("Obstaw mecze")
            all_mecze = supabase.table("mecze").select("*").order("data_meczu").execute().data
            now = datetime.now(timezone.utc)
            for m in all_mecze:
                if m['status'] != 'FT':
                    mecz_time = datetime.fromisoformat(m['data_meczu'].replace('Z', '+00:00'))
                    is_locked = now >= (mecz_time - timedelta(minutes=5))
                    st.write(f"{m['gospodarze']} vs {m['goscie']}")
                    st.button(f"Typuj {m['id']}", key=f"btn_{m['id']}")
        except Exception as e: st.error(f"Błąd Typera: {e}")

    elif wybor == "🏆 Ranking":
        try:
            st.subheader("🏆 Ranking")
            gracze = supabase.table("gracze").select("nick, punkty").order("punkty", desc=True).execute().data
            st.table(pd.DataFrame(gracze))
        except Exception as e: st.error(f"Błąd Rankingu: {e}")

    elif wybor == "⚙️ Panel Admina":
        try:
            st.subheader("Zarządzanie")
            if st.button("🔄 RĘCZNA SYNCHRONIZACJA"):
                if sync_with_api(): st.success("Gotowe!")
        except Exception as e: st.error(f"Błąd Admina: {e}")
