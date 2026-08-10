# BetStats 1.0 BETA — README ADMIN

## Status
This build is the closed beta of BetStats.

- Login required to access the application.
- New registration is disabled in the UI. For real enforcement, also disable **Allow new users to sign up** in Supabase Authentication settings.
- Football is the only enabled sport in this beta.
- Polish football leagues are enabled.
- La Liga, Bundesliga and UEFA competitions are marked **WKRÓTCE**.
- Volleyball is marked **WKRÓTCE**.
- The separate Model Center UI has been removed. `betstats-engine.js` remains and is still used by match analysis and the Radar.

## File map

### Frontend
- `index.html` — current application shell, navigation, match UI, auth gate, community UI and app logic.
- `betstats-engine.js` — probability/model engine. Keep this file.
- `betstats.css` — reserved for future extraction of global UI styles; the current legacy page still contains existing inline styles for compatibility.
- `logo.png` — application logo.
- `manifest.json` — PWA metadata.
- `sw.js` — service worker.

### Data / scrapers
- `scraper.py` / `auto_scraper.py` / `live_scraper.py` — data collection scripts.
- `data_*.json` — league data.
- `finished_*.json` — finished match feeds.
- `live_*.json` — live feeds.
- `run_scraper.bat` — local scraper launcher.
- `backtest.py` — backtest/calibration helper.

### Database
- `supabase_community.sql` — community posts, likes/dislikes, comments and private bets RLS policies.
- `supabase_prediction_logs.sql` — prediction log storage.

## Required Supabase setup

Run `supabase_community.sql` in Supabase SQL Editor.

Then go to:

**Authentication → Settings / Providers**

and disable:

**Allow new users to sign up**

For a closed beta, create/invite test accounts from the Supabase dashboard instead.

## Community

The Community tab is no longer localStorage-based.

Posts are stored in:
- `community_posts`

Reactions:
- `community_reactions`
- `value = 1` → like
- `value = -1` → dislike

Comments:
- `community_comments`

Every logged-in user sees the same approved feed. Each user can react/comment using their own account.

## Player panel privacy

The frontend now filters bets by the logged-in user's `user_id`.

The SQL file also contains RLS policies intended to enforce:
- read own bets
- insert own bets
- update own bets
- delete own bets

Do not rely on frontend filtering alone; keep RLS enabled.

## Important deployment note

The public Supabase `anon` key can be present in a browser application. Never put the Supabase `service_role` key in `index.html`, JavaScript, GitHub or the public ZIP.

## Beta checklist

1. Run the community SQL in Supabase.
2. Disable public registration in Supabase Auth.
3. Create/invite beta accounts.
4. Deploy all frontend files together.
5. Test login on desktop and mobile.
6. Test two different accounts:
   - account A must not see account B's private bets;
   - both accounts must see the same community posts;
   - likes/dislikes must update for everyone;
   - comments must appear for everyone.
7. Test finished-match search by typing multiple characters.
8. Test clicking a finished match and opening its statistics.
9. Test the Radar show/hide button.
10. Test disabled leagues and volleyball.

## Architecture note

The current project is still a legacy single-page frontend because that minimizes regression risk for the beta. New modules should be extracted into separate files incrementally rather than rewriting the whole application before launch.


## Prywatność kuponów — WAŻNE

Plik `supabase_bets_private.sql` usuwa wszystkie dotychczasowe polityki RLS dla `public.bets` i tworzy polityki, dzięki którym użytkownik może odczytywać, dodawać, zmieniać i usuwać wyłącznie własne kupony.

Uruchom ten plik w Supabase SQL Editor przed testami beta. Włączone jest także `FORCE ROW LEVEL SECURITY`.

Publiczne profile BetStats nie pobierają już tabeli `bets` — historia kuponów pozostaje prywatna i jest dostępna wyłącznie w Panelu gracza zalogowanego właściciela.
