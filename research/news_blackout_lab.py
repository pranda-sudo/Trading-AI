"""Exploratory macro-news blackout comparison. NO ORDERS.
Requires existing conservative_backtest.py and walk_forward.py, requests and
SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY (server environment only).
Run: py -3.11 C:\\AITrading\\research\\news_blackout_lab.py
Provide BACKTEST_COST_XAUUSD, BACKTEST_COST_US30, BACKTEST_COST_DE40,
BACKTEST_COST_USTECH, BACKTEST_COST_US500 in instrument price units.
Only compares entry exclusion, not post-news price execution or a live strategy.
"""
import os, json, math, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from bisect import bisect_left
from pathlib import Path
import conservative_backtest as bt
from session_lab import summarize

SYMBOLS=("XAUUSD","US30","DE40","USTECH","US500")
WINDOWS=(0,15,30,45,60)
SESSIONS={"ASIA":(0,7),"EUROPE":(7,12),"USA":(12,21)}
MARKETS={"XAUUSD":("ASIA","USA"),"US30":("ASIA","USA"),
         "DE40":("EUROPE",),"USTECH":("ASIA","USA"),"US500":("ASIA","USA")}

def fetch_events(start,end):
    url=os.environ["SUPABASE_URL"].rstrip("/")
    key=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    if not url.startswith("https://"):raise ValueError("Invalid SUPABASE_URL")
    records=[];offset=0
    while True:
        params=urllib.parse.urlencode({"select":"event_time,currency,country,title,importance",
          "event_time":"gte."+start.isoformat(),"order":"event_time.asc",
          "limit":"1000","offset":str(offset)})
        req=urllib.request.Request(url+"/rest/v1/economic_events?"+params,headers={
            "apikey":key,"Authorization":"Bearer "+key})
        with urllib.request.urlopen(req,timeout=40) as response:
            batch=json.load(response)
        if not isinstance(batch,list):raise RuntimeError("Invalid economic_events response")
        records.extend(batch)
        if len(batch)<1000:break
        offset+=len(batch)
        if offset>100000:raise RuntimeError("Unexpectedly large calendar dataset")
    return [e for e in records if start<=bt.dt(e["event_time"])<=end]

def relevant(symbol,event):
    c=str(event.get("currency") or "").upper()
    if symbol!="DE40":return c=="USD"
    t=(str(event.get("country") or "")+" "+str(event.get("title") or "")).lower()
    return c=="EUR" or "german" in t or "deutsch" in t or (c=="USD" and int(event.get("importance") or 0)>=3)

def subset(trades,session):
    a,b=SESSIONS[session]
    return [t for t in trades if a<=bt.dt(t["time"]).hour<b]

def compare(rows,events,symbol,window):
    important=sorted(bt.dt(e["event_time"]) for e in events
                     if int(e.get("importance") or 0)>=2 and relevant(symbol,e))
    stamps=[x.timestamp() for x in important]
    excluded=[];retained=[]
    for trade in rows:
        t=bt.dt(trade["time"]).timestamp()
        i=bisect_left(stamps,t)
        near=any(abs(stamps[j]-t)<=window*60 for j in (i-1,i) if 0<=j<len(stamps)) if window else False
        (excluded if near else retained).append(trade)
    return retained,excluded

def main():
    missing=[f"BACKTEST_COST_{s}" for s in SYMBOLS if not os.getenv(f"BACKTEST_COST_{s}")]
    if missing:raise RuntimeError("Missing mandatory cost assumptions: "+", ".join(missing))
    results=[]
    for symbol in SYMBOLS:
        cost=float(os.environ[f"BACKTEST_COST_{symbol}"])
        if not math.isfinite(cost) or cost<=0:raise ValueError(f"Invalid positive cost for {symbol}")
        trades=sorted(bt.test(symbol,cost=cost),key=lambda t:t["time"])
        if not trades:continue
        begin=bt.dt(trades[0]["time"]);end=bt.dt(trades[-1]["time"])
        events=fetch_events(begin-timedelta(hours=1),end+timedelta(hours=1))
        # Absence of events is NOT evidence that the period had no macro risk.
        days=(end-begin).total_seconds()/86400
        distinct_days=len({bt.dt(e["event_time"]).date() for e in events})
        print(f"{symbol}: {len(trades)} trades; {len(events)} calendar rows across {distinct_days} days / {days:.1f} elapsed days")
        if not events or distinct_days<max(2,days*.05):
            print("SKIP: insufficient observable calendar coverage; cannot interpret no-news periods as safe.")
            continue
        for session in MARKETS[symbol]:
            base=subset(trades,session)
            for minutes in WINDOWS:
                kept,excluded=compare(base,events,symbol,minutes)
                record={"symbol":symbol,"session":session,"window_minutes_each_side":minutes,
                  "cost_price_units":cost,"calendar_events":len(events),"calendar_distinct_days":distinct_days,
                  "original_trades":len(base),"excluded_trades":len(excluded),
                  "retained_trades":len(kept),"retained_metrics":summarize(kept),
                  "excluded_metrics":summarize(excluded)}
                results.append(record)
                print(json.dumps(record,ensure_ascii=False),flush=True)
    out=Path(__file__).resolve().parent/"results"
    out.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path=out/f"news_blackout_{stamp}.json"
    path.write_text(json.dumps({"created_utc":stamp,"method":"entry exclusion; symmetric windows; previously inspected historical data",
      "limitations":["Calendar coverage may be incomplete","OHLC simulated fills, not ticks",
       "Approximate UTC sessions, not DST-aware","No independent holdout",
       "Only trades whose entries are near events are excluded; no re-entry simulation"],
      "results":results},ensure_ascii=False,indent=2),encoding="utf-8")
    print("SAVED",path)
    print("Research only; not live validated. Do not choose a winner from repeatedly inspected data.")

if __name__=="__main__":main()
