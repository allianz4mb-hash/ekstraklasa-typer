from datetime import datetime
import re
from zoneinfo import ZoneInfo
import database
import pandas as pd
import streamlit as st


def wyciągnij_numer_kolejki(kolejka_raw):
  if not kolejka_raw:
    return 1
  cyfry = re.findall(r"\d+", str(kolejka_raw))
  return int(cyfry[0]) if cyfry else 1


def wyznacz_aktualna_kolejke(wszystkie_mecze):
  """Kolejka, której nierozegrane mecze są NAJBLIŻSZE obecnej dacie."""
  if not wszystkie_mecze:
    return "1"

  teraz = datetime.now(ZoneInfo("Europe/Warsaw"))
  kolejki_przyszle = {}

  for m in wszystkie_mecze:
    status = str(m.get("status", "")).upper()
    if status in ["FT", "PPD"]:
      continue

    data_str = m.get("data_meczu", "")
    dt = None
    if data_str:
      try:
        val_str = str(data_str)
        if val_str.endswith("Z"):
          val_str = val_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(val_str).astimezone(
            ZoneInfo("Europe/Warsaw")
        )
      except Exception:
        dt = None

    if dt and dt >= teraz:
      nr = wyciągnij_numer_kolejki(m.get("kolejka"))
      if nr not in kolejki_przyszle:
        kolejki_przyszle[nr] = []
      kolejki_przyszle[nr].append(dt)

  if kolejki_przyszle:
    najblizszy_nr = min(
        kolejki_przyszle.keys(), key=lambda k: min(kolejki_przyszle[k])
    )
    return str(najblizszy_nr)

  wszystkie_nry = [
      wyciągnij_numer_kolejki(m.get("kolejka")) for m in wszystkie_mecze
  ]
  return str(max(wszystkie_nry)) if wszystkie_nry else "1"


def oblicz_punkty_za_mecz(typ_h, typ_a, wynik_h, wynik_a):
  if (
      typ_h is None
      or typ_a is None
      or wynik_h is None
      or wynik_a is None
  ):
    return 0

  try:
    typ_h, typ_a = int(typ_h), int(typ_a)
    wynik_h, wynik_a = int(wynik_h), int(wynik_a)
  except (ValueError, TypeError):
    return 0

  # 1. Dokładny wynik -> 3 pkt
  if typ_h == wynik_h and typ_a == wynik_a:
    return 3

  # 2. Trafione rozstrzygnięcie (1X2) -> 1 pkt
  roznica_typ = typ_h - typ_a
  roznica_wynik = wynik_h - wynik_a

  if (
      (roznica_typ > 0 and roznica_wynik > 0)
      or (roznica_typ < 0 and roznica_wynik < 0)
      or (roznica_typ == 0 and roznica_wynik == 0)
  ):
    return 1

  return 0


def render_ranking(wszystkie_mecze):
  gracze = database.pobierz_liste_graczy()
  wszystkie_typy = database.pobierz_wszystkie_typy()
  info_gracze = database.pobierz_informacje_o_graczach()
  kluby_mapa = database.pobierz_mapa_klubow_logo(wszystkie_mecze)

  if not gracze:
    st.info("Brak zarejestrowanych graczy w bazie.")
    return

  mapa_meczow = {m["id"]: m for m in wszystkie_mecze}
  aktualna_kolejka_nr = wyznacz_aktualna_kolejke(wszystkie_mecze)

  statystyki = {
      g: {
          "Gracz": g,
          "Punkty": 0,
          "Dokładne": 0,
          "Trafione": 0,
          "Mecze": 0,
          "Klub": info_gracze.get(g, {}).get("ulubiony_klub", ""),
      }
      for g in gracze
  }

  for t in wszystkie_typy:
    nick = t.get("gracz_nick")
    mecz_id = t.get("mecz_id")

    if nick not in statystyki:
      continue

    if mecz_id in mapa_meczow:
      mecz = mapa_meczow[mecz_id]

      status_meczu = str(mecz.get("status", "")).upper()
      if status_meczu != "FT":
        continue

      gole_h = mecz.get("gole_gospodarze")
      gole_a = mecz.get("gole_goscie")
      wynik_str = str(mecz.get("wynik", ""))

      if (gole_h is None or gole_a is None) and ":" in wynik_str:
        parts = wynik_str.split(":")
        try:
          gole_h = int(parts[0].strip())
          gole_a = int(parts[1].strip())
        except Exception:
          pass

      if gole_h is not None and gole_a is not None:
        pts = oblicz_punkty_za_mecz(
            t.get("typ_gospodarze"),
            t.get("typ_goscie"),
            gole_h,
            gole_a,
        )

        statystyki[nick]["Mecze"] += 1
        statystyki[nick]["Punkty"] += pts

        if pts == 3:
          statystyki[nick]["Dokładne"] += 1
        elif pts == 1:
          statystyki[nick]["Trafione"] += 1

  df = pd.DataFrame(list(statystyki.values()))
  df = df.sort_values(
      by=["Punkty", "Dokładne", "Mecze"], ascending=[False, False, False]
  ).reset_index(drop=True)

  l_graczy = len(df)

  css_style = """<style>
.ekstraklasa-container {
    font-family: 'Montserrat', 'Arial Black', sans-serif;
    max-width: 900px;
    margin: 0 auto;
    background-color: #0b0e14;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.tv-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #06090e;
    padding: 12px 18px;
    border-radius: 8px;
    margin-bottom: 12px;
    border-bottom: 2px solid #00f2ff;
}
.tv-logo-title {
    color: #ffffff;
    font-size: 16px;
    font-weight: 900;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.tv-logo-sub {
    color: #8f9bba;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}
.tv-round-badge {
    background: linear-gradient(135deg, #0052cc 0%, #00f2ff 100%);
    color: #ffffff;
    padding: 6px 14px;
    border-radius: 6px;
    font-weight: 900;
    font-size: 14px;
    letter-spacing: 1px;
    text-transform: uppercase;
    box-shadow: 0 2px 8px rgba(0,242,255,0.3);
}
.ekstraklasa-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 6px;
}
.ekstraklasa-header {
    color: #8f9bba;
    font-size: 11px;
    text-transform: uppercase;
    font-weight: 800;
    letter-spacing: 1px;
    padding: 8px 6px;
}
.ekstraklasa-row {
    height: 48px;
    font-size: 15px;
    font-weight: 800;
    text-transform: uppercase;
}
.pos-lider {
    background: linear-gradient(90deg, #00f2ff 0%, #15c5cf 100%);
    color: #05131a;
}
.pos-podium {
    background: linear-gradient(90deg, #bcbebe 0%, #a2a4a4 100%);
    color: #111;
}
.pos-srodek {
    background: #1b2028;
    color: #ffffff;
}
.pos-spadek {
    background: linear-gradient(90deg, #d32f2f 0%, #9a0007 100%);
    color: #ffffff;
}
.cell-pos {
    width: 35px;
    text-align: center;
    font-size: 16px;
    font-weight: 900;
    border-top-left-radius: 6px;
    border-bottom-left-radius: 6px;
}
.cell-logo {
    width: 35px;
    text-align: center;
}
.cell-logo img {
    width: 26px;
    height: 26px;
    object-fit: contain;
    vertical-align: middle;
}
.cell-nick {
    text-align: left;
    padding-left: 8px;
    letter-spacing: 0.5px;
}
.cell-pts {
    text-align: center;
    width: 65px;
    font-size: 18px;
    font-weight: 900;
}
.cell-stat {
    text-align: center;
    width: 55px;
    font-size: 13px;
    opacity: 0.85;
}
.cell-stat-last {
    text-align: center;
    width: 55px;
    font-size: 13px;
    opacity: 0.85;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}
</style>"""

  tv_header_html = (
      f'<div class="tv-header"><div><div class="tv-logo-sub">PKO BANK'
      ' POLSKI</div><div class="tv-logo-title">⚽'
      f' EKSTRAKLAPA</div></div><div class="tv-round-badge">{aktualna_kolejka_nr}.'
      ' KOLEJKA</div></div>'
  )

  html_rows = []
  for idx, row in df.iterrows():
    miejsce = idx + 1
    nick = row["Gracz"]
    klub = row["Klub"]
    pts = row["Punkty"]
    dok = row["Dokładne"]
    traf = row["Trafione"]
    mcz = row["Mecze"]

    logo_url = kluby_mapa.get(klub, "")
    if logo_url:
      logo_img = f'<img src="{logo_url}" title="{klub}">'
    else:
      logo_img = '<span style="opacity:0.3;">⚽</span>'

    if miejsce == 1:
      klasa_pos = "pos-lider"
    elif miejsce in [2, 3]:
      klasa_pos = "pos-podium"
    elif l_graczy >= 4 and miejsce > (l_graczy - 2):
      klasa_pos = "pos-spadek"
    else:
      klasa_pos = "pos-srodek"

    row_html = (
        f'<tr class="ekstraklasa-row {klasa_pos}"><td'
        f' class="cell-pos">{miejsce}</td><td'
        f' class="cell-logo">{logo_img}</td><td'
        f' class="cell-nick">{nick}</td><td class="cell-pts">{pts}</td><td'
        f' class="cell-stat">{dok}</td><td class="cell-stat">{traf}</td><td'
        f' class="cell-stat-last">{mcz}</td></tr>'
    )
    html_rows.append(row_html)

  rows_combined = "".join(html_rows)

  full_html = (
      f"{css_style}<div"
      f' class="ekstraklasa-container">{tv_header_html}<table'
      ' class="ekstraklasa-table"><thead><tr><th class="ekstraklasa-header"'
      ' style="text-align:center;">#</th><th class="ekstraklasa-header"'
      ' style="text-align:center;">KLUB</th><th class="ekstraklasa-header"'
      ' style="text-align:left; padding-left:8px;">GRACZ</th><th'
      ' class="ekstraklasa-header" style="text-align:center;">PKT</th><th'
      ' class="ekstraklasa-header" style="text-align:center;">3PKT</th><th'
      ' class="ekstraklasa-header" style="text-align:center;">1PKT</th><th'
      ' class="ekstraklasa-header"'
      f' style="text-align:center;">MECZE</th></tr></thead><tbody>{rows_combined}</tbody></table></div>'
  )

  st.markdown(full_html, unsafe_allow_html=True)
