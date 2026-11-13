# Trading AI

Český responzivní analytický prototyp pro XAUUSD, US30, DE40, USTECH a US500.

## Spuštění
Otevřete `index.html` v prohlížeči, případně zapněte GitHub Pages z větve `main` (root).

## Stav
- Grafy používají **syntetická demonstrační data**, nikoliv živé kotace.
- SMA20, SMA50 a RSI14 se počítají z demonstračních dat.
- Obchodní plánovač počítá risk/reward z ručně zadaných cen.
- Aplikace **nepředpovídá trh, neposílá signály a neobchoduje**.

## Roadmapa
1. Datový poskytovatel s licencí a OHLC historií, bezpečný backend a časová razítka.
2. Historické testy včetně spreadu, swapů, skluzu a walk-forward validace.
3. Kalibrované pravděpodobnosti a transparentní evidence úspěšnosti.
4. Upozornění, volitelně integrace MT5 po odděleném bezpečnostním auditu.

Žádné klíče ani přístupové údaje neukládejte do frontendu nebo GitHubu.
