# Wind en golven

Wereldkaart met geanimeerde wind en golven in de stijl van Windy: geen kleurenlaag, alleen bewegende lijntjes
over een rustige basiskaart.

- **Wind**: dunne witte lijntjes met een lange, uitdovende staart. Ze liggen in de windrichting, bewegen mee
  en zijn sneller en langer waar het harder waait. Overal, over land en zee.
- **Golven**: korte witte kammen dwars op de looprichting die vooruitschuiven en een vage staart achterlaten
  (de blokjes van Windy). Groter en feller bij hogere golven, sneller bij een langere periode. Alleen op zee
  (land/zee-masker van het golfmodel).
- **Bediening**: aparte knoppen voor wind en golven (samen aan mag) en een tijdlijn met afspeelknop door de
  voorspelling van **15 dagen**.

## Data: ECMWF

Hetzelfde model dat Windy standaard toont. Bron: [ECMWF open data](https://www.ecmwf.int/en/forecasts/datasets/open-data)
(CC BY 4.0), via de spiegel op Google Cloud (`ecmwf-open-data`), met AWS en data.ecmwf.int als reserve.

| Laag | Model | Velden |
|---|---|---|
| Wind | ECMWF IFS 0,25° | `10u`, `10v`: wind op 10 m |
| Golven | ECMWF WAM 0,25° | `swh` significante golfhoogte, `mwd` gemiddelde golfrichting, `pp1d` piekperiode |

De runs van 00 en 12 UTC lopen tot +360 uur: per 3 uur tot +144, daarna per 6 uur (85 tijdstippen).
`pipeline/build.py` haalt per veld alleen het nodige stuk van het GRIB2-bestand op en schrijft per tijdstip:

| Vooruit | Zichtbaar gebied ingezoomd | Wereldraster (uitgezoomd) |
|---|---|---|
| tot +120 u | tegels van 0,25° (volle modelresolutie) | 1° |
| +123 tot +240 u | – | 0,5° |
| +246 tot +360 u | – | 1° |

Het wereldraster is een gemiddelde over de buurcellen (golfrichting gewogen naar golfhoogte), het land/zee-
masker blijft dat van het model. De verre toekomst is grover omdat Vercel (gratis plan) hooguit 100 MB per
publicatie aanvaardt; de site is ongeveer 85 MB.

Afbeeldingen in lossless WebP; codering in de kop van `pipeline/build.py`. Controle (14 oktober 2026, +9 u):
de waarden die de browser terugleest wijken op 0,25° hooguit 0,2 m/s, 0,03 m en 1–2° af van de ruwe ECMWF-waarden.

## Weergave

`web/src/particles.ts`: een MapLibre custom layer (WebGL). Zoals bij earth.nullschool en Windy tekent elk
deeltje per frame alleen het stukje dat het net aflegde in een beeldbuffer die elk frame wat vervaagt; zo
ontstaan vloeiende staarten. Bij pannen en zoomen wordt die buffer mee verschoven en geschaald, zodat de
animatie niet hapert. `web/src/field.ts` laadt en bemonstert de rasters.

Basiskaart: Natural Earth (publiek domein), zelf gehost in `web/public/basis/` (`python -m pipeline.basemap`);
plaatsnamen in `web/src/labels.ts`.

## Lokaal

```sh
python -m venv .venv && .venv/bin/pip install -r pipeline/requirements.txt
.venv/bin/python -m pipeline.build --max-hour 24     # schrijft web/public/data
.venv/bin/pytest -q tests
cd web && npm ci && npm run dev
```

## Publiceren

`.github/workflows/kaart.yml` draait twee keer per dag (en met de hand): data ophalen, site bouwen en naar de
tak `site` zetten, die Vercel publiceert.
