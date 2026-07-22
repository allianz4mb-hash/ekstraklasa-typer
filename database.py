import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from supabase import create_client

db = None


def init_supabase():
  global db
  if db is None:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    db = create_client(url, key)
  return db


# Inicjalizujemy bazę przy starcie modułu
init_supabase()


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
    zapisany_hash = res.data[0]["pin_hash"]
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
  rekordy = []
  for m in surowe_mecze:
    data_iso = m.get("fixture", {}).get("date", "")
    kolejka_str = m.get("league", {}).get("round", "Kolejka 1")

    rekordy.append({
        "id": m["fixture"]["id"],
        "kolejka": kolejka_str,
        "data_meczu": data_iso,
        "gospodarze": m["teams"]["home"]["name"],
        "goscie": m["teams"]["away"]["name"],
        "logo_gospodarze": m["teams"]["home"]["logo"],
        "logo_goscie": m["teams"]["away"]["logo"],
        "gole_gospodarze": m["goals"]["home"],
        "gole_goscie": m["goals"]["away"],
        "status": m["fixture"]["status"]["short"],
        "wynik": (
            f"{m['goals']['home']} : {m['goals']['away']}"
            if m["goals"]["home"] is not None
            else "- : -"
        ),
    })

  db.table("mecze").upsert(rekordy, on_conflict="id").execute()

  teraz_warszawa = datetime.now(ZoneInfo("Europe/Warsaw")).strftime(
      "%d.%m.%Y %H:%M:%S"
  )
  db.table("ustawienia").upsert(
      {"klucz": "ostatnia_synchro", "wartosc": teraz_warszawa},
      on_conflict="klucz",
  ).execute()
  return True


def pobierz_czas_synchro():
  res = (
      db.table("ustawienia")
      .select("wartosc")
      .eq("klucz", "ostatnia_synchro")
      .execute()
  )
  if res.data:
    return res.data[0]["wartosc"]
  return "Brak danych"
