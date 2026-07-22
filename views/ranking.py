import database
import pandas as pd
import streamlit as st


def oblicz_punkty_za_mecz(
    typ_h, typ_a, wynik_h, wynik_a, status_meczu
) -> tuple[int, bool]:
  """Zwraca (liczba_punktów, czy_dokładny_wynik)."""
  # Jeśli mecz nie ma rozstrzygniętego wyniku, nie przyznajemy punktów
  if wynik_h is None or wynik_a is None:
    return 0, False

  try:
    typ_h, typ_a = int(typ_h), int(typ_a)
    wynik_h, wynik_a = int(wynik_h), int(wynik_a)
  except (ValueError, TypeError):
    return 0, False

  # 1. Dokładny wynik (3 pkt)
  if typ_h == wynik_h and typ_a == wynik_a:
    return 3, True

  # 2. Poprawne rozstrzygnięcie - 1X2 (1 pkt)
  roznica_typ = typ_h - typ_a
  roznica_wynik = wynik_h - wynik_a

  if (
      (roznica_typ > 0 and roznica_wynik > 0)
      or (roznica_typ < 0 and roznica_wynik < 0)
      or (roznica_typ == 0 and roznica_wynik == 0)
  ):
    return 1, False

  return 0, False


def render_ranking(wszystkie_mecze):
  st.header("🏆 Tabela i Klasyfikacja Generalna")

  gracze = database.pobierz_liste_graczy()
  wszystkie_typy = database.pobierz_wszystkie_typy()

  if not gracze:
    st.info("Brak zarejestrowanych graczy w bazie.")
    return

  # Mapa meczów dla szybkiego dostępu do wyników
  mapa_meczow = {m["id"]: m for m in wszystkie_mecze}

  # Inicjalizacja statystyk dla każdego gracza
  statystyki = {
      g: {
          "Gracz": g,
          "Punkty": 0,
          "Dokładne wyniki (3pkt)": 0,
          "Trafione 1X2 (1pkt)": 0,
          "Frekwencja (Liczba typów)": 0,
      }
      for g in gracze
  }

  # Zliczanie punktów
  for t in wszystkie_typy:
    nick = t.get("gracz_nick")
    mecz_id = t.get("mecz_id")

    if nick in statystyki and mecz_id in mapa_meczow:
      mecz = mapa_meczow[mecz_id]
      status = mecz.get("status", "")

      # Uwzględniamy tylko mecze zakończone lub mające wpisany wynik
      gole_h = mecz.get("gole_gospodarze")
      gole_a = mecz.get("gole_goscie")
      wynik_str = mecz.get("wynik", "")

      # Jeśli wynik jest dostępny
      if wynik_str and wynik_str != "- : -":
        pts, dokladny = oblicz_punkty_za_mecz(
            t.get("typ_gospodarze"),
            t.get("typ_goscie"),
            gole_h,
            gole_a,
            status,
        )

        statystyki[nick]["Punkty"] += pts
        statystyki[nick]["Frekwencja (Liczba typów)"] += 1

        if pts == 3:
          statystyki[nick]["Dokładne wyniki (3pkt)"] += 1
        elif pts == 1:
          statystyki[nick]["Trafione 1X2 (1pkt)"] += 1

  # Konwersja do DataFrame
  df = pd.DataFrame(list(statystyki.values()))

  # AUTOMATYCZNE SORTOWANIE ZGODNIE Z REGULAMINEM:
  # 1. Punkty (malejąco)
  # 2. Dokładne wyniki (malejąco)
  # 3. Frekwencja (malejąco)
  df = df.sort_values(
      by=["Punkty", "Dokładne wyniki (3pkt)", "Frekwencja (Liczba typów)"],
      ascending=[False, False, False],
  ).reset_index(drop=True)

  # Dodanie kolumny z miejscem
  df.index = df.index + 1
  df.index.name = "Miejsce"

  # Wyświetlenie tabeli
  st.dataframe(
      df,
      use_container_width=True,
      column_config={
          "Punkty": st.column_config.NumberColumn(
              "🏆 Punkty", help="Łączna liczba punktów"
          ),
          "Dokładne wyniki (3pkt)": st.column_config.NumberColumn(
              "🎯 Dokładne (3pkt)"
          ),
          "Trafione 1X2 (1pkt)": st.column_config.NumberColumn(
              "👍 Trafione (1pkt)"
          ),
          "Frekwencja (Liczba typów)": st.column_config.NumberColumn(
              "📊 Oddane typy"
          ),
      },
  )
