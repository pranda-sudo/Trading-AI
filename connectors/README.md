# MT5 – první funkční read-only konektor

**Stav:** Zdrojový kód konektoru je připravený. Na VPS ještě není nainstalovaný ani ověřený.

## Windows VPS – postup
1. Na VPS spusť MetaTrader 5 a přihlas se ke svému účtu RoboForex (ideálně demo nebo read-only investor login).
2. Nainstaluj Python 3.10+ ve Windows.
3. Naklonuj repozitář a v jeho kořeni spusť `py -m pip install -r connectors/requirements.txt`.
4. V MT5 Market Watch ověř **přesný název symbolu** (může mít suffix).
5. Exportuj posledních 30 dní minutových svíček:

```powershell
py -m connectors.mt5_collector --symbol XAUUSD --timeframe M1 --days 30 --output data/xauusd_m1.csv
```

Pokud MT5 není ve výchozí instalaci, přidej `--terminal-path "C:\\Program Files\\MetaTrader 5\\terminal64.exe"`.

6. Spusť backtest:

```powershell
py -m engine.run data/xauusd_m1.csv --output data/results.json --stop-distance 2 --spread 0.15
```

**Pozor:** Parametry stop-distance/spread jsou pouze ukázkové a nejsou kalibrované pro konkrétní účet. MT5 omezuje dostupnou historii podle brokera a nastavení grafu (Max. bars in chart). Import aktuálně načítá OHLC a spread po svíčkách, nikoli tickový Bid/Ask. Přesnost backtestu je tedy omezená.

## Bezpečnost
- Konektor neobsahuje žádné obchodní příkazy a nečte přihlašovací heslo.
- Nezveřejňuj čísla účtů, hesla, výpisy ani exporty se soukromými údaji v public GitHub repozitáři.
- Historická data mohou mít licenční omezení pro další sdílení.
- MT5 terminál a Python běží na stejném Windows VPS; GitHub Pages samotný MT5 nepřipojí.

## Další fáze
Pravidelné inkrementální ukládání, kontrola duplicit a mezer, bezpečné API, tickový import, validace spreadu, demo forward test.
