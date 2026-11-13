"""RSI comparison by allowed UTC session. Research only; never places orders.
Requires conservative_backtest.py, session_lab.py, walk_forward.py and Supabase env.
Set BACKTEST_COST_<SYMBOL> to verified broker round-trip price-unit costs.
"""
import os,json,math
import conservative_backtest as bt
from session_lab import summarize

MARKETS=("XAUUSD","US30","DE40","USTECH","US500")
WINDOWS={"DE40":(("EUROPE",7,12),)}
for s in ("XAUUSD","US30","USTECH","US500"):
    WINDOWS[s]=(("ASIA",0,7),("USA",12,21))
VARIANTS=(("BASELINE",None,50,50),("RSI7 50/50",7,50,50),
          ("RSI14 50/50",14,50,50),("RSI21 50/50",21,50,50),
          ("RSI14 55/45",14,55,45),("RSI14 60/40",14,60,40))
def main():
    print("RSI FILTER COMPARISON | closed M15 Wilder RSI | research only")
    print("UTC session windows are simplified, not broker/DST-adjusted.")
    print("Previously inspected data; results are NOT independent validation.")
    for symbol in MARKETS:
        raw=os.getenv("BACKTEST_COST_"+symbol)
        if raw is None:
            print("SKIP",symbol,"missing BACKTEST_COST_"+symbol);continue
        try:
            cost=float(raw)
            if not math.isfinite(cost) or cost<0:raise ValueError("invalid cost")
            print("\nMARKET",symbol,"roundtrip price-unit cost",cost,flush=True)
            for label,period,long_min,short_max in VARIANTS:
                trades=bt.test(symbol,cost=cost,rsi_period=period,
                               rsi_long_min=long_min,rsi_short_max=short_max)
                for session,start,end in WINDOWS[symbol]:
                    rows=[t for t in trades if start<=bt.dt(t["time"]).hour<end]
                    print(symbol,session,label,json.dumps(summarize(rows)),flush=True)
        except Exception as exc:
            print("ERROR",symbol,type(exc).__name__,str(exc),flush=True)
    print("CAUTION: RSI filtering can change overlapping trade outcomes and sample size.")
    print("Never select the best historical variant as a live signal without")
    print("independent future rolling tests, verified spread, fees, swaps and news exclusions.")
if __name__=="__main__":main()
