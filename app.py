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
            
            # Wymuszenie pobrania tylko z 90 minut
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

# --- LOGIKA GŁÓWNA ---
check_and_sync()

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
            if len(clean_nick) < 3: st.error("Nick musi mieć min. 3 znaki!")
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
    wybor = st.radio("Nawigacja:", opcje, horizontal=True, label_visibility="collapsed", key="nawigacja_radio")
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
                    if time_diff <= timedelta(hours=24) and time_diff > timedelta(0):
                        total_seconds = int(time_diff.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        countdown_str = f"⏳ Do zamknięcia typowania pozostało: {hours}h {minutes}m"
                        if hours == 0 and minutes < 30: st.warning(countdown_str)
                        else: st.write(countdown_str)
                else: st.error("🔒 Typowanie zamknięte")
                
                stary_typ = supabase.table("typy").select("*").eq("nick", st.session_state.nick).eq("mecz_id", m['id']).execute().data
                if stary_typ:
                    st.success(f"✅ Twój typ: {stary_typ[0]['typ_gospodarze']} : {stary_typ[0]['typ_goscie']}")
                    btn_text = "Zaktualizuj typ"
                else: btn_text = "Zapisz typ"

                c1, c2 = st.columns(2)
                g = c1.number_input(f"Gole {m['gospodarze']}", 0, 10, value=int(stary_typ[0]['typ_gospodarze']) if stary_typ else 0, key=f"g_{m['id']}", disabled=is_locked)
                go = c2.number_input(f"Gole {m['goscie']}", 0, 10, value=int(stary_typ[0]['typ_goscie']) if stary_typ else 0, key=f"go_{m['id']}", disabled=is_locked)
                
                if not is_locked and st.button(btn_text, key=f"btn_{m['id']}"):
                    dane = {"nick": st.session_state.nick, "mecz_id": m['id'], "typ_gospodarze": g, "typ_goscie": go, "rozliczony": False}
                    if stary_typ: supabase.table("typy").update(dane).eq("id", stary_typ[0]['id']).execute()
                    else: supabase.table("typy").insert(dane).execute()
                    st.rerun()
                st.markdown("---")
                
        if zakonczone:
            with st.expander("🏁 Zobacz zakończone mecze"):
                for m in zakonczone:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
                        <img src="{m['logo_gospodarze']}" width="20">
                        <span>{m['gospodarze']} {m['gole_gospodarze']} : {m['gole_goscie']} {m['goscie']}</span>
                        <img src="{m['logo_goscie']}" width="20">
                    </div>
                    """, unsafe_allow_html=True)

    elif wybor == "🏆 Ranking":
        st.subheader("🏆 Podium Typerów")
        gracze = supabase.table("gracze").select("nick, punkty").order("punkty", desc=True).execute().data
        ranking_data = []
        for g in gracze:
            typy = supabase.table("typy").select("punkty_za_mecz").eq("nick", g['nick']).execute().data
            punkty_1x2 = sum(1 for t in typy if t.get('punkty_za_mecz') == 1)
            punkty_dokladne = sum(1 for t in typy if t.get('punkty_za_mecz') == 3)
            ranking_data.append({"Gracz": g['nick'], "Punkty": g['punkty'], "Trafione 1X2": punkty_1x2, "Trafione dokładne": punkty_dokladne})
            
        if len(ranking_data) >= 3:
            col1, col2, col3 = st.columns(3)
            col1.metric("1. Miejsce 🥇", ranking_data[0]['Gracz'], f"{ranking_data[0]['Punkty']} pkt")
            col2.metric("2. Miejsce 🥈", ranking_data[1]['Gracz'], f"{ranking_data[1]['Punkty']} pkt")
            col3.metric("3. Miejsce 🥉", ranking_data[2]['Gracz'], f"{ranking_data[2]['Punkty']} pkt")
            
        st.markdown("---")
        st.subheader("Pełna tabela")
        st.table(pd.DataFrame(ranking_data))

    elif wybor == "⚙️ Panel Admina":
        st.subheader("Zarządzanie")
        if st.button("🔄 RĘCZNA SYNCHRONIZACJA"):
            with st.spinner("Pobieram dane i przeliczam..."):
                if sync_with_api():
                    st.success("Synchronizacja udana!")
                else:
                    st.error("Błąd połączenia z API.")
        
        if st.button("🛡️ PEŁNA NAPRAWA PUNKTÓW"):
            recalculate_all_points()
            st.success("Punkty zostały na nowo przeliczone dla wszystkich graczy!")
