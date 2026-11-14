"""Compare original MTF strategy with an extra pattern confirmation, 3 UTC sessions.
Run: py -3.11 C:\\AITrading\\research\\pattern_session_backtest.py
Requires existing conservative_backtest.py, session_lab.py, pattern_indicators.py.
Research only. Pattern is checked on M15 candle CLOSED at or before trade entry.
This is a FILTER on baseline trades, not a separate pattern entry/exit engine.
"""
import os,json,math
from bisect import bisect_right
from datetime import timedelta
import conservative_backtest as bt
import pattern_indicators as pi
from session_lab import summarize

MARKETS=("XAUUSD","US30","DE40","USTECH","US500")
SESSIONS=(("ASIA",0,7),("EUROPE",7,12),("USA",12,21))
PATTERNS=("BULL_ENGULF","BEAR_ENGULF","BULL_PIN","BEAR_PIN","BREAK_RETEST_UP","BREAK_RETEST_DOWN")

def prep(bars):
    result=[]
    for x in bars:
        result.append({k:float(x[k]) for k in ("open","high","low","close")})
    return result

def pattern_at_closed(m15):
    # Compute each candle pattern once, without later bars.
    out=[set() for _ in m15]
    for i in range(25,len(m15)):
        for name,side in pi.detect(m15[i-25:i+1]):
            out[i].add((name,side))
    return out

def main():
    print("PATTERN + INDICATOR MTF HISTORICAL COMPARISON | 3 SESSIONS",flush=True)
    print("Pattern check: latest CLOSED M15 candle at entry, no future candles.",flush=True)
    print("NOTE: original strategy already has EMA H1/H4, M15 EMA pullback, M5 confirmation.",flush=True)
    print("Pattern comparison filters EXISTING baseline entries, not new entries.",flush=True)
    print("RSI21 50/50 and ATR-based risk/TP remain in both groups.",flush=True)
    for symbol in MARKETS:
        raw=os.getenv("BACKTEST_COST_"+symbol)
        if raw is None:
            print("SKIP",symbol,"missing BACKTEST_COST_"+symbol,flush=True)
            continue
        try:
            cost=float(raw)
            if not math.isfinite(cost) or cost<0:raise ValueError("cost must be nonnegative finite")
            baseline=sorted(bt.test(symbol,cost=cost,rsi_period=21),key=lambda t:t["time"])
            raw_m15=bt.load(symbol,"M15")
            m15=prep(raw_m15)
            ends=[x["_t"]+timedelta(minutes=15) for x in raw_m15]
            labels=pattern_at_closed(m15)
            enhanced=[]
            counts={}
            for t in baseline:
                entry=bt.dt(t["time"])
                k=bisect_right(ends,entry)-1
                if k<25:continue
                matching=[name for name,side in labels[k] if side==t["side"]]
                if not matching:continue
                enhanced.append(t)
                for name in matching:counts[name]=counts.get(name,0)+1
            print("\nMARKET",symbol,"COST",cost,"M15 BARS",len(m15),flush=True)
            for name,start,end in SESSIONS:
                if symbol=="DE40" and name=="ASIA":
                    print("SKIP DE40 ASIA: market closed / excluded by strategy",flush=True)
                    continue
                a=[t for t in baseline if start<=bt.dt(t["time"]).hour<end]
                b=[t for t in enhanced if start<=bt.dt(t["time"]).hour<end]
                print("RESULT",symbol,name,"BASE",json.dumps(summarize(a)),flush=True)
                print("RESULT",symbol,name,"PATTERN",json.dumps(summarize(b)),flush=True)
                for side in ("LONG","SHORT"):
                    print("SIDE",symbol,name,side,"BASE",json.dumps(summarize([t for t in a if t["side"]==side])),flush=True)
                    print("SIDE",symbol,name,side,"PATTERN",json.dumps(summarize([t for t in b if t["side"]==side])),flush=True)
            print("PATTERN_COUNTS",symbol,json.dumps(counts),flush=True)
        except Exception as exc:
            print("ERROR",symbol,type(exc).__name__,str(exc),flush=True)
    print("LIMITATIONS: already researched historical data, selection bias, OHLC fills,")
    print("approximate fees, UTC windows not DST-aware; results are NOT forward probabilities.")
    print("Do not deploy to live signals without untouched out-of-sample testing.")
if __name__=="__main__":main()
