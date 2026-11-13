"""Trading AI: exploratory XAUUSD session/hour breakdown, no live trading.
Run: py -3.11 C:\\AITrading\\research\\session_lab.py XAUUSD
Uses conservative_backtest.test(), so entry times are in UTC and returns in R.
Windows are NON-OVERLAPPING UTC proxies, not exact exchange/DST schedules.
"""
import sys,json
from collections import defaultdict
import conservative_backtest as bt

SESSIONS=[
    ("ASIA",0,7),
    ("EUROPE",7,12),
    ("USA",12,21),
    ("LATE",21,24),
]
def summarize(rows):
    result=bt.score(rows)
    n=len(rows)
    wins=sum(x["R"]>0 for x in rows)
    losses=sum(x["R"]<0 for x in rows)
    gross_win=sum(x["R"] for x in rows if x["R"]>0)
    gross_loss=-sum(x["R"] for x in rows if x["R"]<0)
    result["profit_factor"]=round(gross_win/gross_loss,3) if gross_loss else None
    result["wins"]=wins
    result["losses"]=losses
    result["wilson95_winrate_pct"]=wilson(wins,n)
    return result
def wilson(w,n,z=1.96):
    if not n:return None
    import math
    p=w/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    margin=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [round(100*(mid-margin),2),round(100*(mid+margin),2)]
def show(label,rows):
    print(label,json.dumps(summarize(rows),ensure_ascii=False))
def main():
    symbol=sys.argv[1] if len(sys.argv)>1 else "XAUUSD"
    trades=bt.test(symbol)
    trades.sort(key=lambda x:x["time"])
    print("SESSION LAB",symbol,"UTC; historical exploratory analysis; NO live trading")
    print("UTC proxies: ASIA 00-07; EUROPE 07-12; USA 12-21; LATE 21-24")
    print("WARNING: session overlaps and DST are simplified. Hours are entry timestamps, not exit timestamps.")
    show("ALL",trades)
    for name,start,end in SESSIONS:
        rows=[t for t in trades if start<=bt.dt(t["time"]).hour<end]
        show("SESSION "+name,rows)
        for direction in ("LONG","SHORT"):
            show("  "+name+" "+direction,[t for t in rows if t["side"]==direction])
    print("HOURLY UTC")
    for hour in range(24):
        show(f"HOUR {hour:02d}:00 UTC",[t for t in trades if bt.dt(t["time"]).hour==hour])
    print("DAY OF WEEK UTC (0=Monday)")
    for day in range(7):
        show(f"WEEKDAY {day}",[t for t in trades if bt.dt(t["time"]).weekday()==day])
    # Time-based diagnostics; this does not create a new untouched holdout.
    split=int(len(trades)*.7)
    for tag,part in [("EARLY70",trades[:split]),("LATE30",trades[split:])]:
        print("STABILITY",tag)
        for name,start,end in SESSIONS:
            show(tag+" "+name,[t for t in part if start<=bt.dt(t["time"]).hour<end])
    print("CAUTION: Historical data already viewed; many comparisons mean selection bias.")
    print("Do not choose a winning session and deploy without future unseen rolling validation.")
    print("Trade R is based on approximate OHLC costs; real spreads, slippage, news and tick fills are not validated.")
if __name__=="__main__":
    main()
