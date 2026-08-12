from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import api
import database
import streamlit as st
from views.matryca import render_matryca
from views.profil import render_profil
from views.ranking import render_ranking
from views.regulamin import render_regulamin
from views.typowanie import render_typowanie

st.set_page_config(
    page_title="Ekstraklasa Typer", page_icon="⚽", layout="wide"
)


# --- AUTOMATYCZNA SYNCHRONIZACJA W TLE (MAX RAZ NA 30 MINUT) ---
def automatyczna_synchronizacja():
  czas_str = database.pobierz_czas_synchro()
  wykonaj = False

  if czas_str == "Brak danych":
    wykonaj = True
  else:
    try:
      ostatnia = datetime.strptime(czas_str, "%d.%m.%Y %H:%M:%S").replace(
          tzinfo=ZoneInfo("Europe/Warsaw")
      )
      teraz = datetime.now(ZoneInfo("Europe/Warsaw"))
      if teraz - ostatnia >= timedelta(minutes=30):
        wykonaj = True
    except Exception:
      wykonaj = True

  if wykonaj:
    try:
      surowe_mecze = api.pobierz_mecze_ekstraklasy(90990, 2026)
      if surowe_mecze:
        database.synchronizuj_mecze_wsadowo(surowe_mecze)
    except Exception:
      pass


automatyczna_synchronizacja()

try:
  res_mecze = (
      database.db.table("mecze")
      .select("*")
      .order("data_meczu", desc=False)
      .execute()
  )
  wszystkie_mecze = res_mecze.data
except Exception:
  wszystkie_mecze = []

kluby_mapa = database.pobierz_mapa_klubow_logo(wszystkie_mecze)
lista_klubow = ["— Brak —"] + sorted(list(kluby_mapa.keys()))

if "zalogowany_gracz" not in st.session_state:
  st.session_state["zalogowany_gracz"] = None


# --- PROFESJONALNY BANER TELEWIZYJNY EKSTRAKLAPA ---
def renderuj_naglowek_logo():
  html_code = """
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 25px; padding: 15px; background: linear-gradient(135deg, #0b0e14 0%, #161b22 100%); border-radius: 12px; box-shadow: 0 8px 25px rgba(0,0,0,0.4); border-bottom: 3px solid #00f2ff;">
        <div style="display: flex; align-items: center; gap: 15px;">
            <div style="background: #ffffff; border-radius: 50%; width: 45px; height: 45px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 10px rgba(0,242,255,0.3);">
                <span style="font-size: 24px;">⚽</span>
            </div>
            <div>
                <div style="font-family: 'Montserrat', sans-serif; font-size: 11px; font-weight: 700; color: #8f9bba; letter-spacing: 3px; text-transform: uppercase;">PKO Bank Polski</div>
                <div style="font-family: 'Montserrat', sans-serif; font-size: 32px; font-weight: 900; color: #ffffff; letter-spacing: 4px; text-transform: uppercase; line-height: 1.1;">
                    EKSTRAKLAPA
                </div>
            </div>
        </div>
        <div style="margin-top: 10px; background: linear-gradient(135deg, #0052cc 0%, #00f2ff 100%); color: #ffffff; padding: 4px 16px; border-radius: 20px; font-family: 'Montserrat', sans-serif; font-size: 13px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase; box-shadow: 0 3px 10px rgba(0,242,255,0.4);">
            TYPER 2026/27
        </div>
    </div>
    """
  st.markdown(html_code, unsafe_allow_html=True)


renderuj_naglowek_logo()


# --- PANEL BOCZNY ---
st.sidebar.header("👤 Panel Gracza")

dostepni_gracze = database.pobierz_liste_graczy()

if not st.session_state["zalogowany_gracz"]:
  tab_login, tab_register = st.sidebar.tabs(["🔑 Logowanie", "📝 Rejestracja"])

  with tab_login:
    if dostepni_gracze:
      wybrany_gracz_do_logowania = st.selectbox(
          "Wybierz gracza:", dostepni_gracze, key="login_select"
      )
      wpisany_pin = st.text_input(
          "Wpisz 4-cyfrowy PIN:",
          type="password",
          max_chars=4,
          key="login_pin",
      )

      if st.button("🔑 Zaloguj się", use_container_width=True):
        if database.weryfikuj_pin_gracza(
            wybrany_gracz_do_logowania, wpisany_pin
        ):
          st.session_state["zalogowany_gracz"] = wybrany_gracz_do_logowania
          st.success("Zalogowano pomyślnie!")
          st.rerun()
        else:
          st.error("❌ Nieprawidłowy PIN!")
    else:
      st.info("Brak graczy w bazie. Zarejestruj się obok!")

  with tab_register:
    nowy_nick = st.text_input("Nick / Imię:", key="reg_nick")
    wybrany_klub = st.selectbox(
        "Ulubiony klub:", lista_klubow, key="reg_klub"
    )
    nowy_pin = st.text_input(
        "Ustal 4-cyfrowy PIN:",
        type="password",
        max_chars=4,
        key="reg_pin",
        help="PIN musi składać się z 4 cyfr",
    )
    powtorz_pin = st.text_input(
        "Powtórz 4-cyfrowy PIN:",
        type="password",
        max_chars=4,
        key="reg_pin_repeat",
    )

    if st.button("✨ Zarejestruj się", use_container_width=True):
      if not nowy_nick.strip():
        st.error("Podaj swój nick!")
      elif not nowy_pin.strip():
        st.error("Ustal PIN!")
      elif nowy_pin != powtorz_pin:
        st.error("Wpisane PIN-y nie są identyczne!")
      else:
        klub_val = "" if wybrany_klub == "— Brak —" else wybrany_klub
        sukces, komunikat = database.zarejestruj_gracza(
            nowy_nick, nowy_pin, klub_val
        )
        if sukces:
          st.success(komunikat)
          st.session_state["zalogowany_gracz"] = nowy_nick.strip()
          st.rerun()
        else:
          st.error(komunikat)

else:
  wybrany_gracz = st.session_state["zalogowany_gracz"]
  st.sidebar.success(f"Zalogowany jako: **{wybrany_gracz}**")

  if st.sidebar.button("🚪 Wyloguj się", use_container_width=True):
    st.session_state["zalogowany_gracz"] = None
    st.rerun()

wybrany_gracz = st.session_state["zalogowany_gracz"]

# --- ZARZĄDZANIE LIGĄ WIDOCZNE TYLKO DLA "Mateusz" ---
if wybrany_gracz == "Mateusz":
  st.sidebar.markdown("---")
  st.sidebar.subheader("⚙️ Zarządzanie ligą")

  if st.sidebar.button(
      "🔄 Wymuś synchronizację z API", use_container_width=True
  ):
    st.cache_data.clear()
    with st.spinner("Pobieranie terminarza Ekstraklasy..."):
      surowe_mecze = api.pobierz_mecze_ekstraklasy(90990, 2026)

      if surowe_mecze:
        sukces = database.synchronizuj_mecze_wsadowo(surowe_mecze)
        if sukces:
          st.sidebar.success("Zsynchronizowano mecze pomyślnie!")
          st.rerun()
        else:
          st.sidebar.error("Błąd zapisu meczów do bazy.")
      else:
        st.sidebar.warning("API zwróciło pustą listę meczów.")

st.sidebar.markdown("---")
czas_synchro = database.pobierz_czas_synchro()
st.sidebar.caption(f"⏱️ **Ostatnia synchro:** {czas_synchro}")

# --- WCHODZENIE W ZAKŁADKI ---
lista_zakladek = [
    "🎯 Formularz Typowania",
    "🏆 Tabela / Ranking",
    "👁️ Podgląd Typów",
    "⚙️ Profil",
    "📜 Regulamin",
]

if wybrany_gracz == "Mateusz":
  lista_zakladek.append("💰 Składki (Admin)")

tabs = st.tabs(lista_zakladek)

with tabs[0]:
  render_typowanie(wszystkie_mecze, wybrany_gracz)

with tabs[1]:
  render_ranking(wszystkie_mecze)

with tabs[2]:
  render_matryca(wszystkie_mecze, wybrany_gracz)

with tabs[3]:
  render_profil(wybrany_gracz, wszystkie_mecze)

with tabs[4]:
  render_regulamin()

# --- ZAKŁADKA SKŁADEK DLA ADMINA ---
if wybrany_gracz == "Mateusz":
  with tabs[5]:
    st.header("💰 Zarządzanie Wpłatami na Nagrody")
    st.markdown("---")

    statusy_wplat = database.pobierz_status_wplat()
    wszyscy = database.pobierz_liste_graczy()

    if not wszyscy:
      st.info("Brak graczy w bazie danych.")
    else:
      oplaceni_count = sum(1 for g in wszyscy if statusy_wplat.get(g, False))
      total_count = len(wszyscy)
      zebrana_kwota = oplaceni_count * 100
      pelna_pula = total_count * 100

      col_k1, col_k2 = st.columns(2)
      with col_k1:
        st.metric("👥 Status wpłat", f"{oplaceni_count} / {total_count} graczy")
      with col_k2:
        st.metric("💵 Zebrana pula", f"{zebrana_kwota} zł / {pelna_pula} zł")

      st.markdown("---")
      st.subheader("Lista uczestników:")

      nowe_stany = {}
      with st.form("form_wplaty"):
        cols = st.columns(2)
        for i, gracz in enumerate(wszyscy):
          c = cols[i % 2]
          obecny_stan = statusy_wplat.get(gracz, False)
          etykieta = (
              f"✅ **{gracz}** (Opłacono)"
              if obecny_stan
              else f"⏳ **{gracz}** (Oczekuje na wpłatę)"
          )
          nowe_stany[gracz] = c.checkbox(
              etykieta, value=obecny_stan, key=f"wplata_{gracz}"
          )

        st.markdown("<br>", unsafe_allow_html=True)
        btn_zapisz_wplaty = st.form_submit_button(
            "💾 Zapisz zmiany wpłat", type="primary", use_container_width=True
        )

        if btn_zapisz_wplaty:
          sukces = database.zapisz_status_wplat(nowe_stany)
          if sukces:
            st.success("✅ Zaktualizowano statusy wpłat w bazie!")
            st.rerun()
          else:
            st.error("❌ Błąd zapisu do bazy.")
