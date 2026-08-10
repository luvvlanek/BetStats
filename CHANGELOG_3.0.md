## 3.1 — Explainability + Alerts
- Dodano sekcję „Dlaczego ten mecz?” w szczegółach spotkania.
- Dodano alerty filtrowane po lidze, rynku, minimalnym prawdopodobieństwie i jakości danych.
- Dodano opcjonalne powiadomienia przeglądarki z deduplikacją.
- Podniesiono wersję silnika do `3.1-explain-alerts-calibratable`.

# BetStats 1.0

- Nowy ensemble goal model.
- Data Quality / Confidence / Model Agreement.
- Green/Value/SKIP selekcja z regulowanymi progami.
- Model Center + Radar.
- Prediction log w localStorage.
- Automatyczne rozliczanie z finished feeds.
- Calibration / Brier / ROI / performance breakdown.
- Opcjonalna synchronizacja prediction logów z Supabase.
- Explainability w szczegółach meczu.


## 3.0.1 — Model Center click/overlay fix
- Fixed the full-screen Model Center overlay capturing clicks unexpectedly.
- Added robust delegated controls and ESC/backdrop closing.
- Added pointer-event guards so only the visible modal captures input.
