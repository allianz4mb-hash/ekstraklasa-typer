import streamlit as st
import pandas as pd
import requests
import bcrypt
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="Typer Mundialu", layout="wide")

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

def get_last_sync_time():
    try:
        res = supabase.table("ustawienia").select("ostatnia_sync").eq("id", 1).execute()
        if res.data and res.data[0].get('ostatnia_sync'):
            dt = datetime.fromisoformat(res.data[0]['ostatnia_sync'].replace('Z', '+00:00'))
            return dt.astimezone(ZoneInfo("Europe/Warsaw")).strftime('%d.%m %H:%M')
    except: pass
    return "Brak danych"

# --- NAGŁÓWEK (NOWA METODA) ---
def render_header():
    c1, c2 = st.columns([0.1, 0.9])
    with c1:
        # Używamy st.image, co jest bezpieczniejsze niż HTML
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/FIFA_World_Cup_2026_Logo.svg/200px-FIFA_World_Cup_2026_Logo.svg.png", width=60)
    with c2:
        st.title("Typer Mundialu")

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
                st.query_params["nick"] = clean_nick
                st.rerun()
else:
    with st.sidebar:
        st.write(f"Zalogowany: **{st.session_state.nick}**")
        st.write(f"🕒 Ostatnia sync: **{get_last_sync_time()}**")
        if st.button("Wyloguj się"):
            st.session_state.nick = ''
            st.query_params.clear()
            st.rerun()

    render_header()
    
    opcje = ["🎯 Typer", "🏆 Ranking"]
    if st.session_state.nick in ADMINI: opcje.append("⚙️ Panel Admina")
    wybor = st.radio("Nawigacja:", opcje, horizontal=True, key="nav")
    st.markdown("---")

    if wybor == "🎯 Typer":
        st.subheader("Obstaw mecze")
        all_mecze = supabase.table("mecze").select("*").order("data_meczu").execute().data
        now = datetime.now(timezone.utc)
        aktywne = [m for m in all_mecze if m['status'] != 'FT' and m['gospodarze'] != 'Nieznany']
        zakonczone = [m for m in all_mecze if m['status'] == 'FT' and m['gospodarze'] != 'Nieznany']

        for m in aktywne:
            mecz_time = datetime.fromisoformat(m['data_meczu'].replace('Z', '+00:00'))
            lock_time = mecz_time - timedelta(minutes=5)
            is_locked = now >= lock_time
            pl_time = mecz_time.astimezone(ZoneInfo("Europe/Warsaw"))
            
            st.markdown(f"""<div style="display: flex; align-items: center; gap: 10px;">
                <img src="{m['logo_gospodarze']}" width="30">
                <strong>{m['gospodarze']} vs {m['goscie']}</strong>
                <img src="{m['logo_goscie']}" width="30"></div>""", unsafe_allow_html=True)
            st.write(f"📅 Start: {pl_time.strftime('%d.%m, %H:%M')}")
            
            stary_typ = supabase.table("typy").select("*").eq("nick", st.session_state.nick).eq("mecz_id", m['id']).execute().data
            if stary_typ: st.success(f"✅ Twój typ: {stary_typ[0]['typ_gospodarze']} : {stary_typ[0]['typ_goscie']}")
            
            if not is_locked:
                time_diff = lock_time - now
                if time_diff < timedelta(hours=24):
                    st.warning(f"⏳ Do zamknięcia: {int(time_diff.total_seconds()//3600)}h {int((time_diff.total_seconds()%3600)//60)}m")
            else: st.error("🔒 Zamknięte")
            
            c1, c2 = st.columns(2)
            g = c1.number_input(f"Gole {m['gospodarze']}", 0, 10, value=int(stary_typ[0]['typ_gospodarze']) if stary_typ else 0, key=f"g_{m['id']}", disabled=is_locked)
            go = c2.number_input(f"Gole {m['goscie']}", 0, 10, value=int(stary_typ[0]['typ_goscie']) if stary_typ else 0, key=f"go_{m['id']}", disabled=is_locked)
            
            if not is_locked and st.button("Zapisz", key=f"btn_{m['id']}"):
                dane = {"nick": st.session_state.nick, "mecz_id": m['id'], "typ_gospodarze": g, "typ_goscie": go, "rozliczony": False}
                if stary_typ: supabase.table("typy").update(dane).eq("id", stary_typ[0]['id']).execute()
                else: supabase.table("typy").insert(dane).execute()
                st.rerun()
            st.markdown("---")
        
        if zakonczone:
            with st.expander("🏁 Zakończone mecze"):
                for m in zakonczone:
                    st.markdown(f"""<div style="display: flex; align-items: center; gap: 10px;">
                        <img src="{m['logo_gospodarze']}" width="20">
                        <strong>{m['gospodarze']} {m['gole_gospodarze']} : {m['gole_goscie']} {m['goscie']}</strong>
                        <img src="{m['logo_goscie']}" width="20"></div>""", unsafe_allow_html=True)

    elif wybor == "🏆 Ranking":
        st.subheader("🏆 Podium Typerów")
        gracze = supabase.table("gracze").select("nick, punkty").order("punkty", desc=True).execute().data
        ranking_data = []
        for g in gracze:
            typy = supabase.table("typy").select("punkty_za_mecz").eq("nick", g['nick']).execute().data
            p1x2 = sum(1 for t in typy if t.get('punkty_za_mecz') == 1)
            p3 = sum(1 for t in typy if t.get('punkty_za_mecz') == 3)
            ranking_data.append({"Gracz": g['nick'], "Punkty": g['punkty'], "1X2": p1x2, "Dokładne": p3})
        
        if len(ranking_data) >= 3:
            c1, c2, c3 = st.columns(3)
            c1.metric("1. Miejsce 🥇", ranking_data[0]['Gracz'], f"{ranking_data[0]['Punkty']} pkt")
            c2.metric("2. Miejsce 🥈", ranking_data[1]['Gracz'], f"{ranking_data[1]['Punkty']} pkt")
            c3.metric("3. Miejsce 🥉", ranking_data[2]['Gracz'], f"{ranking_data[2]['Punkty']} pkt")
        st.table(pd.DataFrame(ranking_data))

    elif wybor == "⚙️ Panel Admina":
        if st.button("🔄 RĘCZNA SYNC"):
            s, m = sync_with_api()
            if s: st.success(m)
            else: st.error(m)
        if st.button("🛡️ PEŁNA NAPRAWA PUNKTÓW"):
            recalculate_all_points()
            st.success("Przeliczono!")
