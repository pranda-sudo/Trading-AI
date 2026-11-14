"""Pattern + indicator research, using CLOSED OHLC candles only.
Pure Python; no orders, no future candles, no fitted parameters.
Usage: import pattern_indicators; pattern_indicators.evaluate(bars)
bars: chronological list of dicts with open/high/low/close.
Returns signal on last CLOSED bar, or None.
"""
def ema(values, length):
    if len(values)<length: return None
    value=sum(values[:length])/length
    for x in values[length:]: value+=2/(length+1)*(x-value)
    return value

def rsi(values, length=14):
    if len(values)<length+1:return None
    diffs=[values[i]-values[i-1] for i in range(len(values)-length,len(values))]
    gains=sum(max(x,0) for x in diffs)/length
    losses=sum(max(-x,0) for x in diffs)/length
    return 100 if losses==0 and gains>0 else 50 if losses==0 else 100-100/(1+gains/losses)

def atr(bars, length=14):
    if len(bars)<length+1:return None
    trs=[]
    for i in range(len(bars)-length,len(bars)):
        a,b=bars[i-1],bars[i]
        trs.append(max(b['high']-b['low'],abs(b['high']-a['close']),abs(b['low']-a['close'])))
    return sum(trs)/length

def detect(bars):
    """Confirmed candle patterns and prior-level break/retest.
    Does not use unconfirmed pivots or later candles.
    """
    if len(bars)<26:return []
    p,c=bars[-2],bars[-1]
    body=lambda x:abs(x['close']-x['open'])
    rng=max(c['high']-c['low'],1e-10)
    upper=c['high']-max(c['open'],c['close'])
    lower=min(c['open'],c['close'])-c['low']
    bullish=c['close']>c['open']
    bearish=c['close']<c['open']
    out=[]
    if bullish and p['close']<p['open'] and c['open']<=p['close'] and c['close']>=p['open'] and body(c)>=body(p)*0.8:
        out.append(('BULL_ENGULF','LONG'))
    if bearish and p['close']>p['open'] and c['open']>=p['close'] and c['close']<=p['open'] and body(c)>=body(p)*0.8:
        out.append(('BEAR_ENGULF','SHORT'))
    if lower>=2*max(body(c),rng*0.08) and upper<=rng*.2 and c['close']>=c['low']+rng*.6:
        out.append(('BULL_PIN','LONG'))
    if upper>=2*max(body(c),rng*0.08) and lower<=rng*.2 and c['close']<=c['low']+rng*.4:
        out.append(('BEAR_PIN','SHORT'))
    # Retest is based on a prior 20-bar high/low, excluding last two bars.
    level_hi=max(x['high'] for x in bars[-22:-2])
    level_lo=min(x['low'] for x in bars[-22:-2])
    tolerance=max(atr(bars),1e-10)*.25
    if p['close']>level_hi and c['low']<=level_hi+tolerance and c['close']>level_hi and bullish:
        out.append(('BREAK_RETEST_UP','LONG'))
    if p['close']<level_lo and c['high']>=level_lo-tolerance and c['close']<level_lo and bearish:
        out.append(('BREAK_RETEST_DOWN','SHORT'))
    return out

def evaluate(bars, higher_bars=None):
    """All bars must already be closed. H1 optional, but required for confirmation."""
    if len(bars)<55 or higher_bars is None or len(higher_bars)<55:return None
    closes=[float(b['close']) for b in bars]
    hcloses=[float(b['close']) for b in higher_bars]
    fast,slow=ema(closes,20),ema(closes,50)
    hfast,hslow=ema(hcloses,20),ema(hcloses,50)
    momentum=rsi(closes,14)
    volatility=atr(bars,14)
    patterns=detect(bars)
    if not patterns or not volatility or volatility<=0:return None
    for name,side in patterns:
        if side=='LONG' and fast>slow and hfast>hslow and 50<=momentum<=70 and bars[-1]['close']>fast:
            return {'side':side,'pattern':name,'rsi14':round(momentum,2),'atr14':volatility,'ema20':fast,'ema50':slow,'confirmation':'M15+H1'}
        if side=='SHORT' and fast<slow and hfast<hslow and 30<=momentum<=50 and bars[-1]['close']<fast:
            return {'side':side,'pattern':name,'rsi14':round(momentum,2),'atr14':volatility,'ema20':fast,'ema50':slow,'confirmation':'M15+H1'}
    return None
