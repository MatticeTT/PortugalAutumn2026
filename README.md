# Wind en golven

Wereldkaart met geanimeerde wind en golven in de stijl van Windy: geen kleurenlaag, alleen bewegende lijntjes
over een rustige, donkere basiskaart.

- **Wind** (wit, dun, met uitdovend staartje): windrichting en -snelheid op 10 m. De lijntjes liggen in de
  windrichting, bewegen mee en zijn sneller en langer waar het harder waait. Overal, over land en zee.
- **Golven** (lichtblauw, dikker, zonder staart): golfkammen dwars op de looprichting die vooruitschuiven.
  Langer en feller bij hogere golven, sneller bij langere periode. Alleen op zee (land/zee-masker van het golfmodel).
- **Bediening**: aparte knoppen voor wind en golven (samen aan mag), en een tijdlijn met afspeelknop door de
  voorspelling (5 dagen, per 3 uur).

## Data

`pipeline/build.py` haalt per tijdstip één wereldwijd raster op uit de nieuwste NOAA GFS-run (AWS Open Data):

| Laag | Model | Velden |
|---|---|---|
| Wind | GFS 0,25° | `UGRD`, `VGRD` op 10 m |
| Golven | GFS-Wave (WaveWatch III) 0,25° | `HTSGW` (significante golfhoogte), `DIRPW` (richting), `PERPW` (periode) |

Per veld wordt alleen het nodige stuk van het GRIB2-bestand gedownload (byte-range via het `.idx`-bestand).
Per tijdstip schrijft het script:

- een grof wereldraster van 1° (`<uur>/wind.png`, `<uur>/wave.png`, 360 × 181 px, ±100 kB) voor uitgezoomd;
- fijne tegels van 0,25° (`<uur>/wind/<rij>_<kol>.png`, 45° × 45°), die de browser vanaf zoom 3 alleen voor het
  zichtbare gebied bijlaadt;
- `manifest.json` met de run, de tijdstippen en de codering.

Codering in de PNG's (zie de kop van `pipeline/build.py`): wind als u/v in R/G met wortelcompressie (precies bij
zwakke wind); golven als looprichting in R/G (lengte = periode) en golfhoogte in B, met B = 0 op land.

## Browser

`web/` (Vite + TypeScript + MapLibre GL). De deeltjes staan in `web/src/particles.ts`: een MapLibre custom layer
die in dezelfde WebGL-context en hetzelfde frame als de kaart tekent, zodat pannen en zoomen niet hapert. De
deeltjes leven in Web Mercator-coördinaten en bewegen met een vaste schermsnelheid op elk zoomniveau.
`web/src/field.ts` laadt en bemonstert de rasters (fijne tegel als die er is, anders het grove raster).

## Lokaal

```sh
python -m venv .venv && .venv/bin/pip install -r pipeline/requirements.txt
.venv/bin/python -m pipeline.build --max-hour 24     # schrijft web/public/data
.venv/bin/pytest -q tests
cd web && npm ci && npm run dev
```

## Publiceren

`.github/workflows/kaart.yml` draait elke 6 uur (en met de hand): data ophalen, site bouwen en naar de tak
`site` zetten, die Vercel publiceert. Basiskaart: © OpenStreetMap-bijdragers, © CARTO.
