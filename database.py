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
  res = db.table("typy").select("*").eq("gracz_nick", nick).execute()
  return {
      row["mecz_id"]: (row["typ_gospodarze"], row["typ_goscie"])
      for row in res.data
  }


def pobierz_wszystkie_typy():
  res = db.table("typy").select("*").execute()
  return res.data


def zapisz_typy_gracza(lista_typow):
  if not lista_typow:
    return True
  db.table("typy").upsert(lista_typow, on_conflict="gracz_nick,mecz_id").execute()
  return True


def synchronizuj_mecze_wsadowo(surowe_mecze):
  if not surowe_mecze:
    return False

  rekordy = []
  for m in surowe_mecze:
    fixture = m.get("fixture", {})
    if not fixture or "id" not in fixture:
      continue

    league = m.get("league", {})
    teams = m.get("teams", {})
    goals = m.get("goals", {})

    home_team = teams.get("home", {})
    away_team = teams.get("away", {})
    status_fixture = fixture.get("status", {})

    gole_h = goals.get("home")
    gole_a = goals.get("away")

    rekordy.append({
        "id": fixture.get("id"),
        "kolejka": league.get("round", "Kolejka 1"),
        "data_meczu": fixture.get("date", ""),
        "gospodarze": home_team.get("name", "Gospodarz"),
        "goscie": away_team.get("name", "Gość"),
        "logo_gospodarze": home_team.get("logo", ""),
        "logo_goscie": away_team.get("logo", ""),
        "gole_gospodarze": gole_h,
        "gole_goscie": gole_a,
        "status": status_fixture.get("short", "NS"),
        "wynik": (f"{gole_h} : {gole_a}" if gole_h is not None else "- : -"),
    })

  if rekordy:
    try:
      db.table("mecze").upsert(rekordy, on_conflict="id").execute()

      teraz_warszawa = datetime.now(ZoneInfo("Europe/Warsaw")).strftime(
          "%d.%m.%Y %H:%M:%S"
      )
      db.table("ustawienia").upsert(
          {"klucz": "ostatnia_synchro", "wartosc": teraz_warszawa},
          on_conflict="klucz",
      ).execute()
      return True
    except Exception as e:
      st.error(f"⚠️ SZCZEGÓŁY BŁĘDU BAZY: {str(e)}")
      raise e

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
