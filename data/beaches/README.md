# Strandentabel

Gegenereerd door `pipeline/beaches/build.py` (workflow `beaches`). Niet met de hand bewerken: pas de brondata of het script aan.

## Licentie

`stranden.geojson` is een afgeleide databank van OpenStreetMap en valt onder de **Open Database License (ODbL) 1.0**: © OpenStreetMap-bijdragers, https://www.openstreetmap.org/copyright. Het script dat de tabel maakt staat ernaast in deze repository.

De koppeling met de officiële zwemwateren gebruikt data van het EEA en het APA (CC BY 4.0), seizoen 2025.

## Bestanden

- `stranden.geojson`: één punt per strand, op de kustlijn.
- `onzeker.csv`: stranden waarvan de kijkrichting of het venster handmatig nagekeken moet worden, met de reden en een link naar het satellietbeeld.
- `verslag.json`: tellingen, en wat werd weggelaten.

## Velden per strand

| Veld | Betekenis |
|---|---|
| `naam`, `osm_ids` | Naam en OSM-objecten (`way/…`, `relation/…`, `node/…`) |
| `eea_ids`, `eea_namen`, `eea_type` | Gekoppelde officiële zwemwateren (Coastal of Transitional) |
| `bron` | `osm`, `eea` (alleen officieel) of `eea+osm zonder naam` |
| `kijkrichting` | Graden, de richting waarin het strand naar zee kijkt (270 = west) |
| `richting_zekerheid` | 0 tot 1: hoe recht de kust is binnen 400 m |
| `venster` | Open sectoren in graden, [van, tot] met de klok mee |
| `afstand_land_km` | Per 5 graden: afstand tot het eerste land, tot 300 km |
| `blootstelling` | f per golfrichting 0, 10, …, 350 graden (waar de golf vandaan komt), zie hieronder |
| `district`, `ipma_area` | District en de code van de IPMA-waarschuwingen |
| `onzeker`, `redenen` | Te controleren, en waarom |
| `kandidaat_besloten_water` | Land recht vooruit binnen 3 km: mogelijk baai of lagune |
| `besloten_water` | In te vullen door de eigenaar (PLAN.md 2.4); standaard `false` |
| `getij_voorkeur` | In te vullen door de eigenaar (PLAN.md 2.7) |

## Blootstellingsfactor f

f² = het gemiddelde, over een sector van 30 graden rond de golfrichting, van [die richting is open zee] × cos(hoek tussen golfrichting en kijkrichting).

- f² is een energiefactor: de WAVE-formule (PLAN.md 2.5) gebruikt f² · H² · T.
- De cosinus is de afname van de energiestroom naar de kust bij een schuin invallende golf.
- Een richting is "open" als er binnen 20 km geen land ligt.
- Golven die rond een kaap buigen, tellen niet mee. Beschutte stranden krijgen daardoor waarschijnlijk een te lage f.

Bewijsniveau: **eigen keuze** (meetkunde, geen meting). Te ijken in M7. Alle getallen staan in `PARAMS` bovenaan `build.py`.
