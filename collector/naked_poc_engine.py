"""Local-only forward Naked POC research. No orders, no cloud writes.
Uses the existing Supabase closed/forming OHLC feed via read-only GET.
"""
import argparse, csv, json, math, os, time, tempfile
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import urlencode

FRAME=300
def epoch(s):
    return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp())
def finite(x):
    try: return math.isfinite(float(x))
    except (TypeError,ValueError): return False
def get(table, params):
    url=os.environ['SUPABASE_URL'].rstrip('/')
    key=os.getenv('SUPABASE_SECRET_KEY') or os.environ['SUPABASE_SERVICE_ROLE_KEY']
    if url!='https://hatzdirgwutbdarpgwro.supabase.co': raise ValueError('Unexpected project URL')
    h={'apikey':key}
    if not key.startswith('sb_secret_'): h['Authorization']='Bearer '+key
    with urlopen(Request(url+'/rest/v1/'+table+'?'+urlencode(params),headers=h),timeout=15) as r:
        return json.load(r)
def save(path,obj):
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False,encoding='utf8') as f:
        json.dump(obj,f,allow_nan=False,indent=2); name=f.name
    os.replace(name,path)
def new_state(now):
    return {'version':1,'started_utc':now,'levels':{},'health':'STARTING'}
def process(state,rows,bars,forming,now):
    # Work in raw MT5 candle keys, infer offset from fresh corrected forming bar.
    raw=epoch(forming['candle_time']); utc=epoch(forming['candle_time_utc'])
    offset=raw-utc
    if offset not in (0,7200,10800) or not 0<=now-epoch(forming['received_at'])<=45 or not utc<=now<utc+FRAME:
        raise ValueError('Forming candle stale or clock unverified')
    if any(not finite(forming[k]) for k in ('low','high')): raise ValueError('Invalid forming OHLC')
    by={epoch(b['candle_time']):b for b in bars if epoch(b['candle_time'])<raw}
    candidates={}
    for r in rows:
        if r['kind']!='CANDLE_POC_CANDIDATE' or r['symbol']!='XAUUSD' or r['timeframe']!='PERIOD_M5': continue
        try:
            t=int(r['time0_mt5']); obs=int(r['observed_utc_epoch']); p=float(r['price0'])
            if not math.isfinite(p) or p<=0 or int(r['window'])!=0 or r['status']!='OBSERVED_UNVERIFIED' or not 0<=now-obs<=45: continue
            if t not in by or t-offset<state['started_utc'] or t+FRAME>raw or obs<t-offset+FRAME: continue
            b=by[t]
            if not float(b['low'])<=p<=float(b['high']): continue
            candidates.setdefault(t,set()).add(round(p,8))
        except (KeyError,ValueError,TypeError): continue
    levels=state['levels']
    for t,ps in candidates.items():
        k=str(t)
        if len(ps)!=1:
            if k in levels and levels[k]['status']=='ACTIVE': levels[k]['status']='UNVERIFIED_CONFLICT'
            continue
        p=next(iter(ps))
        if k in levels:
            if levels[k]['price']!=p and levels[k]['status']=='ACTIVE': levels[k]['status']='UNVERIFIED_REVISION'
            continue
        levels[k]={'price':p,'bar_time_mt5':t,'bar_utc':t-offset,'first_observed_utc':now,'status':'ACTIVE','checked_through':t,'offset':offset}
    for k,l in levels.items():
        if l['status']!='ACTIVE': continue
        if l['offset']!=offset:
            l['status']='UNVERIFIED_CLOCK_CHANGE';continue
        t=l['checked_through']+FRAME
        while t<raw:
            b=by.get(t)
            if b is None:
                l['status']='UNVERIFIED_GAP';break
            if float(b['low'])<=l['price']<=float(b['high']):
                l['status']='TOUCHED';l['touch_bar_mt5']=t;l['detected_utc']=now;break
            l['checked_through']=t;t+=FRAME
        if l['status']=='ACTIVE' and float(forming['low'])<=l['price']<=float(forming['high']):
            l['status']='TOUCHED';l['touch_bar_mt5']=raw;l['detected_utc']=now
    # Bounded local retention; do not resurrect pruned levels from old snapshots.
    state['started_utc']=max(state['started_utc'],now-30*86400)
    state['levels']={k:l for k,l in levels.items() if l['bar_utc']>=state['started_utc']}
    state['health']='OBSERVED_UNVERIFIED';state['checked_utc']=now
    return state
def poll(state,path):
    now=int(time.time())
    if not 0<=now-path.stat().st_mtime<=45: raise ValueError('V3 CSV stale')
    with path.open(encoding='cp1252',newline='') as f: rows=list(csv.DictReader(f))
    forms=get('market_forming_candles',{'symbol':'eq.XAUUSD','timeframe':'eq.M5','select':'candle_time,candle_time_utc,low,high,received_at'})
    if len(forms)!=1: raise ValueError('Missing forming candle')
    # Fetch bounded incremental data, plus enough closed bars to validate recent POC.
    # Initial source history is never imported as POC.
    raw=epoch(forms[0]['candle_time'])
    active=[l['checked_through'] for l in state['levels'].values() if l['status']=='ACTIVE']
    begin=min([raw-12*FRAME]+active)
    if raw-begin>1000*FRAME: raise ValueError('Too long since last successful check; manual review needed')
    start=datetime.fromtimestamp(begin,timezone.utc).isoformat()
    bars=get('market_candles',{'symbol':'eq.XAUUSD','timeframe':'eq.M5','select':'candle_time,low,high','candle_time':'gte.'+start,'order':'candle_time.asc','limit':'1000'})
    return process(state,rows,bars,forms[0],int(time.time()))
def main():
    a=argparse.ArgumentParser();a.add_argument('--once',action='store_true');a.add_argument('--self-test',action='store_true');args=a.parse_args()
    if args.self_test:
        import unittest
        class Tests(unittest.TestCase):
            def test_forward_touch(self):
                t=1800000000; iso=lambda v:datetime.fromtimestamp(v,timezone.utc).isoformat()
                s=new_state(t); row={'kind':'CANDLE_POC_CANDIDATE','symbol':'XAUUSD','timeframe':'PERIOD_M5','time0_mt5':str(t+7200),'observed_utc_epoch':str(t+310),'price0':'100','window':'0','status':'OBSERVED_UNVERIFIED'}
                b=[{'candle_time':iso(t+7200),'low':99,'high':101}]
                f={'candle_time':iso(t+7500),'candle_time_utc':iso(t+300),'received_at':iso(t+310),'low':101,'high':102}
                process(s,[row],b,f,t+310);self.assertEqual(s['levels'][str(t+7200)]['status'],'ACTIVE')
                f['low']=99;process(s,[row],b,f,t+311);self.assertEqual(s['levels'][str(t+7200)]['status'],'TOUCHED')
            def test_no_history(self):
                s=new_state(1800000000); self.assertEqual(s['levels'],{})
        unittest.main(argv=['self-test']);return
    base=Path(__file__).resolve().parent; statefile=base/'naked_poc_state.json'
    path=Path(os.environ['APPDATA'])/'MetaQuotes'/'Terminal'/'Common'/'Files'/'TradingAI_CD_Objects_V3.csv'
    state=json.loads(statefile.read_text(encoding='utf8')) if statefile.exists() else new_state(int(time.time()))
    # Persist the start boundary even if the first poll fails.
    save(statefile,state)
    while True:
        try:
            state=poll(state,path)
            save(statefile,state)
            counts={k:sum(l['status']==k for l in state['levels'].values()) for k in ('ACTIVE','TOUCHED')}
            print(datetime.now(timezone.utc).isoformat(),counts,'total',len(state['levels']),'OBSERVED_UNVERIFIED',flush=True)
        except Exception as e:
            state['health']='BLOCKED';save(statefile,state)
            print('BLOCKED',type(e).__name__,str(e),flush=True)
            if args.once: raise SystemExit(1)
        if args.once: break
        time.sleep(15)
if __name__=='__main__':main()
