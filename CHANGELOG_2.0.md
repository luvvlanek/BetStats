# BetStats 1.0 — changes

Implemented in this build:

- New football probability engine (`betstats-engine.js`)
- Poisson goal model based on attack/defence + xG + form
- Conservative empirical blend
- Data Quality Score
- Confidence Score
- Model Agreement
- Fair odds
- Edge and EV when odds exist
- GREEN / SKIP selection
- Green-only match filter
- Radar with ranked strongest signals
- Confidence/Data Quality badge on match cards
- `backtest.py` helper for future prediction-log calibration
- README with deployment and modelling notes

Not yet fully automated:
- persistent pre-match prediction logging
- automatic result matching
- bookmaker odds ingestion for every market
- out-of-sample calibration
- automated league/market performance pruning

Those require historical prediction snapshots and/or a live odds feed; fabricating them would make the model look better without evidence.
