"""Read-only RoboForex MT5 market data snapshot and historical bars.

Run on Windows VPS: py collector\\collect_once.py
No trading functions are imported or called.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

TERMINAL = r"C:\AItrading\petr\terminal64.exe"
EXPECTED_LOGIN = 68531109
SYMBOLS = {
    "XAUUSD": "XAUUSD",
    "US30": ".US30Cash",
    "DE40": ".DE40Cash",
    "USTECH": ".USTECHCash",
    "US500": ".US500Cash",
}
TIMEFRAMES = {
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}
BAR_LIMIT = 1000
OUTPUT = Path(__file__).resolve().parent / "data"


def main():
    if not mt5.initialize(path=TERMINAL, timeout=15000):
        raise RuntimeError(f"MT5 connection failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if not account or account.login != EXPECTED_LOGIN or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise RuntimeError("Wrong MT5 account or not a demo account. No data collected.")
        OUTPUT.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "collected_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "RoboForex MT5 demo",
            "symbols": {},
        }
        for label, symbol in SYMBOLS.items():
            info = mt5.symbol_info(symbol)
            if info is None:
                print(f"{label}: symbol unavailable")
                continue
            if not info.visible and not mt5.symbol_select(symbol, True):
                print(f"{label}: cannot enable symbol")
                continue
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                print(f"{label}: no tick")
                continue
            snapshot["symbols"][label] = {
                "broker_symbol": symbol,
                "bid": tick.bid,
                "ask": tick.ask,
                "tick_time_utc": datetime.fromtimestamp(tick.time, timezone.utc).isoformat(),
            }
            for tf_name, tf in TIMEFRAMES.items():
                bars = mt5.copy_rates_from_pos(symbol, tf, 0, BAR_LIMIT)
                if bars is None:
                    print(f"{label} {tf_name}: no history, {mt5.last_error()}")
                    continue
                filename = OUTPUT / f"{label}_{tf_name}.csv"
                with filename.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["time_utc", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"])
                    for bar in bars:
                        writer.writerow([
                            datetime.fromtimestamp(int(bar["time"]), timezone.utc).isoformat(),
                            float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"]),
                            int(bar["tick_volume"]), int(bar["spread"]), int(bar["real_volume"]),
                        ])
                print(f"{label} {tf_name}: {len(bars)} bars -> {filename.name}")
        (OUTPUT / "latest.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Snapshot saved:", OUTPUT / "latest.json")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
