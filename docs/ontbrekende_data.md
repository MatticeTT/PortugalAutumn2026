# Ontbrekende data per strand (antwoord rekenchat, 9 oktober 2026)

Status: alleen bewaard, nog niets mee gedaan.

## Periode (rekenchat)
- De app haalt GFS-Wave via Open-Meteo (`ncep_gfswave016`) en rekent per deiningscomponent.
- Piekperiodes per component (`swell_wave_peak_period` enz.) worden opgevraagd, maar Open-Meteo geeft ze
  voor dit model niet: de app gebruikt dus de **gemiddelde** periode per component.
- Open vraag aan de rekenchat: zo laten, of omrekenen (piek ≈ 1,3 × gemiddelde) voor de 9 s-regel en de grenzen.

## Spotgidsen: precies wat we zoeken, maar niet vrij
| Bron | Per spot | Bruikbaar? |
|---|---|---|
| Stormrider Surf Guide | bodemtype, getij, ideale windrichting, golfrichting, min/max golfhoogte, golftype | alleen met licentie (Windy gebruikt dit voor 4.500 spots) |
| Wannasurf | type break, ervaring, richting; 21 spots in België | nee: auteursrecht, geen API |
| Surfline | uitgebreide spotgids | geen openbare API; niet scrapen |

Beste getij per spot bestaat dus, maar alleen via licentie (Stormrider) of zelf verzamelen.

## Open data: vrij, per kilometer kust
| Bron | Wat erin zit | Dekking | Vorm |
|---|---|---|---|
| Global Coastal Characteristics (Athanasiou e.a. 2024) | kusttype, helling onder water, strandhelling, getijniveaus, golfklimaat, kijkrichting | wereldwijd, elke km | CSV |
| EMODnet Bathymetry | diepteprofiel langs een lijn → helling per strand | Europa, ~115 m | REST API, JSON |
| EMODnet Geology | bodemsoort zeebodem, kusttype | Europa | WMS/WFS |
| OpenStreetMap | stranden, riffen, `sport=surfing` | wereldwijd | API |
| Meetnet Vlaamse Banken | gemeten golven, wind, getij (live) | Belgische kust | API (commercieel: eerst contact) |
| Jarkus-kustprofielen | jaarlijkse profielen, om de 250–500 m | Nederland | netCDF |
| Beach-face slope dataset (Vos e.a. 2022) | gemeten strandhelling, om de 100 m | alleen Australië | GeoJSON |

## Bestaat nergens
- Actuele diepte en ligging van zandbanken (behalve jaarlijkse profielen in Nederland).
- Een vrije, wereldwijde lijst met het beste getij per spot.

## Voorstel van de rekenchat
1. Global Coastal Characteristics als basis (bodemtype, helling, getijverschil, kijkrichting).
2. Europese stranden: helling verfijnen met EMODnet-diepteprofiel.
3. Beste getij per spot: licentie bij Stormrider, of laten leren uit beoordeelde sessies.
4. Onbekende velden neutraal scoren en een lagere betrouwbaarheid tonen.
5. Licentie van elk databestand zelf nog nakijken (van de artikels: vrij met bronvermelding).
