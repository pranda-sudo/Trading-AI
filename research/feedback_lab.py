"""Research diagnostics for Trading AI. No live orders or automatic deployment.
Uses same Supabase env vars as walk_forward.py.
Usage: py -3.11 C:\\AITrading\\research\\feedback_lab.py XAUUSD M15
"""
import os,sys,json
from datetime import datetime,timezone
from statistics import mean
from walk_forward import fetch,ema

def hour_utc(s):
    return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc).hour

def test(bars, fast_n,slow_n,atr_k,rr,cost,lo,hi,allowed_hours=None,direction="BOTH"):
    close=[float(b["close"]) for b in bars]
    op=[float(b["open"]) for b in bars]
    high=[float(b["high"]) for b in bars]
    low=[float(b["low"]) for b in bars]
    fast=ema(close,fast_n);slow=ema(close,slow_n)
    tr=[high[0]-low[0]]+[max(high[i]-low[i],abs(high[i]-close[i-1]),abs(low[i]-close[i-1])) for i in range(1,len(bars))]
    atr=[None]*13+[sum(tr[i-13:i+1])/14 for i in range(13,len(bars))]
    trades=[];next_i=lo
    for i in range(max(lo,slow_n+5,20),min(hi-1,len(bars)-51)):
        if i<next_i:continue
        if allowed_hours is not None and hour_utc(bars[i]["candle_time"]) not in allowed_hours:continue
        buy=fast[i]>slow[i] and slow[i]>slow[i-4] and close[i-1]<=fast[i-1] and close[i]>fast[i]
        sell=fast[i]<slow[i] and slow[i]<slow[i-4] and close[i-1]>=fast[i-1] and close[i]<fast[i]
        if not buy and not sell:continue
        side=1 if buy else -1
        if direction=="LONG" and side<0 or direction=="SHORT" and side>0:continue
        risk=atr[i]*atr_k
        if risk<=0:continue
        entry=op[i+1]+side*cost/2;sl=entry-side*risk;tp=entry+side*risk*rr
        exit_i=i+50;out=None
        for j in range(i+1,i+51):
            if side*(op[j]-sl)<0:
                out=side*(op[j]-entry)/risk;exit_i=j;break
            stop=(low[j]<=sl if side>0 else high[j]>=sl)
            target=(high[j]>=tp if side>0 else low[j]<=tp)
            if stop or target:
                out=-1 if stop else rr;exit_i=j;break
        if out is None:out=side*(close[exit_i]-entry)/risk
        out-=cost/(2*risk)
        trades.append({"time":bars[i]["candle_time"],"hour_utc":hour_utc(bars[i]["candle_time"]),
                       "direction":"LONG" if side>0 else "SHORT","R":out,"entry":entry,"sl":sl,"tp":tp})
        next_i=exit_i+1
    return trades

def stats(trades):
    if not trades:return {"n":0}
    values=[t["R"] for t in trades];balance=peak=dd=0
    for v in values:
        balance+=v;peak=max(peak,balance);dd=max(dd,peak-balance)
    return {"n":len(values),"winrate_pct":round(100*sum(v>0 for v in values)/len(values),2),
            "expectancy_R":round(mean(values),4),"net_R":round(sum(values),2),"max_drawdown_R":round(dd,2)}

def main():
    symbol=sys.argv[1] if len(sys.argv)>1 else "XAUUSD"
    tf=sys.argv[2] if len(sys.argv)>2 else "M15"
    import walk_forward
    walk_forward.SYMBOL=symbol;walk_forward.TF=tf
    bars=fetch();n=len(bars)
    if n<1500:raise SystemExit("Need >=1500 candles")
    train=int(n*.6);valid=int(n*.8)
    cost=float(os.getenv("BACKTEST_COST_PRICE","0.30" if symbol=="XAUUSD" else "2"))
    configs=[]
    # Hypotheses are chosen on TRAIN only. Validation chooses ONE winner.
    for f in (9,14,20):
      for s in (35,50,100):
       for k in (1.0,1.5,2.0):
        for rr in (1.0,1.5,2.0):
         for direction in ("BOTH","LONG","SHORT"):
          for session,hours in (("ALL",None),("EU",set(range(7,13))),("US",set(range(13,21)))):
           tr=test(bars,f,s,k,rr,cost,0,train,hours,direction)
           st=stats(tr)
           if st["n"]>=35 and st["expectancy_R"]>0 and st["net_R"]>0:
            configs.append((st["expectancy_R"],(f,s,k,rr,direction,session,hours),st))
    print("CANDLES",n,"TRAIN",train,"VALIDATION",valid-train,"FINAL HOLDOUT",n-valid)
    if not configs:
        print("No positive candidate with sufficient trades in training. Do not deploy.");return
    # Limit hypothesis search and choose by validation. No final holdout inspection until selection.
    configs.sort(key=lambda x:x[0],reverse=True)
    finalists=[]
    for _,p,train_stats in configs[:20]:
        f,s,k,rr,direction,session,hours=p
        val=stats(test(bars,f,s,k,rr,cost,train,valid,hours,direction))
        if val["n"]>=12 and val["expectancy_R"]>0:
            finalists.append((val["expectancy_R"],p,train_stats,val))
    if not finalists:
        print("No candidate survived validation. Do not deploy.");return
    _,p,training,validation=max(finalists,key=lambda x:x[0])
    f,s,k,rr,direction,session,hours=p
    final=stats(test(bars,f,s,k,rr,cost,valid,n,hours,direction))
    baseline=stats(test(bars,14,100,2.0,1.5,cost,valid,n,None,"BOTH"))
    print("SELECTED",{"ema_fast":f,"ema_slow":s,"atr_stop":k,"reward_risk":rr,
                      "direction":direction,"session_utc":session})
    print("TRAIN",json.dumps(training))
    print("VALIDATION",json.dumps(validation))
    print("FINAL_HOLDOUT",json.dumps(final))
    print("BASELINE_FINAL_HOLDOUT",json.dumps(baseline))
    print("CAUTION: selection bias, OHLC ambiguity, gaps, spread variation, commission, swap, news and execution are not fully modeled.")
    print("No automatic live trading; verify with tick data and rolling walk-forward windows.")
if __name__=="__main__":main()
