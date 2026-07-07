import streamlit as st
from supabase import create_client, Client
import pandas as pd

# Ustawienia strony
st.set_page_config(page_title="Typer Mundialu", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

if 'nick' not in st.session_state: st.session_state.nick = ''
ADMINI = ["Mateusz Bielecki", "Admin"]

# --- FUNKCJE POMOCNICZE ---
def oblicz_punkty(typ_g, typ_go, real_g, real_go):
    if typ_g == real_g and typ_go == real_go: return 3
    elif (typ_g > typ_go and real_g > real_go) or (typ_g < typ_go and real_g < real_go) or (typ_g == typ_go and real_g == real_go): return 1
    return 0

# --- FUNKCJE ZAKŁADEK ---
def render_typer():
    st.subheader("Obstaw mecze")
    mecze = supabase.table("mecze").select("*").order("id").execute().data
    for m in mecze:
        st.write("---")
        stary_typ = supabase.table("typy").select("*").eq("nick", st.session_state.nick).eq("mecz_id", m['id']).execute().data
        if m['status'] == 'FT':
            st.write(f"🏁 **{m['gospodarze']} {m['gole_gospodarze']} : {m['gole_goscie']} {m['goscie']}**")
        else:
            st.write(f"⏳ **{m['gospodarze']}** vs **{m['goscie']}**")
            col1, col2 = st.columns(2)
            def_g = stary_typ[0]['typ_gospodarze'] if stary_typ else 0
            def_go = stary_typ[0]['typ_goscie'] if stary_typ else 0
            g = col1.number_input(f"Gole {m['gospodarze']}", 0, 10, value=int(def_g), key=f"g_{m['id']}")
            go = col2.number_input(f"Gole {m['goscie']}", 0, 10, value=int(def_go), key=f"go_{m['id']}")
            if st.button("Zapisz typ", key=f"btn_{m['id']}"):
                dane = {"nick": st.session_state.nick, "mecz_id": m['id'], "typ_gospodarze": g, "typ_goscie": go, "rozliczony": False}
                if stary_typ: supabase.table("typy").update(dane).eq("id", stary_typ[0]['id']).execute()
                else: supabase.table("typy").insert(dane).execute()
                st.rerun()

def render_ranking():
    st.subheader("Tabela Typerów")
    gracze = supabase.table("gracze").select("nick, punkty").order("punkty", desc=True).execute().data
    if gracze:
        df = pd.DataFrame(gracze)
        df.columns = ["Gracz", "Suma Punktów"]
        st.table(df)

def render_admin():
    st.subheader("Zarządzanie Grą")
    # Formularz dodawania meczu
    with st.expander("➕ Dodaj nowy mecz"):
        col_gosp, col_gosc = st.columns(2)
        new_gosp = col_gosp.text_input("Gospodarze", key="admin_add_gosp")
        new_gosc = col_gosc.text_input("Goście", key="admin_add_gosc")
        if st.button("Dodaj mecz"):
            supabase.table("mecze").insert({"gospodarze": new_gosp, "goscie": new_gosc, "status": "NS"}).execute()
            st.rerun()

    st.markdown("---")
    st.markdown("### 🏁 Rozlicz mecz")
    mecze_do_rozliczenia = supabase.table("mecze").select("*").neq("status", "FT").execute().data
    if mecze_do_rozliczenia:
        opcje = {f"{m['gospodarze']} vs {m['goscie']} (ID: {m['id']})": m for m in mecze_do_rozliczenia}
        wybrany_str = st.selectbox("Wybierz mecz:", list(opcje.keys()), key="admin_select")
        mecz = opcje[wybrany_str]
        
        c1, c2 = st.columns(2)
        r_g = c1.number_input(f"Wynik {mecz['gospodarze']}", 0, 10, key="res_g_admin")
        r_go = c2.number_input(f"Wynik {mecz['goscie']}", 0, 10, key="res_go_admin")
        
        if st.button("Zakończ mecz i podlicz"):
            supabase.table("mecze").update({"gole_gospodarze": r_g, "gole_goscie": r_go, "status": "FT"}).eq("id", mecz['id']).execute()
            for t in supabase.table("typy").select("*").eq("mecz_id", mecz['id']).execute().data:
                pts = oblicz_punkty(t['typ_gospodarze'], t['typ_goscie'], r_g, r_go)
                supabase.table("typy").update({"punkty_za_mecz": pts, "rozliczony": True}).eq("id", t['id']).execute()
            # Przelicz punkty
            for gracz in supabase.table("gracze").select("nick").execute().data:
                typy = supabase.table("typy").select("punkty_za_mecz").eq("nick", gracz['nick']).execute().data
                suma = sum([t['punkty_za_mecz'] for t in typy if t['punkty_za_mecz'] is not None])
                supabase.table("gracze").update({"punkty": suma}).eq("nick", gracz['nick']).execute()
            st.success("Rozliczono!")
            st.rerun()
    else:
        st.info("Brak meczów do rozliczenia.")

# --- GŁÓWNA LOGIKA ---
if st.session_state.nick == '':
    st.title("⚽ Typer Mundialu")
    tab_log, tab_rej = st.tabs(["🔐 Logowanie", "📝 Rejestracja"])
    with tab_log:
        log_nick = st.text_input("Nick:", key="log_nick")
        log_haslo = st.text_input("Hasło:", type="password", key="log_haslo")
        if st.button("Zaloguj"):
            res = supabase.table('gracze').select('*').eq('nick', log_nick).execute()
            if res.data and res.data[0].get('haslo') == log_haslo:
                st.session_state.nick = log_nick
                st.rerun()
            else: st.error("Błędny nick lub hasło!")
    with tab_rej:
        rej_nick = st.text_input("Wymyśl nick:", key="rej_nick")
        rej_haslo = st.text_input("Wymyśl hasło:", type="password", key="rej_haslo")
        if st.button("Zarejestruj"):
            if not supabase.table('gracze').select('*').eq('nick', rej_nick).execute().data:
                supabase.table('gracze').insert({'nick': rej_nick, 'haslo': rej_haslo, 'punkty': 0}).execute()
                st.session_state.nick = rej_nick
                st.rerun()
            else: st.error("Nick zajęty!")
else:
    with st.sidebar:
        st.write(f"Zalogowany: **{st.session_state.nick}**")
        if st.button("Wyloguj się"):
            st.session_state.nick = ''
            st.rerun()

    st.title("⚽ Typer Mundialu")
    tabs = st.tabs(["🎯 Typer", "🏆 Ranking", "⚙️ Panel Admina"])
    with tabs[0]: render_typer()
    with tabs[1]: render_ranking()
    with tabs[2]:
        if st.session_state.nick in ADMINI: render_admin()
        else: st.warning("Brak uprawnień administratora.")
