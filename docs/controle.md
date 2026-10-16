# Controle van de data

Vergelijking op 16 oktober 2026 tussen deze kaart en [Open-Meteo](https://open-meteo.com), dat hetzelfde
ECMWF-model aanbiedt (`ecmwf_ifs025` voor wind, `ecmwf_wam025` voor golven). Run: 16 oktober 00 UTC. Telkens
op hetzelfde rasterpunt (0,25 graad). "ECMWF ruw" is de waarde in het GRIB-bestand van ECMWF, "kaart" is wat de
browser na het inpakken in de afbeelding teruggeeft.

## Wind (knopen, richting waar de wind vandaan komt)

| Uur (UTC) | Spot | Open-Meteo | ECMWF ruw | Kaart |
|---|---|---|---|---|
| vr 16 okt 12:00 | Viana do Castelo | 6,6 kn 339° | 6,7 kn 340° | 6,7 kn 340° |
| | Porto/Matosinhos | 12,5 kn 332° | 12,5 kn 333° | 12,8 kn 332° |
| | Figueira da Foz | 7,8 kn 337° | 7,8 kn 336° | 7,7 kn 337° |
| | Nazaré | 9,4 kn 347° | 9,4 kn 347° | 9,6 kn 348° |
| | Peniche | 10,3 kn 357° | 10,4 kn 356° | 10,3 kn 356° |
| | Ericeira | 6,0 kn 358° | 6,0 kn 358° | 5,9 kn 358° |
| | Cascais/Carcavelos | 2,9 kn 42° | 2,8 kn 43° | 2,7 kn 42° |
| | Sagres | 2,0 kn 17° | 2,0 kn 19° | 1,9 kn 20° |
| ma 19 okt 00:00 | Viana do Castelo | 4,5 kn 80° | 4,6 kn 81° | 4,6 kn 82° |
| | Porto/Matosinhos | 10,1 kn 65° | 10,1 kn 64° | 9,8 kn 65° |
| | Figueira da Foz | 9,2 kn 82° | 9,2 kn 82° | 9,4 kn 81° |
| | Nazaré | 5,6 kn 61° | 5,5 kn 59° | 5,6 kn 60° |
| | Peniche | 6,3 kn 74° | 6,3 kn 73° | 6,2 kn 73° |
| | Ericeira | 7,1 kn 69° | 7,0 kn 69° | 7,2 kn 69° |
| | Cascais/Carcavelos | 6,6 kn 47° | 6,6 kn 47° | 6,6 kn 47° |
| | Sagres | 8,0 kn 51° | 8,0 kn 51° | 8,0 kn 52° |

Grootste verschil kaart tegenover Open-Meteo: 0,3 kn en 2°.

## Golven (significante golfhoogte, richting waar de golven vandaan komen, piekperiode)

| Uur (UTC) | Spot | Open-Meteo | ECMWF ruw | Kaart |
|---|---|---|---|---|
| vr 16 okt 12:00 | Viana do Castelo | 2,38 m 301° 13,2 s | 2,37 m 301° 13,1 s | 2,35 m 302° 13,1 s |
| | Porto/Matosinhos | 2,04 m 300° 13,3 s | 2,04 m 300° 13,3 s | 2,03 m 300° 13,3 s |
| | Figueira da Foz | 2,26 m 308° 13,2 s | 2,26 m 308° 13,2 s | 2,24 m 308° 13,2 s |
| | Nazaré | 2,20 m 310° 13,2 s | 2,19 m 310° 13,3 s | 2,19 m 310° 13,3 s |
| | Peniche | 2,00 m 308° 13,2 s | 2,00 m 308° 13,1 s | 1,98 m 308° 13,0 s |
| | Ericeira | 2,12 m 309° 13,3 s | 2,11 m 309° 13,3 s | 2,14 m 309° 13,4 s |
| | Sagres | 1,72 m 310° 13,6 s | 1,72 m 310° 13,6 s | 1,74 m 310° 13,7 s |
| ma 19 okt 00:00 | Viana do Castelo | 1,10 m 334° 9,1 s | 1,09 m 334° 9,1 s | 1,08 m 334° 9,1 s |
| | Porto/Matosinhos | 0,82 m 324° 9,4 s | 0,81 m 324° 9,4 s | 0,81 m 325° 9,4 s |
| | Figueira da Foz | 1,32 m 333° 10,1 s | 1,32 m 333° 10,0 s | 1,31 m 333° 10,1 s |
| | Nazaré | 1,56 m 337° 9,6 s | 1,55 m 337° 9,5 s | 1,56 m 337° 9,6 s |
| | Peniche | 1,50 m 340° 9,2 s | 1,51 m 340° 9,3 s | 1,52 m 340° 9,4 s |
| | Ericeira | 1,54 m 337° 9,7 s | 1,54 m 337° 9,6 s | 1,52 m 338° 9,7 s |
| | Sagres | 1,26 m 326° 10,9 s | 1,26 m 326° 11,0 s | 1,27 m 326° 10,8 s |

Grootste verschil: 3 cm, 1° en 0,2 s. Bij Cascais (38,75° N 9,5° W) rekent het golfmodel land; de kaart vult
daar aan vanuit de dichtstbijzijnde zeecellen.

## Wat niet exact gelijk kan zijn

- **Windy** gebruikt ECMWF op 9 km (betalende licentie); de open data van ECMWF zijn 0,25 graad (ongeveer 25 km).
  Op open zee zijn de waarden vrijwel gelijk, vlak aan de kust kan Windy afwijken.
- **Windguru** toont andere modellen (GFS, ICON, eigen WG-modellen) en dus andere getallen.
- Tussen twee runs (00 en 12 UTC) verschuift de voorspelling; vergelijk altijd met dezelfde run.
