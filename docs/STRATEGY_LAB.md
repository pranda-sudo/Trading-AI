# Strategy Lab – návrh implementace

## Účel
Vývoj, backtesting, walk-forward validace a demo testování Expert Advisorů pro MT5. Žádné automatické live obchodování ve výchozím nastavení.

## Architektura
- Web dashboard (GitHub Pages): strategie, parametry, výsledky, porovnání verzí.
- Python backend na Windows VPS: MT5 connector, fronta úloh, backtesting, reporting.
- Datový archiv: Parquet OHLC/tick + metadata zdroje, timezone, bid/ask, spread.
- Supabase: strategie, verze, backtest runs, trade logs, metriky, přístupy. Tajné klíče pouze na serveru.
- EA runtime: MQL5 Expert Advisor nebo Python signálový engine; exekuce přes MT5 jen po samostatném schválení.

## MVP
1. Import CSV/Parquet a validace časových řad.
2. Strategie SMA crossover, breakout a RSI mean-reversion jako transparentní baseline.
3. Parametry a verze strategií; náklady spread, komise, swap, skluz.
4. Backtest bez look-ahead bias; walk-forward split; out-of-sample test.
5. Metriky: net P/L, max drawdown, profit factor, expectancy, Sharpe, win rate, počet obchodů, exposure.
6. Export výsledků a graf equity, trade log.
7. Paper/demo forward test na MT5 s limity rizika.

## Bezpečnost
- Výchozí režim read-only a simulace; žádná exekuce na reálném účtu.
- Denní ztrátový limit, limit pozic, kill switch, auditní log, oddělené demo/live credentials.
- Kontrola časových zón, kvality dat a rozdílu CFD vs futures.
- Žádné sliby výnosu; optimalizace není důkaz budoucí ziskovosti.

## Další krok
Implementovat Python backtesting engine a datový import, pak napojit dashboard na výsledky.
