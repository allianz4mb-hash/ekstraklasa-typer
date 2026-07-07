import streamlit as st
from supabase import create_client, Client
import requests

st.set_page_config(page_title="Typer Ekstraklasy", page_icon="⚽")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
api_key = st.secrets["FOOTBALL_API_KEY"]
supabase: Client = create_client(url, key)

st.title("⚽ Typer Ekstraklasy")

if 'nick' not in st.session_state:
    st.session_state.nick = ''

if st.session_state.nick == '':
    st.subheader("Dołącz do gry")
    wpisany_nick = st.text_input("Podaj swój nick:")
    wpisane_haslo = st.text_input("Podaj hasło (lub wymyśl nowe, jeśli logujesz się pierwszy raz):", type="password")
    
    if st.button("Wejdź"):
        if wpisany_nick and wpisane_haslo:
            response = supabase.table('gracze').select('*').eq('nick', wpisany_nick).execute()
            if not response.data:
                supabase.table('gracze').insert({'nick': wpisany_nick, 'haslo': wpisane_haslo}).execute()
                st.session_state.nick = wpisany_nick
                st.rerun()
            else:
                dane_gracza = response.data[0]
                if dane_gracza.get('haslo') == wpisane_haslo:
                    st.session_state.nick = wpisany_nick
                    st.rerun()
                else:
                    st.error("Błędne hasło dla tego nicku!")
        else:
            st.warning("Wpisz nick i hasło!")
else:
    st.success(f"Witaj, {st.session_state.nick}! Jesteś w grze.")
    
    st.subheader("Zarządzanie meczami")
    if st.button("Pobierz najbliższą kolejkę z API"):
        with st.spinner("Pobieranie meczów..."):
            url_api = "https://v3.football.api-sports.io/fixtures"
            # 106 to ID polskiej Ekstraklasy, pobieramy 9 najbliższych meczów
            querystring = {"league": "106", "season": "2026", "next": "9"} 
            headers = {
                "x-apisports-key": api_key
            }
            
            odpowiedz = requests.get(url_api, headers=headers, params=querystring)
            dane = odpowiedz.json()
            
            if "response" in dane:
                for mecz in dane["response"]:
                    mecz_id = mecz["fixture"]["id"]
                    data_meczu = mecz["fixture"]["date"]
                    status = mecz["fixture"]["status"]["short"]
                    kolejka_str = str(mecz["league"]["round"])
                    gospodarze = mecz["teams"]["home"]["name"]
                    goscie = mecz["teams"]["away"]["name"]
                    
                    try:
                        kolejka_num = int(kolejka_str.split("-")[-1].strip())
                    except:
                        kolejka_num = 1
                    
                    # Sprawdzamy czy mecz już jest, żeby go nie zduplikować
                    istnieje = supabase.table("mecze").select("*").eq("id", mecz_id).execute()
                    
                    if not istnieje.data:
                        supabase.table("mecze").insert({
                            "id": mecz_id,
                            "kolejka": kolejka_num,
                            "data_meczu": data_meczu,
                            "gospodarze": gospodarze,
                            "goscie": goscie,
                            "status": status
                        }).execute()
                        
                st.success("Mecze pobrane i zapisane w bazie!")
            else:
                st.error("Coś poszło nie tak z pobieraniem danych.")
                
    st.subheader("Mecze do obstawienia")
    mecze_z_bazy = supabase.table("mecze").select("*").order("data_meczu").execute()
    
    if mecze_z_bazy.data:
        for m in mecze_z_bazy.data:
            st.write(f"**{m['gospodarze']}** vs **{m['goscie']}**")
    else:
        st.info("Brak meczów w bazie. Kliknij przycisk powyżej, aby je pobrać.")

    if st.button("Wyloguj"):
        st.session_state.nick = ''
        st.rerun()
