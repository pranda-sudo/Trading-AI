"""XAUUSD macro-filter robustness audit. Research only; never places orders.
Tests chronological segments and historical calendar timestamp shifts to expose
possible broker-server DST conversion errors. Previously inspected history is
NOT a genuinely unseen holdout. Future forward paper trading remains necessary.
"""
import os,json,math
from datetime import timedelta,timezone,datetime
from pathlib import Path
import conservative_backtest as bt
from session_lab import summarize
from news_blackout_lab import fetch_events,compare,subset

WINDOWS=(0,15,30,45,60)
SHIFTS=(-120,-60,0,60,120)

def metrics(trades):
    x=summarize(trades)
    return {k:x.get(k) for k in ("n","winrate_pct","net_R","max_drawdown_R","profit_factor","expectancy_R")}

def main():
    cost=float(os.getenv("BACKTEST_COST_XAUUSD","0.30"))
    if not math.isfinite(cost) or cost<=0:raise ValueError("Positive BACKTEST_COST_XAUUSD required")
    trades=sorted(subset(bt.test("XAUUSD",cost=cost),"USA"),key=lambda t:bt.dt(t["time"]))
    if len(trades)<60:raise RuntimeError("Insufficient XAUUSD USA trades")
    begin,end=bt.dt(trades[0]["time"]),bt.dt(trades[-1]["time"])
    events=fetch_events(begin-timedelta(days=2),end+timedelta(days=2))
    if not events:raise RuntimeError("No economic events returned")
    coverage=len({bt.dt(e["event_time"]).date() for e in events})
    duration=(end-begin).days
    if coverage<max(10,duration*.05):raise RuntimeError("Calendar coverage insufficient")
    # Calendar timestamp shifts are sensitivity checks, NOT a DST correction.
    cutoff=begin+(end-begin)*.7
    parts={"early_70pct_time":[t for t in trades if bt.dt(t["time"])<cutoff],
           "late_30pct_time":[t for t in trades if bt.dt(t["time"])>=cutoff],
           "all":[*trades]}
    results=[]
    for shift in SHIFTS:
        shifted=[dict(e,event_time=(bt.dt(e["event_time"])+timedelta(minutes=shift)).isoformat()) for e in events]
        for part,rows in parts.items():
            for window in WINDOWS:
                kept,excluded=compare(rows,shifted,"XAUUSD",window)
                results.append({"shift_minutes":shift,"period":part,"window_minutes":window,
                  "original_trades":len(rows),"excluded_trades":len(excluded),
                  "kept":metrics(kept),"excluded":metrics(excluded)})
    # Fixed choice is 60 minutes, already selected after examining full history.
    # Never optimize on the late segment and call it out-of-sample.
    print("XAUUSD USA: historical robustness only, NOT untouched validation")
    for shift in SHIFTS:
        print("CALENDAR SHIFT",shift,"minutes")
        for part in ("early_70pct_time","late_30pct_time","all"):
            a=next(r for r in results if r["shift_minutes"]==shift and r["period"]==part and r["window_minutes"]==0)
            b=next(r for r in results if r["shift_minutes"]==shift and r["period"]==part and r["window_minutes"]==60)
            print(part,"no_filter",a["kept"],"60min",b["kept"],"excluded",b["excluded_trades"])
    report={"generated_utc":datetime.now(timezone.utc).isoformat(),"symbol":"XAUUSD",
      "session":"USA UTC proxy 12:00-21:00","cost_price_units":cost,
      "calendar_events":len(events),"calendar_days":coverage,"history_days":duration,
      "split_utc":cutoff.isoformat(),"results":results,
      "limitations":["ALL historical results were previously inspected; late period is NOT a clean holdout",
      "Calendar offset shifts are sensitivity scenarios, not verified MT5 server timezone conversion",
      "Trade entry timestamps and MT5 event timestamps must be independently verified",
      "OHLC backtest and approximate costs, no spread spikes, slippage or tick-level fills",
      "Filtering completed trades is not a full strategy re-simulation; skipped trades may change future entries",
      "No live orders; requires forward paper test before deployment"]}
    out=Path(__file__).resolve().parent/"results";out.mkdir(exist_ok=True)
    dest=out/("xauusd_robustness_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+".json")
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SAVED",dest)
    print("WARNING: This is retrospective sensitivity analysis, not a validated edge.")

if __name__=="__main__":main()
