# BetStats 2.0

This ZIP contains a first integrated version of the BetStats 2.0 selection engine.

## What changed

- `betstats-engine.js` — dependency-free football probability engine.
- Goal model using:
  - goals scored/conceded
  - xG when available
  - recent form
  - soft home advantage
  - empirical historical percentages
- Poisson-derived probabilities for:
  - BTTS
  - Over 1.5
  - Over 2.5
  - Over 3.5
- Data Quality Score
- Confidence Score
- Model Agreement
- Fair odds
- Edge / EV when market odds are available
- Green / Skip classification
- Green-only filter
- BetStats Radar with top signals
- Responsive Radar UI
- Model version attached to every engine result

## Important

The probabilities are estimates, not guarantees. This is deliberately a **model v1**. The confidence number is not a calibrated probability until enough historical predictions have been logged and backtested.

Do not use the Green label as a guarantee of a winning bet. The correct next step is to collect prediction logs and calibrate the model.

## Deployment

The new file is loaded from `index.html`:

```html
<script src="betstats-engine.js"></script>
```

Both files must be deployed to the same Vercel project root.

## Next development phase

1. Persist every prediction before kickoff.
2. Attach final result after the match.
3. Build calibration curves.
4. Backtest by league / market / confidence bucket.
5. Add bookmaker odds feed.
6. Calibrate probabilities with historical data.
7. Only then tune Green thresholds from out-of-sample results.

## Model outputs

Example:

- probability: 67%
- fair odds: 1.49
- confidence: 84/100
- data quality: 88/100
- model agreement: 79/100
- status: GREEN

A true VALUE status additionally requires an available market price and positive edge/EV.

