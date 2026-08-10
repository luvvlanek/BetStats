# BetStats 1.0 Polska — Beta

BetStats to aplikacja do analizy meczów piłkarskich i siatkarskich. Łączy statystyki drużyn z modelem prawdopodobieństwa, pokazuje jakość danych oraz pozwala obserwować, jak predykcje wypadają po rozliczeniu.

## Najważniejsze moduły

- **Centrum modelu** — radar, progi selekcji, kalibracja i historia predykcji.
- **Społeczność** — lokalna tablica analiz z kategoriami: analiza, typ społeczności i dyskusja.
- **O projekcie** — opis źródeł danych, metodologii i zasad odpowiedzialnej gry.

## Uruchomienie

Projekt jest statyczny. Opublikuj zawartość folderu na hostingu obsługującym pliki statyczne albo uruchom lokalny serwer HTTP w tym folderze. Do działania części konta i synchronizacji potrzebna jest konfiguracja Supabase.

## O modelu

Model traktuje wynik jako niepewną estymację. Wskaźnik pewności nie jest szansą wygranej — opisuje jakość dostępnych danych i zgodność użytych sygnałów. Rzetelność należy oceniać na dużej liczbie predykcji zapisanych przed meczem.

## Następny etap dla wersji ogólnopolskiej

1. Dodać tabelę wpisów społeczności, komentarze i moderację po stronie Supabase.
2. Wprowadzić profile analityków z transparentną historią rozliczeń.
3. Rozdzielić dane wejściowe, model i interfejs do mniejszych modułów oraz objąć je testami.
4. Zbudować niezależny proces backtestów i publikować metodologię zmian modelu.


## Tryb Beta 1.0

- Rejestracja nowych kont jest tymczasowo wyłączona.
- Dostęp do aplikacji wymaga zalogowania.
- Rozgrywki europejskie (Liga Mistrzów, Liga Europy, Liga Konferencji) są oznaczone jako „Wkrótce”.
- Moduł siatkarski jest oznaczony jako „Wkrótce”.
- Panel gracza pobiera wyłącznie rekordy należące do zalogowanego użytkownika.
- Społeczność korzysta z Supabase; reakcje i komentarze wymagają tabel z `supabase_community.sql`.
