from datetime import datetime
import re
from zoneinfo import ZoneInfo


def pobierz_czas_pl(data_str):
  """Konwertuje ciąg ISO z API na obiekt datetime w czasie polskim."""
  if not data_str:
    return None
  try:
    val_str = str(data_str)
    if val_str.endswith("Z"):
      val_str = val_str[:-1] + "+00:00"

    dt_utc = datetime.fromisoformat(val_str)
    return dt_utc.astimezone(ZoneInfo("Europe/Warsaw"))
  except Exception:
    return None


def formatuj_date(data_str):
  """Formatuje datę na format polski (np. 📅 24.07.2026, godz. 19:00)."""
  dt_pl = pobierz_czas_pl(data_str)
  if dt_pl:
    return dt_pl.strftime("📅 %d.%m.%Y, godz. %H:%M")
  return f"📅 {data_str}"


def czy_mecz_zablokowany(data_str, status_meczu):
  """Sprawdza, czy typowanie meczu powinno być zamknięte."""
  status_clean = str(status_meczu).lower()
  if status_clean not in ["not started", "ns", "scheduled", ""]:
    return True

  dt_mecz_pl = pobierz_czas_pl(data_str)
  if dt_mecz_pl:
    teraz_pl = datetime.now(ZoneInfo("Europe/Warsaw"))
    if teraz_pl >= dt_mecz_pl:
      return True

  return False


def oblicz_punkty_za_mecz(typ_gosp, typ_gosc, real_gosp, real_gosc):
  """Silnik punktowy: 3 pkt za trafiony wynik, 1 pkt za rozstrzygnięcie, 0 pkt w pozostałych przyp."""
  if typ_gosp == real_gosp and typ_gosc == real_gosc:
    return 3

  diff_typ = typ_gosp - typ_gosc
  diff_real = real_gosp - real_gosc

  if (
      (diff_typ > 0 and diff_real > 0)
      or (diff_typ < 0 and diff_real < 0)
      or (diff_typ == 0 and diff_real == 0)
  ):
    return 1

  return 0


def wyciagnij_numer_kolejki(nazwa_kolejki):
  """Pobiera cyfrę numeru kolejki do poprawnego sortowania."""
  cyfry = re.findall(r"\d+", str(nazwa_kolejki))
  return int(cyfry[0]) if cyfry else 0


def wyznacz_aktualna_kolejke(wszystkie_mecze):
  """Wyznacza kolejkę, której nierozegrane mecze są NAJBLIŻSZE obecnej dacie."""
  if not wszystkie_mecze:
    return "1"

  teraz = datetime.now(ZoneInfo("Europe/Warsaw"))
  kolejki_przyszle = {}

  for m in wszystkie_mecze:
    status = str(m.get("status", "")).upper()
    if status in ["FT", "PPD"]:
      continue

    data_str = m.get("data_meczu", "")
    dt = pobierz_czas_pl(data_str) if data_str else None

    if dt and dt >= teraz:
      nr = wyciagnij_numer_kolejki(m.get("kolejka"))
      if nr not in kolejki_przyszle:
        kolejki_przyszle[nr] = []
      kolejki_przyszle[nr].append(dt)

  if kolejki_przyszle:
    najblizszy_nr = min(
        kolejki_przyszle.keys(), key=lambda k: min(kolejki_przyszle[k])
    )
    return str(najblizszy_nr)

  wszystkie_nry = [
      wyciagnij_numer_kolejki(m.get("kolejka")) for m in wszystkie_mecze
  ]
  return str(max(wszystkie_nry)) if wszystkie_nry else "1"
