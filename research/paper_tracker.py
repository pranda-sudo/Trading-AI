"""Trading AI: forward-only paper journal for RoboForex MT5. NO order_send.
Run every 5 minutes with Windows Task Scheduler while MT5 is connected.
All timestamps UTC; entries based on the last CLOSED M15 candle, filled at
the first observed ask/bid (not an assumed historical candle price).
SQLite is local on the VPS. Strategy version is immutable for comparisons.
"""
import datetime as dt
import json
import os
import sqlite3
import sys
from pathlib import Path

import MetaTrader5 as mt5

UTC = dt.timezone.utc
DB_PATH = Path(os.getenv("PAPER_DB", str(Path(__file__).resolve().parent / "paper_trades.sqlite3")))
SYMBOLS = [s.strip() for s in os.getenv("PAPER_SYMBOLS", "XAUUSD,US30,DE40,USTECH,US500").split(",") if s.strip()]
VERSION = "forward_m15_ema20_50_rsi14_atr14_v1"
MAX_SPREAD_ATR = 0.12
RISK_ATR = 1.5
REWARD_R = 2.0
MAX_HOLD_HOURS = 24
COOLDOWN_HOURS = 8

def session(now):
    h = now.hour
    return "ASIA" if 0 <= h < 7 else "EUROPE" if 7 <= h < 12 else "USA" if 12 <= h < 21 else "LATE"

def ema(values, period):
    value = sum(values[:period]) / period
    for price in values[period:]:
        value += (price - value) * 2 / (period + 1)
    return value

def rsi(values, period=14):
    gains = [max(values[i] - values[i-1], 0) for i in range(len(values)-period, len(values))]
    losses = [max(values[i-1] - values[i], 0) for i in range(len(values)-period, len(values))]
    g, l = sum(gains), sum(losses)
    return 100 if l == 0 and g else 50 if l == 0 else 100 - 100 / (1 + g/l)

def atr(rows, period=14):
    tr = []
    for i in range(1, len(rows)):
        previous = float(rows[i-1]["close"])
        bar = rows[i]
        tr.append(max(float(bar["high"])-float(bar["low"]), abs(float(bar["high"])-previous), abs(float(bar["low"])-previous)))
    return sum(tr[-period:]) / period

def initialize(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT, strategy TEXT NOT NULL,
        symbol TEXT NOT NULL, session TEXT NOT NULL, direction TEXT NOT NULL,
        signal_bar_utc TEXT NOT NULL, opened_utc TEXT NOT NULL,
        entry REAL NOT NULL, sl REAL NOT NULL, tp REAL NOT NULL,
        spread REAL NOT NULL, atr REAL NOT NULL, rsi REAL NOT NULL,
        reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN',
        closed_utc TEXT, exit_price REAL, result_r REAL, exit_reason TEXT,
        UNIQUE(strategy, symbol, signal_bar_utc)
    )""")
    conn.commit()

def rates(symbol, tf, count):
    data = mt5.copy_rates_from_pos(symbol, tf, 1, count)  # position 0 is forming; omit it
    if data is None or len(data) < count:
        return None
    return sorted(data, key=lambda row: int(row["time"]))

def inspect_entry(conn, symbol, now):
    if session(now) == "LATE":
        return
    if symbol == "DE40" and session(now) != "EUROPE":
        return
    if symbol != "DE40" and session(now) not in ("ASIA", "USA"):
        return
    info, tick = mt5.symbol_info(symbol), mt5.symbol_info_tick(symbol)
    if info is None or tick is None or not info.visible:
        return
    if not (tick.bid > 0 and tick.ask > tick.bid):
        return
    if now.timestamp() - tick.time > 90:
        return
    rows = rates(symbol, mt5.TIMEFRAME_M15, 85)
    higher = rates(symbol, mt5.TIMEFRAME_H1, 85)
    if rows is None or higher is None:
        return
    bar_time = dt.datetime.fromtimestamp(int(rows[-1]["time"]), UTC)
    if (now - bar_time).total_seconds() > 1800:
        return
    signal_key = bar_time.isoformat()
    if conn.execute("SELECT 1 FROM trades WHERE strategy=? AND symbol=? AND signal_bar_utc=?", (VERSION, symbol, signal_key)).fetchone():
        return
    if conn.execute("SELECT 1 FROM trades WHERE symbol=? AND status='OPEN'", (symbol,)).fetchone():
        return
    last = conn.execute("SELECT opened_utc FROM trades WHERE symbol=? ORDER BY opened_utc DESC LIMIT 1", (symbol,)).fetchone()
    if last and (now - dt.datetime.fromisoformat(last[0])).total_seconds() < COOLDOWN_HOURS * 3600:
        return
    closes = [float(x["close"]) for x in rows]
    hcloses = [float(x["close"]) for x in higher]
    volatility = atr(rows)
    spread = float(tick.ask - tick.bid)
    if volatility <= 0 or spread > volatility * MAX_SPREAD_ATR:
        return
    r = rsi(closes)
    fast = ema(closes, 20)
    slow = ema(closes, 50)
    hfast = ema(hcloses, 20)
    hslow = ema(hcloses, 50)
    prev = rows[-2]
    lastbar = rows[-1]
    long = (fast > slow and hfast > hslow and 52 <= r <= 68 and
            float(prev["close"]) <= float(prev["open"]) and
            float(lastbar["close"]) > float(lastbar["open"]) and float(lastbar["close"]) > fast)
    short = (fast < slow and hfast < hslow and 32 <= r <= 48 and
             float(prev["close"]) >= float(prev["open"]) and
             float(lastbar["close"]) < float(lastbar["open"]) and float(lastbar["close"]) < fast)
    if not (long or short):
        return
    side = "LONG" if long else "SHORT"
    entry = float(tick.ask if long else tick.bid)
    risk = max(volatility * RISK_ATR, spread * 4)
    sl = entry - risk if long else entry + risk
    tp = entry + REWARD_R * risk if long else entry - REWARD_R * risk
    reason = json.dumps({"M15_ema20": round(fast, 5), "M15_ema50": round(slow, 5),
                         "H1_ema20": round(hfast, 5), "H1_ema50": round(hslow, 5),
                         "RSI14": round(r, 2), "ATR14": round(volatility, 5)}, ensure_ascii=False)
    conn.execute("""INSERT OR IGNORE INTO trades
        (strategy,symbol,session,direction,signal_bar_utc,opened_utc,entry,sl,tp,spread,atr,rsi,reason)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (VERSION,symbol,session(now),side,signal_key,now.isoformat(),entry,sl,tp,spread,volatility,r,reason))
    conn.commit()
    print("PAPER OPEN",symbol,session(now),side,entry,sl,tp)

def evaluate(conn, now):
    open_trades = conn.execute("SELECT id,symbol,direction,entry,sl,tp,opened_utc FROM trades WHERE status='OPEN'").fetchall()
    for id_, symbol, direction, entry, sl, tp, opened in open_trades:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None or now.timestamp() - tick.time > 90:
            continue  # never pretend to fill against stale data
        price = float(tick.bid if direction == "LONG" else tick.ask)
        if price <= 0:
            continue
        sl_hit = price <= sl if direction == "LONG" else price >= sl
        tp_hit = price >= tp if direction == "LONG" else price <= tp
        timeout = (now - dt.datetime.fromisoformat(opened)).total_seconds() >= MAX_HOLD_HOURS*3600
        if not (sl_hit or tp_hit or timeout):
            continue
        reason = "SL" if sl_hit else "TP" if tp_hit else "TIMEOUT"
        risk = abs(entry-sl)
        result = (price-entry if direction=="LONG" else entry-price)/risk
        conn.execute("UPDATE trades SET status='CLOSED',closed_utc=?,exit_price=?,result_r=?,exit_reason=? WHERE id=?",
                     (now.isoformat(),price,result,reason,id_))
        conn.commit()
        print("PAPER CLOSE",symbol,reason,round(result,3),"R")
        # Sampling every 5m cannot capture intra-interval fills; R is observed-price estimate.

def summary(conn):
    print("STRATEGY",VERSION)
    for symbol, sess, n, wins, avg, total in conn.execute("""SELECT symbol,session,COUNT(*),
        SUM(CASE WHEN result_r>0 THEN 1 ELSE 0 END),AVG(result_r),SUM(result_r)
        FROM trades WHERE strategy=? AND status='CLOSED'
        GROUP BY symbol,session ORDER BY symbol,session""",(VERSION,)):
        print(f"{symbol:8} {sess:7} n={n:4} winrate={100*wins/n:.1f}% avg_R={avg:.3f} net_R={total:.2f}")

def main():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    initialize(conn)
    if not mt5.initialize():
        raise RuntimeError(f"MT5 not connected: {mt5.last_error()}")
    try:
        now = dt.datetime.now(UTC)
        evaluate(conn,now)
        for symbol in SYMBOLS:
            try:
                inspect_entry(conn,symbol,now)
            except Exception as exc:
                print("ERROR",symbol,str(exc),file=sys.stderr)
        summary(conn)
    finally:
        mt5.shutdown()
        conn.close()

if __name__ == "__main__":
    main()
