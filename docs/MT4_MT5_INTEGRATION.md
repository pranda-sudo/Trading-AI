# MT4 / MT5 integration architecture (V0.1)

## Cíl
Jeden analytický backend pro MetaTrader 4 i MetaTrader 5. Výchozí režim **read-only / demo**, žádná live exekuce.

## MT5
- Python `MetaTrader5` package na Windows VPS se spuštěným terminálem.
- Čtení `symbol_info_tick`, `copy_rates_range`, `copy_ticks_range`; normalizace symbolů, časů UTC a Bid/Ask.
- Přístupové údaje pouze na VPS v zabezpečeném úložišti; nikdy v GitHub Pages, repozitáři nebo Supabase public schema.

## MT4
- MQL4 EA bridge exportuje uzavřené OHLC svíčky a tickové Bid/Ask přes souborovou frontu nebo HTTPS na backend.
- MT4 nemá stejnou oficiální Python integraci jako MT5.
- HTTPS bridge vyžaduje explicitní povolení URL v nastavení terminálu; autentizace, podpis zpráv, omezení rychlosti a replay protection.
- Live obchodní příkazy nejsou v první verzi povoleny.

## Normalizované schéma
`{platform, broker, account_alias, symbol_native, symbol_canonical, timestamp_utc, timeframe, open, high, low, close, bid, ask, volume, source}`.
- `account_alias` nesmí obsahovat číslo účtu ani přihlašovací údaje.
- Každý zdroj uchovává metadata o timezone, spreadu, jednotkách kontraktu a přesnosti ceny.
- CFD kotace jednotlivých brokerů se mohou lišit; neporovnávat slepě s futures.

## Implementační fáze
1. Read-only MT5 konektor + import historických OHLC.
2. Read-only MQL4 bridge a kontrola dat.
3. Sjednocené grafy a backtesty; broker-specific spread/komise.
4. Generování zdrojových EA .mq4/.mq5, kompilace v MetaEditoru a demo forward test.
5. Případná live exekuce pouze s explicitním opt-in, risk limity, kill switchem a auditem.

## Bezpečnost
- Oddělit data, signal engine a order execution.
- EA může uzavírat jen pozice s vlastním magic number.
- Na konci seance uzavírání není zaručeno při výpadku nebo odmítnutí příkazu; vyžaduje watchdog a alert.
