import database
import streamlit as st


def render_profil(zalogowany_gracz, wszystkie_mecze=[]):
  st.header("⚙️ Ustawienia Profilu")

  if not zalogowany_gracz:
    st.info("💡 Zaloguj się w panelu bocznym, aby zarządzać swoim profilem.")
    return

  st.write(f"Zalogowany jako: **{zalogowany_gracz}**")
  st.markdown("---")

  col1, col2 = st.columns(2)

  # Mapa klubów i logo
  kluby_mapa = database.pobierz_mapa_klubow_logo(wszystkie_mecze)
  lista_klubow = ["— Brak —"] + sorted(list(kluby_mapa.keys()))

  # Pobranie aktualnego klubu gracza
  info_gracze = database.pobierz_informacje_o_graczach()
  obecny_klub = info_gracze.get(zalogowany_gracz, {}).get(
      "ulubiony_klub", "— Brak —"
  )
  if not obecny_klub:
    obecny_klub = "— Brak —"

  with col1:
    st.subheader("✏️ Zmień Nick oraz Ulubiony Klub")
    with st.form("form_zmiana_profilu"):
      nowy_nick = st.text_input("Nick / Imię:", value=zalogowany_gracz)

      idx_klub = (
          lista_klubow.index(obecny_klub)
          if obecny_klub in lista_klubow
          else 0
      )
      nowy_klub = st.selectbox(
          "Ulubiony Klub Ekstraklasy:", lista_klubow, index=idx_klub
      )

      btn_zapisz = st.form_submit_button(
          "💾 Zapisz zmiany", use_container_width=True, type="primary"
      )

      if btn_zapisz:
        nowy_nick_clean = nowy_nick.strip()
        klub_val = "" if nowy_klub == "— Brak —" else nowy_klub

        # Zmiana klubu
        database.zmien_ulubiony_klub(zalogowany_gracz, klub_val)

        # Zmiana nicku
        if nowy_nick_clean != zalogowany_gracz and nowy_nick_clean:
          sukces, msg = database.zmien_nick_gracza(
              zalogowany_gracz, nowy_nick_clean
          )
          if sukces:
            st.session_state["zalogowany_gracz"] = nowy_nick_clean
            st.success("✅ Zaktualizowano profil!")
            st.rerun()
          else:
            st.error(msg)
        else:
          st.success("✅ Zaktualizowano klub!")
          st.rerun()

  with col2:
    st.subheader("🔑 Zmień 4-cyfrowy PIN")
    with st.form("form_zmiana_pinu"):
      stary_pin = st.text_input(
          "Obecny PIN:", type="password", max_chars=4, key="prof_stary_pin"
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
