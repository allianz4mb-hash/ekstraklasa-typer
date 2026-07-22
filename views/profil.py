import re
import database
import streamlit as st


def render_profil(zalogowany_gracz):
  st.header("⚙️ Ustawienia Profilu")

  if not zalogowany_gracz:
    st.warning("🔒 Zaloguj się w panelu bocznym, aby zarządzać swoim profilem.")
    return

  st.subheader("🔑 Zmiana 4-cyfrowego PIN-u")
  st.caption("Wpisz swój obecny PIN oraz ustal nowykod dostępu.")

  with st.form("form_zmien_pin"):
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

    submit_button = st.form_submit_button(
        "💾 Zapisz nowy PIN", use_container_width=True, type="primary"
    )

    if submit_button:
      if not stary_pin or not nowy_pin or not powtorz_pin:
        st.error("Wszystkie pola są wymagane!")
      elif nowy_pin != powtorz_nowy_pin:
        st.error("Nowo wpisane PIN-y nie są identyczne!")
      elif not re.match(r"^\d{4}$", nowy_pin):
        st.error("Nowy PIN musi składać się z dokładnie 4 cyfr!")
      elif not database.weryfikuj_pin_gracza(zalogowany_gracz, stary_pin):
        st.error("Podany obecny PIN jest nieprawidłowy!")
      else:
        sukces, komunikat = database.zmien_pin_gracza(
            zalogowany_gracz, nowy_pin
        )
        if sukces:
          st.success(komunikat)
        else:
          st.error(komunikat)
