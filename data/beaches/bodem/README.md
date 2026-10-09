# Bodemgegevens per strand

Gemaakt door `pipeline/bodem/` (workflow `bodem`, stap `bouw`). Voegt alleen velden toe; de score gebruikt ze nog niet.

- `bodem.json`: per strand-id de nieuwe velden.
- `rapport.json`: tellingen per land, voorbeelden en alles wat onlogisch lijkt.
- `profielen.json`: het volledige diepteprofiel om de 25 m (0 tot 2.000 m) per strand; `python -m pipeline.bodem.bouw --lokaal` rekent hieruit opnieuw zonder download.
- `getij_stations.json`: springverval (MHWS - MLWS) per getijstation.
- `verkenning*.json`: proefantwoorden van de bronnen (teken, referentievlak, kolomnamen).

## Velden

| Veld | Betekenis |
|---|---|
| `diepte_profiel` | diepte in m op 100, 200, 300, 500, 750, 1000, 1500, 2000 m van het kustpunt, in de kijkrichting. Positief = onder het referentievlak; negatief = erboven (droogvallend strand of land) |
| `diepte_kustpunt` | idem op het kustpunt zelf |
| `droogval_breedte_m` | afstand kustpunt - nullijn (eerste plek waar de diepte 0 wordt): droogvallend strand |
| `afstand_tot_5m_m`, `afstand_tot_10m_m` | vanaf het kustpunt: eerste afstand (stap 25 m, lineair geïnterpoleerd) waar de diepte 5 of 10 m haalt; leeg als dat niet binnen 2 km gebeurt |
| `helling_0_5m`, `helling_0_10m` | vanaf de nullijn: 5 / (afstand_tot_5m_m - droogval_breedte_m), idem voor 10 m |
| `ondiepe_vooroever` | ja als er binnen 2 km geen 5 m diepte is |
| `onzeker`, `onzeker_redenen` | ja als de lijn echt land raakt (hoger dan hoogwater, vanaf 300 m) of het op 100 m al dieper is dan 10 m; dan geen geschatte getij_voorkeur |
| `bodem_type` | zand, rots, slik of anders (GCC `coast_type_flag`: Sandy, Rocky, Muddy, Vegetated/Other); leeg zonder GCC-punt binnen 1.500 m of zonder klasse |
| `bodem_afstand_m`, `gcc_kusttype`, `gcc_id` | afstand tot het GCC-punt, de ruwe klasse en het punt |
| `getijverschil_m`, `getij_klasse` | MHWS - MLWS van het gekoppelde station; klein < 2 m, middel 2-4 m, groot > 4 m |
| `helling_klasse` | vlak (< 1:50), gemiddeld (1:50 tot 1:20), steil (> 1:20), uit `helling_0_5m` |
| `getij_voorkeur`, `getij_voorkeur_bron` | startregel: zand+vlak = half tot hoog, zand+gemiddeld = half, zand+steil = laag; anders leeg. Bron "geschat". `getij_voorkeur_nota` en `helling_klasse_nota`: "niet gebruiken in de score" (startwaarde) |
| `bodem_zekerheid` | laag als profiel of bodemtype ontbreekt of de diepte op 100 m al meer dan 10 m is; anders middel |

## Bronnen en licenties

- **EMODnet Bathymetry**, Digital Terrain Model (raster 1/16 boogminuut, ~115 m), via WCS `emodnet:mean`.
  Licentie CC BY 4.0. Bronvermelding: "EMODnet Bathymetry Consortium, EMODnet Digital Bathymetry (DTM)".
  Waarden zijn hoogtes: negatief onder water (proef: Noordzee -32,7 m; Brussel +30,6 m). Verticaal referentievlak
  volgens de documentatie van EMODnet: LAT waar het getij groot is, anders MSL.
- **Global Coastal Characteristics (GCC) v1.1**, Athanasiou e.a. 2024, Zenodo 10.5281/zenodo.11072020,
  `GCC_geophysical.csv`, kolom `coast_type_flag` (op basis van Hulskamp e.a. 2023). Licentie CC BY 4.0
  (vermeld in het Zenodo-record zelf).
- **TICON-4** via Neaps (DOI 10.17882/109129), datums MHWS en MLWS. Licentie CC BY-NC 4.0 (al in gebruik).
