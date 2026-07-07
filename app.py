import streamlit as st
from supabase import create_client, Client

# Konfiguracja strony
st.set_page_config(page_title="Typer Ekstraklasy", page_icon="⚽")

# Pobieranie ukrytych kluczy z ustawień Streamlit
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("⚽ Typer Ekstraklasy")

# System logowania na nick i hasło
if 'nick' not in st.session_state:
    st.session_state.nick = ''

if st.session_state.nick == '':
    st.subheader("Dołącz do gry")
    wpisany_nick = st.text_input("Podaj swój nick:")
    wpisane_haslo = st.text_input("Podaj hasło (lub wymyśl nowe, jeśli logujesz się pierwszy raz):", type="password")
    
    if st.button("Wejdź"):
        if wpisany_nick and wpisane_haslo:
            # Sprawdzenie czy gracz jest w bazie
            response = supabase.table('gracze').select('*').eq('nick', wpisany_nick).execute()
            
            # Jeśli go nie ma, tworzymy nowy profil z hasłem
            if not response.data:
                supabase.table('gracze').insert({'nick': wpisany_nick, 'haslo': wpisane_haslo}).execute()
                st.session_state.nick = wpisany_nick
                st.rerun()
            else:
                # Istniejący gracz - sprawdzamy poprawność hasła
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
    
    if st.button("Wyloguj"):
        st.session_state.nick = ''
        st.rerun()
