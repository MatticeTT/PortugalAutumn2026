# M3: de Windguru-stand naast Windguru

Handmatige controle op 6 oktober 2026, modelrun 00 UTC, eerste 60 uur (dinsdag 6 tot donderdag 8 oktober, 03 tot 22 uur Portugese tijd). De twee Windguru-tabellen zijn de tabellen die PLAN.md (hoofdstuk 10) noemt. Ze zijn één keer bekeken; de cijfers van Windguru zelf zijn niet bewaard.

| Strand | Wat | Onze bron | Binnen | Resultaat | Gem. verschil |
|---|---|---|---|---|---|
| Praia da Rocha | wind | GFS 13 km (`gfs_seamless`) | 2 kn | 59/60 = 98 % ✅ | +0,3 kn |
| Praia da Rocha | vlagen | GFS 13 km | 2 kn | 34/60 = 57 % | −2,2 kn |
| Praia da Rocha | wind, ter vergelijking | ECMWF IFS (`ecmwf_ifs`) | 2 kn | 37/60 = 62 % | −1,3 kn |
| Arrifana | golfhoogte | GFS-Wave 16 km (`ncep_gfswave016`) | 0,1 m | 59/60 = 98 % ✅ | −0,02 m |
| Arrifana | golfperiode | GFS-Wave 16 km, `wave_period` | 1 s | 59/60 = 98 % ✅ | +0,1 s |

Gelijkgezet: Windguru toont Portugese tijd (UTC+1), wij rekenen in UTC; onze waarden zijn afgerond zoals Windguru (wind op 1 kn, golf op 0,1 m, periode op 1 s).

Bevindingen:

- De Windguru-stand haalt de norm van M3 (95 procent binnen 0,1 m, 1 s en 2 kn) voor deze twee spots.
- Vlagen wijken af: Windguru toont ze gemiddeld 2 kn hoger. Windguru rekent vlagen kennelijk anders uit dan Open-Meteo. De vlagen vallen buiten de norm van M3, maar ze tellen wel mee in de WIND-score (PLAN.md 2.4, stap 3). Zie OPEN.md punt 18.
- De "Wave period" van Windguru komt overeen met `wave_period` van Open-Meteo (de gemiddelde periode), niet met een piekperiode.
- Nog niet gedaan: de drie andere referentiespots (Moledo, Peniche, Ericeira). Zie OPEN.md punt 18.
