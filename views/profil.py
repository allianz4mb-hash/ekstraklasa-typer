import database
import streamlit as st


def render_profil(zalogowany_gracz):
  st.header("⚙️ Ustawienia Profilu")

  if not zalogowany_gracz:
    st.info("💡 Zaloguj się w panelu bocznym, aby zarządzać swoim profilem.")
    return

  st.write(f"Zalogowany jako: **{zalogowany_gracz}**")
  st.markdown("---")

  col1, col2 = st.columns(2)

  # --- SEKCJA 1: ZMIANA NICKU / IMIENIA ---
  with col1:
    st.subheader("✏️ Zmień Nick / Imię")
    with st.form("form_zmiana_nicku"):
      nowy_nick = st.text_input(
          "Nowy nick / imię:",
          value=zalogowany_gracz,
          placeholder="Wpisz nowy nick",
      )
      btn_zmien_nick = st.form_submit_button(
          "💾 Zapisz nowy nick", use_container_width=True, type="primary"
      )

      if btn_zmien_nick:
        nowy_nick_clean = nowy_nick.strip()
        if nowy_nick_clean == zalogowany_gracz:
          st.info("Nowy nick jest taki sam jak obecny.")
        elif not nowy_nick_clean:
          st.error("Nick nie może być pusty!")
        else:
          sukces, msg = database.zmien_nick_gracza(
              zalogowany_gracz, nowy_nick_clean
          )
          if sukces:
            # Aktualizujemy nazwę w aktywnej sesji
            st.session_state["zalogowany_gracz"] = nowy_nick_clean
            st.success("✅ Nick został zmieniony!")
            st.rerun()
          else:
            st.error(msg)

  # --- SEKCJA 2: ZMIANA PIN-U ---
  with col2:
    st.subheader("🔑 Zmień 4-cyfrowy PIN")
    with st.form("form_zmiana_pinu"):
      stary_pin = st.text_input(
          "Obecny PIN:",
          type="password",
          max_chars=4,
          key="prof_stary_pin",
      )
      nowy_pin = st.text_input(
          "Nowy 4-cyfrowy PIN:",
          type="password",
          max_chars=4,
          key="prof_nowy_pin",
      )
      powtorz_nowy_pin = st.text_input(
          "Powtórz nowy PIN:",
          type="password",
          max_chars=4,
          key="prof_powtorz_pin",
      )

      btn_zmien_pin = st.form_submit_button(
          "🔒 Zmień PIN", use_container_width=True, type="primary"
      )

      if btn_zmien_pin:
        if not stary_pin or not nowy_pin:
          st.error("Wypełnij wszystkie pola!")
        elif nowy_pin != powtorz_nowy_pin:
          st.error("Nowe PIN-y nie są identyczne!")
        elif len(nowy_pin) != 4 or not nowy_pin.isdigit():
          st.error("PIN musi składać się dokładnie z 4 cyfr!")
        else:
          if database.weryfikuj_pin_gracza(zalogowany_gracz, stary_pin):
            sukces, msg = database.zmien_pin_gracza(zalogowany_gracz, nowy_pin)
            if sukces:
              st.success("✅ PIN został pomyślnie zmieniony!")
            else:
              st.error(msg)
          else:
            st.error("❌ Podano nieprawidłowy obecny PIN!")
