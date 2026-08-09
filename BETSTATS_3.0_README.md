# BetStats 3.1 — Green Radar + Model Center + Explainability + Alerts

## Co jest w tej wersji

### 🔎 Dlaczego ten mecz?
- proste wyjaśnienie sygnału dla konkretnego meczu
- argumenty za i przeciw
- model / kurs uczciwy / edge dla głównych rynków
- osobne pokazanie jakości danych i zgodności modeli

### 🔔 Alerty
- wybór ligi i rynku
- minimalne prawdopodobieństwo modelu i jakość danych
- lokalne warunki alertów
- opcjonalne powiadomienia przeglądarki
- deduplikacja powiadomień, żeby nie spamować


### 🧠 Silnik
- Poisson / expected goals model
- xG, gole strzelone/stracone, SoT, forma i home advantage
- ensemble: model strukturalny + dane historyczne + słaby sygnał strzałów
- BTTS, Over 1.5, Over 2.5, Over 3.5
- 1X2 fair probabilities
- Fair Odds
- Implied Probability
- Edge / EV, gdy są kursy
- Model Agreement
- Data Quality
- Confidence
- risk flags
- explainability: skąd bierze się sygnał

### 🟢 Selekcja
- ELITE / STRONG / LEAN / SKIP
- regulowane bramki Green Mode:
  - confidence
  - data quality
  - model agreement
  - minimum probability
  - minimum edge
- Radar z TOP picks
- osobny status VALUE, gdy jest realny kurs i dodatni edge/EV
- model może powiedzieć SKIP — nie musi grać każdego meczu

### 📚 Prediction log
Aplikacja zapisuje lokalnie predykcje przed meczem:
- match
- market
- probability
- odds
- fair odds
- edge
- EV
- confidence
- data quality
- agreement
- model version
- status

Po pobraniu feedu `finished_*.json` próbuje automatycznie rozliczyć predykcje.

### 📈 Kalibracja / backtest
Model Center pokazuje:
- win rate
- ROI, gdy są kursy
- Brier score
- calibration buckets
- wyniki wg confidence
- wyniki wg rynku

`backtest.py` generuje pełny raport z eksportowanego JSON.

## Cloud sync przez Supabase

Opcjonalnie uruchom:

`supabase_prediction_logs.sql`

w Supabase SQL Editor.

Potem w Model Center:
- ☁️ Sync — wysyła lokalną historię do konta
- ☁️ Pobierz — pobiera historię z Supabase

RLS ogranicza rekordy do zalogowanego użytkownika.

## Ważne

Confidence 90/100 **nie oznacza 90% szansy wygranej**. To wynik jakości danych i zgodności sygnałów. Dopiero po dużej liczbie rozliczonych predykcji można kalibrować prawdopodobieństwa.

Nie stroimy progów pod maksymalną liczbę „zielonych”. Celem jest wysoka jakość selekcji, kalibracja i dodatnia przewaga względem ceny rynkowej.

## Deployment

Wszystkie pliki powinny być w root Vercela, szczególnie:

- `index.html`
- `betstats-engine.js`
- pliki `data_*.json`
- pliki `live_*.json`
- pliki `finished_*.json`

Po commicie do GitHub Vercel powinien zrobić automatyczny deploy.

## Wersja

`BetStats 3.1 — explain-alerts-calibratable`
