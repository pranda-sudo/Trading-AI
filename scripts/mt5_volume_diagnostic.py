import MetaTrader5 as mt5
import numpy as np
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Optional: set the exact path of the DEMO terminal executable.
TERMINAL_PATH = ''
ALIASES = {'XAUUSD':['XAUUSD','GOLD'], 'USTECH':['USTECH','US100','NAS100','NASDAQ'], 'US500':['US500','SPX500'], 'US30':['US30','DJ30'], 'DE40':['DE40','GER40','DAX40']}

def count(a, field):
    return int(np.count_nonzero(a[field])) if a is not None and field in a.dtype.names else None

def error():
    return list(mt5.last_error())

def main():
    if not (mt5.initialize(path=TERMINAL_PATH) if TERMINAL_PATH else mt5.initialize()):
        raise RuntimeError(str(error()))
    try:
        account = mt5.account_info()
        if account is None or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise RuntimeError('Open the DEMO MT5 terminal first. Diagnostic stopped.')
        symbols = mt5.symbols_get() or []
        report = {'generated_utc':datetime.now(timezone.utc).isoformat(), 'demo':True, 'instruments':{}}
        end = datetime.now(timezone.utc)
        for name, aliases in ALIASES.items():
            candidates = sorted([s.name for s in symbols if any(a in s.name.upper() for a in aliases)])
            print('\n',name, candidates, flush=True)
            if not candidates:
                report['instruments'][name]={'error':'symbol_not_found'}; continue
            symbol = min(candidates,key=lambda s:(not mt5.symbol_info(s).visible, min(abs(len(s)-len(a)) for a in aliases),s))
            r = {'symbol':symbol,'candidates':candidates,'days':[]}
            report['instruments'][name]=r
            if not mt5.symbol_select(symbol,True):
                r['error']=error();continue
            info=mt5.symbol_info(symbol)
            r['point']=info.point
            r['book_depth_advertised']=info.ticks_bookdepth
            for d in range(7):
                start=end-timedelta(days=d+1); stop=end-timedelta(days=d)
                ticks=mt5.copy_ticks_range(symbol,start,stop,mt5.COPY_TICKS_ALL)
                day={'from_utc':start.isoformat(),'to_utc':stop.isoformat()}
                if ticks is None: day['error']=error()
                else:
                    day.update({'ticks':len(ticks), **{f+'_nonzero':count(ticks,f) for f in ['bid','ask','last','volume','volume_real']}})
                    for label,mask in [('buy',32),('sell',64),('last_change',8),('volume_change',16)]:
                        day[label+'_flags']=int(np.count_nonzero(ticks['flags'] & mask))
                    day['priced_trade_with_volume_and_side']=int(np.count_nonzero((ticks['last']>0)&((ticks['volume_real']>0)|(ticks['volume']>0))&(((ticks['flags']&32)>0)^((ticks['flags']&64)>0))))
                r['days'].append(day)
                print(symbol, start.date(), day.get('ticks',day.get('error')),flush=True)
            bars=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,end-timedelta(days=7),end)
            r['m1_bars'] = {'error':error()} if bars is None else {'count':len(bars),'tick_volume_nonzero':count(bars,'tick_volume'),'real_volume_nonzero':count(bars,'real_volume')}
            subscribed=mt5.market_book_add(symbol)
            r['dom_subscribed']=bool(subscribed)
            if subscribed:
                try:
                    book=mt5.market_book_get(symbol)
                    r['dom_entries']=len(book) if book is not None else None
                finally: mt5.market_book_release(symbol)
            else: r['dom_error']=error()
        path=Path(__file__).resolve().parent/'mt5_volume_report.json'
        path.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('\nREPORT:',path)
    finally: mt5.shutdown()

if __name__=='__main__': main()
