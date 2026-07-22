import database
import pandas as pd
import streamlit as st
import utils


def render_matryca(wszystkie_mecze, zalogowany_gracz):
  st.header("👁️ Podgląd Typów Rywali / Matryca Kolejki")

  if not wszystkie_mecze:
    st.info("Brak meczów w bazie.")
    return

  kolejki = sorted(
      list(set(m["kolejka"] for m in wszystkie_mecze)),
      key=utils.wyciagnij_numer_kolejki,
  )
  wybrana_kolejka = st.selectbox(
      "Wybierz kolejkę do podglądu:", kolejki, key="matryca_kolejka"
  )

  mecze_w_kolejce = [
      m for m in wszystkie_mecze if m["kolejka"] == wybrana_kolejka
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
    wynik_real = mecz.get("wynik") or "- : -"

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
