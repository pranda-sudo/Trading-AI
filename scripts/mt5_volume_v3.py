import argparse, csv, os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import MetaTrader5 as mt5
import numpy as np

def save(path, header, rows):
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    os.replace(tmp, path)

def profile(hist, step):
    if not hist:
        return (None, None, None)
    lo, hi = min(hist), max(hist)
    h = np.array([hist.get(i, 0) for i in range(lo, hi+1)])
    p = l = r = int(h.argmax())
    s = h[p]
    while s < .7*h.sum() and (l>0 or r<len(h)-1):
        if (h[l-1] if l>0 else -1) >= (h[r+1] if r<len(h)-1 else -1):
            l -= 1
            s += h[l]
        else:
            r += 1
            s += h[r]
    return ((lo+p+.5)*step,(lo+r+1)*step,(lo+l)*step)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--terminal", required=True)
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--tick-days", type=int, default=365)
    p.add_argument("--out", default="data_v2")
    p.add_argument("--bin", type=float, default=1)
    a=p.parse_args()
    if not 1<=a.days<=365 or not 1<=a.tick_days<=365 or not .01<=a.bin<=100:
        p.error("Invalid range")
    out=Path(a.out)/a.symbol/("bin_"+str(a.bin))
    out.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize(a.terminal):
        raise RuntimeError(mt5.last_error())
    try:
        def guard():
            acc=mt5.account_info()
            if acc is None or acc.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
                raise RuntimeError("Demo required")
        guard()
        if not mt5.symbol_select(a.symbol,True):
            raise RuntimeError("Symbol unavailable")
        end=datetime.now(timezone.utc).replace(second=0,microsecond=0)
        today=end.replace(hour=0,minute=0)
        start=today-timedelta(days=a.days)
        bars=mt5.copy_rates_range(a.symbol,mt5.TIMEFRAME_M1,start,end-timedelta(seconds=1))
        if bars is None or not len(bars):
            raise RuntimeError(mt5.last_error())
        bars=np.sort(bars,order="time")
        save(out/"m1.csv",bars.dtype.names,bars.tolist())
        print("M1 actual coverage:",datetime.fromtimestamp(int(bars[0]["time"]),timezone.utc),datetime.fromtimestamp(int(bars[-1]["time"]),timezone.utc),len(bars),flush=True)
        daily=[]; weekly=[]; intraday=[]
        previous=(None,None,None); week=None; wh={}
        for day in np.unique(bars["time"]//86400):
            date=datetime.fromtimestamp(int(day)*86400,timezone.utc).date()
            wk=date-timedelta(days=date.weekday())
            if week!=wk:
                if week is not None:
                    weekly.append([week,*profile(wh,a.bin)])
                week=wk; wh={}
            hist={}; weight=mean=m2=0.
            b=bars[bars["time"]//86400==day]
            for row in b:
                price=float((row["high"]+row["low"]+row["close"])/3)
                v=float(row["tick_volume"])
                if v>0:
                    old=mean
                    weight+=v
                    mean+=v/weight*(price-mean)
                    m2+=v*(price-old)*(price-mean)
                    k=int(np.floor(price/a.bin))
                    hist[k]=hist.get(k,0)+v
                    wh[k]=wh.get(k,0)+v
                if weight:
                    sigma=np.sqrt(max(0,m2/weight))
                    intraday.append([int(row["time"])+60,mean,sigma,*[mean+i*sigma for i in (-3,-2,-1,1,2,3)],*previous])
            previous=profile(hist,a.bin)
            daily.append([date,len(b),weight,mean,np.sqrt(max(0,m2/weight)) if weight else None,*previous])
        if week is not None:
            weekly.append([week,*profile(wh,a.bin)])
        save(out/"daily_profile.csv",["utc_date","bars","tick_volume","vwap_proxy","sigma","poc","vah","val"],daily)
        save(out/"weekly_profile.csv",["utc_week","poc","vah","val"],weekly)
        save(out/"intraday.csv",["available_utc_epoch","vwap","sigma","minus3","minus2","minus1","plus1","plus2","plus3","prev_poc","prev_vah","prev_val"],intraday)
        tickdir=out/"ticks"; tickdir.mkdir(exist_ok=True)
        tickprofiles=[]
        for n in range(a.tick_days,-1,-1):
            guard()
            day=today-timedelta(days=n)
            stop=min(day+timedelta(days=1),end)
            if stop<=day: continue
            hist={}; count=0; sumprice=0.; sumsq=0.
            path=tickdir/(day.date().isoformat()+".csv")
            marker=path.with_suffix(".complete")
            if marker.exists() and path.exists() and stop < end:
                cached=list(csv.reader(marker.open()))
                if cached:
                    tickprofiles.append(cached[0])
                print("Cached tick day",day.date(),flush=True)
                continue
            tmp=path.with_suffix(".tmp")
            ok=True
            with tmp.open("w",newline="") as f:
                w=csv.writer(f)
                for hour in range(24):
                    t=day+timedelta(hours=hour)
                    e=min(t+timedelta(hours=1),stop)
                    if t>=e: break
                    ticks=mt5.copy_ticks_range(a.symbol,t,e,mt5.COPY_TICKS_INFO)
                    if ticks is None:
                        print("Tick request failed:",t,mt5.last_error(),flush=True)
                        ok=False; break
                    ticks=ticks[(ticks["time_msc"]>=int(t.timestamp()*1000)) & (ticks["time_msc"]<int(e.timestamp()*1000))]
                    if hour==0: w.writerow(ticks.dtype.names)
                    w.writerows(ticks.tolist())
                    valid=ticks[(ticks["bid"]>0)&(ticks["ask"]>=ticks["bid"])]
                    mid=(valid["bid"]+valid["ask"])/2
                    count+=len(mid); sumprice+=float(mid.sum()); sumsq+=float((mid**2).sum())
                    keys,counts=np.unique(np.floor(mid/a.bin).astype(int),return_counts=True)
                    for k,c in zip(keys,counts): hist[int(k)]=hist.get(int(k),0)+int(c)
            if not ok:
                tmp.unlink(missing_ok=True)
                continue
            os.replace(tmp,path)
            record=[]
            if count:
                avg=sumprice/count
                record=[day.date(),count,avg,np.sqrt(max(0,sumsq/count-avg**2)),*profile(hist,a.bin)]
                tickprofiles.append(record)
            if stop < end and count:
                mtmp=marker.with_suffix(".marker_tmp")
                with mtmp.open("w",newline="") as f:
                    csv.writer(f).writerow(record)
                os.replace(mtmp,marker)
            print("Tick day",day.date(),count,flush=True)
        save(out/"tick_profile.csv",["utc_date","quote_count","mid_vwap_proxy","sigma","poc","vah","val"],tickprofiles)
        print("OK",out.resolve(),flush=True)
    finally:
        mt5.shutdown()

if __name__=="__main__":
    main()
