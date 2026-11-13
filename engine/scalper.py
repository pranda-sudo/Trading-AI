"""Scalper V1: deterministic research backtester, NOT a live trading engine.
CSV columns: time,open,high,low,close, optional spread (price units).
All times ISO-8601 with explicit UTC offset; candles sorted ascending.
Execution model: signals at completed bar close, entry at NEXT bar open,
stop/target intrabar; if both touched, assume STOP first (conservative).
No leverage, no broker order execution, no forward-looking indicators.
"""
import csv
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

@dataclass
class Config:
    fast: int = 20
    slow: int = 50
    stop_distance: float = 2.0
    reward_risk: float = 1.5
    risk_fraction: float = 0.0025
    max_trades_day: int = 5
    daily_loss_fraction: float = 0.015
    spread: float = 0.15
    slippage: float = 0.05
    commission_per_trade: float = 0.0
    session_timezone: str = "Europe/Prague"
    session_start: str = "09:00"
    last_entry: str = "16:30"
    flatten_at: str = "16:50"
    starting_equity: float = 10000.0

def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        dt = datetime.fromisoformat(row["time"].replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("Timestamp must contain UTC offset")
        bar = {k:float(row[k]) for k in ("open","high","low","close")}
        if min(bar.values()) <= 0 or bar["high"] < max(bar["open"],bar["close"],bar["low"]) or bar["low"] > min(bar["open"],bar["close"]):
            raise ValueError("Invalid OHLC")
        bar["time"] = dt
        bar["spread"] = float(row.get("spread") or 0)
        out.append(bar)
    if any(out[i]["time"] >= out[i+1]["time"] for i in range(len(out)-1)):
        raise ValueError("Times must be strictly increasing")
    return out

def hhmm(s):
    return time.fromisoformat(s)

def backtest(bars, cfg=Config()):
    if cfg.fast < 2 or cfg.slow <= cfg.fast or cfg.stop_distance <= 0 or cfg.reward_risk <= 0 or not (0 < cfg.risk_fraction < 1) or cfg.max_trades_day < 1 or cfg.daily_loss_fraction <= 0 or cfg.spread < 0 or cfg.slippage < 0:
        raise ValueError("Invalid strategy parameters")
    tz = ZoneInfo(cfg.session_timezone)
    start, last, flatten = map(hhmm,(cfg.session_start,cfg.last_entry,cfg.flatten_at))
    if not start < last < flatten:
        raise ValueError("Session hours must satisfy start < last_entry < flatten_at")
    equity = cfg.starting_equity
    if equity <= 0: raise ValueError("starting_equity must be positive")
    trades, curve = [], []
    position = None
    day = None
    day_start = equity
    count = 0
    # Position size is in synthetic price-units, NOT broker lots.
    def exit_position(p, price, stamp, reason):
        nonlocal equity, position
        # Entry is adjusted for half-spread and slippage; exit similarly.
        exit_price = price + (-1 if p["side"] == 1 else 1) * (p["spread"]/2 + cfg.slippage)
        pnl = (exit_price-p["entry"])*p["side"]*p["qty"]-cfg.commission_per_trade
        equity += pnl
        trades.append({"entry_time":p["time"].isoformat(),"exit_time":stamp.isoformat(),
                       "side":"LONG" if p["side"]==1 else "SHORT","entry":round(p["entry"],6),
                       "exit":round(exit_price,6),"pnl":round(pnl,2),"reason":reason})
        position = None
    for i, b in enumerate(bars):
        local = b["time"].astimezone(tz)
        d, clock = local.date(), local.time().replace(tzinfo=None)
        if day != d:
            if position:
                # Last known prior close if crossing a day boundary.
                exit_position(position,bars[i-1]["close"],bars[i-1]["time"],"day_boundary")
            day,day_start,count=d,equity,0
        spread = b["spread"] if b["spread"]>0 else cfg.spread
        if position:
            p=position
            # Treat OHLC as mid; bid/ask costs handled at entry and exit.
            if p["side"]==1:
                stop_hit=b["low"]<=p["stop"]
                target_hit=b["high"]>=p["target"]
            else:
                stop_hit=b["high"]>=p["stop"]
                target_hit=b["low"]<=p["target"]
            if stop_hit:
                exit_position(p,p["stop"],b["time"],"stop")
            elif target_hit:
                exit_position(p,p["target"],b["time"],"target")
            elif clock >= flatten:
                exit_position(p,b["open"],b["time"],"session_close")
        if position is None and i>=cfg.slow+1 and start<=clock<last and count<cfg.max_trades_day and equity>0:
            if equity <= day_start*(1-cfg.daily_loss_fraction):
                pass
            else:
                # Signals from prior closed candle only. Cross of fast/slow SMA.
                prev=[x["close"] for x in bars[:i]]
                f0=sum(prev[-cfg.fast:])/cfg.fast
                s0=sum(prev[-cfg.slow:])/cfg.slow
                f1=sum(prev[-cfg.fast-1:-1])/cfg.fast
                s1=sum(prev[-cfg.slow-1:-1])/cfg.slow
                side=1 if f1<=s1 and f0>s0 else -1 if f1>=s1 and f0<s0 else 0
                if side:
                    entry=b["open"]+side*(spread/2+cfg.slippage)
                    qty=max(0,equity*cfg.risk_fraction/(cfg.stop_distance+spread+2*cfg.slippage))
                    position={"side":side,"entry":entry,"stop":entry-side*cfg.stop_distance,
                              "target":entry+side*cfg.stop_distance*cfg.reward_risk,
                              "qty":qty,"time":b["time"],"spread":spread}
                    count+=1
        curve.append({"time":b["time"].isoformat(),"equity":round(equity,2)})
    if position and bars:
        exit_position(position,bars[-1]["close"],bars[-1]["time"],"end_of_data")
        curve[-1]["equity"]=round(equity,2)
    peak=cfg.starting_equity
    max_dd=0
    for p in curve:
        peak=max(peak,p["equity"])
        max_dd=max(max_dd,(peak-p["equity"])/peak)
    wins=sum(t["pnl"]>0 for t in trades)
    profit=sum(max(0,t["pnl"]) for t in trades)
    loss=-sum(min(0,t["pnl"]) for t in trades)
    return {"summary":{"trades":len(trades),"longs":sum(t["side"]=="LONG" for t in trades),
        "shorts":sum(t["side"]=="SHORT" for t in trades),
        "win_rate":round(wins/len(trades),4) if trades else None,
        "profit_factor":round(profit/loss,4) if loss else None,
        "max_drawdown_pct":round(max_dd*100,2),
        "final_equity":round(equity,2)},"trades":trades,"equity_curve":curve}
