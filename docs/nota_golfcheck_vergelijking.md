# Nota: Golfcheck Europa en de Surfkaart vergeleken

Voor de chat die Golfcheck bouwt. Vergelijking op 19 oktober 2026 met de bestanden zelf, niet met metingen:
geen van beide apps is al systematisch tegen boeien getoetst. Wat hieronder staat is wat in de data en de code
te zien is.

## 1. Kijkrichting van het strand (26 spots die in beide zitten)

| Spot | Golfcheck | Surfkaart | Verschil |
|---|---|---|---|
| Knokke, Blankenberge, Zandvoort, Lacanau, Anglet, Coxos | – | – | 0–3° |
| Oostende | 328° | 314° | 14° |
| Oostduinkerke | 323° | 335° | 12° |
| Wissant | 323° | 306° | 17° |
| Nazaré | 284° | 269° | 15° |
| Carcavelos | 188° | 206° | 18° |
| Biarritz, Côte des Basques | 301° | 266° | 35° (de baai kijkt naar het westen: Surfkaart klopt beter) |
| Zarautz | 23° | 346° | 37° (het strand kijkt ongeveer naar het noorden: geen van beide goed) |
| Zurriola | 352° | 312° | 40° (kijkt naar het noorden: Golfcheck klopt beter) |
| Somo | 5° | 326° | 39° (geen van beide goed) |
| Mundaka, Rodiles, Belharra | – | – | niet vergelijkbaar: de Surfkaart heeft daar een ander strand of geen spot |

**Les:** op rechte stranden geven beide hetzelfde, ook met de grove Natural Earth-kustlijn. In baaien en
monden zitten beide er tot 40° naast. Een fijnere kustlijn (OpenStreetMap, 400 m) lost dat niet vanzelf op:
de kijkrichting van een baaistrand moet je per spot nakijken.

## 2. Golf aan de kust

- **Golfcheck:** DWD EWAM (5 km) met ECMWF WAM als vergelijking. Bij Oostende 0,46 m bij 6,4 s, gemeten 0,46 m
  bij 5 s. Goed.
- **Surfkaart:** GFS-Wave (0,16°, zoals Windguru). Het rekenpunt voor Oostende ligt ongeveer 13 km uit de kust.
  Dat is hetzelfde soort punt dat in de Golfcheck-test 0,82 m gaf tegenover 0,46 m gemeten. De Surfkaart
  overschat de golf aan de Belgische en Nederlandse kust dus waarschijnlijk.
- **Brekende golf:** de Surfkaart gebruikt Komar & Gaughan met hoogte en periode, en per golfsysteem
  cos θ × swell-venster × stroomfactor. Golfcheck gebruikt `hoogte × periodefactor (tot 1,4) × √cos Δ`
  (minimum 0,35). Beide zijn niet getoetst; de Surfkaart-formule is wel een gekende formule, die van
  Golfcheck een eigen schatting.

## 3. Wat de Surfkaart beter doet

- Rekent per golfsysteem (windzee en deiningen apart), niet met de totale zee.
- Getij uit TICON-4 (peilmeterstations), niet uit een golfmodel-API.
- Swell-venster per strand uit de OpenStreetMap-kustlijn, en een bodemprofiel uit EMODnet.
- Stroming (Open-Meteo Marine), neerslag, onweer en storm in de score.
- Scores lopen geleidelijk (trapezia), geen sprongen tussen grootteklassen.
- Plannen op het beste blok van minstens 3 uur, niet op een daggemiddelde.

## 4. Wat Golfcheck beter doet

- Fijner golfmodel aan de kust (EWAM 5 km) en een vergelijking van twee modellen als betrouwbaarheid.
- Eén echte controle tegen een meting.
- Golftype per spot (in de nieuwe versie ook in de score).
- Toont betrouwbaarheid per spot met redenen.

## 5. Eigen fouten van de Surfkaart, gevonden bij deze vergelijking

- 2.534 van de 6.568 stranden hebben in de eigen stranddata een kijkrichting of venster gemarkeerd als
  "nakijken" (Portugal 103, Spanje 1.482, Frankrijk 905, Nederland 44). De app rekent er toch mee.
- Voorbeeld: Praia dos Coxos kijkt naar het westen (270°), maar het venster staat op 105–160°. Daar komt
  dus nooit golf aan, terwijl het een bekende spot is.

## 6. Voorstel voor beide

1. Golf aan de kust uit het fijnste model (EWAM in Europa) en een rekenpunt dichter bij het strand.
2. Kijkrichting en venster per bekende spot met de hand nakijken; de rest tonen met lagere betrouwbaarheid.
3. Toetsen tegen boeien: Meetnet Vlaamse Banken, Rijkswaterstaat, Puertos del Estado, Instituto Hidrográfico.
4. Pas dan de plank- of sportscore verfijnen.

## 7. Nieuwe inzichten (19 oktober 2026, rechtstreeks bij Open-Meteo opgevraagd)

- **Getij niet verschoven.** Open-Meteo Marine (SMOC) met `timezone=UTC`: hoogwater Zeebrugge 05:00 en 18:00,
  laagwater 12:00 UTC. TICON-4 (peilmeterstation): 05:47, 12:14 en 18:23 UTC. Ongeveer een half uur verschil,
  geen 6 uur. De "6 uur verschoven" in de Golfcheck-prompt is waarschijnlijk een tijdzonefout (Open-Meteo geeft
  lokale tijd met `timezone=auto`). Vraag altijd UTC op. Het getijverschil klopt ook (2,4 m tegenover 2,3 m).
- **Stroming in fase met het getij.** Bij Zeebrugge loopt de vloedstroom (naar het oostnoordoosten) het
  sterkst 1 à 2 uur voor hoogwater, de ebstroom (naar het westzuidwesten) na hoogwater. Dat klopt met de
  Belgische kust.
- **EWAM heeft de piekperiode van de deining** (`swell_wave_peak_period`), GFS-Wave niet. Golfmodellen
  vergelijken met de piekperiode zoals Windguru die toont gaat dus wel, met EWAM.
- **EWAM heeft geen tweede deining**, alleen deining en windzee. GFS-Wave heeft twee deiningen, maar de labels
  springen: uren met "windzee" van 9 s en "deining" van 11 s die de volgende uren weer wisselen. Beoordeel op
  periode, niet op het label.
- **EWAM tegenover GFS-Wave, 19 oktober.** Oostende 08:00: 0,40 m (EWAM) tegenover 0,70 m (GFS-Wave);
  gemeten 0,46 m. Ericeira 08:00: 1,82 m bij 10,8 s (EWAM) tegenover 1,44 m bij 9,7 s (GFS-Wave): aan
  open kusten kan GFS-Wave ook lager uitkomen. Het verschil gaat dus niet altijd dezelfde kant op.
- **Watertemperatuur** komt mee uit dezelfde Open-Meteo Marine-aanroep (15 °C bij Zeebrugge).

## 8. Wat de Surfkaart daarmee aanpast

1. Golven aan de kust uit DWD EWAM (5 km) waar beschikbaar, met de piekperiode van de deining; GFS-Wave als
   reserve. Per uur alles uit één bron. De fiche toont welke bron.
2. Stranden waarvan het startpunt voor de kust op land lag (zoals Praia dos Coxos): het startpunt schuift tot
   2 km de zee in, en anders wordt de kijkrichting omgekeerd. Werkt pas na een nieuwe bouw van de stranden.
3. De fiche meldt bij elk strand met een onzekere kijkrichting of een onzeker venster dat het minder
   betrouwbaar is, met de reden.
