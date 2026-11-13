"""Walk-forward research, NOT live trading. Run on trusted VPS only.
pip install requests
Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment (never in GitHub/browser).
"""
import os, sys, requests, math
from datetime import datetime
from statistics import mean

URL=os.environ["SUPABASE_URL"].rstrip("/")
KEY=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SYMBOL=sys.argv[1] if len(sys.argv)>1 else "XAUUSD"
TF=sys.argv[2] if len(sys.argv)>2 else "H1"
HEAD={"apikey":KEY,"Authorization":"Bearer "+KEY}
def fetch():
    out=[];offset=0
    while True:
        r=requests.get(URL+"/rest/v1/market_candles",headers=HEAD,
          params={"select":"candle_time,open,high,low,close","symbol":"eq."+SYMBOL,
                  "timeframe":"eq."+TF,"order":"candle_time.asc","limit":1000,"offset":offset},timeout=45)
        r.raise_for_status();chunk=r.json();out.extend(chunk)
        if len(chunk)<1000:break
        offset+=1000
    return out

def ema(values,n):
    alpha=2/(n+1);x=values[0];result=[]
    for v in values:x=alpha*v+(1-alpha)*x;result.append(x)
    return result
def evaluate(bars,fast_n,slow_n,atr_mult,rr,spread,begin,end):
    closes=[float(b["close"]) for b in bars];fast=ema(closes,fast_n);slow=ema(closes,slow_n)
    highs=[float(b["high"]) for b in bars];lows=[float(b["low"]) for b in bars]
    opens=[float(b["open"]) for b in bars]
    tr=[highs[0]-lows[0]]+[max(highs[i]-lows[i],abs(highs[i]-closes[i-1]),abs(lows[i]-closes[i-1])) for i in range(1,len(bars))]
    atr=[None]*13+[sum(tr[i-13:i+1])/14 for i in range(13,len(bars))]
    outcomes=[];next_allowed=begin
    for i in range(max(begin,slow_n+5,20),min(end,len(bars)-52)):
        if i<next_allowed:continue
        # Signal formed at CLOSE of i; execution at OPEN of i+1, never at prior candle.
        long=fast[i]>slow[i] and slow[i]>slow[i-4] and closes[i-1]<=fast[i-1] and closes[i]>fast[i]
        short=fast[i]<slow[i] and slow[i]<slow[i-4] and closes[i-1]>=fast[i-1] and closes[i]<fast[i]
        if not(long or short):continue
        risk=atr[i]*atr_mult
        if risk<=0:continue
        side=1 if long else -1;entry=opens[i+1]+side*spread/2
        sl=entry-side*risk;tp=entry+side*risk*rr
        outcome=None;exit_bar=i+50
        for j in range(i+1,i+51):
            # Gap opening: fill at opening price if worse than planned SL.
            if (side==1 and opens[j]<sl) or (side==-1 and opens[j]>sl):
                outcome=side*(opens[j]-entry)/risk;exit_bar=j;break
            hit_sl=lows[j]<=sl if side==1 else highs[j]>=sl
            hit_tp=highs[j]>=tp if side==1 else lows[j]<=tp
            if hit_sl or hit_tp:
                outcome=-1 if hit_sl else rr;exit_bar=j;break
        if outcome is None:
            outcome=side*(closes[exit_bar]-entry)/risk
        # Approximate round-trip spread/slippage penalty in R.
        outcome-=spread/(2*risk)
        outcomes.append(outcome);next_allowed=exit_bar+1
    if not outcomes:return None
    eq=0;peak=0;dd=0
    for x in outcomes:eq+=x;peak=max(peak,eq);dd=max(dd,peak-eq)
    return {"trades":len(outcomes),"win_pct":round(100*sum(x>0 for x in outcomes)/len(outcomes),1),
            "expectancy_R":round(mean(outcomes),3),"total_R":round(sum(outcomes),2),"max_drawdown_R":round(dd,2)}

def main():
    bars=fetch();n=len(bars)
    if n<1000:raise SystemExit("Not enough history")
    split=int(n*.7);print("Symbol",SYMBOL,TF,"candles",n,"train",split,"test",n-split)
    # Costs must be supplied in instrument PRICE units, e.g. XAUUSD $0.30.
    spread=float(os.environ.get("BACKTEST_COST_PRICE","0.30" if SYMBOL=="XAUUSD" else "2"))
    candidates=[]
    for f in (9,14,20):
      for slow in (35,50,100):
       for mult in (1.0,1.5,2.0):
        for rr in (1.0,1.5,2.0):
         train=evaluate(bars,f,slow,mult,rr,spread,0,split-52)
         if train and train["trades"]>=30:candidates.append((train["expectancy_R"],(f,slow,mult,rr),train))
    if not candidates:raise SystemExit("No sufficiently frequent strategy")
    # Select ONLY on train. Holdout is never used for tuning.
    best=max(candidates,key=lambda x:x[0]);params=best[1]
    test=evaluate(bars,*params,spread,split,n)
    print("TRAIN BEST:",params,best[2])
    print("OUT OF SAMPLE (untouched last 30%):",test)
    print("Warning: no tick-level spread, swaps, commission, slippage or news blackout modeled.")
    print("Do not deploy until independently validated with broker tick data and realistic costs.")
if __name__=="__main__":main()
