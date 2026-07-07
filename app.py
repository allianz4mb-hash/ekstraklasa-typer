import streamlit as st
from supabase import create_client, Client
from bs4 import BeautifulSoup
import requests

st.set_page_config(page_title="Typer Mundialu", page_icon="⚽")

# Konfiguracja Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("⚽ Typer Mundialu")

# Logowanie
if 'nick' not in st.session_state:
    st.session_state.nick = ''

if st.session_state.nick == '':
    wpisany_nick = st.text_input("Podaj swój nick:")
    wpisane_haslo = st.text_input("Hasło:", type="password")
    if st.button("Wejdź"):
        # Logika sprawdzania użytkownika...
        response = supabase.table('gracze').select('*').eq('nick', wpisany_nick).execute()
        if not response.data:
            supabase.table('gracze').insert({'nick': wpisany_nick, 'haslo': wpisane_haslo}).execute()
        st.session_state.nick = wpisany_nick
        st.rerun()
else:
    st.success(f"Witaj, {st.session_state.nick}!")
    
    # Zakładki
    tab1, tab2, tab3 = st.tabs(["Typer", "Ranking", "Admin"])
    
    with tab1:
        st.subheader("Obstaw mecze")
        # Tu będziemy wyświetlać mecze z bazy
        
    with tab2:
        st.subheader("Tabela wyników")
        # Tu będzie ranking
        
    with tab3:
        if st.button("Odśwież dane z internetu"):
            st.info("Tu będzie działał nasz scraper!")
    
    if st.button("Wyloguj"):
        st.session_state.nick = ''
        st.rerun()
