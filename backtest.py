#!/usr/bin/env python3
"""
BetStats 3.0 backtest / calibration report.

Use prediction records exported from the app:
  python backtest.py betstats-predictions.json

Only settled predictions are evaluated. Predictions should have been
generated before kickoff; do not mix post-match data into the feature set.
"""
import json, sys, math
from collections import defaultdict

def mean(xs):
    return sum(xs)/len(xs) if xs else None

def bucket(p):
    p=float(p)
    lo=max(.0,min(.95,math.floor(p*20)/20))
    return lo

def calibration(rows):
    groups=defaultdict(list)
    for r in rows:
        groups[bucket(r["probability"])].append(r)
    out=[]
    for lo,rs in sorted(groups.items()):
        pred=mean([float(r["probability"]) for r in rs])
        act=mean([int(r["result"]) for r in rs])
        out.append({
            "range":f"{int(lo*100)}-{int((lo+.05)*100)}%",
            "n":len(rs),"predicted_pct":round(pred*100,2),
            "actual_pct":round(act*100,2),
            "delta_pp":round((act-pred)*100,2)
        })
    return out

def report(rows):
    settled=[r for r in rows if r.get("result") in (0,1)]
    wins=sum(int(r["result"]) for r in settled)
    brier=mean([(float(r["probability"])-int(r["result"]))**2 for r in settled])
    logloss=None
    if settled:
        vals=[]
        for r in settled:
            p=max(.0001,min(.9999,float(r["probability"])))
            y=int(r["result"])
            vals.append(-(y*math.log(p)+(1-y)*math.log(1-p)))
        logloss=mean(vals)
    with_odds=[r for r in settled if r.get("odds") and float(r["odds"])>1]
    pnl=sum((float(r["odds"])-1 if r["result"] else -1) for r in with_odds)
    def grouped(field):
        g=defaultdict(list)
        for r in settled:g[str(r.get(field) or "Unknown")].append(r)
        out=[]
        for k,v in g.items():
            out.append({"group":k,"n":len(v),"win_rate_pct":round(mean([r["result"] for r in v])*100,2),
                        "avg_probability_pct":round(mean([r["probability"] for r in v])*100,2)})
        return sorted(out,key=lambda x:-x["n"])
    conf=defaultdict(list)
    for r in settled:
        c=float(r.get("confidence",0))
        k="90+" if c>=90 else "85-89" if c>=85 else "80-84" if c>=80 else "75-79" if c>=75 else "<75"
        conf[k].append(r)
    conf_out=[]
    for k,v in conf.items():
        conf_out.append({"bucket":k,"n":len(v),"win_rate_pct":round(mean([r["result"] for r in v])*100,2),
                         "avg_probability_pct":round(mean([r["probability"] for r in v])*100,2)})
    return {
        "records":len(rows),"settled":len(settled),
        "win_rate_pct":round(wins/len(settled)*100,2) if settled else None,
        "brier_score":round(brier,5) if brier is not None else None,
        "log_loss":round(logloss,5) if logloss is not None else None,
        "roi_pct":round(pnl/len(with_odds)*100,2) if with_odds else None,
        "with_odds":len(with_odds),
        "calibration":calibration(settled),
        "by_market":grouped("market_name"),
        "by_league":grouped("league"),
        "by_confidence":sorted(conf_out,key=lambda x:x["bucket"])
    }

def main(path):
    with open(path,encoding="utf-8") as f: data=json.load(f)
    if isinstance(data,dict): data=data.get("predictions",data.get("rows",[]))
    print(json.dumps(report(data),ensure_ascii=False,indent=2))

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Użycie: python backtest.py betstats-predictions.json")
    main(sys.argv[1])
