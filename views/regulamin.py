import streamlit as st


def render_regulamin():
  st.header("📜 Regulamin i Zasady Typera")
  st.markdown("---")

  st.markdown("""
    ### ⚽ 1. Zasady Punktacji
    Za każdy wytypowany mecz przyznawane są punkty według poniższego klucza:
    * **3 pkt** — **Dokładny wynik** (np. twój typ *2:1*, wynik meczu *2:1*)
    * **1 pkt** — **Poprawne rozstrzygnięcie** (np. twój typ *1:0*, wynik meczu *3:1* — trafiłeś zwycięzcę, ale nie dokładny wynik; lub trafiłeś remis *1:1*, a padł remis *2:2*)
    * **0 pkt** — **Brak trafienia** (np. twój typ *2:0*, wynik meczu *0:1*)

    ---

    ### ⏱️ 2. Czas na składanie typów
    * Typy można wpisywać oraz modyfikować **do momentu rozpoczęcia danego meczu**.
    * Wraz z pierwszym gwizdkiem arbitra opcja edycji typów dla danego spotkania wygasa.

    ---

    ### 🏆 3. Klasyfikacja i Rozstrzygnięcia
    * O pozycji w tabeli decyduje łączna liczba zdobytych punktów.
    * W przypadku równej liczby punktów decyduje:
      1. Większa liczba dokładnie trafionych wyników (za 3 pkt).
      2. Wyższa frekwencja typowania.

    ---

    ### 💰 4. Wpisowe i Nagrody (Runda Jesienna)
    * Składka wpisowa wynosi **100 zł** od uczestnika.
    
    * 💳 **Szybka płatność Revolut:**
      * Link: [Prześlij przez Revolut](https://revolut.me/mateusfpzf)

    * 🏛️ **Tradycyjny przelew bankowy:**
      * **Odbiorca:** Mateusz Bielecki
      * **Numer konta:** `20 2910 0006 0000 0000 0268 4494`
      * **Bank:** UniCredit NV/SA Oddział w Polsce, Dobra 40, 00-344 Warszawa
    
    * ⚠️ **WAŻNE — Tytuł przelewu / wpłaty:**
      * W tytule przelewu podaj koniecznie swój **nick / nazwę konta z Typera** (np. `Składka Typer - Mateusz`), abym wiedział, od kogo wpłynęła wpłata!

    * **Podział puli nagród po rundzie jesiennej:**
      * **1. miejsce:** 60% zebranej kwoty 🥇
      * **2. miejsce:** 25% zebranej kwoty 🥈
      * **3. miejsce:** 15% zebranej kwoty 🥉
    
    * 💡 *Pamiętaj: wygrana ma charakter symboliczny, gramy przede wszystkim dla świetnej zabawy!*

    ---

    💡 *Masz pytania lub propozycję zmiany w regulaminie? Skontaktuj się z organizatorem!*
    """)
