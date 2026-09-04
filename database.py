import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from supabase import create_client

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
db = create_client(url, key)


def haszuj_pin(pin: str) -> str:
  return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def pobierz_liste_graczy():
  res = db.table("gracze").select("nick").order("nick").execute()
  return [row["nick"] for row in res.data]


def pobierz_informacje_o_graczach():
  res = db.table("gracze").select("nick, ulubiony_klub").execute()
  return {
      g["nick"]: {"ulubiony_klub": g.get("ulubiony_klub", "")} for g in res.data
  }


def pobierz_mapa_klubow_logo(wszystkie_mecze):
  mapa = {}
  for m in wszystkie_mecze:
    if m.get("gospodarze") and m.get("logo_gospodarze"):
      mapa[m["gospodarze"]] = m["logo_gospodarze"]
    if m.get("goscie") and m.get("logo_goscie"):
      mapa[m["goscie"]] = m["logo_goscie"]
  return mapa


def zarejestruj_gracza(nick, pin, ulubiony_klub=""):
  nick = nick.strip()
  if not nick or not pin:
    return False, "Nick i PIN nie mogą być puste!"

  res = db.table("gracze").select("*").eq("nick", nick).execute()
  if res.data:
    return False, "Gracz o takim nicku już istnieje!"

  pin_hash = haszuj_pin(pin)
  db.table("gracze").insert({
      "nick": nick,
      "pin_hash": pin_hash,
      "ulubiony_klub": ulubiony_klub,
  }).execute()
  return True, "Zarejestrowano pomyślnie!"


def weryfikuj_pin_gracza(nick, pin):
  res = db.table("gracze").select("pin_hash").eq("nick", nick).execute()
  if res.data:
    zapisany_hash = res.data[0].get("pin_hash")
    return zapisany_hash == haszuj_pin(pin)
  return False


def zmien_nick_gracza(stary_nick, nowy_nick):
  nowy_nick = nowy_nick.strip()
  if not nowy_nick:
    return False, "Nick nie może być pusty!"

  res = db.table("gracze").select("*").eq("nick", nowy_nick).execute()
  if res.data:
    return False, "Podany nick jest już zajęty!"

  db.table("gracze").update({"nick": nowy_nick}).eq(
      "nick", stary_nick
  ).execute()
  db.table("typy").update({"gracz_nick": nowy_nick}).eq(
      "gracz_nick", stary_nick
  ).execute()
  return True, "Nick został zmieniony!"


def zmien_ulubiony_klub(nick, nowy_klub):
  db.table("gracze").update({"ulubiony_klub": nowy_klub}).eq(
      "nick", nick
  ).execute()
  return True, "Ulubiony klub zaktualizowany!"


def zmien_pin_gracza(nick, nowy_pin):
  nowy_hash = haszuj_pin(nowy_pin)
  db.table("gracze").update({"pin_hash": nowy_hash}).eq("nick", nick).execute()
  return True, "PIN zmieniony pomyślnie!"


def pobierz_typy_gracza(nick):
  if not nick:
    return {}
  res = (
      db.table("typy")
      .select("*")
      .eq("gracz_nick", nick)
      .limit(1000)
      .execute()
  )
  return {
      row["mecz_id"]: (row["typ_gospodarze"], row["typ_goscie"])
      for row in res.data
  }


def pobierz_wszystkie_typy():
  # POPRAWKA: Zwiększenie limitu z domyślnego 1000 do 10000
  res = db.table("typy").select("*").limit(10000).execute()
  return res.data


def zapisz_typy_gracza(lista_typow):
  if not lista_typow:
    return True

  rekordy = []
  for t in lista_typow:
    rekordy.append({
        "gracz_nick": str(t["gracz_nick"]),
        "mecz_id": int(t["mecz_id"]),
        "typ_gospodarze": int(t["typ_gospodarze"]),
        "typ_goscie": int(t["typ_goscie"]),
    })

  try:
    # Bezpieczne zapisywanie (upsert) bez błędu unikalności
    db.table("typy").upsert(rekordy).execute()
    return True
  except Exception as e:
    st.error(f"Błąd zapisu typów: {str(e)}")
    return False


def synchronizuj_mecze_wsadowo(surowe_mecze):
  if not surowe_mecze:
    st.sidebar.error("⚠️ API zwróciło pustą listę meczów!")
    return False

  rekordy = []
  for m in surowe_mecze:
    mecz_id = m.get("id")
    if not mecz_id:
      continue

    mecz_id_int = int(mecz_id)

    home_team = m.get("homeTeam", {})
    away_team = m.get("awayTeam", {})

    state_obj = m.get("state", {})
    status_desc = str(state_obj.get("description", "Not started"))

    score_obj = (
        state_obj.get("score", {}) if isinstance(state_obj, dict) else {}
    )
    score_current = (
        score_obj.get("current") if isinstance(score_obj, dict) else None
    )

    gole_h_int = None
    gole_a_int = None

    if score_current and "-" in str(score_current):
      parts = str(score_current).split("-")
      try:
        gole_h_int = int(parts[0].strip())
        gole_a_int = int(parts[1].strip())
      except (ValueError, TypeError):
        gole_h_int = None
        gole_a_int = None

    status_lower = status_desc.lower()
    if any(
        s in status_lower
        for s in ["postponed", "cancelled", "delayed", "postp"]
    ):
      status = "PPD"
    elif any(s in status_lower for s in ["finished", "ended", "awarded"]):
      status = "FT"
    elif any(
        s in status_lower
        for s in ["half", "progress", "extra", "penalties", "break"]
    ):
      status = "LIVE"
    else:
      status = "NS"

    kolejka = str(m.get("round", "Kolejka 1"))
    data_meczu = str(m.get("date", ""))

    if status == "PPD":
      wynik_str = "Przełożony"
    else:
      wynik_str = (
          f"{gole_h_int} : {gole_a_int}"
          if gole_h_int is not None and gole_a_int is not None
          else "- : -"
      )

    rekordy.append({
        "id": mecz_id_int,
        "kolejka": kolejka,
        "data_meczu": data_meczu,
        "gospodarze": str(home_team.get("name", "Gospodarz")),
        "goscie": str(away_team.get("name", "Gość")),
        "logo_gospodarze": str(home_team.get("logo", "")),
        "logo_goscie": str(away_team.get("logo", "")),
        "gole_gospodarze": gole_h_int,
        "gole_goscie": gole_a_int,
        "status": status,
        "wynik": wynik_str,
    })

  if not rekordy:
    st.sidebar.error("⚠️ Parsowanie danych nie powiodło się.")
    return False

  try:
    db.table("mecze").upsert(rekordy).execute()

    try:
      teraz_warszawa = datetime.now(ZoneInfo("Europe/Warsaw")).strftime(
          "%d.%m.%Y %H:%M:%S"
      )
      db.table("ustawienia").upsert(
          {"klucz": "ostatnia_synchro", "wartosc": teraz_warszawa}
      ).execute()
    except Exception:
      pass

    return True

  except Exception as e:
    st.sidebar.error(f"❌ NIEZNANY BŁĄD BAZY: {str(e)}")
    return False


def pobierz_czas_synchro():
  try:
    res = (
        db.table("ustawienia")
        .select("wartosc")
        .eq("klucz", "ostatnia_synchro")
        .execute()
    )
    if res.data:
      return res.data[0]["wartosc"]
    return "Brak danych"
  except Exception:
    return "Brak danych"


def pobierz_status_wplat():
  try:
    res = db.table("gracze").select("nick, wplacono").order("nick").execute()
    return {row["nick"]: bool(row.get("wplacono", False)) for row in res.data}
  except Exception:
    return {}


def zapisz_status_wplat(mapa_wplat):
  try:
    for nick, stan in mapa_wplat.items():
      db.table("gracze").update({"wplacono": stan}).eq("nick", nick).execute()
    return True
  except Exception:
    return False
