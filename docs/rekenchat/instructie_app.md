# Instructie voor de app: score per strand en per uur

Bijgevoegd: `score.py` (rekencode), `tests.py` (tests), `score_parameters.json` (alle grenswaarden).
Zet de rekencode om naar de taal van de app en neem de grenswaarden over uit het json-bestand.
Verander geen enkele grenswaarde. Draai daarna de tests: alle moeten slagen.

## Wat de app toont

- Per strand en per uur twee cijfers van 0 tot 4: links WIND (cyaan), rechts WAVE (blauw).
- 0 = niets (score 0-19), 1 = iets (20-39), 2 = potentieel (40-59), 3 = zekerheid (60-79), 4 = ideaal (80-100).
- Het cijfer is het hoogste van de categorieën in die groep. WAVE = 7 categorieën, WIND = 10 categorieën.
- Rand, alleen bij 3 of 4: groen als een beginnerscategorie 60 of meer haalt, anders oranje als een
  gemiddelde categorie 60 of meer haalt, anders rood.
- Filter op niveau: het cijfer is dan het hoogste binnen dat niveau.
- Uitklappen: de score op 100 voor elk van de 17 categorieën, met de deelscores.
- Categorie 18, stille waters: eigen score op 100 en eigen cijfer 0-4.
- Storm: achtergrond zwart bij gemiddelde wind van 41 knopen of meer, of vlagen van 48 knopen of meer.
- Te gevaarlijk: het cijfer 0 betekent ofwel "niets" ofwel "te veel". `te_veel = ja` bij een groep:
  toon die cirkel zwart. Zo ziet de gebruiker het verschil tussen een vlakke zee en te grote golven,
  en tussen windstil en te harde wind. Werkt ook met de niveaufilter (te groot voor beginners).
- Waarschuwingen per categorie: toon ze naast de score. Ze veranderen de score niet.

Alles hierboven komt uit één functie: `strand_uur(condities, niveau)`.

## De 17 categorieën

WAVE: golfsurfen beginner, gemiddeld, ervaren; longboard gemiddeld, ervaren; shortboard gemiddeld, ervaren.
WIND: windsurfen beginner, gemiddeld, ervaren; kitesurfen beginner, gemiddeld, ervaren;
windsurfen op golven gemiddeld, ervaren; kitesurfen op golven gemiddeld, ervaren.

## Invoer per strand en per uur

| Veld | Eenheid | Herkomst |
| --- | --- | --- |
| wind, vlaag | knopen | voorspelling |
| windhoek | 0-180 graden | verschil tussen windrichting en kijkrichting; 0 = recht aanlandig, 180 = recht aflandig |
| golfhoogte | m | hoogte op het strand van het hoofdgolfsysteem, zoals de app die al berekent |
| periode | s | periode van het hoofdgolfsysteem |
| golfhoek | 0-90 graden | verschil tussen golfrichting en kijkrichting |
| aandeel_hoofdgolf | 0-1 | hoogte in het kwadraat gedeeld door de som van de kwadraten van alle golfsystemen |
| golf_aan_strand | m | wortel uit de som van de kwadraten van de hoogtes op het strand |
| stroming, stroming_tov_wind | knopen; tegen, mee of dwars | voorspelling; tegen of mee binnen 45 graden van de windas |
| neerslag, onweer | mm per uur; ja of nee | voorspelling |
| donker | ja of nee | na zonsondergang of voor zonsopgang |
| uur_tot_donker | uur | berekend |
| watertemperatuur | graden Celsius | voorspelling |
| gewicht | kg | instelling van de gebruiker; 75 als het leeg is |
| getij_match | 1, 0,6 of 0,2 | alleen als getij_voorkeur ingevuld of geleerd is; anders weglaten |

Het hoofdgolfsysteem is het golfsysteem dat op het strand het hoogst breekt.

## Regels die vastliggen

- Onweer of donker: elke categorie 0.
- De brekende golf wordt berekend uit hoogte en periode. Of ze te klein is, wordt beoordeeld met 80% van
  die waarde; of ze te groot is, met de volle waarde.
- Kitesurfen bij aflandige wind: 0.
- Getij telt alleen mee waar het beste getij bekend is. Geschatte waarden niet gebruiken.
- Stranden met `onzeker = ja`: toon geen score.

## Wat nog niet vaststaat

De grenswaarden zijn deels onderbouwd met bronnen en deels eigen keuze van de rekenchat.
Houd ze daarom in het json-bestand en niet in de code, zodat ze later aangepast kunnen worden.
