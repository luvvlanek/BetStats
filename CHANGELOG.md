# BetStats BETA — aktualizacja prywatności

- Dashboard ładuje wyłącznie kupony zalogowanego użytkownika.
- Publiczny profil nie pobiera ani nie wyświetla historii kuponów.
- Dodano `supabase_bets_private.sql` z pełnym resetem polityk RLS tabeli `bets`.
- Włączono `FORCE ROW LEVEL SECURITY` dla `bets`.
- Dodano dodatkową filtrację `user_id` po stronie UI jako zabezpieczenie defensywne.

**WAŻNE:** uruchom `supabase_bets_private.sql` w Supabase SQL Editor.

# BetStats 1.0 BETA — Changelog

## Beta launch

### Dostęp
- Aplikacja wymaga logowania.
- Rejestracja nowych kont została zamknięta.
- Supabase powinien dodatkowo mieć wyłączone publiczne signup.

### Sport i ligi
- Piłka nożna pozostaje aktywna.
- Polskie rozgrywki pozostają aktywne.
- La Liga, Bundesliga i rozgrywki UEFA są oznaczone jako WKRÓTCE.
- Siatkówka jest oznaczona jako WKRÓTCE.

### UI
- Usunięto osobny interfejs Model Center.
- Silnik `betstats-engine.js` nadal działa.
- Radar jest domyślnie ukryty i otwierany przyciskiem.
- Dodano hover/motion dla przycisków i kart.
- Dodano animacje przejść między sportem, ligą i aplikacją.
- Poprawiono responsywność i zachowanie formularzy.

### Wyniki
- Naprawiono wyszukiwarkę zakończonych meczów, która traciła fokus po jednym znaku.
- Kliknięcie zakończonego meczu otwiera jego statystyki zamiast zamykać widok.

### Społeczność
- Usunięto lokalny `localStorage` feed.
- Posty są przechowywane w Supabase.
- Dodano wspólny feed dla użytkowników.
- Dodano like/dislike.
- Dodano komentarze.
- Reakcje i komentarze są przypisane do kont użytkowników.

### Prywatność panelu gracza
- Pobieranie zakładów jest filtrowane po `user_id`.
- Aktualizacja i usuwanie zakładów są dodatkowo ograniczone do właściciela.
- Dodano RLS dla tabeli `bets` w skrypcie Supabase.
