import database
import pandas as pd
import streamlit as st
import utils


def formatuj_nazwe_kolejki(kolejka_raw):
  """Zamienia np. 'Regular Season - 1' na '1. Kolejka PKO BP Ekstraklasy'"""
  num = utils.wyciagnij_numer_kolejki(kolejka_raw)
  return f"{num}. Kolejka PKO BP Ekstraklasy"


def render_matryca(wszystkie_mecze, zalogowany_gracz):
  st.header("👁️ Podgląd Typów Rywali / Matryca Kolejki")

  if not wszystkie_mecze:
    st.info("Brak meczów w bazie.")
    return

  kolejki_raw = sorted(
      list(set(m["kolejka"] for m in wszystkie_mecze)),
      key=utils.wyciagnij_numer_kolejki,
  )

  kolejki_mapa = {k: formatuj_nazwe_kolejki(k) for k in kolejki_raw}

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

  # SŁOWNIK DO ZLICZANIA PUNKTÓW DANEJ KOLEJKI
  punkty_graczy_kolejka = {gracz: 0 for gracz in lista_graczy}
  rozegrane_mecze_w_kolejce = 0

  tabela_rows = []

  for mecz in mecze_w_kolejce:
    mecz_id = mecz["id"]
    mecz_nazwa = f"{mecz['gospodarze']} - {mecz['goscie']}"
    status_meczu = str(mecz.get("status", "")).upper()

    mecz_przelozony = status_meczu == "PPD"
    mecz_zakonczony = status_meczu == "FT"

    if mecz_zakonczony:
      rozegrane_mecze_w_kolejce += 1

    if mecz_przelozony:
      wynik_real = "Przełożony"
    else:
      wynik_real = mecz.get("wynik") or "- : -"

    gole_h = mecz.get("gole_gospodarze")
    gole_a = mecz.get("gole_goscie")

    if (gole_h is None or gole_a is None) and ":" in str(wynik_real):
      parts = str(wynik_real).split(":")
      try:
        gole_h = int(parts[0].strip())
        gole_a = int(parts[1].strip())
      except Exception:
        pass

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
        typ_str = f"{typ[0]} - {typ[1]}"

        if mecz_zakonczony and gole_h is not None and gole_a is not None:
          pts = utils.oblicz_punkty_za_mecz(typ[0], typ[1], gole_h, gole_a)
          punkty_graczy_kolejka[gracz] += pts
          if pts == 3:
            typ_str += " 🎯"
          elif pts == 1:
            typ_str += " ✅"
          else:
            typ_str += " ❌"

        if zablokowany or gracz == zalogowany_gracz:
          row[gracz] = typ_str
        else:
          row[gracz] = "🔒 Ukryty"

    tabela_rows.append(row)

  # WYŁANIANIE TURBOKOZAKA KOLEJKI
  if rozegrane_mecze_w_kolejce > 0 and punkty_graczy_kolejka:
    max_pkt = max(punkty_graczy_kolejka.values())
    if max_pkt > 0:
      liderzy = [
          g for g, pkt in punkty_graczy_kolejka.items() if pkt == max_pkt
      ]
      liderzy_str = ", ".join(liderzy)

      tytuł_sekcji = (
          "⚡ TURBOKOZACY KOLEJKI ⚡"
          if len(liderzy) > 1
          else "⚡ TURBOKOZAK KOLEJKI ⚡"
      )

      st.markdown(
          f"""
            <div style="background: linear-gradient(135deg, #1f1c2c, #928dab); padding: 15px; border-radius: 12px; text-align: center; color: white; margin-bottom: 20px; border: 1px solid #ffd700;">
                <h3 style="margin: 0; color: #ffd700; font-size: 1.2rem;">{tytuł_sekcji}</h3>
                <h2 style="margin: 5px 0; font-size: 1.8rem; color: #ffffff;">👑 {liderzy_str}</h2>
                <p style="margin: 0; font-size: 1.1rem; color: #e0e0e0;">Zdobyty wynik: <b>{max_pkt} pkt</b></p>
            </div>
            """,
          unsafe_allow_html=True,
      )

  st.caption(
      "💡 *Typy rywali odsłaniają się po rozpoczęciu meczu.* <br>"
      " *Oznaczenia po zakończeniu: 🎯 Dokładny wynik (3 pkt) | ✅ Trafiony"
      " zwycięzca/remis (1 pkt) | ❌ Pudło (0 pkt)*",
      unsafe_allow_html=True,
  )

  # ZMIANA NAGŁÓWKÓW KOLUMN — DODAJEMY PUNKTY DO IMION GRACZY
  mapa_zmiany_kolumn = {
      gracz: f"{gracz} ({punkty_graczy_kolejka[gracz]} pkt)"
      for gracz in lista_graczy
  }

  df_matryca = pd.DataFrame(tabela_rows)

  if not df_matryca.empty:
    df_matryca = df_matryca.rename(columns=mapa_zmiany_kolumn)
    st.dataframe(df_matryca, use_container_width=True, hide_index=True)
  else:
    st.info("Brak typów dla tej kolejki.")
