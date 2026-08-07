from datetime import datetime
from zoneinfo import ZoneInfo
import database
import streamlit as st
import utils


def render_typowanie(wszystkie_mecze, zalogowany_gracz):
  st.header("🎯 Formularz Typowania")

  if not zalogowany_gracz:
    st.info("💡 Zaloguj się w panelu bocznym, aby móc zapisywać swoje typy!")

  if not wszystkie_mecze:
    st.warning("Brak meczów w bazie danych. Wykonaj synchronizację w panelu.")
    return

  surowe_kolejki = list(set(m.get("kolejka", "1") for m in wszystkie_mecze))
  surowe_kolejki = sorted(surowe_kolejki, key=utils.wyciagnij_numer_kolejki)

  mapa_kolejek = {k: utils.formatuj_nazwe_kolejki(k) for k in surowe_kolejki}

  # AUTOMATYCZNY WYBÓR AKTUALNEJ KOLEJKI
  aktualna_kolejka_nr = utils.wyznacz_aktualna_kolejke(wszystkie_mecze)

  domyslny_idx = 0
  for idx, k_raw in enumerate(surowe_kolejki):
    if str(utils.wyciagnij_numer_kolejki(k_raw)) == str(aktualna_kolejka_nr):
      domyslny_idx = idx
      break

  wybrana_kolejka_raw = st.selectbox(
      "Wybierz kolejkę do wytypowania:",
      options=surowe_kolejki,
      index=domyslny_idx,
      format_func=lambda x: mapa_kolejek[x],
  )

  mecze_kolejki = [
      m for m in wszystkie_mecze if m.get("kolejka") == wybrana_kolejka_raw
  ]

  dotychczasowe_typy = (
      database.pobierz_typy_gracza(zalogowany_gracz) if zalogowany_gracz else {}
  )

  pogrupowane_mecze = {}
  for mecz in mecze_kolejki:
    naglowek, dt = utils.daj_klimatyczny_naglowek(mecz.get("data_meczu", ""))
    if naglowek not in pogrupowane_mecze:
      pogrupowane_mecze[naglowek] = []
    pogrupowane_mecze[naglowek].append(mecz)

  nowy_typy = []

  form_key = f"form_typy_{wybrana_kolejka_raw}_{zalogowany_gracz or 'gosc'}"

  with st.form(key=form_key):
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
        godzina_str = utils.formatuj_godzine(data_meczu)
        status_meczu = str(mecz.get("status", "")).upper()

        mecz_przelozony = status_meczu == "PPD"
        mecz_rozpocziety = False

        if not mecz_przelozony and data_meczu:
          try:
            if data_meczu.endswith("Z"):
              dt_str = data_meczu[:-1] + "+00:00"
            else:
              dt_str = data_meczu
            dt_meczu = datetime.fromisoformat(dt_str).astimezone(
                ZoneInfo("Europe/Warsaw")
            )
            if datetime.now(ZoneInfo("Europe/Warsaw")) >= dt_meczu:
              mecz_rozpocziety = True
          except Exception:
            pass

        if zalogowany_gracz and mecz_id in dotychczasowe_typy:
          domyslne_h, domyslne_a = dotychczasowe_typy[mecz_id]
          if mecz_przelozony:
            badge_html = (
                f"<div style='text-align: right; color: #f57c00; font-weight:"
                f" bold;'>🟠 Przełożony (Typ: {domyslne_h} - {domyslne_a})</div>"
            )
          elif mecz_rozpocziety:
            badge_html = (
                f"<div style='text-align: right; color: #d32f2f; font-weight:"
                f" bold;'>🔒 Zablokowane (Typ: {domyslne_h} - {domyslne_a})</div>"
            )
          else:
            badge_html = (
                f"<div style='text-align: right; color: #2e7d32; font-weight:"
                f" bold;'>🟢 Obstawiono: {domyslne_h} - {domyslne_a}</div>"
            )
        else:
          domyslne_h, domyslne_a = 0, 0
          if mecz_przelozony:
            badge_html = (
                "<div style='text-align: right; color: #f57c00; font-weight:"
                " bold;'>🟠 Przełożony (Można typować)</div>"
            )
          elif mecz_rozpocziety:
            badge_html = (
                "<div style='text-align: right; color: #d32f2f; font-weight:"
                " bold;'>🔒 Zablokowane (Brak typu)</div>"
            )
          else:
            badge_html = (
                "<div style='text-align: right; color: #757575;'>⚪ Brak"
                " typu</div>"
            )

        col_info1, col_info2 = st.columns([1, 1])
        with col_info1:
          if mecz_przelozony:
            st.caption("⏱️ Termin do ustalenia")
          else:
            st.caption(f"⏱️ {godzina_str}")
        with col_info2:
          st.markdown(badge_html, unsafe_allow_html=True)

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
              key=f"h_{zalogowany_gracz}_{mecz_id}",
              label_visibility="collapsed",
              disabled=mecz_rozpocziety and not mecz_przelozony,
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
              key=f"a_{zalogowany_gracz}_{mecz_id}",
              label_visibility="collapsed",
              disabled=mecz_rozpocziety and not mecz_przelozony,
          )

        if zalogowany_gracz and (not mecz_rozpocziety or mecz_przelozony):
          nowy_typy.append({
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
        sukces = database.zapisz_typy_gracza(nowy_typy)
        if sukces:
          st.success("✅ Twoje typy zostały pomyślnie zapisane w bazie!")
          st.rerun()
        else:
          st.error("Błąd podczas zapisu typów.")
