import database
import pandas as pd
import streamlit as st
import utils


def render_matryca(wszystkie_mecze, zalogowany_gracz):
  st.header("👁️ Podgląd Typów Rywali / Matryca Kolejki")

  if not wszystkie_mecze:
    st.info("Brak meczów w bazie.")
    return

  kolejki_raw = sorted(
      list(set(m["kolejka"] for m in wszystkie_mecze)),
      key=utils.wyciagnij_numer_kolejki,
  )

  kolejki_mapa = {k: utils.formatuj_nazwe_kolejki(k) for k in kolejki_raw}

  # AUTOMATYCZNY WYBÓR AKTUALNEJ KOLEJKI
  aktualna_kolejka_nr = utils.wyznacz_aktualna_kolejke(wszystkie_mecze)

  domyslny_idx = 0
  for idx, k_raw in enumerate(kolejki_raw):
    if str(utils.wyciagnij_numer_kolejki(k_raw)) == str(aktualna_kolejka_nr):
      domyslny_idx = idx
      break

  wybrana_kolejka_raw = st.selectbox(
      "Wybierz kolejkę do podglądu:",
      options=kolejki_raw,
      index=domyslny_idx,
      format_func=lambda k: kolejki_mapa[k],
      key="matryca_kolejka",
  )

  mecze_w_kolejce = [
      m for m in wszystkie_mecze if m["kolejka"] == wybrana_kolejka_raw
  ]
  wszystkie_typy = database.pobierz_wszystkie_typy()
  lista_graczy = database.pobierz_liste_graczy()

  mapa_typow = {
      (t["gracz_nick"], t["mecz_id"]): (t["typ_gospodarze"], t["typ_goscie"])
      for t in wszystkie_typy
  }

  st.caption(
      "💡 *Typy rywali są odsłaniane automatycznie z chwilą rozpoczęcia"
      " danego meczu.*"
  )

  tabela_rows = []

  for mecz in mecze_w_kolejce:
    mecz_id = mecz["id"]
    mecz_nazwa = f"{mecz['gospodarze']} - {mecz['goscie']}"
    status_meczu = str(mecz.get("status", "")).upper()

    mecz_przelozony = status_meczu == "PPD"

    if mecz_przelozony:
      wynik_real = "Przełożony"
    else:
      wynik_real = mecz.get("wynik") or "- : -"

    if mecz_przelozony:
      zablokowany = False
    else:
      zablokowany = utils.czy_mecz_zablokowany(
          mecz.get("data_meczu"), mecz.get("status")
      )

    row = {"Mecz": mecz_nazwa, "Wynik końcowy": wynik_real}

    for gracz in lista_graczy:
      typ = mapa_typow.get((gracz, mecz_id))

      if typ is None:
        row[gracz] = "—"
      else:
        if zablokowany or gracz == zalogowany_gracz:
          row[gracz] = f"{typ[0]} - {typ[1]}"
        else:
          row[gracz] = "🔒 Ukryty"

    tabela_rows.append(row)

  df_matryca = pd.DataFrame(tabela_rows)

  if not df_matryca.empty:
    st.dataframe(df_matryca, use_container_width=True, hide_index=True)
  else:
    st.info("Brak typów dla tej kolejki.")
