"""Feedback Lab v2: trade journal, failure diagnostics, candidate filters, rolling tests.
Research only. Never places orders or changes live signals.
Usage: py -3.11 C:\AITrading\research\feedback_lab_v2.py XAUUSD M15
Environment: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, optional BACKTEST_COST_PRICE.
"""
import os,sys,json,csv
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
from statistics import mean
import walk_forward
from feedback_lab import test,stats

def group_report(trades,key):
    groups=defaultdict(list)
    for t in trades:groups[key(t)].append(t)
    return {str(k):stats(v) for k,v in sorted(groups.items(),key=lambda kv:str(kv[0]))}

def report(trades):
    return {"overall":stats(trades),
      "direction":group_report(trades,lambda t:t["direction"]),
      "utc_hour":group_report(trades,lambda t:t["hour_utc"]),
      "year":group_report(trades,lambda t:t["time"][:4])}

def run(bars,params,lo,hi,cost):
    f,s,k,rr,side,session=params
    hours={"ALL":None,"EU":set(range(7,13)),"US":set(range(13,21)),
           "US_EARLY":set(range(13,17)),"US_LATE":set(range(17,21))}[session]
    return test(bars,f,s,k,rr,cost,lo,hi,hours,side)

def candidate_key(p):
    return {"ema_fast":p[0],"ema_slow":p[1],"atr_stop":p[2],
            "reward_risk":p[3],"direction":p[4],"session_utc":p[5]}

def main():
    symbol=sys.argv[1] if len(sys.argv)>1 else "XAUUSD"
    tf=sys.argv[2] if len(sys.argv)>2 else "M15"
    walk_forward.SYMBOL=symbol;walk_forward.TF=tf
    bars=walk_forward.fetch()
    if len(bars)<2000:raise SystemExit("Need at least 2000 candles")
    n=len(bars);train=int(n*.6);valid=int(n*.8)
    cost=float(os.getenv("BACKTEST_COST_PRICE","0.30" if symbol=="XAUUSD" else "2"))
    # Fixed baseline and limited, explicit hypotheses. Avoid tuning on final 20%.
    baseline=(14,100,2.0,1.5,"BOTH","ALL")
    candidates=[baseline,
      (14,100,2.0,1.5,"LONG","ALL"),
      (14,100,2.0,1.5,"SHORT","ALL"),
      (14,100,2.0,1.5,"BOTH","EU"),
      (14,100,2.0,1.5,"BOTH","US"),
      (14,100,2.0,1.5,"LONG","US"),
      (14,100,2.0,1.5,"SHORT","US"),
      (14,100,2.0,1.5,"BOTH","US_EARLY"),
      (14,100,2.0,1.5,"BOTH","US_LATE"),
      (14,100,2.0,2.0,"BOTH","ALL"),
      (14,100,1.5,1.5,"BOTH","ALL"),
      (20,100,2.0,1.5,"BOTH","ALL"),
      (14,50,2.0,1.5,"BOTH","ALL")]
    rows=[]
    for p in candidates:
        t=run(bars,p,0,train,cost);v=run(bars,p,train,valid,cost)
        a=stats(t);b=stats(v)
        rows.append({"params":p,"train":a,"validation":b})
    # Select on train + validation only, penalize low sample counts and unstable expectancy.
    eligible=[x for x in rows if x["train"]["n"]>=40 and x["validation"]["n"]>=20
              and x["train"]["expectancy_R"]>0 and x["validation"]["expectancy_R"]>0]
    chosen=max(eligible,key=lambda x:min(x["train"]["expectancy_R"],x["validation"]["expectancy_R"])) if eligible else None
    base_trades=run(bars,baseline,valid,n,cost)
    result={"symbol":symbol,"timeframe":tf,"candles":n,"split":{"train_end":train,"validation_end":valid},
       "cost_price_units":cost,
       "baseline":candidate_key(baseline),
       "baseline_final_holdout":report(base_trades),
       "candidates":[{"params":candidate_key(x["params"]),"train":x["train"],"validation":x["validation"]} for x in rows],
       "selection_status":"research_candidate_only" if chosen else "no_candidate_passed",
       "selected":candidate_key(chosen["params"]) if chosen else None}
    if chosen:
        chosen_trades=run(bars,chosen["params"],valid,n,cost)
        result["selected_final_holdout"]=report(chosen_trades)
        result["holdout_comparison"]={
          "winrate_delta_pct_points":round(stats(chosen_trades)["winrate_pct"]-stats(base_trades)["winrate_pct"],2),
          "expectancy_delta_R":round(stats(chosen_trades)["expectancy_R"]-stats(base_trades)["expectancy_R"],4)}
    else:chosen_trades=[]
    # Journal of evaluated holdout trades only, not a live execution journal.
    out=Path(__file__).resolve().parent/"reports";out.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    prefix=f"{symbol}_{tf}_{stamp}"
    json_path=out/(prefix+"_feedback.json")
    json_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    csv_path=out/(prefix+"_holdout_trades.csv")
    with csv_path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=["strategy","time","hour_utc","direction","R","entry","sl","tp"])
        writer.writeheader()
        for label,ts in (("baseline",base_trades),("candidate",chosen_trades)):
            for t in ts:writer.writerow({"strategy":label,**t})
    print("BASELINE FINAL",json.dumps(stats(base_trades)))
    if chosen:
        print("RESEARCH CANDIDATE",json.dumps(candidate_key(chosen["params"])))
        print("CANDIDATE FINAL",json.dumps(stats(chosen_trades)))
        print("DELTA",json.dumps(result["holdout_comparison"]))
    else:print("No candidate passed train and validation. Keep baseline for research only.")
    print("REPORT",json_path)
    print("TRADES",csv_path)
    print("IMPORTANT: this is NOT machine learning, does not know news or H1/H4 trend, and must not control live signals.")
    print("Historical holdout is now viewed: use NEW unseen data for future independent tests.")
if __name__=="__main__":main()
