# Overdracht plankscore: van onderzoek naar bouw

Opgesteld 22 oktober 2026 door de onderzoekschat. De eigenaar beslist. Regelversie **2026-10-23h** (zie onderaan: wat veranderde na de laatste reviews).

## Wat zit erin

| Bestand | Wat |
|---|---|
| `regels.json` | **Alle getallen** van de plankscore, met status per getal. Eén blok per plank. Fysica, veiligheid, grenzen en koppeling met spotkennis. |
| `referentie.py` | De specificatie in code, één bestand. Leest `regels.json` en rekent strand en score uit. |
| `testset_100.json` | 100 situaties: ruwe invoer (met getij waar de beschrijving het eenduidig zegt), berekend strand, **handscore** (nagekeken door de eigenaar) en score van de regel. |
| `testset_1000.json` | 1000 situaties: ruwe invoer (met getij, getijverschil van die dag en de spotvelden `werkt_bij_tij` en `deining_venster`), berekend strand en verwachte score van de regel. |
| `testset_getij_uur.json` | 96 uren: een gewone getijdag in Bretagne (5 m) en aan de Middellandse Zee (0,3 m), voor een halftij-bank en een laag-tot-halftij-bank. Golf en wind blijven gelijk, alleen het water beweegt. Toont hoeveel uur na elkaar goed eruit komt. |
| `toets.py` | De eerlijke toets: vijf keer afstemmen op 80 nagekeken situaties en toetsen op de 20 die de regel niet zag. Draai hem opnieuw na elke wijziging van de regel. |
| `LEESMIJ.md` | Dit bestand. |

Controle: `python3 referentie.py testset_100.json`, `testset_1000.json` en `testset_getij_uur.json` geven alle drie een grootste verschil van 0,000.

Bijbehorende pagina's (voor mensen, niet om uit te lezen):
- Honderd surfdagen: de 100 nagekeken situaties, met uitleg per plank.
- Duizend surfdagen: de 1000 situaties, met de eerlijke toets.
- Databronnen voor een wereldwijde surf-app: waar elke variabele vandaan komt. Hoofdstuk 14 bevat de spotvelden.

## Vastgelegd voor de bouw (invoer)

- **Periode = piekperiode Tp per systeem** (deining 1, deining 2, windzee), in seconden. Alle grenzen (9, 11, 13 s), Komar & Gaughan, Iribarren en kracht rekenen daarmee. Per bron:

  | Bron | Geeft per systeem | Omrekenen |
  |---|---|---|
  | Copernicus IBI, NW-shelf, Global (MFWAM) | gemiddelde periode Tm01 (`VTM01_SW1`, `VTM01_SW2`, `VTM01_WW`); `VTPK` (piek) alleen voor het hele spectrum | ja: **Tp = Tm01 / 0,835** (JONSWAP, piekfactor 3,3; DNV-RP-C205) |
  | NOAA GFS-Wave (WAVEWATCH III) | `SWPER` (deining 1–3), `WVPER` (windzee); de GRIB-lijst noemt ze "mean period" | **nog na te gaan voor gebruik:** oudere NOAA-documentatie spreekt van piekperiode. Vergelijk `SWPER` een maand met de piekperiode (DPD) van een paar NDBC-boeien: ongeveer gelijk = piek (niet omrekenen), ongeveer 0,83 × DPD = gemiddeld (wel omrekenen). Tot dan GFS-Wave niet voor de score gebruiken. |
  | Eigen invoer of spotrapport | meestal piek | nee |

  Zonder omrekening scoort elke dag te laag, vooral voor step-up en gun.
- **Tij: rekenen met de waterstand, niet met bakjes.** `getij_stand` = (waterstand − laagwater) / (hoogwater − laagwater) van die cyclus, uit het getijmodel (0 = laagwater, 1 = hoogwater). Het spotveld blijft voor de redactie "laag", "half" of "hoog"; achter de schermen is elk woord een stuk van de stand: **laag 0–30%, half 20–80%, hoog 70–100%** (`regels.json` > `tijvenster` > `stukken`). Bij een gewoon getij duurt "half" zo ongeveer 2u30 per opkomend of afgaand tij. `getij_bereik_m` = hoogwater − laagwater van die cyclus. De bakjes (derden) dienen alleen nog voor de tekst ("nu halftij") en voor de vlaggen "ondiep bij laagwater" en "vol bij hoogwater".
- **Voorbeelden om je eigen code mee te toetsen** (uit `referentie.py`):

  | Functie | Invoer | Uitkomst |
  |---|---|---|
  | `piekperiode` | Tm01 = 8 / 10 / 12 s | 9,6 / 12,0 / 14,4 s |
  | `getij_stand` | laag 0,5 m, hoog 4,5 m, water 1,3 / 2,5 / 3,9 m | 0,20 / 0,50 / 0,85 |
  | `getij_bakje` (tekst) | laag 0,5 m, hoog 4,5 m, water 1,8 / 1,9 / 3,2 m | laag / half / hoog |
  | `tijfactor` | halftij-bank, Bretagne 5 m, golf 1,0 m 12 s, per uur | zie `testset_getij_uur.json` |

- **Hoek van de deining:** zie "Wat is de hoek?" hieronder. Negatief = van de baaikant.

## Hoe de score werkt

1. **Strand berekenen** uit de voorspelling voor de kust:
   - golfhoogte aan het strand (Komar & Gaughan)
   - vorm (Iribarren)
   - langsstroming (Komar; op zand uit de deiningshoek; op een point met een vaste breekhoek van 10°, dus groeiend met de golfhoogte; plus stroom uit getij, rivier of spotkennis)
   - kracht
   - rommel
2. **Factoren per plank**, elk tussen 0 en 1: hoogte, vorm, kracht, periode, wind, offshore, inpeddelen, windstoten, rommel, stroming. Afhankelijk van de spot komen daar nog bij: point, deiningsrichting, steil strand, terugslag, volle bank en tijvenster.
   - **Wind:** chop = wind × deel volgens de richting × gewicht volgens de golfhoogte. Deel: offshore tot cross-offshore (0–45°) 0, zuivere zijwind 0,8, recht onshore 1 (geleidelijk). Gewicht: strand en point √(1,2/H) met ondergrens 0,6; rif geen korting; op zware riffen en grote golven ×1,4 (de take-off is daar kritisch): volledig bij vorm 'zwaar' of zwaarder of vanaf 2,5 m, geleidelijk vanaf 1,5 m, niet op kleine gewone riffen.
   - **Deiningsrichting:** op een point heeft de deining een hoek nodig om rond de kaap te buigen. Is het spotveld `deining_venster` [min, max] gekend, dan telt dat (voor elk spottype): buiten het venster ligt de spot in de schaduw van een kaap of eiland, 15° ernaast = ×0,5. Zonder venster op een point: recht erop ×0,55, 20–60° ×1, daarboven schaduw; deining van de baaikant (negatieve hoek) is ook schaduw: 0,55 / (1 + (hoek/15)²).
   - **Wat is de hoek? (vast voor de bouw)** Verschil tussen de richting waar de deining vandaan komt (diep water, uit het golfmodel) en de loodlijn op de algemene kustlijn ter hoogte van de spot, naar zee gericht. Bij een point: de kustlijn bij de punt over ongeveer 1 km (kaart 1:25 000), dus **niet** de baai erachter en **niet** de lijn waarlangs de golf pelt. Positief = deining van de kant waar de golf begint te breken (de punt), negatief = van de baaikant. Voorbeeld: kust bij de punt loopt noord-zuid, zee in het westen: loodlijn 270°; deining uit 300° geeft +30°.
   - **Redactie:** `deining_venster` is **verplicht voor elke point** en aanbevolen voor elke spot achter een kaap of eiland. Zonder venster valt de regel terug op de vuistregel hierboven.
   - **Stroming op een point:** telt in de score maar voor een kwart (×0,25): je rijdt ermee mee en peddelt terug via de geul, en de handscores straffen ze nauwelijks. Op de pagina en voor het label telt ze volledig. Spotveld `langs_factor` schaalt ze per spot (bv. 1,5 voor een 'loopband' zoals Snapper).
   - **Windstoten:** geleidelijk tussen 6 en 14 kn verschil tussen stoot en wind (van ×1 naar ×0,55). Geen klif.
   - **Tijvenster:** spotveld `werkt_bij_tij` (laag/half/hoog) wordt een stuk van de waterstand (zie boven). Valt de waterstand van dat uur erin: ×1. Erbuiten telt hoeveel meter water de stand buiten het venster ligt (stand buiten het stuk × getijverschil), tegenover de diepte waar de golf breekt (Hb / 0,78): factor = 1 / (1 + (verschil / breekdiepte / 0,5)²). Geleidelijk, geen sprong van uur tot uur. Zo telt tij bijna niet waar het getijverschil klein is (Middellandse Zee) en sterk bij 4 tot 6 m (Bretagne, Cornwall), en hebben grote golven er minder last van dan kleine. Het getijverschil van die dag komt uit het getijmodel. Niet als het venster onbekend is, of als de vlag `vol` of `ondiep` al geldt.
   - Score = 1 + 4 × (product van de factoren)^alfa.
3. **Harde grenzen**:
   - Veiligheid zet alles op 1.
   - Daarnaast gelden maxima voor close-out, mist, pier, open strand, kleine golf en tow-in.

**Label "alleen voor ervaren surfers"** (`expert_label`): grote golven (vanaf 2,5 m), holle golf over rif of rotsen (vanaf 1,5 m), ondiep rif of rotsen (vorm met 'ondiep', vanaf 0,8 m), sterke stroming (vanaf 1 m/s), zware shorebreak (vanaf 1,5 m). Staat naast de score, verandert die niet. Testsets: veld `expert`.

Afronden: ,5 gaat naar boven. "Goed" is een 4 of een 5. Niveau telt nooit mee (beslissing van de eigenaar).

## Regels voor de bouw

- **Data en regels blijven gescheiden.** Zet geen plankgetal in de code. Een nieuwe plank is één blok onder `planken` in `regels.json`.
- **Pas een score nooit met de hand aan in de code.** Een betere regel komt alleen van meer nagekeken situaties (handscores), gevolgd door opnieuw afstemmen.
- **Testen:** de eigen implementatie moet `testset_1000.json` volgen met een verschil van hoogstens 0,01. Verandert een regel bewust, maak dan een nieuwe testset en vermeld waarom.
- **Spotkennis wordt vlaggen.** De koppeling staat in `regels.json` onder `vlaggen_uit_spotkennis`. Voorbeeld: "gevaarlijk ondiep bij laagwater" = ja, en het is laag tij, dan geldt de vlag `ondiep` en wordt de score 1.

## Hoe goed is de regel (eerlijk getest)

Getest met `toets.py` op versie 23h: vijf keer afstemmen op 80 nagekeken situaties en toetsen op de 20 die de regel niet zag. De afstemming vertrekt van de expertinschatting (niet van de waarden die al op alle 100 afgestemd zijn, want dat zou lekken) en blijft er licht aan vastgehouden.

| JA vanaf | JA klopt | Echte JA's gevonden |
|---|---|---|
| 3,5 | 78% | 83% |
| 3,7 | 85% | 73% |
| 3,8 | 86% | 66% |
| 4,0 | 96% | 54% |

Bij de kaartdrempel 3,8: 99 van de 150 goede planken gevonden, 16 keer te veel, waarvan 2 echt fout (handscore onder 3). Gemiddelde afwijking: 0,295 (22g: 0,297; 96 gevonden, 15 te veel, 2 echt fout).

Dezelfde toets op versie 22c (voor de laatste twee reviews): vanaf 3,8 84% / 65%, vanaf 3,5 76% / 78%, afwijking 0,312. De wijzigingen zijn dus ook in de eerlijke toets een verbetering. De vroegere cijfers (79 % / 79 % vanaf 3,5) kwamen van een afstemming die niet meer na te rekenen is; vanaf nu telt `toets.py`.

**Kleine lek die de toets niet ziet:** de nieuwe vaste getallen (stroming op een point ×0,25; point 0,55 en 20–60°; geen chop tot 45°) zijn gekozen terwijl naar alle 100 gekeken werd. `toets.py` stemt alleen de plankgetallen af, dus deze keuzes zitten niet in de eerlijke toets. Het effect is klein, maar de echte toets blijven de sessielogs.

**Let op:** de plankgetallen in `regels.json` zijn afgestemd op alle 100 (nodig voor de app). Het testverschil van 0,000 gaat over die getallen; de toets hierboven meet hoe goed de werkwijze is op situaties die ze niet zag.

## Open beslissingen voor de eigenaar

1. **Kaartdrempel:** gekozen op **3,8** (22/10). Eén getal in `regels.json` > `score` > `kaart_drempel`; 3,7 is ook verdedigbaar.
2. **Regen en waterkwaliteit:** vanaf hoeveel mm regen geldt "risico vuil water"? Er is nog geen grens.

## Na te kijken (status: nog te meten of nagaan)

- **Zware riffen en big wave met wind op de golf** (×1,4, niet op kleine riffen): gun op 5 m bij recht onshore: 3 kn 4,7; 5 kn 4,1; 7,5 kn 3,2; 10 kn 2,3; 15 kn 1,5. Toetsen met nagekeken big-wave sessies; geen van de 100 is een big wave met onshore.
- **Deiningsrichting op points** (0,55 / 20° / 60°) en **cross-offshore zonder chop** (grens 45°): verbeteren de 100, maar de getallen zelf zijn expert. Vul per spot `deining_venster` in (hoofdstuk 14: werkende deiningsrichting).
- **Expertlabel:** grenzen 2,5 m, 1,5 m, 0,8 m (ondiep) en 1 m/s (stroming) zijn expert.
- **Stroming langs points:** breekhoek 10° en gewicht 0,25 zijn expert. Toetsen op big-day points (Jeffreys Bay, Snapper, Rincon).
- **Periode-omrekening 0,835:** voor smalle, oude deining eerder 0,86 tot 0,87. Toetsen tegen boeien met spectra (NDBC, Copernicus In Situ).
- **Kleine point met offshore voor de longboard:** knie- tot heuphoog met 10 kn offshore geeft 1,9 ("sterke offshore houdt de take-off tegen"); in het water is dat voor een longboard nog een prima dag. Laten meelopen in de sessielogs.
- **Deiningsvensters:** in de 1000 testset verzonnen (alle points, ongeveer 30% van rif, baai en big wave).
- **Ideale hoogtes per plank:** na het afstemmen liggen ze lager dan de inschatting (longboard 0,9 i.p.v. 1,2; step-up vanaf 1,54 i.p.v. 2,0). Midlength en fish zijn in 23h op de surfer zijn vraag vastgelegd: midlength ideaal tot minstens 1,5 m (nu 1,61), fish tot minstens 1,3 m (nu 1,41). Getest: terug naar de inschatting maakt de regel slechter op de 100 (afwijking 0,286 → 0,343). De handscores vragen dit dus zelf. Opgelet: de flank boven het ideaal is zacht (midlength op 1,5 m nog ×0,83), en hoogte en kracht hangen samen. Toetsen met echte sessies; tot dan niet lezen als 'zo gebruiken surfers die plank'. Ook de **ondergrens 0,6** op strand en point.
- **Tijvenster, getal 0,5:** afgeleid uit één veldmeting (Guedes e.a. 2011: 1,1 m extra water boven de bank, golven onder 1 m, van "meeste golven breken" naar "breken amper"). Toetsen met echte spots met een gekend venster, liefst bij groot én klein getijverschil. Een bank die bij hoogwater altijd dood is, krijgt beter de vlag `vol`.
- **Windstoten 6–14 kn:** expert, nog te toetsen.
- **Testinvoer:** de tijvensters en de getijverschillen in `testset_1000.json` zijn verzonnen (afgeronde typische waarden per kust); echte vensters komen uit de spotvelden (databronnen-doc, hoofdstuk 14), het echte verschil uit het getijmodel.
- **Remfactor van een strekdam (0,4 tot 0,7):** nog te meten.
- **Vormklassen voor rif en point** (Iribarren-equivalent): expertschatting.
- **Krachtlabels** (zwak, matig, krachtig): eigen grenzen.
- **Stormopzet in NW-shelf:** zit die al in het model? Anders wordt hij niet of dubbel geteld.
- **Bliksemvoorspelling (litota) en zicht:** zitten ze in de gratis ECMWF-set?
- **Licenties:** GloFAS en EEA-zwemwater.
- **Nog niet in de regel (review 3):** opkomend of afgaand tij (de "push" van de vloed), hoe regelmatig de sets komen bij lange periode, en een score tegenover de eigen regio ("beste in je buurt", vooral voor de Noordzee: 6 van de 133 situaties halen een 4). Dat laatste is een keuze voor de app, niet voor de regel.
- **Dichtklappers op zandbanken:** hangen vooral af van de vorm van de bank, niet van de zeetoestand. Een factor "rechte lange deining klapt dicht" is getest en verworpen: situatie 69 (holle A-frames bij rechte lange deining) kreeg van de eigenaar 4,8. Blijft de spotvlag `closeout`.
- **Niet te modelleren:** drukte en verschuivende zandbanken. De app zegt hier "volgens spotbeschrijving".

## Voorgestelde volgende stap

**Toets de bronnen aan metingen** (map `proef/`), voor de regel gebouwd wordt:
- golfhoogte en periode van het model tegenover boeien (Copernicus In Situ, NDBC)
- getijstroom en waterstand van NW-shelf en IBI tegenover peilmeters
- golfhoogte aan het strand (Komar & Gaughan) tegenover een paar gemeten stranden
- wind aan de kust: ECMWF tegenover AROME/ICON en kuststations, **de ochtend apart en strenger** dan de middag (zeebries)
- de scores zelf: laat de eigenaar en een paar locals een seizoen lang op 5 à 10 spots hun sessies loggen, met een cijfer per plank

Begin met een handvol spots verspreid over de wereld. De keuze van de bron komt uit die toets, niet uit een mening.

## Wat veranderde in versie 2026-10-22b (na de review)

| Punt | Was | Nu |
|---|---|---|
| Big wave en rif met onshore | Korting √(1,2/H) maakte 15 kn onshore op 6 m tot ±6 kn. Situatie 33 (gun, 5,2 m, 8 kn onshore) gaf 4,6; 875 en 783 gaven 4. | Rif en big wave: geen korting, onshore weegt zwaarder naarmate de golf groter is. 33 → 2,7; 875 → 2,5; 783 → 1,4. Strand en point: korting met ondergrens 0,6. |
| Windstoten | Klif: vanaf 12 kn verschil ×0,55, bij 11 kn niets. | Geleidelijk tussen 6 en 14 kn verschil. Testset 1000: stoten begrensd tot max(wind + 8; 1,6 × wind) kn, 91 situaties aangepast (261: 0 kn met stoten tot 18 → tot 8). |
| Tijvenster | Spotveld "werkt bij tij" niet gebruikt; alleen de uitersten (ondiep, vol). | Factor tijvenster (zie boven). Getij staat nu in de ruwe invoer van beide testsets. |
| Kaartdrempel | Leeg. | 3,8. |
| Tekst op de 1000-pagina | "Verwaaid: chop op de wall" ook bij wind zonder onshore-deel. | "Harde zijwind (van land): hobbels op de wall". |

Effect: op de 100 nagekeken situaties veranderen 15 van de 800 scores, met hoogstens 0,02; de eerlijke toets blijft dus geldig. Op de 1000 veranderen 1870 van de 8000 scores, in 306 situaties; bij 68 situaties verandert welke planken goed zijn. Geen big wave met minstens 5 kn onshore haalt nog een 4.

## Wat veranderde in versie 2026-10-22c (na de tweede review)

| Punt | Was (22b) | Nu (22c) | Waarom |
|---|---|---|---|
| Big wave en rif met wind op de golf | Geen korting, plus extra straf die meegroeit met de golf (macht 0,15). 7–8 kn onshore gaf een gun rond 2,7. | Geen korting, geen extra straf. 33 → 3,4; 875 → 3,1; 783 (15 kn) → 1,8. | Chop door wind wordt niet hoger als de deining groter is; een straf die meegroeit met de golf heeft geen grond. Reviewer: 7–8 kn eerder een 3. |
| Tijvenster | Vaste factor: één stap ernaast ×0,75, twee ×0,5, overal ter wereld gelijk. | Factor hangt af van het getijverschil van die dag en de golfhoogte (zie boven). | Een golf breekt bij een diepte van ongeveer 1,3 × zijn hoogte. Wat telt is dus hoeveel water er bij komt tegenover die diepte: 0,3 m in de Middellandse Zee doet bijna niets, 4 m in Frankrijk maakt een laagwaterbank dood. |

Effect: de 100 nagekeken situaties veranderen niet (0 van de 800 scores). Situatie 184 (zandbank, werkt bij laag tot half, nu hoogwater, Zuidwest-Frankrijk 3,8 m): shortboard 4,0 → 2,1.

## Wat veranderde in versie 2026-10-22d (na de derde review)

| Punt | Was (22c) | Nu (22d) | Getoetst op de 100 |
|---|---|---|---|
| Wind van het land | Zijwind telde altijd voor 80% als chop, ook cross-offshore. Cross-onshore (135°) scoorde slechter dan recht onshore. | Wind van het land maakt geen chop (0–45°): geen stuk water om chop op te bouwen. Zij 0,8, onshore 1, geleidelijk. | Beter |
| Deiningsrichting op een point | De hoek maakte de golf alleen kleiner; rechte deining scoorde het best. De zandstrandformule voor stroming strafte schuine deining nog eens. | Recht erop ×0,55, 20–60° ×1, daarboven schaduw. Geen zandstrandstroming op points. Spotveld `deining_venster` telt als het gekend is. | Beter (vooral 34, 39, 40) |
| Big wave en rif met onshore | Geen korting, geen extra weging: 7,5 kn gaf nog een 4. | ×1,4 op rif en big wave: 7,5 kn 3,2; 33 → 3,0. | Geen effect (zit niet in de 100) |
| Label voor ervaren surfers | Geen. | Apart label, score blijft gelijk. | n.v.t. |
| Kruisende deining op zand (voorstel review) | Rommel vanaf 0,3. | Ongewijzigd: jouw handscores zien kruisende deining als rommel (afwijking zou groeien van 0,36 naar 0,41). | Voorstel verworpen |
| Dichtklappers uit rechte lange deining (voorstel review) | Alleen spotvlag. | Ongewijzigd: verworpen (zie boven). | Voorstel verworpen |

Effect op de 100 (zelfde plankgetallen, niet opnieuw afgestemd): gemiddelde afwijking 0,286 → 0,272. JA vanaf 3,8: 104 van de 150 goede planken gevonden (was 99), 6 keer te veel (was 5). Op de 1000 veranderen 3717 van de 8000 scores tegenover de eerste overdracht.

## Wat veranderde in versie 2026-10-22e (na de vierde review)

| Punt | Was (22d) | Nu (22e) |
|---|---|---|
| Hoek op een point | Niet vastgelegd: kust bij de punt, baai of pellijn gaven tot 30° verschil (3,1 of 4,7 op dezelfde dag). | Vastgelegd (zie "Wat is de hoek?"). `deining_venster` verplicht voor points. In de 1000 nu bij alle points en ongeveer 30% van rif, baai en big wave, dus de code is getest. |
| Stroming op een point | Weg (alleen getij of rivier): hoogstens 0,3 m/s, ook op grote dagen. | Groeit met de golfhoogte (1 m 0,6 m/s; 2 m 0,9; 3 m 1,1). Score ×0,25 (getoetst: volledig meetellen verdubbelt de afwijking op de points van de 100), label en pagina volledig. |
| Wind ×1,4 op rif | Elk rif, ook een klein rif van 1 m. | Alleen zware riffen en grote golven (zie boven). Kleine riffen ×1. |
| Expertlabel | Grote golf, hol rif, shorebreak. | Plus ondiep rif vanaf 0,8 m en stroming vanaf 1 m/s. |
| Eerlijke toets | Cijfers van vóór 22d. | Opnieuw gedraaid met `toets.py` (zie boven). |
| Pagina | Wind schuin van zee heette "onshore"; voetnoot verouderd. | Cross-onshore en cross-offshore heten zo; voetnoot bijgewerkt. |

## Wat veranderde in versie 2026-10-22f (na de vijfde review)

| Punt | Nu |
|---|---|
| Periode | Vastgelegd: piekperiode per systeem; omrekening uit de gemiddelde periode van het model (zie boven). |
| Laag, half, hoog tij | Vastgelegd: derden van de waterstand tussen laag- en hoogwater van die cyclus. |
| Negatieve hoek zonder venster | Schaduw. In de 1000 nu 12 points zonder venster, waarvan 6 met deining van de baaikant, dus getest. |
| Pagina | Stromingstekst op points klopt weer met de regel (telt voor een kwart). |

Op de 100 verandert niets (afwijking 0,272), dus de eerlijke toets blijft dezelfde.

## Wat veranderde in versie 2026-10-22g (na de zesde review)

| Punt | Was (22f) | Nu (22g) |
|---|---|---|
| Tij | Drie bakjes (derden van de waterstand). Halftij duurde maar 1u20; een halftij-spot haalde de kaart (3 uur na elkaar) nooit; bij groot getij sprong de factor van 1 naar 0,09 in één uur. | Rekent met de waterstand zelf (zie boven). Testdag Bretagne, halftij-bank: rond elk middentij ongeveer 4 uur na elkaar goed, rond laag- en hoogwater een 3 ("breekt slecht"), geen sprong. Middellandse Zee: de hele dag goed. |
| Periode per bron | Alleen IBI en NW-shelf. | Ook MFWAM (gemiddeld, omrekenen) en GFS-Wave (na te gaan met boeien, tot dan niet gebruiken). |
| Voorbeelden | Geen. | Tabel met voorbeelden hierboven en `testset_getij_uur.json`. |

Op de 100 verandert niets (afwijking 0,272), dus de eerlijke toets blijft dezelfde. Op de 1000 veranderen scores waar het tij buiten het venster ligt: de straf is kleiner geworden, omdat nu telt hoe ver het water buiten het venster staat in plaats van een hele stap. Voorbeeld 184 (laag-tot-halftij-bank, hoogwater, 3,8 m getij, golf 1,8 m): 0,6 m water te veel, shortboard 4,2.

## Wat veranderde in versie 2026-10-23h (review 6, surfer)

Twee planken waren verkeerd afgesteld. Alleen midlength en fish zijn opnieuw afgestemd op de 100 (`afstemmen.py MID FI`); de andere planken en alfa zijn ongemoeid. Vaste grenzen staan in `regels.json` als `min` of `max`; `afstemmen.py` en `toets.py` houden zich eraan.

| Punt | Was (22g) | Nu (23h) |
|---|---|---|
| Midlength, ideaal tot (c) | 0,93 m (inschatting 1,9) | 1,61 m (inschatting 1,7; vast op minstens 1,5) |
| Midlength, d | 3,46 (inschatting 3,2) | 2,81 (inschatting 3,5) |
| Fish, straf in zachte golven (zacht_min) | 0,25 | 0 |
| Fish, kracht nodig (kp) | 0,57 (inschatting 0,6) | 0,28 (inschatting 0,25; vast op hoogstens 0,3) |
| Fish, ideaal tot (c) | 1,06 m (inschatting 1,5) | 1,41 m (inschatting 1,5; vast op minstens 1,3) |
| Handscores midlength 26 / 30 / 40 (4,7 / 4,7 / 4,2) | regel 3,95 / 3,74 / 3,39 | regel 4,13 / 4,58 / 3,83 |

**Gevolg op de 100** (getallen zoals in de app): afwijking 0,272 → 0,265 (midlength 0,361 → 0,328, fish 0,285 → 0,265, de andere planken gelijk). Bij drempel 3,8: 104 → 106 goede planken gevonden, 6 te veel (gelijk), 0 echt fout.

**Eerlijke toets** (`toets.py`): afwijking 0,297 → 0,295; bij 3,8 JA klopt 86,5% → 86,1%, echte JA's gevonden 64% → 66% (96 → 99 van 150, te veel 15 → 16, echt fout 2 → 2). Vanaf 3,5 stijgt 'echt fout' van 2 naar 5; de kaart gebruikt 3,8.

**Fish op zachte dagen** (1000, golf aan het strand 0,6–1,2 m, zacht): fish 1,72 → 1,92, midlength 2,06 → 2,09, shortboard 1,32. Fish boven de shortboard in 102 → 119 van de 134. Op kleine slappe dagen blijft de fish onder de groveler (in de 100: hand −1,05, regel −0,93 → −0,72).

**Hoe vaak is elke plank de beste in de 1000**

| Plank | België + Nederland (87), vóór → na | Portugal + Zuidwest-Frankrijk (223), vóór → na |
|---|---|---|
| Longboard | 20 → 22 | 42 → 42 |
| Minimal | 1 → 1 | 19 → 19 |
| Midlength | 20 → 19 | 26 → 29 |
| Groveler | 46 → 42 | 71 → 63 |
| Fish | 0 → 3 | 1 → 5 |
| Shortboard | 0 → 0 | 43 → 44 |
| Step-up | 0 → 0 | 14 → 14 |
| Gun | 0 → 0 | 7 → 7 |

De testsets (`testset_100.json`, `testset_1000.json`, `testset_getij_uur.json`) zijn herberekend: `referentie.py` geeft weer 0,000. De pagina's "Honderd surfdagen" en "Duizend surfdagen" staan niet in deze repository en zijn dus niet aangepast.
