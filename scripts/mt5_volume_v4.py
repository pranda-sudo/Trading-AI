import argparse, sqlite3, time, json, os
from pathlib import Path
from datetime import datetime, timezone
import MetaTrader5 as mt5
import numpy as np
from mt5_volume_v3 import profile

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--terminal",required=True)
    p.add_argument("--out",default="live_v4")
    p.add_argument("--symbol",default="XAUUSD")
    p.add_argument("--start",default="2026-11-21")
    p.add_argument("--once",action="store_true")
    a=p.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(out/"quotes.sqlite",timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS ticks (msc INTEGER, seq INTEGER,bid REAL,ask REAL,flags INTEGER, PRIMARY KEY(msc,seq))")
    db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, cursor INTEGER)")
    start=int(datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc).timestamp())
    db.execute("INSERT OR IGNORE INTO state VALUES(1,?)",(start,)); db.commit()
    def guard():
        acc=mt5.account_info()
        if acc is None or acc.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise RuntimeError("Demo required")
    def sync():
        if not mt5.initialize(a.terminal): raise RuntimeError(mt5.last_error())
        try:
            guard()
            if not mt5.symbol_select(a.symbol,True): raise RuntimeError(mt5.last_error())
            cursor=db.execute("SELECT cursor FROM state WHERE id=1").fetchone()[0]
            end=int(time.time()//60)*60
            while cursor<end:
                guard()
                stop=min(cursor+3600,end)
                t=mt5.copy_ticks_range(a.symbol,datetime.fromtimestamp(cursor,timezone.utc),datetime.fromtimestamp(stop,timezone.utc),mt5.COPY_TICKS_INFO)
                if t is None: raise RuntimeError(mt5.last_error())
                t=t[(t["time_msc"]>=cursor*1000)&(t["time_msc"]<stop*1000)]
                if len(t)==0 and datetime.fromtimestamp(cursor,timezone.utc).weekday()<5:
                    bars=mt5.copy_rates_range(a.symbol,mt5.TIMEFRAME_M1,datetime.fromtimestamp(cursor,timezone.utc),datetime.fromtimestamp(stop-1,timezone.utc))
                    if bars is None or len(bars): raise RuntimeError("Missing quotes: "+str(cursor))
                rows=[]; prev=-1; seq=0
                for r in t:
                    ms=int(r["time_msc"])
                    seq=seq+1 if ms==prev else 0; prev=ms
                    rows.append((ms,seq,float(r["bid"]),float(r["ask"]),int(r["flags"])))
                with db:
                    db.executemany("INSERT OR IGNORE INTO ticks VALUES(?,?,?,?,?)",rows)
                    db.execute("UPDATE state SET cursor=? WHERE id=1",(stop,))
                cursor=stop
            daily=cursor//86400*86400
            week=daily-datetime.fromtimestamp(daily,timezone.utc).weekday()*86400
            def stats(lo,hi):
                hist={}; n=0; total=0.; square=0.
                for k,c,s,q in db.execute("SELECT CAST((bid+ask)/2 AS INTEGER),count(*),sum((bid+ask)/2),sum(((bid+ask)/2)*((bid+ask)/2)) FROM ticks WHERE msc>=? AND msc<? AND bid>0 AND ask>=bid GROUP BY 1",(lo*1000,hi*1000)):
                    hist[k]=c;n+=c;total+=s;square+=q
                if not n:return None
                avg=total/n; sigma=float(np.sqrt(max(0,square/n-avg*avg)))
                poc,vah,val=profile(hist,1)
                return dict(count=n,vwap_proxy=avg,sigma=sigma,poc=float(poc),vah=float(vah),val=float(val),bands={str(i):avg+i*sigma for i in (-3,-2,-1,1,2,3)})
            result=dict(symbol=a.symbol,through_utc=datetime.fromtimestamp(cursor,timezone.utc).isoformat(),daily=stats(daily,cursor),weekly=stats(week,cursor),source="quote activity; not exchange volume",week_partial=week<start)
            tmp=out/"latest.tmp";tmp.write_text(json.dumps(result),encoding="utf-8");os.replace(tmp,out/"latest.json")
            print("OK",result["through_utc"],flush=True)
        finally: mt5.shutdown()
    while True:
        try: sync()
        except Exception as e:
            print("ERROR",repr(e),flush=True)
            if a.once: raise
        if a.once: break
        time.sleep(60)
if __name__=="__main__": main()
