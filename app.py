import streamlit as st
from supabase import create_client, Client
import pandas as pd

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

if 'nick' not in st.session_state: 
    st.session_state.nick = ''

# Tutaj wpisałem Twoją pełną nazwę jako Admina
ADMINI = ["Mateusz Bielecki", "Admin"]

def oblicz_punkty(typ_g, typ_go, real_g, real_go):
    if typ_g == real_g and typ_go == real_go:
        return 3
    elif (typ_g > typ_go and real_g > real_go) or (typ_g < typ_go and real_g < real_go) or (typ_g == typ_go and real_g == real_go):
        return 1
    return 0

if st.session_state.nick == '':
    st.title("⚽ Typer Mundialu")
    tab_log, tab_rej = st.tabs(["🔐 Logowanie", "📝 Rejestracja"])
    
    with tab_log:
        st.subheader("Masz już konto?")
        log_nick = st.text_input("Nick:", key="log_nick")
        log_haslo = st.text_input("Hasło:", type="password", key="log_haslo")
        if st.button("Zaloguj", key="btn_log"):
            res = supabase.table('gracze').select('*').eq('nick', log_nick).execute()
            if res.data and res.data[0].get('haslo') == log_haslo:
                st.session_state.nick = log_nick
                st.rerun()
            else:
                st.error("Błędny nick lub hasło!")

    with tab_rej:
        st.subheader("Załóż nowe konto")
        rej_nick = st.text_input("Wymyśl nick:", key="rej_nick")
        rej_haslo = st.text_input("Wymyśl hasło:", type="password", key="rej_haslo")
        if st.button("Zarejestruj", key="btn_rej"):
            if not supabase.table('gracze').select('*').eq('nick', rej_nick).execute().data:
                supabase.table('gracze').insert({'nick': rej_nick, 'haslo': rej_haslo, 'punkty': 0}).execute()
                st.session_state.nick = rej_nick
                st.rerun()
            else:
                st.error("Ten nick jest już zajęty!")
else:
    with st.sidebar:
        st.write(f"Zalogowany jako: **{st.session_state.nick}**")
        if st.button("Wyloguj się"):
            st.session_state.nick = ''
            st.rerun()

    st.title(f"⚽ Typer Mundialu")
    
    jest_adminem = st.session_state.nick in ADMINI
    nazwy_zakladek = ["🎯 Typer", "🏆 Ranking"]
    if jest_adminem: nazwy_zakladek.append("⚙️ Panel Admina")
        
    tabs = st.tabs(nazwy_zakladek)
    
    with tabs[0]:
        st.subheader("Obstaw mecze")
        mecze = supabase.table("mecze").select("*").order("id").execute().data
        for m in mecze:
            st.write(f"---")
            stary_typ = supabase.table("typy").select("*").eq("nick", st.session_state.nick).eq("mecz_id", m['id']).execute().data
            if m['status'] == 'FT':
                st.write(f"🏁 **{m['gospodarze']} {m['gole_gospodarze']} : {m['gole_goscie']} {m['goscie']}**")
                if stary_typ: st.info(f"Twój typ: {stary_typ[0]['typ_gospodarze']}:{stary_typ[0]['typ_goscie']} | Punkty: {stary_typ[0]['punkty_za_mecz']}")
            else:
                st.write(f"⏳ **{m['gospodarze']}** vs **{m['goscie']}**")
                def_g = stary_typ[0]['typ_gospodarze'] if stary_typ else 0
                def_go = stary_typ[0]['typ_goscie'] if stary_typ else 0
                col1, col2 = st.columns(2)
                g = col1.number_input(f"Gole: {m['gospodarze']}", 0, 10, value=int(def_g), key=f"g_{m['id']}")
                go = col2.number_input(f"Gole: {m['goscie']}", 0, 10, value=int(def_go), key=f"go_{m['id']}")
                if st.button("Zapisz typ", key=f"btn_{m['id']}"):
                    dane = {"nick": st.session_state.nick, "mecz_id": m['id'], "typ_gospodarze": g, "typ_goscie": go, "rozliczony": False}
                    if stary_typ: supabase.table("typy").update(dane).eq("id", stary_typ[0]['id']).execute()
                    else: supabase.table("typy").insert(dane).execute()
                    st.rerun()

    with tabs[1]:
        st.subheader("Tabela Typerów")
        gracze = supabase.table("gracze").select("nick, punkty").order("punkty", desc=True).execute().data
        if gracze:
            df = pd.DataFrame(gracze)
            df.columns = ["Gracz", "Suma Punktów"]
            st.table(df)

    if jest_adminem:
        with tabs[2]:
            st.subheader("Zarządzanie Grą")
            # Używamy formularza (st.form), aby uniknąć przeładowywania strony przy każdej zmianie
            with st.form("admin_form"):
                mecze_do_rozliczenia = supabase.table("mecze").select("*").neq("status", "FT").execute().data
                if mecze_do_rozliczenia:
                    opcje = {f"{m['gospodarze']} vs {m['goscie']} (ID: {m['id']})": m for m in mecze_do_rozliczenia}
                    wybrany_mecz_str = st.selectbox("Wybierz mecz:", list(opcje.keys()))
                    mecz_obj = opcje[wybrany_mecz_str]
                    
                    c1, c2 = st.columns(2)
                    res_g = c1.number_input(f"Wynik {mecz_obj['gospodarze']}", 0, 10)
                    res_go = c2.number_input(f"Wynik {mecz_obj['goscie']}", 0, 10)
                    
                    submitted = st.form_submit_button("Zakończ mecz i podlicz punkty")
                    if submitted:
                        supabase.table("mecze").update({"gole_gospodarze": res_g, "gole_goscie": res_go, "status": "FT"}).eq("id", mecz_obj['id']).execute()
                        for t in supabase.table("typy").select("*").eq("mecz_id", mecz_obj['id']).execute().data:
                            pts = oblicz_punkty(t['typ_gospodarze'], t['typ_goscie'], res_g, res_go)
                            supabase.table("typy").update({"punkty_za_mecz": pts, "rozliczony": True}).eq("id", t['id']).execute()
                        for gracz in supabase.table("gracze").select("nick").execute().data:
                            suma = sum([item['punkty_za_mecz'] for item in supabase.table("typy").select("punkty_za_mecz").eq("nick", gracz['nick']).execute().data if item['punkty_za_mecz']])
                            supabase.table("gracze").update({"punkty": suma}).eq("nick", gracz['nick']).execute()
                        st.success("Rozliczono!")
                        st.rerun()
