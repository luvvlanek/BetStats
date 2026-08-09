#!/usr/bin/env python3
"""
BetStats prediction-log backtest helper.

Input JSON should be a list of prediction records, e.g.
[
  {"market":"Over 2.5","probability":0.68,"odds":1.80,"result":1},
  {"market":"Over 2.5","probability":0.62,"odds":1.90,"result":0}
]

result: 1 for win, 0 for loss.
This script intentionally does not fabricate historical predictions from
finished match scores; proper backtesting requires pre-match snapshots.
"""
import json, sys, math
from collections import defaultdict

def brier(rows):
    return sum((r["probability"]-r["result"])**2 for r in rows)/len(rows)

def calibration(rows):
    buckets=defaultdict(list)
    for r in rows:
        p=float(r["probability"])
        key=min(0.95, max(0.05, math.floor(p*20)/20))
        buckets[key].append(r)
    return [
        {"predicted_range":f"{int(k*100)}-{int((k+0.05)*100)}%",
         "count":len(v),
         "predicted":round(sum(x["probability"] for x in v)/len(v)*100,2),
         "actual":round(sum(x["result"] for x in v)/len(v)*100,2)}
        for k,v in sorted(buckets.items())
    ]

def main(path):
    rows=json.load(open(path,encoding="utf-8"))
    rows=[r for r in rows if "probability" in r and "result" in r]
    if not rows:
        raise SystemExit("Brak poprawnych prediction records.")
    wins=sum(int(r["result"]) for r in rows)
    roi=0.0; staked=0
    with_odds=0
    for r in rows:
        if r.get("odds") and float(r["odds"])>1:
            with_odds+=1; staked+=1
            roi += float(r["odds"])-1 if r["result"] else -1
    print(json.dumps({
        "predictions":len(rows),
        "win_rate":round(wins/len(rows)*100,2),
        "brier_score":round(brier(rows),5),
        "roi_pct":round(roi/staked*100,2) if staked else None,
        "with_odds":with_odds,
        "calibration":calibration(rows)
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Użycie: python backtest.py predictions.json")
    main(sys.argv[1])
