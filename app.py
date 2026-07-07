import streamlit as st
from supabase import create_client, Client
import pandas as pd

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

if 'nick' not in st.session_state: 
    st.session_state.nick = ''

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
            if log_nick and log_haslo:
                res = supabase.table('gracze').select('*').eq('nick', log_nick).execute()
                if res.data:
                    if res.data[0].get('haslo') == log_haslo:
                        st.session_state.nick = log_nick
                        st.rerun()
                    else:
                        st.error("Błędne hasło!")
                else:
                    st.error("Konto z takim nickiem nie istnieje. Sprawdź literówki lub przejdź do rejestracji.")
            else:
                st.warning("Wpisz nick i hasło.")

    with tab_rej:
        st.subheader("Załóż nowe konto")
        rej_nick = st.text_input("Wymyśl nick:", key="rej_nick")
        rej_haslo = st.text_input("Wymyśl hasło:", type="password", key="rej_haslo")
        if st.button("Zarejestruj", key="btn_rej"):
            if rej_nick and rej_haslo:
                res = supabase.table('gracze').select('*').eq('nick', rej_nick).execute()
                if not res.data:
                    supabase.table('gracze').insert({'nick': rej_nick, 'haslo': rej_haslo, 'punkty': 0}).execute()
                    st.session_state.nick = rej_nick
                    st.rerun()
                else:
                    st.error("Ten nick jest już zajęty. Wymyśl inny!")
            else:
                st.warning("Uzupełnij wszystkie pola.")

else:
    st.title(f"⚽ Typer Mundialu")
    st.write(f"Zalogowany jako: **{st.session_state.nick}**")
    tab1, tab2, tab3 = st.tabs(["🎯 Typer", "🏆 Ranking", "⚙️ Panel Admina"])
    
    with tab1:
        st.subheader("Obstaw mecze lub zobacz wyniki")
        mecze = supabase.table("mecze").select("*").order("id").execute().data
        
        for m in mecze:
            st.write(f"---")
            stary_typ = supabase.table("typy").select("*").eq("nick", st.session_state.nick).eq("mecz_id", m['id']).execute().data
            
            if m['status'] == 'FT':
                st.write(f"🏁 **{m['gospodarze']} {m['gole_gospodarze']} : {m['gole_goscie']} {m['goscie']}** (Mecz zakończony)")
                if stary_typ:
                    t = stary_typ[0]
                    st.info(f"Twój typ: {t['typ_gospodarze']}:{t['typ_goscie']} | Zdobyte punkty: **{t['punkty_za_mecz']}**")
                else:
                    st.warning("Nie obstawiłeś tego meczu. Punkty: 0")
            else:
                st.write(f"⏳ **{m['gospodarze']}** vs **{m['goscie']}**")
                
                def_g = stary_typ[0]['typ_gospodarze'] if stary_typ else 0
                def_go = stary_typ[0]['typ_goscie'] if stary_typ else 0
                
                col1, col2 = st.columns(2)
                g = col1.number_input(f"Gole: {m['gospodarze']}", 0, 10, value=int(def_g), key=f"g_{m['id']}")
                go = col2.number_input(f"Gole: {m['goscie']}", 0, 10, value=int(def_go), key=f"go_{m['id']}")
                
                if st.button("Zapisz mój typ", key=f"btn_{m['id']}"):
                    dane_typu = {
                        "nick": st.session_state.nick,
                        "mecz_id": m['id'],
                        "typ_gospodarze": g,
                        "typ_goscie": go,
                        "rozliczony": False
                    }
                    try:
                        if stary_typ:
                            # Jeśli gracz już obstawił, aktualizujemy jego rekord używając ID z bazy
                            supabase.table("typy").update(dane_typu).eq("id", stary_typ[0]['id']).execute()
                        else:
                            # Jeśli to pierwszy raz, dodajemy nowy wiersz
                            supabase.table("typy").insert(dane_typu).execute()
                        st.success("Typ zapisany!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd zapisu w bazie: {e}")

    with tab2:
        st.subheader("Tabela Typerów")
        gracze = supabase.table("gracze").select("nick, punkty").order("punkty", desc=True).execute().data
        if gracze:
            df = pd.DataFrame(gracze)
            df.index = df.index + 1
            df.columns = ["Gracz", "Suma Punktów"]
            st.table(df)
        else:
            st.info("Brak zarejestrowanych graczy.")

    with tab3:
        st.subheader("Zarządzanie Grą")
        
        st.markdown("### ➕ Dodaj nowy mecz")
        gosp = st.text_input("Gospodarze")
        gosc = st.text_input("Goście")
        if st.button("Dodaj mecz do bazy"):
            if gosp and gosc:
                nowy_mecz = {
                    "gospodarze": gosp,
                    "goscie": gosc,
                    "status": "NS",
                    "data_meczu": "2026-07-08T20:00:00+00:00",
                    "kolejka": 1,
                    "gole_gospodarze": None,
                    "gole_goscie": None
                }
                try:
                    supabase.table("mecze").insert(nowy_mecz).execute()
                    st.success(f"Dodano mecz: {gosp} vs {gosc}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd bazy: {e}")
            else:
                st.warning("Uzupełnij obie drużyny!")
                
        st.markdown("### 🏁 Rozlicz wynik meczu i przyznaj punkty")
        mecze_do_rozliczenia = supabase.table("mecze").select("*").neq("status", "FT").execute().data
        
        if mecze_do_rozliczenia:
            opcje_meczow = {f"{m['gospodarze']} vs {m['goscie']} (ID: {m['id']})": m for m in mecze_do_rozliczenia}
            wybrany_mecz_str = st.selectbox("Wybierz rozegrany mecz:", list(opcje_meczow.keys()))
            mecz_obj = opcje_meczow[wybrany_mecz_str]
            
            col1, col2 = st.columns(2)
            res_g = col1.number_input(f"Wynik końcowy: {mecz_obj['gospodarze']}", 0, 10, key="res_g")
            res_go = col2.number_input(f"Wynik końcowy: {mecz_obj['goscie']}", 0, 10, key="res_go")
            
            if st.button("Zakończ mecz i podlicz punkty"):
                try:
                    supabase.table("mecze").update({
                        "gole_gospodarze": res_g,
                        "gole_goscie": res_go,
                        "status": "FT"
                    }).eq("id", mecz_obj['id']).execute()
                    
                    wszystkie_typy = supabase.table("typy").select("*").eq("mecz_id", mecz_obj['id']).execute().data
                    
                    for t in wszystkie_typy:
                        pts = oblicz_punkty(t['typ_gospodarze'], t['typ_goscie'], res_g, res_go)
                        supabase.table("typy").update({
                            "punkty_za_mecz": pts,
                            "rozliczony": True
                        }).eq("id", t['id']).execute()
                    
                    wszyscy_gracze = supabase.table("gracze").select("nick").execute().data
                    for gracz in wszyscy_gracze:
                        typy_gracza = supabase.table("typy").select("punkty_za_mecz").eq("nick", gracz['nick']).execute().data
                        suma_punktow = sum([item['punkty_za_mecz'] for item in typy_gracza if item['punkty_za_mecz'] is not None])
                        supabase.table("gracze").update({"punkty": suma_punktow}).eq("nick", gracz['nick']).execute()
                        
                    st.success("Mecz rozliczony! Punkty zostały dodane, a ranking zaktualizowany.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd podczas rozliczania: {e}")
        else:
            st.info("Wszystkie mecze w bazie są już rozliczone.")
        
        st.write("---")
        if st.button("Wyloguj się"):
            st.session_state.nick = ''
            st.rerun()
