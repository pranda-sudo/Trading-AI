"""Exploratory historical probability lab. NO trading or live signal changes.
Uses existing conservative_backtest.py results and prior CLOSED M15 candles only.
Run: py -3.11 C:\\AITrading\\research\\probability_lab.py XAUUSD
CAUTION: previously inspected data; all comparisons exploratory, not out-of-sample.
"""
import sys,math,json,statistics
from bisect import bisect_right
from datetime import timedelta
import conservative_backtest as base

def wilson(w,n,z=1.96):
    if not n:return None
    p=w/n;d=1+z*z/n
    c=(p+z*z/(2*n))/d
    h=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return [round(100*(c-h),2),round(100*(c+h),2)]

def adx(high,low,close,n=14):
    # Wilder smoothed directional movement, using only historical bars.
    out=[None]*len(close)
    if len(close)<2*n+1:return out
    tr=[];plus=[];minus=[]
    for i in range(1,len(close)):
        up=high[i]-high[i-1];down=low[i-1]-low[i]
        plus.append(up if up>down and up>0 else 0.)
        minus.append(down if down>up and down>0 else 0.)
        tr.append(max(high[i]-low[i],abs(high[i]-close[i-1]),abs(low[i]-close[i-1])))
    a=sum(tr[:n]);p=sum(plus[:n]);m=sum(minus[:n]);dx=[]
    for k in range(n-1,len(tr)):
        if k>n-1:
            a=a-a/n+tr[k];p=p-p/n+plus[k];m=m-m/n+minus[k]
        dx.append(100*abs(p-m)/(p+m) if p+m else 0.)
        if len(dx)==n:out[k+1]=sum(dx)/n
        elif len(dx)>n:out[k+1]=(out[k]* (n-1)+dx[-1])/n
    return out

def describe(name,items):
    n=len(items);w=sum(t["R"]>0 for t in items)
    result=base.score(items)
    result["wilson_95_pct"]=wilson(w,n)
    result["label"]=name
    return result

def main():
    symbol=sys.argv[1] if len(sys.argv)>1 else "XAUUSD"
    trades=base.test(symbol)
    candles=base.load(symbol,"M15")
    high=[float(x["high"]) for x in candles]
    low=[float(x["low"]) for x in candles]
    close=[float(x["close"]) for x in candles]
    times=[x["_t"]+timedelta(minutes=15) for x in candles]
    strength=adx(high,low,close)
    enriched=[]
    for t in trades:
        when=base.dt(t["time"])
        # At the M5 entry, use only M15 bars that closed BEFORE the entry.
        k=bisect_right(times,when)-1
        if k<60 or strength[k] is None:continue
        side=1 if t["side"]=="LONG" else -1
        atr=sum(high[q]-low[q] for q in range(k-13,k+1))/14
        if atr<=0:continue
        prior_high=max(high[k-40:k])
        prior_low=min(low[k-40:k])
        # Distance to adverse level: nearest historical resistance for long,
        # nearest historical support for short. No future candle information.
        room=(prior_high-t["entry"] if side==1 else t["entry"]-prior_low)/atr
        x=dict(t)
        x.update(adx=round(strength[k],2),room_atr=round(room,2),
                 utc_hour=when.hour,atr=round(atr,4))
        enriched.append(x)
    print("HISTORICAL PROBABILITY LAB",symbol)
    print("DISCLAIMER: exploratory filters on already-viewed history, NOT independent validation.")
    print("BASELINE",json.dumps(describe("all",enriched)))
    variants={
      "ADX >= 20":[x for x in enriched if x["adx"]>=20],
      "ADX >= 25":[x for x in enriched if x["adx"]>=25],
      "ADX >= 30":[x for x in enriched if x["adx"]>=30],
      "Room to prior S/R >= 1 ATR":[x for x in enriched if x["room_atr"]>=1],
      "ADX >= 25 AND room >= 1 ATR":[x for x in enriched if x["adx"]>=25 and x["room_atr"]>=1],
      "UTC 07-16":[x for x in enriched if 7<=x["utc_hour"]<16],
      "UTC 12-21":[x for x in enriched if 12<=x["utc_hour"]<21],
    }
    for name,subset in variants.items():
        print("FILTER",json.dumps(describe(name,subset)))
    # Historical win probability conditioned on ADX buckets, with sample sizes.
    for lo,hi in [(0,20),(20,25),(25,30),(30,1000)]:
        sub=[x for x in enriched if lo<=x["adx"]<hi]
        print("ADX_BUCKET",json.dumps(describe(f"{lo}-{hi}",sub)))
    print("INTERPRETATION: winrate and Wilson interval are descriptive, not calibrated future probabilities.")
    print("WARNING: costs approximate; OHLC intrabar ambiguity, news, broker spread and slippage not fully modeled.")
    print("NO DEPLOYMENT: freeze candidate rules and retest on future unseen data, tick costs and multiple rolling windows.")

if __name__=="__main__":main()
