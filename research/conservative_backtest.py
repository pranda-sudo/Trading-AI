"""Conservative multi-timeframe research backtest. NO live orders.
Run: py -3.11 C:\\AITrading\\research\\conservative_backtest.py XAUUSD
Requires existing walk_forward.py, requests, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
Uses closed H1/H4/M15 bars and next M5 open. News filter NOT implemented.
"""
import os,sys,json
from datetime import datetime,timezone,timedelta
from bisect import bisect_right
import walk_forward

def dt(s):
    return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc)
def load(symbol,tf):
    walk_forward.SYMBOL=symbol;walk_forward.TF=tf
    b=walk_forward.fetch()
    for x in b:x["_t"]=dt(x["candle_time"])
    return b
def ema(v,n):
    return walk_forward.ema(v,n)
def series(b):
    c=[float(x["close"]) for x in b];h=[float(x["high"]) for x in b];l=[float(x["low"]) for x in b]
    tr=[h[0]-l[0]]+[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,len(b))]
    atr=[None]*len(b)
    for i in range(13,len(b)):atr[i]=sum(tr[i-13:i+1])/14
    return {"close":c,"high":h,"low":l,"ema20":ema(c,20),"ema50":ema(c,50),"ema100":ema(c,100),"atr":atr,
            "end":[x["_t"]+timedelta(minutes={"M5":5,"M15":15,"H1":60,"H4":240}[b[0]["_tf"]]) for x in b]}
def at_closed(s,t):
    return bisect_right(s["end"],t)-1
def trend(s,i):
    if i<105:return 0
    c=s["close"];e20=s["ema20"];e50=s["ema50"];e100=s["ema100"]
    if c[i]>e50[i]>e100[i] and e50[i]>e50[i-4]:return 1
    if c[i]<e50[i]<e100[i] and e50[i]<e50[i-4]:return -1
    return 0
def score(trades):
    if not trades:return {"n":0,"winrate_pct":None,"expectancy_R":None,"net_R":0,"max_drawdown_R":0}
    vals=[t["R"] for t in trades];eq=peak=dd=0
    for v in vals:eq+=v;peak=max(peak,eq);dd=max(dd,peak-eq)
    return {"n":len(vals),"winrate_pct":round(100*sum(x>0 for x in vals)/len(vals),2),
            "expectancy_R":round(sum(vals)/len(vals),4),"net_R":round(sum(vals),2),"max_drawdown_R":round(dd,2)}
def test(symbol,rr=2.0,atr_stop=1.5,cost=0.30):
    data={tf:load(symbol,tf) for tf in ("M5","M15","H1","H4")}
    for tf,b in data.items():
        if len(b)<150:raise RuntimeError(f"Insufficient {tf}: {len(b)} bars")
        for x in b:x["_tf"]=tf
    S={tf:series(b) for tf,b in data.items()}
    b=data["M5"];m=S["M5"];trades=[];next_i=0
    for i in range(110,len(b)-2):
        if i<next_i:continue
        # Evaluate at close of M5 bar i; enter at next M5 open.
        signal_t=m["end"][i]
        j={tf:at_closed(S[tf],signal_t) for tf in ("M15","H1","H4")}
        if min(j.values())<110:continue
        a=trend(S["H1"],j["H1"]);d=trend(S["H4"],j["H4"])
        if a==0 or a!=d:continue
        z=S["M15"];k=j["M15"]
        # M15 pullback to EMA20, then close back on trend side.
        if a==1:
            setup=z["low"][k]<=z["ema20"][k] and z["close"][k]>z["ema20"][k]
            confirm=m["close"][i]>m["ema20"][i] and m["close"][i]>float(b[i]["open"])
        else:
            setup=z["high"][k]>=z["ema20"][k] and z["close"][k]<z["ema20"][k]
            confirm=m["close"][i]<m["ema20"][i] and m["close"][i]<float(b[i]["open"])
        if not(setup and confirm):continue
        # Only one entry per M15 candle; avoids multiple signals from same setup.
        if i>0 and at_closed(z,m["end"][i-1])==k:continue
        atr=z["atr"][k]
        if atr is None or atr<=0:continue
        risk=atr*atr_stop
        entry=float(b[i+1]["open"])+a*cost/2
        sl=entry-a*risk;tp=entry+a*risk*rr
        outcome=None;end=min(i+1+36,len(b)-1)
        for p in range(i+1,end+1):
            o=float(b[p]["open"]);hi=float(b[p]["high"]);lo=float(b[p]["low"])
            if (a==1 and o<sl) or (a==-1 and o>sl):
                outcome=a*(o-entry)/risk;end=p;break
            stop=lo<=sl if a==1 else hi>=sl
            target=hi>=tp if a==1 else lo<=tp
            if stop or target:
                outcome=-1 if stop else rr;end=p;break # ambiguous OHLC => stop first
        if outcome is None:outcome=a*(float(b[end]["close"])-entry)/risk
        outcome-=cost/(2*risk)
        trades.append({"time":b[i+1]["candle_time"],"side":"LONG" if a==1 else "SHORT",
                       "entry":round(entry,4),"sl":round(sl,4),"tp":round(tp,4),"R":round(outcome,4)})
        next_i=end+1
    return trades
def main():
    symbol=sys.argv[1] if len(sys.argv)>1 else "XAUUSD"
    cost=float(os.getenv("BACKTEST_COST_PRICE","0.30" if symbol=="XAUUSD" else "2"))
    trades=test(symbol,cost=cost)
    # This is diagnostic, NOT a fresh holdout or validated strategy selection.
    n=len(trades);split=int(n*.7)
    print("CONSERVATIVE MTF RESEARCH",symbol,"trades",n)
    print("FIRST 70%",json.dumps(score(trades[:split])))
    print("LAST 30%",json.dumps(score(trades[split:])))
    print("LAST 10 TRADES",json.dumps(trades[-10:],ensure_ascii=False))
    print("LIMITATIONS: missing macro-news blackout, tick-level costs, true S/R retest, DST/session checks; H4 candle timestamps assumed OPEN and UTC.")
    print("Do not deploy. Prior holdouts already viewed. Re-test on future unseen data.")
if __name__=="__main__":main()
