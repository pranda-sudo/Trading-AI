"""Read-only RoboForex MT5 -> Supabase live quotes and closed candles.
Windows VPS: py -m pip install MetaTrader5; py C:\\AItrading\\collector\\live_sync.py
Requires SUPABASE_URL and SUPABASE_SECRET_KEY in the current Windows user environment.
Does not submit, modify or close trades.
"""
import json
import os
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import MetaTrader5 as mt5

URL = os.environ["SUPABASE_URL"].strip().rstrip("/")
KEY = os.environ["SUPABASE_SECRET_KEY"].strip()
INTERVAL = max(5, int(os.getenv("LIVE_SYNC_SECONDS", "15")))
EXPECTED_LOGIN = os.getenv("TRADING_AI_MT5_LOGIN", "").strip()
TERMINAL = os.getenv("TRADING_AI_MT5_PATH", "").strip()
SYMBOLS = {"XAUUSD": "XAUUSD", "US30": ".US30Cash", "DE40": ".DE40Cash",
           "USTECH": ".USTECHCash", "US500": ".US500Cash"}
FRAMES = {"M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
          "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}

def stamp(epoch):
    return datetime.fromtimestamp(int(epoch), timezone.utc).isoformat()

def upsert(table, rows, conflict):
    if not rows:
        return
    headers = {"apikey": KEY, "Content-Type": "application/json",
               "Prefer": "resolution=merge-duplicates,return=minimal"}
    if not KEY.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + KEY
    endpoint = URL + "/rest/v1/" + table + "?on_conflict=" + conflict
    req = Request(endpoint, data=json.dumps(rows, allow_nan=False).encode("utf-8"),
                  headers=headers, method="POST")
    for attempt in range(4):
        try:
            with urlopen(req, timeout=35) as res:
                if res.status not in (200, 201, 204):
                    raise RuntimeError("Unexpected HTTP " + str(res.status))
            return
        except HTTPError as exc:
            detail = exc.read(1500).decode(errors="replace")
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 3:
                raise RuntimeError(f"{table}: HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError) as exc:
            if attempt == 3:
                raise RuntimeError(f"{table}: {exc}") from exc
        time.sleep(2 ** attempt)

def poll():
    if not mt5.initialize(path=TERMINAL, timeout=10000) if TERMINAL else not mt5.initialize(timeout=10000):
        raise RuntimeError("MT5 initialization failed: " + str(mt5.last_error()))
    try:
        account = mt5.account_info()
        if not account:
            raise RuntimeError("MT5 is not logged in")
        if EXPECTED_LOGIN and str(account.login) != EXPECTED_LOGIN:
            raise RuntimeError("Wrong MT5 account; check TRADING_AI_MT5_LOGIN")
        quotes, candles = [], []
        for name, broker_symbol in SYMBOLS.items():
            info = mt5.symbol_info(broker_symbol)
            if info is None:
                print("Missing symbol:", broker_symbol, flush=True)
                continue
            if not info.visible and not mt5.symbol_select(broker_symbol, True):
                continue
            tick = mt5.symbol_info_tick(broker_symbol)
            if tick is not None and tick.bid > 0 and tick.ask > 0 and tick.time > 0:
                quotes.append({"symbol": name, "bid": float(tick.bid),
                               "ask": float(tick.ask), "quote_time": stamp(tick.time)})
            for frame_name, frame in FRAMES.items():
                # Last 3 bars: exclude the currently forming candle at position 0.
                bars = mt5.copy_rates_from_pos(broker_symbol, frame, 0, 3)
                if bars is None or len(bars) < 2:
                    continue
                for bar in bars[:-1]:
                    candles.append({"symbol": name, "timeframe": frame_name,
                                    "candle_time": stamp(bar["time"]),
                                    "open": float(bar["open"]), "high": float(bar["high"]),
                                    "low": float(bar["low"]), "close": float(bar["close"]),
                                    "tick_volume": int(bar["tick_volume"]),
                                    "spread": int(bar["spread"]),
                                    "real_volume": int(bar["real_volume"])})
        upsert("market_quotes", quotes, "symbol")
        upsert("market_candles", candles, "symbol,timeframe,candle_time")
        print(datetime.now(timezone.utc).isoformat(), "quotes", len(quotes),
              "closed candles", len(candles), flush=True)
    finally:
        mt5.shutdown()

def main():
    if not URL.startswith("https://") or len(KEY) < 20:
        raise RuntimeError("Missing or invalid Supabase configuration")
    print("Read-only MT5 live sync started. Stop with Ctrl+C.", flush=True)
    while True:
        try:
            poll()
        except KeyboardInterrupt:
            print("Stopped", flush=True)
            break
        except Exception as exc:
            print("SYNC ERROR:", str(exc), flush=True)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
