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
    * Wraz ze pierwszym gwizdkiem arbitra opcja edycji typów dla danego spotkania wygasa.

    ---

    ### 🏆 3. Klasyfikacja i Rozstrzygnięcia
    * O pozycji w tabeli decyduje łączna liczba zdobytych punktów.
    * W przypadku równej liczby punktów decyduje:
      1. Większa liczba dokładnie trafionych wyników (za 3 pkt).
      2. Wyższa frekwencja typowania.

    ---

    ### 💰 4. Wpisowe i Nagrody (Runda Jesienna)
    * Każdy uczestnik zobowiązuje się przelać na wskazane konto kwotę **100 zł**.
    * Pula nagród po zakończeniu **rundy jesiennej** zostanie podzielona w następujący sposób:
      * **1. miejsce:** 60% zebranej kwoty
      * **2. miejsce:** 25% zebranej kwoty
      * **3. miejsce:** 15% zebranej kwoty
    * 💡 *Pamiętaj: wygrana ma charakter symboliczny, gramy przede wszystkim dla świetnej zabawy!*

    ---

    💡 *Masz pytania lub propozycję zmiany w regulaminie? Skontaktuj się z organizatorem!*
    """)
