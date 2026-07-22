import database
import streamlit as st
import utils


def render_typowanie(wszystkie_mecze, wybrany_gracz):
  st.header("🎯 Formularz Typowania")

  if not wszystkie_mecze:
    st.info(
        "Brak meczów w bazie. Kliknij **'Synchronizuj terminarz z API'** w"
        " panelu bocznym!"
    )
    return

  kolejki = sorted(
      list(set(m["kolejka"] for m in wszystkie_mecze)),
      key=utils.wyciagnij_numer_kolejki,
  )
  wybrana_kolejka = st.selectbox("Wybierz kolejkę do wytypowania:", kolejki)

  mecze_w_kolejce = [
      m for m in wszystkie_mecze if m["kolejka"] == wybrana_kolejka
  ]

  dotychczasowe_typy = (
      database.pobierz_typy_gracza(wybrany_gracz) if wybrany_gracz else {}
  )

  if not wybrany_gracz:
    st.warning(
        "🔒 Zaloguj się lub zarejestruj w panelu bocznym po lewej stronie, aby"
        " typować!"
    )

  with st.form("formularz_typowania"):
    nowe_typy = {}

    for mecz in mecze_w_kolejce:
      mecz_id = mecz["id"]
      zapisany_typ = dotychczasowe_typy.get(mecz_id, None)

      data_f = utils.formatuj_date(mecz.get("data_meczu"))
      zablokowany = utils.czy_mecz_zablokowany(
          mecz.get("data_meczu"), mecz.get("status")
      )

      col_header1, col_header2 = st.columns([2, 2])
      with col_header1:
        st.caption(f"⏱️ {data_f}")

      with col_header2:
        if zablokowany:
          if zapisany_typ is not None:
            st.markdown(
                f"<div style='text-align: right; color: #d32f2f; font-weight:"
                f" bold;'>🔒 Zamknięte (Twój typ: {zapisany_typ[0]} -"
                f" {zapisany_typ[1]})</div>",
                unsafe_allow_html=True,
            )
          else:
            st.markdown(
                "<div style='text-align: right; color: #d32f2f; font-weight:"
                " bold;'>🔒 Zamknięte (Brak typu)</div>",
                unsafe_allow_html=True,
            )
        else:
          if zapisany_typ is not None:
            st.markdown(
                f"<div style='text-align: right; color: #2e7d32; font-weight:"
                f" bold;'>🟢 Obstawiono: {zapisany_typ[0]} -"
                f" {zapisany_typ[1]}</div>",
                unsafe_allow_html=True,
            )
          else:
            st.markdown(
                "<div style='text-align: right; color: #888888;'>⚪ Brak"
                " typu</div>",
                unsafe_allow_html=True,
            )

      col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 3])

      logo_h = mecz.get("logo_gospodarze")
      logo_a = mecz.get("logo_goscie")

      with col1:
        if logo_h:
          st.markdown(
              f"<div style='display: flex; align-items: center; gap:"
              f" 10px;'><img src='{logo_h}' width='28' height='28'/>"
              f" <b>{mecz['gospodarze']}</b></div>",
              unsafe_allow_html=True,
          )
        else:
          st.write(f"**{mecz['gospodarze']}**")

      domyslna_gosp = int(zapisany_typ[0]) if zapisany_typ is not None else 0
      domyslna_gosc = int(zapisany_typ[1]) if zapisany_typ is not None else 0

      disabled_flag = (not wybrany_gracz) or zablokowany

      with col2:
        typ_gosp = st.number_input(
            "Gospodarze",
            min_value=0,
            max_value=15,
            value=domyslna_gosp,
            key=f"gosp_{mecz_id}",
            label_visibility="collapsed",
            disabled=disabled_flag,
        )

      with col3:
        st.markdown(
            "<h4 style='text-align: center; margin: 0;'>:</h4>",
            unsafe_allow_html=True,
        )

      with col4:
        typ_gosc = st.number_input(
            "Goście",
            min_value=0,
            max_value=15,
            value=domyslna_gosc,
            key=f"gosc_{mecz_id}",
            label_visibility="collapsed",
            disabled=disabled_flag,
        )

      with col5:
        if logo_a:
          st.markdown(
              f"<div style='display: flex; align-items: center; gap:"
              f" 10px;'><img src='{logo_a}' width='28' height='28'/>"
              f" <b>{mecz['goscie']}</b></div>",
              unsafe_allow_html=True,
          )
        else:
          st.write(f"**{mecz['goscie']}**")

      st.markdown("---")

      if wybrany_gracz and not zablokowany:
        nowe_typy[mecz_id] = {
            "gracz_nick": wybrany_gracz,
            "mecz_id": mecz_id,
            "typ_gospodarze": typ_gosp,
            "typ_goscie": typ_gosc,
        }

    zapisz_button = st.form_submit_button(
        "💾 Zapisz moje typy na tę kolejkę",
        use_container_width=True,
        type="primary",
        disabled=not wybrany_gracz,
    )

    if zapisz_button and wybrany_gracz:
      paczka_do_zapisu = list(nowe_typy.values())
      if paczka_do_zapisu:
        sukces = database.zapisz_typy_gracza(paczka_do_zapisu)
        if sukces:
          st.success("✅ Pomyślnie zapisano Twoje typy!")
          st.rerun()
      else:
        st.info("Brak aktywnych meczów do zapisania w tej kolejce.")
