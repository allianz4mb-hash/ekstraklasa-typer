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
  res = db.table("typy").select("gracz_nick, mecz_id").execute()
  istniejace = {(r["gracz_nick"], r["mecz_id"]) for r in res.data}

  do_dodania = []
  for t in lista_typow:
    if (t["gracz_nick"], t["mecz_id"]) in istniejace:
      db.table("typy").update({
          "typ_gospodarze": t["typ_gospodarze"],
          "typ_goscie": t["typ_goscie"],
      }).eq("gracz_nick", t["gracz_nick"]).eq("mecz_id", t["mecz_id"]).execute()
    else:
      do_dodania.append(t)

  if do_dodania:
    db.table("typy").insert(do_dodania).execute()
  return True


def synchronizuj_mecze_wsadowo(surowe_mecze):
  if not surowe_mecze:
    st.sidebar.error("⚠️ API zwróciło pustą listę meczów!")
    return False

  rekordy = []
  for m in surowe_mecze:
    mecz_id = m.get("id") or m.get("matchId")
    if not mecz_id:
      continue

    home_team = m.get("homeTeam", {})
    away_team = m.get("awayTeam", {})

    # Precyzyjne wyciąganie goli z Highlightly (obsługa różnych wariantów JSON)
    gole_h = m.get("homeScore")
    if gole_h is None:
      gole_h = home_team.get("score")
    if gole_h is None and isinstance(m.get("score"), dict):
      gole_h = m["score"].get("home")

    gole_a = m.get("awayScore")
    if gole_a is None:
      gole_a = away_team.get("score")
    if gole_a is None and isinstance(m.get("score"), dict):
      gole_a = m["score"].get("away")

    # Jeśli gole to słownik (np. current/fulltime)
    if isinstance(gole_h, dict):
      gole_h = gole_h.get("current", gole_h.get("fulltime", gole_h.get("display")))
    if isinstance(gole_a, dict):
      gole_a = gole_a.get("current", gole_a.get("fulltime", gole_a.get("display")))

    # Status meczu
    status_raw = m.get("status")
    if isinstance(status_raw, dict):
      status = str(status_raw.get("type") or status_raw.get("short") or status_raw.get("name") or "NS")
    else:
      status = str(status_raw or "NS")

    status_lower = status.lower()
    if any(s in status_lower for s in ["ft", "finished", "ended", "closed", "post"]):
      status = "FT"
    elif any(s in status_lower for s in ["ns", "not", "upcoming", "scheduled"]):
      status = "NS"
    else:
      status = "LIVE"  # w trakcie

    kolejka_raw = m.get("round")
    if isinstance(kolejka_raw, dict):
      kolejka_raw = kolejka_raw.get("round") or kolejka_raw.get("name")
    kolejka = str(kolejka_raw if kolejka_raw else "Kolejka 1")

    data_meczu = str(
        m.get("date") or m.get("startTimestamp") or m.get("startTime") or ""
    )

    try:
      gole_h_int = int(gole_h) if gole_h is not None else None
    except (TypeError, ValueError):
      gole_h_int = None

    try:
      gole_a_int = int(gole_a) if gole_a is not None else None
    except (TypeError, ValueError):
      gole_a_int = None

    wynik_str = (
        f"{gole_h_int} : {gole_a_int}"
        if gole_h_int is not None and gole_a_int is not None
        else "- : -"
    )

    rekordy.append({
        "id": int(mecz_id),
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
    res = db.table("mecze").select("id").execute()
    istniejace_id = [row["id"] for row in res.data] if res.data else []

    do_dodania = [r for r in rekordy if r["id"] not in istniejace_id]
    do_aktualizacji = [r for r in rekordy if r["id"] in istniejace_id]

    if do_dodania:
      db.table("mecze").insert(do_dodania).execute()

    for r in do_aktualizacji:
      db.table("mecze").update(r).eq("id", r["id"]).execute()

    try:
      teraz_warszawa = datetime.now(ZoneInfo("Europe/Warsaw")).strftime(
          "%d.%m.%Y %H:%M:%S"
      )
      ust_res = (
          db.table("ustawienia")
          .select("klucz")
          .eq("klucz", "ostatnia_synchro")
          .execute()
      )
      if ust_res.data:
        db.table("ustawienia").update({"wartosc": teraz_warszawa}).eq(
            "klucz", "ostatnia_synchro"
        ).execute()
      else:
        db.table("ustawienia").insert(
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
