# Trading AI — MT5 data collector

Read-only incremental market data collection for the dedicated RoboForex MT5 demo terminal. No trading calls or EA modifications.

## Install on Windows VPS

1. Download collector.py and start_collector.bat from this folder on GitHub.
2. Place both files in C:\\AItrading\\collector\\.
3. Ensure the demo terminal is running, logged in to the expected demo account.
4. Run start_collector.bat and inspect the output and logs\\collector.log.
5. New files appear in data\\: latest.json and CSVs for XAUUSD, US30, DE40, USTECH and US500 on M5, M15, H1, H4 and D1.

This collector appends only CLOSED candles, with Unix UTC timestamps. It fetches 10 recent bars per poll (every 60 seconds). Gaps can occur after a longer interruption and must be backfilled from MT5. Existing history\\ files are not modified. CSV format can differ from the earlier download_history.py output; do not concatenate without checking schemas.

## Automatic start

First verify it runs manually. Then use Windows Task Scheduler: trigger At startup or At log on; action Program: cmd.exe; arguments: /c "C:\\AItrading\\collector\\start_collector.bat". Configure If the task is already running: Do not start a new instance. Do NOT schedule a fresh process every minute; the script loops itself. The collector.lock file prevents accidental duplicate runs. After a crash, check that no collector.py process is active before removing a stale lock file.

## Environment variables

TRADING_AI_MT5_PATH, TRADING_AI_MT5_LOGIN, TRADING_AI_INTERVAL_SECONDS, TRADING_AI_BARS_PER_POLL.

Do not commit passwords, tokens, CSV market data or private account details. This collector does not yet publish to the web or Supabase.
