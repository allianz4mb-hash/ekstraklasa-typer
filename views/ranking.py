import database
import pandas as pd
import streamlit as st
import utils


def render_ranking(wszystkie_mecze):
  st.header("🏆 Tabela Ligi / Klasyfikacja Generalna")

  wszystkie_typy = database.pobierz_wszystkie_typy()
  lista_graczy = database.pobierz_liste_graczy()

  slownik_meczow = {m["id"]: m for m in wszystkie_mecze}

  statystyki_graczy = {
      gracz: {
          "Punkty": 0,
          "Trafienia (3 pkt)": 0,
          "Rozstrzygnięcia (1 pkt)": 0,
          "Liczba typów": 0,
      }
      for gracz in lista_graczy
  }

  for typ in wszystkie_typy:
    gracz = typ.get("gracz_nick")
    mecz_id = typ.get("mecz_id")
    typ_h = typ.get("typ_gospodarze")
    typ_a = typ.get("typ_goscie")

    mecz = slownik_meczow.get(mecz_id)

    if mecz and gracz in statystyki_graczy:
      wynik_str = mecz.get("wynik")
      status = str(mecz.get("status")).lower()

      if status in [
          "ended",
          "finished",
          "ft",
          "full time",
          "after et",
      ] or (wynik_str and ":" in str(wynik_str) and wynik_str != "- : -"):
        real_h = mecz.get("gole_gospodarze", 0)
        real_a = mecz.get("gole_goscie", 0)

        pts = utils.oblicz_punkty_za_mecz(typ_h, typ_a, real_h, real_a)

        statystyki_graczy[gracz]["Punkty"] += pts
        statystyki_graczy[gracz]["Liczba typów"] += 1
        if pts == 3:
          statystyki_graczy[gracz]["Trafienia (3 pkt)"] += 1
        elif pts == 1:
          statystyki_graczy[gracz]["Rozstrzygnięcia (1 pkt)"] += 1

  tabela_data = []
  for gracz, stats in statystyki_graczy.items():
    tabela_data.append({
        "Gracz": gracz,
        "Punkty": stats["Punkty"],
        "🎯 Trafienia (3 pkt)": stats["Trafienia (3 pkt)"],
        "👍 Rozstrzygnięcia (1 pkt)": stats["Rozstrzygnięcia (1 pkt)"],
        "📊 Obstawione mecze": stats["Liczba typów"],
    })

  df = pd.DataFrame(tabela_data)

  if not df.empty:
    df = df.sort_values(
        by=[
            "Punkty",
            "🎯 Trafienia (3 pkt)",
            "👍 Rozstrzygnięcia (1 pkt)",
        ],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    pozycje = []
    for idx in range(len(df)):
      if idx == 0:
        pozycje.append("🥇 1")
      elif idx == 1:
        pozycje.append("🥈 2")
      elif idx == 2:
        pozycje.append("🥉 3")
      else:
        pozycje.append(f"  {idx + 1}")

    df.insert(0, "Pozycja", pozycje)

    st.dataframe(df, use_container_width=True, hide_index=True)
  else:
    st.info("Brak danych do wyświetlenia w tabeli.")
