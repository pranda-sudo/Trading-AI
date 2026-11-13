"""Read-only MT5 market snapshot. No order_send, no account credentials."""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import MetaTrader5 as mt5

SYMBOLS = [s.strip() for s in os.getenv("MT5_SYMBOLS", "XAUUSD,US30Cash,DE40Cash,USTECHCash,US500Cash").split(",") if s.strip()]
TERMINAL = os.getenv("MT5_TERMINAL_PATH")
OUT = Path(os.getenv("MT5_OUTPUT", "snapshot.json"))
INTERVAL = max(5, int(os.getenv("MT5_INTERVAL_SECONDS", "15")))

def collect():
    result = {"collected_at": datetime.now(timezone.utc).isoformat(), "source": "RoboForex MT5 demo", "symbols": {}, "errors": {}}
    for name in SYMBOLS:
        if not mt5.symbol_select(name, True):
            result["errors"][name] = "Symbol not found or unavailable"
            continue
        tick = mt5.symbol_info_tick(name)
        info = mt5.symbol_info(name)
        if tick is None or info is None:
            result["errors"][name] = "No tick data"
            continue
        result["symbols"][name] = {
            "bid": tick.bid, "ask": tick.ask, "last": tick.last,
            "spread": round(tick.ask - tick.bid, info.digits),
            "digits": info.digits,
            "tick_time": datetime.fromtimestamp(tick.time, timezone.utc).isoformat(),
        }
    return result

def main():
    if not TERMINAL:
        sys.exit("Set MT5_TERMINAL_PATH to the dedicated DEMO terminal64.exe")
    if not mt5.initialize(path=TERMINAL, timeout=10000):
        sys.exit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            sys.exit("SAFETY STOP: selected MT5 terminal is not logged into a DEMO account")
        print("Connected to DEMO account; collecting read-only market data")
        while True:
            payload = collect()
            OUT.parent.mkdir(parents=True, exist_ok=True)
            temp = OUT.with_suffix(".tmp")
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(OUT)
            print(payload["collected_at"], len(payload["symbols"]), "symbols", flush=True)
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
