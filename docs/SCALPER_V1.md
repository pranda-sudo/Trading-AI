# Scalper V1 – intradenní strategie (návrh k testování)

Cíl: všechny pozice otevřené tímto EA uzavřít před koncem definované obchodní seance; nepřenášet je přes noc. **Není zaručeno provedení uzavření** při výpadku spojení, uzavřeném trhu či odmítnutí příkazu. Nutné opakování příkazů, monitoring a alarm.

## Výchozí hypotéza
- Instrumenty: nejprve XAUUSD a US500; ostatní až po validaci.
- M15 trend, M5 setup, M1 vstup.
- Max 5–10 obchodů/den; 0,25–0,5 % equity risk/obchod, denní stop 1,5 % včetně realizovaného i otevřeného P/L.
- Každý obchod má SL a TP na straně brokera; bez martingale, gridu a averaging down.
- Ověřit časové zóny brokera, DST, obchodní hodiny, volatilitu při zprávách, spread a slippage.
- Nové vstupy zakázat např. 30 min před koncem seance; likvidaci zahájit např. 10 min předem. Konkrétní časy až podle symbolu.
- Na konci seance uzavírat **jen pozice označené magic number EA**, nikoli ruční či kopírované pozice.
- Při chybě uzavření opakovat s limitem, logovat a upozornit operátora; broker-side SL zůstává.
- Kill switch, demo-only default, oddělení přístupů a přepínač live jen po explicitním schválení.

## Validace
Backtest na Bid/Ask tick datech nebo kvalitních M1 datech s realistickými náklady; walk-forward a out-of-sample; demo forward test. Sledovat profit factor, drawdown, expectancy, fill rate, uzavření před koncem seance a citlivost na spread.

## Stav
Specifikace, neimplementovaný ani netestovaný EA. Žádné tvrzení o očekávaném zisku.
