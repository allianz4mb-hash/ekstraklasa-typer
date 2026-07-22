from datetime import datetime
from zoneinfo import ZoneInfo
import database
import streamlit as st


def daj_klimatyczny_naglowek(data_iso_str):
  """Zamienia datę ISO na klimatyczny nagłówek dnia tygodnia."""
  try:
    if data_iso_str.endswith("Z"):
      data_iso_str = data_iso_str[:-1] + "+00:00"

    dt = datetime.fromisoformat(data_iso_str).astimezone(
        ZoneInfo("Europe/Warsaw")
    )
    dzien_tygodnia = dt.weekday()  # 0=Mon, 1=Tue, ..., 6=Sun
    data_ladna = dt.strftime("%d.%m.%Y")

    slogany = {
        4: f"🔥 Super Piątek — {data_ladna}",
        5: f"⚡ Gorączka Piłkarskiej Soboty — {data_ladna}",
        6: f"⚽ Grana Niedziela — {data_ladna}",
        0: f"🌙 Poniedziałkowa Ekstraklasa po godzinach — {data_ladna}",
        1: f"⚽ Piłkarski Wtorek — {data_ladna}",
        2: f"⚽ Meczowa Środa — {data_ladna}",
        3: f"⚽ Czwartek z Ekstraklasą — {data_ladna}",
    }
    return slogany.get(dzien_tygodnia, f"📅 {data_ladna}"), dt
  except Exception:
    return data_iso_str, None


def formatuj_godzine(data_iso_str):
  """Sformatuje datę ISO do samej godziny HH:MM."""
  try:
    if data_iso_str.endswith("Z"):
      data_iso_str = data_iso_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(data_iso_str).astimezone(
        ZoneInfo("Europe/Warsaw")
    )
    return dt.strftime("godz. %H:%M")
  except Exception:
    return ""


def render_typowanie(wszystkie_mecze, zalogowany_gracz):
  st.header("🎯 Formularz Typowania")

  if not zalogowany_gracz:
    st.info("💡 Zaloguj się w panelu bocznym, aby móc zapisywać swoje typy!")

  if not wszystkie_mecze:
    st.warning("Brak meczów w bazie danych. Wykonaj synchronizację w panelu.")
    return

  # Wybór kolejki
  kolejki = sorted(
      list(set(m.get("kolejka", "Kolejka 1") for m in wszystkie_mecze))
  )
  wybrana_kolejka = st.selectbox("Wybierz kolejkę do wytypowania:", kolejki)

  mecze_kolejki = [
      m for m in wszystkie_mecze if m.get("kolejka") == wybrana_kolejka
  ]

  # Pobranie dotychczasowych typów gracza
  dotychczasowe_typy = (
      database.pobierz_typy_gracza(zalogowany_gracz) if zalogowany_gracz else {}
  )

  # Grupowanie meczów po nagłówkach dni
  pogrupowane_mecze = {}
  for mecz in mecze_kolejki:
    naglowek, dt = daj_klimatyczny_naglowek(mecz.get("data_meczu", ""))
    if naglowek not in pogrupowane_mecze:
      pogrupowane_mecze[naglowek] = []
    pogrupowane_mecze[naglowek].append(mecz)

  nowe_typy = []

  with st.form(key=f"form_typy_{wybrana_kolejka}"):
    for naglowek_dnia, mecze in pogrupowane_mecze.items():
      st.subheader(naglowek_dnia)
      st.markdown("---")

      for mecz in mecze:
        mecz_id = mecz["id"]
        gospodarze = mecz.get("gospodarze", "Gospodarze")
        goscie = mecz.get("goscie", "Goście")
        logo_h = mecz.get("logo_gospodarze", "")
        logo_a = mecz.get("logo_goscie", "")
        data_meczu = mecz.get("data_meczu", "")
        godzina_str = formatuj_godzine(data_meczu)

        # Status typu gracza (badge po prawej stronie)
        czy_obstawiono = mecz_id in dotychczasowe_typy
        if czy_obstawiono:
          domyslne_h, domyslne_a = dotychczasowe_typy[mecz_id]
          badge_html = f"<div style='text-align: right; color: #2e7d32; font-weight: bold;'>🟢 Obstawiono: {domyslne_h} - {domyslne_a}</div>"
        else:
          domyslne_h, domyslne_a = 0, 0
          badge_html = "<div style='text-align: right; color: #757575;'>⚪ Brak typu</div>"

        # Pasek informacji nad meczem (Godzina + Status obstawienia)
        col_info1, col_info2 = st.columns([1, 1])
        with col_info1:
          st.caption(f"⏱️ {godzina_str}")
        with col_info2:
          st.markdown(badge_html, unsafe_allow_html=True)

        # Rząd wyboru wyniku meczu
        col_h, col_vs, col_a = st.columns([4, 1, 4])

        with col_h:
          c1, c2 = st.columns([1, 4])
          if logo_h:
            c1.image(logo_h, width=30)
          c2.markdown(f"**{gospodarze}**")
          typ_h = st.number_input(
              f"Gole {gospodarze}",
              min_value=0,
              max_value=15,
              value=int(domyslne_h),
              key=f"h_{mecz_id}",
              label_visibility="collapsed",
          )

        with col_vs:
          st.markdown(
              "<h3 style='text-align: center;'>:</h3>", unsafe_allow_html=True
          )

        with col_a:
          c1, c2 = st.columns([4, 1])
          c1.markdown(
              f"<div style='text-align: right;'><b>{goscie}</b></div>",
              unsafe_allow_html=True,
          )
          if logo_a:
            c2.image(logo_a, width=30)
          typ_a = st.number_input(
              f"Gole {goscie}",
              min_value=0,
              max_value=15,
              value=int(domyslne_a),
              key=f"a_{mecz_id}",
              label_visibility="collapsed",
          )

        if zalogowany_gracz:
          nowe_typy.append({
              "gracz_nick": zalogowany_gracz,
              "mecz_id": mecz_id,
              "typ_gospodarze": typ_h,
              "typ_goscie": typ_a,
          })

        st.markdown("<br>", unsafe_allow_html=True)

    przycisk_zapisz = st.form_submit_button(
        "💾 Zapisz moje typy", use_container_width=True, type="primary"
    )

    if przycisk_zapisz:
      if not zalogowany_gracz:
        st.error("Musisz być zalogowany, aby zapisać typy!")
      else:
        sukces = database.zapisz_typy_gracza(nowe_typy)
        if sukces:
          st.success("✅ Twoje typy zostały pomyślnie zapisane w bazie!")
          st.rerun()
        else:
          st.error("Błąd podczas zapisu typów.")
