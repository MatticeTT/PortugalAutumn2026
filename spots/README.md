# Stap 1: spots

`python -m spots.bouw --kustlijn lines.shp` maakt in `data/spots/`:

| Bestand | Inhoud |
|---|---|
| `spots.geojson`, `spots.csv` | spots die door de controles komen, met per veld bron en soort |
| `na_te_kijken.csv` | twijfelgevallen met reden, satellietlink en OSM-link |
| `uitgesloten.csv` | elementen met `sport=surfing` die een zaak of school zijn |
| `ruw/` | de ruwe Overpass-antwoorden |

Bronnen: OpenStreetMap (`sport=surfing`, stranden en riffen) en de OSM-kustlijn
(osmdata.openstreetmap.de, `coastlines-split-4326`). Beide ODbL: de afgeleide spotlijst blijft open onder ODbL.

Alle drempels staan in `regels/spots.yaml`.

## Hoe

- **Positie**: dichtste punt op de kustlijn. Verder dan 300 m: spot uit de lijst, naar `na_te_kijken`.
- **Strandrichting**: in OSM ligt het land links van de kustlijn, de zee rechts. De richting is het
  lengtegewogen gemiddelde van de zeewaartse loodlijnen over 500 m rond het kustpunt. Kronkelt de kust
  te veel (baai, kaap) of ligt er vlakbij kust die de andere kant op kijkt (landtong, pier): na te kijken.
- **Swellvenster**: vanaf een punt 50 m in zee gaat elke graad een straal van 50 km. Raakt de straal land,
  dan is die richting dicht. Het venster is de aaneengesloten open boog rond de strandrichting.
  Schaduw smaller dan 5 graden (eilandje, rots) telt niet. Land verder dan 50 km telt niet.
- **Rekenpunt**: het vertrekpunt 50 m in zee; stap 2 zoekt van daaruit het eerste modelpunt op zee.
- **Bodem**: tag op de spot (expertkennis), anders strand of rif in OSM binnen 300 m (afgeleid).
  Strand en rif samen: na te kijken. Point: alleen via tag.
- **Helling**: wereldwijd onbekend. Later per land (COSMO, Litto3D, JARKUS, Afdeling Kust).
