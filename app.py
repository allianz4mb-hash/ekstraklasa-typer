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

def oblicz_punkty(typ_g, typ_go, real_g, real_go):
    if typ_g == real_g and typ_go == real_go: return 3
    elif (typ_g > typ_go and real_g > real_go) or (typ_g < typ_go and real_g < real_go) or (typ_g == typ_go and real_g == real_go): return 1
    return 0

# --- EKRAN LOGOWANIA ---
if st.session_state.nick == '':
    st.title("⚽ Typer Mundialu")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Logowanie")
        log_nick = st.text_input("Nick:")
        log_haslo = st.text_input("Hasło:", type="password")
        if st.button("Zaloguj"):
            res = supabase.table('gracze').select('*').eq('nick', log_nick).execute()
            if res.data and res.data[0].get('haslo') == log_haslo:
                st.session_state.nick = log_nick
                st.rerun()
            else: st.error("Błędny nick lub hasło!")
    with col2:
        st.subheader("Rejestracja")
        rej_nick = st.text_input("Wymyśl nick:")
        rej_haslo = st.text_input("Wymyśl hasło:", type="password")
        if st.button("Zarejestruj"):
            if not supabase.table('gracze').select('*').eq('nick', rej_nick).execute().data:
                supabase.table('gracze').insert({'nick': rej_nick, 'haslo': rej_haslo, 'punkty': 0}).execute()
                st.session_state.nick = rej_nick
                st.rerun()
            else: st.error("Nick zajęty!")

# --- EKRAN GŁÓWNY ---
else:
    with st.sidebar:
        st.write(f"Zalogowany: **{st.session_state.nick}**")
        if st.button("Wyloguj się"):
            st.session_state.nick = ''
            st.rerun()

    st.title("⚽ Typer Mundialu")
    
    # Nawigacja - radio buttony są najbardziej stabilne w Streamlit
    opcje = ["🎯 Typer", "🏆 Ranking"]
    if st.session_state.nick in ADMINI:
        opcje.append("⚙️ Panel Admina")
    
    wybor = st.radio("Nawigacja:", opcje, horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    # LOGIKA ZAKŁADEK
    if wybor == "🎯 Typer":
        st.subheader("Obstaw mecze")
        mecze = supabase.table("mecze").select("*").order("id").execute().data
        for m in mecze:
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

    elif wybor == "🏆 Ranking":
        st.subheader("Tabela Typerów")
        gracze = supabase.table("gracze").select("nick, punkty").order("punkty", desc=True).execute().data
        if gracze:
            df = pd.DataFrame(gracze)
            df.columns = ["Gracz", "Suma Punktów"]
            st.table(df)

    elif wybor == "⚙️ Panel Admina":
        st.subheader("Zarządzanie Grą")
        with st.expander("➕ Dodaj mecz"):
            c1, c2 = st.columns(2)
            n_g = c1.text_input("Gospodarze")
            n_go = c2.text_input("Goście")
            if st.button("Dodaj"):
                if n_g and n_go:
                    supabase.table("mecze").insert({
                        "gospodarze": n_g, "goscie": n_go, "status": "NS", 
                        "data_meczu": "2026-07-08T20:00:00+00:00", "kolejka": 1,
                        "gole_gospodarze": None, "gole_goscie": None
                    }).execute()
                    st.rerun()
        
        st.markdown("### 🏁 Rozlicz mecz")
        mecze_do = supabase.table("mecze").select("*").neq("status", "FT").execute().data
        if mecze_do:
            opcje_m = {f"{m['gospodarze']} vs {m['goscie']} (ID: {m['id']})": m for m in mecze_do}
            sel = st.selectbox("Wybierz mecz:", list(opcje_m.keys()))
            m = opcje_m[sel]
            c1, c2 = st.columns(2)
            r_g = c1.number_input(f"Wynik {m['gospodarze']}", 0, 10, key="r_g")
            r_go = c2.number_input(f"Wynik {m['goscie']}", 0, 10, key="r_go")
            if st.button("Zakończ i podlicz"):
                supabase.table("mecze").update({"gole_gospodarze": r_g, "gole_goscie": r_go, "status": "FT"}).eq("id", m['id']).execute()
                for t in supabase.table("typy").select("*").eq("mecz_id", m['id']).execute().data:
                    pts = oblicz_punkty(t['typ_gospodarze'], t['typ_goscie'], r_g, r_go)
                    supabase.table("typy").update({"punkty_za_mecz": pts, "rozliczony": True}).eq("id", t['id']).execute()
                for gracz in supabase.table("gracze").select("nick").
