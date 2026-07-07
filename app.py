import streamlit as st
from supabase import create_client, Client

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

if 'nick' not in st.session_state: st.session_state.nick = ''

if st.session_state.nick == '':
    wpisany_nick = st.text_input("Nick:")
    wpisane_haslo = st.text_input("Hasło:", type="password")
    if st.button("Wejdź"):
        res = supabase.table('gracze').select('*').eq('nick', wpisany_nick).execute()
        if not res.data:
            supabase.table('gracze').insert({'nick': wpisany_nick, 'haslo': wpisane_haslo}).execute()
        st.session_state.nick = wpisany_nick
        st.rerun()
else:
    st.title(f"Witaj, {st.session_state.nick}!")
    tab1, tab2, tab3 = st.tabs(["Typer", "Ranking", "Admin"])
    
    with tab1:
        st.subheader("Obstaw mecze")
        mecze = supabase.table("mecze").select("*").execute().data
        for m in mecze:
            col1, col2, col3 = st.columns([3, 1, 3])
            col1.write(f"{m['gospodarze']} vs {m['goscie']}")
            g = col2.number_input("G", 0, 10, key=f"g_{m['id']}")
            go = col2.number_input("Go", 0, 10, key=f"go_{m['id']}")
            if col2.button("Zapisz", key=f"btn_{m['id']}"):
                supabase.table("typy").upsert({
                    "nick": st.session_state.nick,
                    "mecz_id": m['id'],
                    "typ_gospodarze": g,
                    "typ_goscie": go
                }).execute()
                st.success("Zapisano!")

    with tab2:
        st.subheader("Ranking")
        gracze = supabase.table("gracze").select("nick, punkty").order("punkty", desc=True).execute().data
        st.table(gracze)

    with tab3:
        if st.button("Wyloguj"):
            st.session_state.nick = ''
            st.rerun()
