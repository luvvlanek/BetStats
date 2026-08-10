# BetStats 1.0 — Beta

## Dostęp
- Aplikacja wymaga logowania.
- Rejestracja nowych kont jest wyłączona na czas zamkniętej bety.

## Zakres
- Piłka nożna: dostępne wybrane ligi.
- Rozgrywki europejskie: WKRÓTCE.
- Siatkówka: WKRÓTCE.

## Bezpieczeństwo danych
- Panel gracza pobiera wyłącznie zakłady `user_id` zalogowanego użytkownika.
- Społeczność działa przez Supabase.


# Dziennik zmian

## 3.1.0 — Społeczność i polski interfejs

### Nowe

- Dodano zakładkę **Społeczność** z tablicą analiz, kategoriami i formularzem publikacji.
- Wpisy użytkownika są zapisywane lokalnie w przeglądarce; moduł ma strukturę gotową do późniejszego podłączenia do Supabase.
- Dodano standard wpisu społeczności: argumenty, dane i ryzyko zamiast obietnic zysku.
- Rozszerzono stronę **O projekcie** o metodologię, ocenę jakości danych i zasady kalibracji.

### Ulepszenia

- Centrum modelu zostało spolszczone: nazwy metryk, selekcji, kalibracji i przycisków są czytelne po polsku.
- Zastąpiono część emoji opisowymi etykietami w głównej nawigacji i Centrum modelu.
- Nazwy statusów prezentowanych użytkownikowi są bardziej zrozumiałe: „Mocny sygnał” i „Przewaga kursowa”.
- Komunikaty o prawdopodobieństwie i pewności wyraźniej podkreślają, że model nie gwarantuje wyniku.

### Znane ograniczenia

- Tablica Społeczności nie ma jeszcze logowania, moderacji, komentarzy ani wspólnej bazy wpisów.
- Model wymaga długiej, rozliczonej próby przed wyciąganiem wniosków o skuteczności lub ROI.

## 3.0.1

- Poprawiono obsługę nakładki Centrum modelu, zamykanie klawiszem Escape i kliknięciem poza oknem.

## 3.0.0

- Dodano model łączący oczekiwane gole, historię oraz strzały celne.
- Dodano radar sygnałów, dziennik predykcji, kalibrację, wynik Brier’a i opcjonalną synchronizację z Supabase.
