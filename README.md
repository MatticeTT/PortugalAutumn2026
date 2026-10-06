# Surfkaart Portugal

Webkaart van de stranden van het Portugese vasteland met per uur wind, golven, getij en twee scores (WIND en WAVE). Het plan staat in [PLAN.md](PLAN.md), de open punten in [OPEN.md](OPEN.md).

Gratis, niet-commercieel, voor een besloten kring.

## Stand

| Mijlpaal | Stand |
|---|---|
| M0 Proeven en sleutels | Klaar; open punten in OPEN.md |
| M1 Stranden | Klaar: 681 stranden; zie OPEN.md punt 13 tot 16 |
| M2 Getij | Klaar; norm gehaald op de open kust, niet in mondingen (OPEN.md punt 17) |
| M3 Voorspelling | Elke 6 uur per strand (tak `data`); Windguru-stand klopt voor 2 van 5 spots (OPEN.md punt 18) |
| M4 tot M7 | Nog niet begonnen |

## Lokaal

```sh
pip install -e ".[dev]"     # Python 3.11 of hoger
npm ci                      # Node 20 of hoger
pytest && npm test
python -m pipeline.probe.probe   # één echte aanroep per bron
node pipeline/tides/probe.mjs    # getij via Neaps
```

Sleutels: kopieer `.env.example` naar `.env`.

## Mappen

- `pipeline/`: ophalen en rekenen (Python), getij (Node).
- `tests/fixtures/probe/`: opgeslagen antwoorden van de bronnen.
- `docs/`: veldnamen per bron, architectuurkeuzes.
- `web/`: de site (vanaf M4).
- `data/`: gegenereerde bestanden.
