import os
import streamlit as st
from supabase import Client, create_client

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")


@st.cache_resource
def init_supabase() -> Client:
  return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = init_supabase()


def pobierz_liste_graczy():
  """Pobiera listę nazwisk/nicków wszystkich graczy."""
  try:
    res = supabase.table("gracze").select("nick").execute()
    return [g["nick"] for g in res.data]
  except Exception as e:
    st.error(f"Błąd pobierania graczy: {e}")
    return []


def weryfikuj_pin_gracza(nick: str, wpisany_pin: str) -> bool:
  try:
    res = supabase.table("gracze").select("pin").eq("nick", nick).execute()
    if res.data:
      db_pin = str(res.data[0].get("pin", "") or "").strip()
      return db_pin == str(wpisany_pin).strip()
    return False
  except Exception as e:
    st.error(f"Błąd weryfikacji PIN-u: {e}")
    return False


def zarejestruj_gracza(nick: str, pin: str):
  nick_clean = str(nick).strip()
  pin_clean = str(pin).strip()

  if not nick_clean or not pin_clean:
    return False, "Nick i PIN nie mogą być puste!"

  try:
    res = (
        supabase.table("gracze")
        .select("nick")
        .eq("nick", nick_clean)
        .execute()
    )
    if res.data:
      return False, "Gracz o takim nicku już istnieje!"

    supabase.table("gracze").insert(
        {"nick": nick_clean, "pin": pin_clean}
    ).execute()
    return True, "Konto zostało pomyślnie utworzone!"
  except Exception as e:
    return False, f"Błąd tworzenia konta: {e}"


def synchronizuj_mecze_wsadowo(mecze_z_api):
  if not mecze_z_api:
    return False

  try:
    paczka_danych = []
    for mecz in mecze_z_api:
      match_id = mecz.get("id")
      round_name = mecz.get("round", "Kolejka")
      date = mecz.get("date")

      home_info = mecz.get("homeTeam", {})
      away_info = mecz.get("awayTeam", {})

      home_team = home_info.get("name")
      away_team = away_info.get("name")

      home_logo = (
          home_info.get("logo")
          or home_info.get("logoUrl")
          or home_info.get("image")
          or home_info.get("badge")
          or ""
      )
      away_logo = (
          away_info.get("logo")
          or away_info.get("logoUrl")
          or away_info.get("image")
          or away_info.get("badge")
          or ""
      )

      state_info = mecz.get("state", {})
      status = state_info.get("description", "Not started")
      score = state_info.get("score", {}).get("current") or "- : -"

      # Odczytujemy dokładną liczbę goli z wyniku API jeśli mecz minął/trwa
      gole_h = 0
      gole_a = 0
      if score and ":" in str(score) and str(score) != "- : -":
        try:
          parts = str(score).split(":")
          gole_h = int(parts[0].strip())
          gole_a = int(parts[1].strip())
        except ValueError:
          pass

      paczka_danych.append({
          "id": match_id,
          "kolejka": round_name,
          "data_meczu": date,
          "gospodarze": home_team,
          "goscie": away_team,
          "logo_gospodarze": home_logo,
          "logo_goscie": away_logo,
          "status": status,
          "gole_gospodarze": gole_h,
          "gole_goscie": gole_a,
          "wynik": score,
      })

    supabase.table("mecze").upsert(paczka_danych, on_conflict="id").execute()
    return True

  except Exception as e:
    st.error(f"Błąd synchronizacji wsadowej z bazą: {e}")
    return False


def pobierz_typy_gracza(gracz_nick: str):
  try:
    res = (
        supabase.table("typy")
        .select("*")
        .eq("gracz_nick", gracz_nick)
        .execute()
    )
    return {
        item["mecz_id"]: (item["typ_gospodarze"], item["typ_goscie"])
        for item in res.data
    }
  except Exception as e:
    st.error(f"Błąd pobierania typów: {e}")
    return {}


def pobierz_wszystkie_typy():
  """Pobiera wszystkie typy wszystkich graczy na potrzeby tabeli rankingowej."""
  try:
    res = supabase.table("typy").select("*").execute()
    return res.data
  except Exception as e:
    st.error(f"Błąd pobierania typów: {e}")
    return []


def zapisz_typy_gracza(paczka_typow):
  try:
    supabase.table("typy").upsert(
        paczka_typow, on_conflict="gracz_nick,mecz_id"
    ).execute()
    return True
  except Exception as e:
    st.error(f"Błąd zapisu typów: {e}")
    return False
