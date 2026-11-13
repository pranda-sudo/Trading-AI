# Trading AI – dedicated MT5 demo collector

Read-only local prototype. **No orders are sent.** It writes a local JSON snapshot only; it does NOT publish to GitHub or expose a port.

1. Install a separate RoboForex MT5 terminal in its own directory and sign into a **demo** account.
2. Find that installation's `terminal64.exe` path. Never point at a production terminal.
3. In Windows Command Prompt:
   ```bat
   py -m pip install -r mt5-bridge\requirements.txt
   set "MT5_TERMINAL_PATH=C:\TradingAI\MT5-Demo\terminal64.exe"
   set "MT5_SYMBOLS=XAUUSD,US30Cash,DE40Cash,USTECHCash,US500Cash"
   py mt5-bridge\collector.py
   ```
4. Inspect `snapshot.json`. Check symbol names in MT5 Market Watch; they differ by account.
5. Stop with Ctrl+C.

The script checks MT5 account trade_mode and refuses to run against a real account. If terminal initialization or symbol selection fails, it does not try to log in or start trading.

**Next step:** securely push snapshots from VPS to an authenticated backend over outbound HTTPS, never from GitHub Pages directly to VPS. Add server-side authentication, freshness checks, access controls, and rate limits before publishing live prices. Keep broker credentials and API tokens outside GitHub. Do not open inbound firewall ports.
