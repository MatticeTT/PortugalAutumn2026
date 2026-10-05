# Surfkaart Portugal: bouwplan voor Claude Code

Dit plan is geschreven om door Claude Code te worden uitgevoerd, mijlpaal per mijlpaal. Zet het als `PLAN.md` in de root van een lege repository en start met: *"Lees PLAN.md en voer mijlpaal 0 uit. Stop na elke mijlpaal en toon de acceptatietests."*

Opgesteld op 5 oktober 2026 na een prototype voor de Algarve en zes bronnenonderzoeken. Bij elke bewering staat hoe zeker ze is:

- **[gemeten]**: zelf nagemeten in het prototype.
- **[bron]**: in een primaire bron gelezen, twee keer gecontroleerd. De links staan in hoofdstuk 10.
- **[onbevestigd]**: aannemelijk maar niet bevestigd. Claude Code moet dit eerst zelf controleren voor erop te bouwen.

## 1. Wat we bouwen

Een webkaart van alle stranden van het Portugese vasteland. Per strand en per uur toont ze:

1. **De ruwe voorspelling**, dezelfde cijfers als op Windguru: wind, vlagen, windrichting, golfhoogte, periode, golfrichting, eerste en tweede deining, windgolf.
2. **Eb en vloed**, met de tijden van hoog- en laagwater en het venster ertussen als surfmoment.
3. **Twee scores van 1 tot 5**: WIND voor kitesurf en windsurf, WAVE voor golfsurfen, met een label en de reden erbij. De schaal: 1 de moeite niet, 2 wellicht niets, 3 ideaal voor beginners, 4 sterk (gevorderden), 5 gevaarlijk.

De look van het prototype blijft: een kaart met per strand een bolletje, een fiche met een golfje dat groter en feller wordt naarmate de golven groter zijn, en een windpijl. Het bolletje heeft een cyaan helft (WIND) en een blauwe helft (WAVE), elk van flets naar fel.

**Maatstaf voor "minstens zo nauwkeurig als Windguru":**

- In de stand "zelfde model als Windguru" wijken de cijfers hoogstens een afronding af van Windguru.
- Tegen echte boeimetingen is de fout van het standaardmodel niet groter dan die van het Windguru-model.
- Hoog- en laagwater vallen binnen enkele minuten van de officiële getijtafel.

## 2. Wat het onderzoek zegt over "deftige surf"

Dit hoofdstuk bepaalt wat de app wel en niet mag beweren. Paragraaf 2.1 en 2.2 geven de achtergrond; 2.3 tot 2.6 leggen de twee scores vast; 2.7 gaat over het getij.

### 2.1 Wat een golf surfbaar maakt

Een surfgolf wordt beschreven door vier eigenschappen: brekende golfhoogte, pelhoek, breekintensiteit en sectielengte (Scarfe e.a. 2003, wetenschappelijk overzicht) **[bron]**.

| Eigenschap | Waar ze van afhangt | Uit een weermodel te halen? |
|---|---|---|
| Brekende golfhoogte | Deining (hoogte, periode, richting) en de zeebodem | Deels, met een ruime marge |
| Pelhoek | Vorm van de zeebodem | Nee |
| Breekintensiteit | Helling van de zeebodem | Nee |
| Sectielengte | Zeebodem en zandbanken | Nee |

Gevolg: uit modeldata is te zeggen of er genoeg golf aankomt en of de wind ze kapotmaakt. Of de golven ook mooi lopen, hangt af van de zeebodem en van zandbanken die verschuiven.

### 2.2 Regels en hoe sterk het bewijs is

| Regel | Bewijs | Gebruik in de app |
|---|---|---|
| Deining en windgolven tel je op als wortel van de som van de kwadraten | Sterk (BoM, NWS) | Ja |
| Langere periode geeft een hogere brekende golf: Hb = 0,39 · g^0,2 · (T · H²)^0,4 (Komar en Gaughan) | Sterk als trend; plaatselijk een factor 0,5 tot 2 door de bodem | Ja, als bereik getoond |
| Minimale en maximale surfbare hoogte per niveau (Hutt, Black en Mead 2001) | Sterk, via een secundaire bron gelezen | Ja, als steun voor de grenzen in 2.5 |
| Aanlandige wind laat golven vroeger en slapper breken, aflandige later en holler (Douglass 1990; Feddersen 2023) | Sterk, gemeten | Ja, als richting van het effect |
| Aflandige wind boven 20 knopen bederft de surf | Vuistregel; bronnen spreken van 20 tot 30 knopen | Alleen als nota, gelabeld als vuistregel |
| Te veel wind om te surfen | Geen gemeten grens; ASI geeft les onder 20 km/u (beginners) en 35 km/u (gevorderden) | Ja, in het label, zie 2.5 en 2.6 |
| Deining begint bij 10, 12 of 13 seconden | Vuistregel; geen afgesproken grens | Niet als grens gebruiken; de periode telt mee via de formule |
| Lange periode is altijd beter | Fout; op rechte strandbreaks klappen lange deiningen dicht | Niet gebruiken |
| Getij verandert een break sterk | Sterk | Getij altijd tonen |
| "Surf bij half tij" als algemene regel | Geen bewijs gevonden; alle bronnen zeggen dat het per break verschilt | Standaardvenster op wens van de eigenaar, per strand aanpasbaar, zie 2.7 |
| "Goed" of "episch" afleiden uit modeldata | Niet verdedigbaar; Surfline laat die oordelen door mensen invullen | Niet doen; de scores zeggen hoeveel wind en golf er is en voor wie |

**Surfbare brekende golfhoogte per niveau** (Hutt e.a., gelezen via Lewis e.a. 2015) **[bron]**:

| Niveau | Hutt-klasse | Minimum | Maximum |
|---|---|---|---|
| Beginner | 2 | 0,65 m | 1,5 m |
| Gevorderd | 4 | 0,55 m | 4,0 m |
| Expert | 6 | 0,45 m | boven 4 m |

### 2.3 Twee scores per strand en per uur

De app geeft geen oordeel "goed" of "slecht". Ze geeft twee cijfers van 1 tot 5, met de betekenis die de eigenaar heeft vastgelegd:

| Score | Betekenis |
|---|---|
| 1 | De moeite niet |
| 2 | Je kan proberen, wellicht niets |
| 3 | Ideaal voor beginners |
| 4 | Sterk: voor gevorderden |
| 5 | Gevaarlijk |

- **WIND** (cyaan): kracht en richting van de wind, voor kitesurf en windsurf.
- **WAVE** (blauw): grootte en periode van de golven, voor golfsurfen.

Bij elke drempel staat hoe sterk het bewijs is:

- **Sterk**: een federatie, reddingsdienst of overheid zegt het, of het is gemeten.
- **Praktijk**: scholen, verhuurders of één vereniging hanteren het; er is geen officiële norm.
- **Eigen keuze**: geen bron geeft dit getal. Het is gekozen binnen wat de bronnen wel zeggen en wordt in M7 geijkt.

Wat het onderzoek vooraf vaststelde **[bron]**:

- Geen enkele federatie (IKO, RYA, World Sailing, GKA) publiceert windsterktes per niveau. De sterktegrenzen komen van scholen, verhuurders, één vereniging en officiële schalen. Alleen de regel over aflandige wind staat bij federaties en reddingsdiensten.
- Voor golven geven de opleidingsorganisaties (ASI, ISA, Surfing England) wel een golfhoogte per niveau. Geen enkele geeft een grens voor de periode.
- Er is geen gepubliceerde index gevonden die windrichting meetelt. De sterren van Windguru volgen volgens hun instellingenpagina alleen de windsnelheid.

Alle drempels staan in één bestand, `rules.yaml`, elk met bron en bewijsniveau. Claude Code verzint geen drempels en verandert er geen zonder dat de eigenaar het vraagt.

### 2.4 De WIND-score

Invoer per uur: gemiddelde wind op 10 m in knopen, vlagen, en de windrichting tegenover de kijkrichting van het strand.

**Stap 1: sterkte.**

| Score | Gemiddelde wind | Waarop het steunt | Bewijs |
|---|---|---|---|
| 1 | onder 8 kn | Kiteverhuur begint bij 8 kn (The Kitesurf Centre); een windsurfschool noemt kracht 1 tot 2 te licht | Praktijk |
| 2 | 8 tot 11 kn | Kiten is "over het algemeen mogelijk" vanaf 10 tot 11 kn (KiteWorldWide); de gemiddelde rijder heeft ongeveer 10,4 kn nodig (MACkite) | Praktijk |
| 3 | 12 tot 21 kn | Beginnersbereik 12 tot 22 kn (KiteWorldWide); leren gaat het best bij 17 tot 24 kn (Kite & Wing WA); windsurfers planeren vanaf 12 tot 14 kn | Praktijk; voor 17 tot 21 kn ook een vereniging |
| 4 | 22 tot 33 kn | Verhuur stopt bij 25 kn gemiddeld of 30 kn in vlagen; beginners krijgen het rond 30 kn hoe dan ook moeilijk (KiteWorldWide); windsurf kracht 6 is gevorderd, kracht 7 expert; World Sailing start geen wedstrijd boven 25 kn | De grens op 22 kn is een eigen keuze: de bronnen zeggen 22, 24 of 25 |
| 5 | 34 kn of meer, of vlagen van 38 kn of meer | Kracht 8 is storm (Met Office); IPMA geeft geel vanaf vlagen van 70 km/u; wedstrijdbereiken eindigen bij 35 kn; de meeste kiters stoppen rond 40 kn | De getallen zijn sterk (officiële schalen); dat ze "gevaarlijk om te varen" betekenen is een eigen keuze |

Een voorzichtiger variant staat klaar in `rules.yaml`: score 5 vanaf 28 kn gemiddeld of vlagen boven 30 kn.

**Stap 2: richting.** De hoek is die tussen de richting waar de wind vandaan komt en de kijkrichting van het strand (0 graden is recht uit zee).

| Klasse | Hoek | Effect op de score | Bewijs |
|---|---|---|---|
| Aanlandig | 0 tot 22,5° | Score blijft. Nota: "recht aanlandig, weinig ruimte, voor kite alleen met ervaring" | Praktijk (één fabrikant raadt het af) |
| Schuin aanlandig | 22,5 tot 67,5° | Score blijft. Nota: "ideale richting" | Sterk voor kite (Kite & Wing WA); praktijk voor beginners |
| Zijwind | 67,5 tot 112,5° | Score blijft. Nota: "ideale richting" | Zelfde |
| Schuin aflandig | 112,5 tot 157,5° | Bij 8 kn of meer wordt de score **5**; onder 8 kn blijft ze 1 | Sterk: IKO telt schuin aflandig bij aflandig |
| Aflandig | 157,5 tot 180° | Zelfde | Sterk: RNLI ("NEVER ... in offshore winds without safety boat cover"), IKO, RYA |

De sectorgrenzen van 45 graden zijn een eigen keuze; geen federatie geeft hoeken. Een strand waarvan de kijkrichting in M1 als onzeker is gemarkeerd, krijgt geen richtingsoordeel maar de nota "richting niet beoordeeld".

**Stap 3: vlagen.** Vlagen boven 30 kn geven minstens score 4 (praktijk: de verhuurgrens van één school). Vlagen van 38 kn of meer geven 5. Liggen de vlagen meer dan 20 procent boven het gemiddelde, dan komt er alleen de nota "vlagerig" bij. Hoe groot die verhouding in de modeldata doorgaans is, is **[onbevestigd]**; M6 meet dat voor de nota wordt aangezet.

**Kite en windsurf verschillen.** De tabel volgt de kite, omdat die het best onderbouwd is. De fiche toont er een regel voor windsurf bij:

- 7 tot 11 kn: windsurfbeginners kunnen al oefenen, zonder planeren (schoolbereik 8 tot 14 kn). Praktijk.
- 12 tot 16 kn: planeren begint; lessen lopen tot kracht 4 (procedures van een RYA-opleidingscentrum). Praktijk.
- 17 tot 21 kn: voor windsurfbeginners te veel; voor kitebeginners nog binnen bereik. Praktijk.

`rules.yaml` bevat de twee tabellen apart, zodat een schakelaar kite/windsurf later kan zonder herschrijven.

**Uitzondering per strand.** Op een lagune of baai waar de overkant dichtbij ligt, drijf je bij aflandige wind niet de zee op. De eigenaar kan een strand als `besloten_water` markeren; dan vervalt de regel van score 5 bij aflandige wind en blijft de nota staan. Standaard staat dit uit.

### 2.5 De WAVE-score

**De maat** is de geschatte brekende golfhoogte op het strand, Hb, in meter. Ze neemt hoogte en periode samen in één getal, in dezelfde eenheid als de grenzen van de surfopleidingen.

- Per deelgolf uit het model (eerste deining, tweede deining, windgolf): hoogte H, piekperiode T en richting.
- Per deelgolf een blootstellingsfactor f tussen 0 en 1: hoeveel van die golf het strand bereikt, volgens het deiningsvenster uit M1.
- Hb = k · 0,39 · g^0,2 · (som van f² · H² · T)^0,4. Dit is de formule van Komar en Gaughan, toegepast op de opgetelde energiestroom van de deelgolven **[bron, afgeleid]**.
- k is één ijkfactor voor de hele kaart, standaard 1,0, aan te passen na M7.

Zonder de factor f is Hb een bovengrens: de hoogte op een volledig open strand zonder verlies. De factor f zelf is een eigen keuze (meetkunde, geen meting); zie de risico's.

**Grenzen.**

| Score | Hb op het strand | Waarop het steunt | Bewijs |
|---|---|---|---|
| 1 | onder 0,3 m | Minimum voor experts bij Hutt (0,3 m); Surfing England vraagt alleen "genoeg kracht" | Eigen keuze |
| 2 | 0,3 tot 0,5 m | Onder de halve meter die ISA voor beginners verkiest en onder het leerlingminimum van Hutt (0,65 m) | Praktijk |
| 3 | 0,5 tot 1,0 m | ISA: beginners "preferable half meter"; ASI: beginners onder 0,5 m, halfgevorderden tot 1 m; Hutt: beginnersmaximum 1,0 m | Ondergrens praktijk, bovengrens sterk |
| 4 | 1,0 tot 3,0 m | ASI gevorderden 1 tot 3 m; Surfing England: lessen voor beginners alleen onder 1,5 m | Sterk als lesgrens |
| 5 | 3,0 m of meer | Plafond van ASI voor gevorderdenles; Amerikaanse brandingswaarschuwingen liggen tussen 1,8 en 4,6 m; surf-forecast noemt 1000 kJ "heavy" (ongeveer 1,6 tot 2,8 m deining) | Sterk als lesgrens; als "gevaarlijk" een eigen keuze |

De bronnen spreken elkaar over beginners tegen: ASI en ISA leggen de grens op 0,5 m, Hutt geeft 0,65 tot 1,0 m, Surfing England laat lessen toe tot 1,5 m. Score 3 volgt het midden daarvan.

Binnen score 4 toont de fiche bij 1,0 tot 1,5 m: "les voor beginners kan nog (grens Surfing England)". Een alternatief voor de bovenste grens staat klaar in `rules.yaml`: 4,0 m, het maximum van Hutt-klasse 4.

Dezelfde grenzen als golfhoogte op zee, voor een volledig open strand (eigen berekening met de formule hierboven):

| Hb | bij 6 s | 8 s | 10 s | 12 s | 14 s | 16 s |
|---|---|---|---|---|---|---|
| 0,3 m | 0,17 m | 0,14 | 0,13 | 0,12 | 0,11 | 0,10 |
| 0,5 m | 0,31 m | 0,27 | 0,24 | 0,22 | 0,21 | 0,19 |
| 1,0 m | 0,75 m | 0,65 | 0,58 | 0,53 | 0,49 | 0,46 |
| 1,5 m | 1,24 m | 1,08 | 0,96 | 0,88 | 0,81 | 0,76 |
| 3,0 m | 2,96 m | 2,56 | 2,29 | 2,09 | 1,93 | 1,81 |
| 4,0 m | 4,23 m | 3,67 | 3,28 | 2,99 | 2,77 | 2,59 |

Voorbeeld: 1 m deining van 12 seconden geeft op een open strand Hb 1,66 m, dus score 4. Dezelfde deining op een strand met f = 0,5 geeft 0,95 m, dus score 3.

**Regels die de score overschrijven.**

- Geldt er een IPMA-waarschuwing voor zeegang (geel of hoger) voor de kuststrook van het strand, dan is de score **5**. De Portugese surffederatie verbiedt lessen onder een afgekondigde waarschuwing en de havenkapitein van Lissabon eist bij oranje een toelating om te surfen. Sterk. IPMA geeft geel vanaf 4 m golfhoogte op zee, en vanaf 2 m bij zuidoostdeining op de zuidkust van de Algarve.
- Is de piekperiode van de grootste deelgolf korter dan 6 seconden, dan is de score hoogstens **2**, behalve als ze al 5 is. Eigen keuze, zwak bewijs: forecasters noemen 3 tot 8 seconden "chop", geen federatie geeft een grens.
- Is de piekperiode 15 seconden of langer, dan komt er een nota bij: "lange deining: lange pauzes tussen de sets, sterkere stroming". Eigen keuze, gesteund op het Australische weerbureau en de Amerikaanse weerdienst.

**Wind bij golven.** De wind verandert het cijfer niet, wel het label (2.6) en de tekst:

- ASI geeft les aan beginners alleen bij wind onder 20 km/u (11 kn) en aan gevorderden onder 35 km/u (19 kn). Praktijk.
- Aflandige wind laat golven later en holler breken, aanlandige vroeger en slapper (Douglass 1990; Feddersen 2023). Sterk als richting van het effect. De fiche zegt "schoon" of "rommelig".

**Wat dit op de kaart geeft.** Op een volledig open strand aan de westkust scoort een gemiddelde zomerdag (1,6 m, 9 s) een 4 en een gemiddelde winterdag (3 m) een 5. Score 3 komt vooral voor op beschutte stranden en op kleine dagen. Dat volgt uit het golfklimaat (Sines: gemiddeld 1,7 m, piekperiode meestal 9 tot 13 s; Faro: gemiddeld 1,0 m) **[bron]**. Beginners surfen bovendien in het schuim, dat lager is dan Hb; de ijkfactor k en het logboek van M7 dienen om dit bij te stellen.

### 2.6 Label en bolletje

**Het bolletje** op de kaart heeft twee helften: links cyaan met het WIND-cijfer, rechts blauw met het WAVE-cijfer. Elke helft loopt in vijf stappen van flets (1) naar fel (5). Voorstel: bij een 5 krijgt het bolletje een rode rand, zodat "gevaarlijk" niet voor "beste" wordt aangezien.

**Het label** op de fiche. De eerste regel die past, geldt:

| # | Voorwaarde | Label |
|---|---|---|
| 1 | WAVE = 5 | Gevaarlijke zee |
| 2 | WIND = 5 door sterkte of vlagen | Gevaarlijk: storm |
| 3 | WIND = 5 door aflandige wind, WAVE = 3 en wind tot 11 kn | Surfdag voor beginners, met de waarschuwing "aflandige wind: niet voor kite, windsurf of sup" |
| 4 | WIND = 5 door aflandige wind, WAVE = 4 en wind tot 19 kn | Surfdag voor gevorderden, met dezelfde waarschuwing |
| 5 | WIND = 5 door aflandige wind, in de andere gevallen | Aflandige wind: gevaarlijk voor kite, windsurf en sup |
| 6 | WIND 3 of 4 en WAVE 3 of 4 | Winddag met golven (gevorderd) |
| 7 | WIND = 4 | Winddag voor gevorderden |
| 8 | WIND = 3 | Winddag voor beginners |
| 9 | WAVE = 4 | Surfdag voor gevorderden |
| 10 | WAVE = 3 | Surfdag voor beginners |
| 11 | WIND en WAVE allebei onder 3 | Stille dag (sup, kayak, wakeboard) |

Regels 3 en 4 bestaan omdat aflandige wind voor surfers net schone golven geeft, terwijl hij voor kite, windsurf en sup gevaarlijk is.

**Stille dag.** Wat de bronnen zeggen over sup en kajak:

- Tot 10 kn: goed (ACA niveau 2 onder 10 kn; British Canoeing kracht 3; ASI 10 kn voor beginners op zee). Sterk.
- 11 kn (de rest van WIND 2): nota "randgeval voor sup". Boven 16 kn is sup in de wateren van Cascais verboden (edital van de havenkapitein). Sterk.
- Aflandige wind, ook zwak: nota "aflandig: blijf dicht bij de kant" (RNLI en Paddle UK raden aflandige wind af). Sterk.
- De Portugese surffederatie beperkt sup-lessen tot golven van 1 m. Sterk.
- Wakeboard: geen bron met een wind- of golfgrens gevonden. Het staat in het label op wens van de eigenaar.

**Onder het label** toont de fiche altijd: de twee cijfers met hun reden in woorden ("WIND 3: 16 kn, schuin aanlandig"; "WAVE 4: 1,7 m brekend, 12 s"), de regel voor windsurf, de nota's, de getijvensters en de ruwe tabel. De golfhoogte op het strand staat er als bereik.

**Plaatselijke regels**, als vaste voetnoot: surf, kite en windsurf zijn verboden in zones voor baders (nationaal strandedict); havenkapiteins leggen in het badseizoen afstanden op (Cascais: 300 m van badstranden) **[bron]**.

### 2.7 Getij: de wens van de eigenaar tegenover de bronnen

De eigenaar wil het venster tussen eb en vloed als surfmoment. Het onderzoek vond daar geen algemeen bewijs voor. Een forecaster van Surfline schrijft dat de meeste spots "laag, opkomend" verkiezen en noemt dat in dezelfde tekst speculatie.

Uitwerking die beide respecteert:

- Hoog- en laagwater staan altijd op de fiche, met een getijcurve.
- Het standaardvenster is het middelste deel tussen elk laag- en hoogwater, bij daglicht. De breedte is instelbaar.
- Per strand kan de eigenaar een eigen voorkeur invullen (laag, half, hoog, opkomend, afgaand).
- Het getij verandert de twee scores nooit. Het bepaalt alleen welke uren als venster worden getoond.

## 3. Databronnen

### 3.1 Wind en golven

| Rol | Bron | Resolutie | Toegang | Zekerheid |
|---|---|---|---|---|
| Zelfde als Windguru: wind | GFS 13 km via Open-Meteo, `models=gfs_seamless` | 13 km | Geen sleutel | [gemeten] |
| Zelfde als Windguru: golven | GFS-Wave 16 km via Open-Meteo Marine, `models=ncep_gfswave016` | 16 km | Geen sleutel | [gemeten] |
| Nauwkeuriger: golven | Copernicus Marine IBI, product `IBI_ANALYSISFORECAST_WAV_005_005`, dataset `cmems_mod_ibi_wav_anfc_0.027deg_PT1H-i` | 3 km, per uur, 10 dagen | Gratis account | [bron] |
| Nauwkeuriger: wind | ECMWF IFS 9 km via Open-Meteo, `models=ecmwf_ifs` | 9 km | Geen sleutel | [bron], model-id [onbevestigd] |
| Azoren, later | Copernicus globaal, `GLOBAL_ANALYSISFORECAST_WAV_001_027` | 8 km | Zelfde account | [bron] |

Wat het prototype mat **[gemeten]**:

- Open-Meteo met de twee GFS-modellen tegen de Windguru-tabel: Arrifana 32 uren, gemiddeld 0,04 m en 0,3 s verschil; Praia da Rocha 17 uren, gemiddeld 0,7 kn verschil.
- De standaardkeuze van Open-Meteo (`best_match`) is een ander model en wijkt wel af van Windguru: tot 6 knopen in wind.
- Een modelvak dat half op land ligt geeft te lage golven (Amado: 0,8 in plaats van 1,1 m). Vraag golven daarom op in het zeevak voor het strand, enkele kilometers uit de kust in de kijkrichting.

Wat de bronnen zeggen over nauwkeurigheid **[bron]**:

- ECMWF meldt dat zijn golfmodel buiten de tropen beter scoort dan de andere centra, waaronder NCEP (GFS-Wave). Dat is een eigen verklaring zonder cijfers in de tekst.
- Copernicus IBI tegen 42 boeien (2018 tot 2019): golfhoogte gemiddeld 0,02 m te laag, met een gemiddelde fout (RMSD) van 0,29 m; aan de kust een spreidingsindex van 32 procent tegen 21 procent op open zee.
- Geen enkel model rekent de branding zelf door. Ze geven de golven die op het strand afkomen.

Er is geen onafhankelijke vergelijking van GFS-Wave en IBI tegen Portugese boeien gevonden. Daarom meet mijlpaal 6 dat zelf en kiest de app het standaardmodel op basis van die meting.

### 3.2 Getij

De zeespiegelreeks van Open-Meteo is hiervoor ongeschikt: ze liep in het prototype 26 tot 31 minuten voor op de getijtafel van Portimão **[gemeten]**, en Open-Meteo waarschuwt zelf voor beperkte nauwkeurigheid aan de kust **[bron]**.

Aanpak:

1. **Zelf berekenen** met harmonische voorspelling, dezelfde methode als het Instituto Hidrográfico. Bibliotheek: Neaps (`@neaps/tide-predictor`, MIT-licentie) met de TICON-4-constanten van de Portugese peilstations **[bron]**.
2. **Stations** op het vasteland: Viana do Castelo, Leixões, Nazaré, Peniche, Cascais, Sines, Lagos **[bron]**.
3. **Tussen de stations** de tijd en hoogte langs de kust interpoleren. Hoogwater komt in de Minho ongeveer 40 minuten later dan in de Algarve, ruwweg 0,07 minuut per kilometer kust **[bron, afgeleid]**.
4. **Hoogtes** uitdrukken tegenover het Zero Hidrográfico: 2,00 m onder gemiddeld zeeniveau op het vasteland **[bron]**.
5. **Tijd**: rekenen in UTC, tonen in Europe/Lisbon.
6. **Riviermondingen en lagunes** (Taag, Sado, Ria Formosa, Ria de Aveiro) apart behandelen; daar klopt interpolatie langs de kust niet.

Eén steekproef (Viana do Castelo, 16 hoog- en laagwaters): −1,6 tot +4,6 minuten tegenover de officiële tafel **[bron]**.

Terugvaloptie: het wereldmodel FES2022 via pyTMD, gratis met een AVISO-account **[bron]**.

**Licentie.** Cascais en Lagos zijn vrij bruikbaar (CC BY). Viana, Leixões, Peniche en Sines staan als niet-commercieel gemarkeerd **[bron]**. De getijtafels van het Instituto Hidrográfico zelf mogen niet zonder toestemming worden overgenomen; gebruik ze alleen om te controleren.

### 3.3 Stranden

| Bron | Aantal | Wat ze geeft | Licentie |
|---|---|---|---|
| OpenStreetMap `natural=beach` | 1.487, waarvan 1.064 met naam (inclusief rivierstranden) | Omtrek, naam, ondergrond | ODbL |
| EEA/APA zwemwateren | 515 kuststranden in 2025; 364 op het vasteland in 2026 | Officiële naam, code, coördinaten | CC BY 4.0 |

Aanpak:

- **Hoofdlijst** uit OpenStreetMap via het Geofabrik-bestand van Portugal, gefilterd op stranden met naam binnen 300 m van de kustlijn. Verwacht 600 tot 800 kuststranden op het vasteland **[onbevestigd]**.
- **Controle op volledigheid** met de officiële lijst: elk officieel zwemwater moet in de hoofdlijst zitten of wordt toegevoegd.
- **Kijkrichting** per strand berekenen uit de OSM-kustlijn (land ligt links van de lijn, dus de zeezijde is de richting van de lijn plus 90 graden) **[bron]**. Stranden in baaien, bij riviermondingen en bij havendammen markeren voor handmatige controle.
- **Deiningsvenster** per strand met stralen over open water rond de kijkrichting.
- **Verplichting**: de samengevoegde strandentabel moet onder ODbL openbaar staan, met het script erbij **[bron]**.

**Surfgegevens per spot** (type break, getijvoorkeur) mogen niet in bulk worden overgenomen van surf-forecast.com, Surfline, Wannasurf of Mondo: hun voorwaarden en het Europese databankrecht staan dat niet toe **[bron]**. Eén spot met de hand opzoeken als controle mag wel. Het prototype deed dit wel voor 38 spots in de Algarve; die tabel mag niet mee naar de publieke versie. Eigen kennis en eigen invoer zijn vrij.

### 3.4 Metingen om tegen te controleren

| Wat | Bron | Toegang |
|---|---|---|
| Golven | Boeien van het Instituto Hidrográfico (Leixões, Sines, Faro; Nazaré [onbevestigd]) via EMODnet Physics ERDDAP of Copernicus In-Situ | Geen sleutel, of het Copernicus-account |
| Wind | IPMA-stations, `api.ipma.pt/open-data/observation/meteorology/stations/observations.json` | Geen sleutel; alleen voor niet-commercieel gebruik |
| Waterstand | Peilstations via de OGC-API van het Instituto Hidrográfico | Geen sleutel; licentie [onbevestigd] |
| Getijtijden | Tabela de Marés 2026 (pdf) | Alleen ter controle |

**Waarschuwingen.** IPMA publiceert zijn waarschuwingen als JSON op `api.ipma.pt/open-data/forecast/warnings/warnings_www.json`, zonder sleutel. Elk record heeft `awarenessTypeName` (onder meer "Agitação Marítima" en "Vento"), `awarenessLevelID` (green, yellow, orange, red), `idAreaAviso`, `startTime` en `endTime` **[gemeten op 5 oktober 2026]**. De pijplijn haalt dit bij elke run op voor de regel uit 2.5. Welke code bij welke kuststrook hoort, is **[onbevestigd]**.

### 3.5 Kaart

MapLibre GL JS met de tegels van OpenFreeMap: gratis, geen sleutel, commercieel gebruik toegestaan **[bron]**. Terugvaloptie: een eigen PMTiles-uittreksel van Portugal.

## 4. Accounts en sleutels

| Account | Nodig voor | Kost | Waar |
|---|---|---|---|
| Copernicus Marine | IBI-golven, boeimetingen | Gratis | data.marine.copernicus.eu/register |
| GitHub | Code, geplande taken, openbare strandentabel | Gratis | github.com |
| Vercel | De site | Gratis plan voor persoonlijk, niet-commercieel gebruik **[onbevestigd]** | vercel.com |
| AVISO, optioneel | FES2022 als terugval voor getij | Gratis | aviso.altimetry.fr |

Geen sleutel nodig voor Open-Meteo (niet-commercieel, tot 10.000 aanroepen per dag), IPMA, EMODnet, OpenFreeMap en Neaps. In de documentatie van Windguru staat alleen een API voor weerstations, geen voor voorspellingen **[bron]**; vergelijken gebeurt met de hand.

Sleutels staan alleen in `.env` (lokaal) en als geheimen in GitHub Actions: `COPERNICUSMARINE_SERVICE_USERNAME` en `COPERNICUSMARINE_SERVICE_PASSWORD`. Nooit in de code of in de site.

## 5. Beslissingen van de eigenaar (5 oktober 2026)

1. **Gratis en niet-commercieel.** Geen advertenties, geen abonnementen. Alleen bronnen en diensten met een gratis niveau.
2. **Alleen het vasteland.** Madeira en de Azoren vallen buiten dit plan.
3. **Besloten kring.** De site staat op Vercel en de link gaat alleen naar bekenden. De site vraagt zoekmachines om haar niet op te nemen (`noindex` en een `robots.txt` die alles weigert).

Wat daaruit volgt:

- De bronvermeldingen uit hoofdstuk 9 staan ook op een besloten site; de licenties vragen ze bij elk gebruik.
- De samengevoegde strandentabel staat als GeoJSON in de repository. Dat kost niets en dekt de deelplicht van OpenStreetMap af, mocht de link verder rondgaan.
- Surfgegevens per spot komen alleen uit eigen invoer van de eigenaar.
- Een Vercel-link is niet afgesloten: wie de link heeft, kan de site zien. Is een echte afscherming gewenst, dan zoekt Claude Code in M0 uit wat het gratis plan van Vercel daarvoor biedt **[onbevestigd]**.

## 6. Architectuur

Een statische site met vooraf berekende data. Er draait geen eigen server.

- **Pijplijn** (Python 3.12): haalt elke 6 uur de modellen op, rekent per strand de reeksen uit en schrijft compacte JSON-bestanden. Draait als geplande taak in GitHub Actions.
- **Getij** (Node-script met Neaps): rekent één keer per jaar alle hoog- en laagwaters per strand uit.
- **Site** (TypeScript, Vite, MapLibre GL JS): leest alleen die bestanden. Ze staat op Vercel; elke nieuwe set databestanden uit de pijplijn start een nieuwe publicatie. Claude Code kiest in M0 hoe de databestanden bij de site komen zonder dat de geschiedenis van de repository volloopt, bijvoorbeeld via een aparte `data`-tak die telkens wordt overschreven.

```
/pipeline
  beaches/     OSM + EEA samenvoegen, kijkrichting, zeevak per strand
  tides/       harmonische voorspelling, interpolatie langs de kust
  forecast/    Open-Meteo (GFS, ECMWF) en Copernicus IBI ophalen
  rules/       rules.yaml en de berekening van WIND, WAVE en het label
  validate/    vergelijking met boeien, stations en getijtafel
/web           kaart, strandfiche, modelkeuze, nauwkeurigheidspagina
/data          gegenereerde bestanden (niet met de hand bewerken)
/tests
```

Regels voor Claude Code:

- Controleer elke bron eerst met één echte aanroep voor je erop bouwt. Alles wat **[onbevestigd]** is, eerst bevestigen.
- Haal geen gegevens geautomatiseerd van sites waarvan de voorwaarden dat verbieden of die je niet hebt kunnen lezen (Surfline, Windguru, surf-forecast.com, Mondo, Wannasurf).
- Elke mijlpaal eindigt met tests die draaien en een kort verslag van wat gemeten is.
- Toon op de site de bronvermeldingen uit hoofdstuk 9.

## 7. Mijlpalen

### M0. Proeven en sleutels

- Repository, `.env.example`, CI.
- Eén echte aanroep per bron: Open-Meteo (drie modellen), Copernicus IBI (uitsnede voor één punt), Neaps (één station), EMODnet (één boei), IPMA (stations en waarschuwingen).
- **Klaar als:** elk antwoord is opgeslagen als testbestand en de veldnamen zijn gedocumenteerd. Wat niet werkt, staat in `OPEN.md` met een voorstel.

### M1. Stranden

- Hoofdlijst bouwen, samenvoegen met de officiële lijst, kijkrichting en deiningsvenster berekenen.
- Per strand de blootstellingsfactor f als functie van de golfrichting afleiden uit het deiningsvenster (2.5), en het veld `besloten_water` voorzien (2.4).
- **Klaar als:** elk officieel kustzwemwater van het vasteland is terug te vinden; de tabel staat als GeoJSON onder ODbL; een lijst van stranden met onzekere kijkrichting is beschikbaar voor handmatige controle; een steekproef van 30 stranden op de kaart is door de eigenaar nagekeken.

### M2. Getij

- Hoog- en laagwater per station en per strand voor het lopende jaar.
- **Klaar als:** tegen de getijtafel 2026 voor alle 13 hoofdhavens de helft van de verschillen binnen 3 minuten valt en 95 procent binnen 10 minuten, met hoogtes binnen 0,1 m. Haalt een haven dat niet, dan staat ze in `OPEN.md`.

### M3. Voorspelling

- Per strand het zeevak bepalen (5 km uit de kust in de kijkrichting, nooit een vak op land).
- GFS en GFS-Wave ophalen; daarna ECMWF-wind en IBI-golven.
- **Klaar als:** voor vijf referentiespots verspreid over de kust (bijvoorbeeld Moledo, Peniche, Ericeira, Arrifana, Praia da Rocha) de GFS-stand met de hand naast Windguru is gelegd en minstens 95 procent van de uren binnen 0,1 m, 1 s en 2 kn valt.

### M4. Site

- Kaart met per strand het tweekleurige bolletje uit 2.6 (cyaan links, blauw rechts, cijfer in elke helft), dat bij uitzoomen samenklontert. Keuze van dag en uur; standaard het huidige uur.
- Fiche: label; de twee cijfers met hun reden; een dagstrook met per uur de twee scores onder de getijcurve; hoog- en laagwater en de vensters; golfje met hoogte als bereik; windpijl; tabel met dezelfde rijen als Windguru; schakelaar tussen "zelfde model als Windguru" en het nauwkeurigste model.
- Een legende die de schaal 1 tot 5 uitlegt, en een pagina "Hoe rekenen we" met de tabellen uit 2.4 tot 2.6 en hun bewijsniveau.
- **Klaar als:** het werkt op een telefoon van 400 px breed, in licht en donker, de fiche binnen een seconde opent, de twee helften ook voor kleurenblinden te onderscheiden zijn (de cijfers staan erin), en de site `noindex` meestuurt.

### M5. Scores en label

- `rules.yaml` met alle drempels uit 2.4 tot 2.6, elk met `bron` (link) en `bewijs` (sterk, praktijk of eigen keuze). Het begin van het bestand:

```yaml
wind:
  kite:      {s2: 8, s3: 12, s4: 22, s5: 34}      # knopen, ondergrens per score
  windsurf:  {s3: 7, s4: 17, s5: 34}               # geen score 2
  vlagen:    {min4: 30, s5: 38, nota_factor: 1.2}
  voorzichtig: {s5: 28, vlagen_s5: 30}             # variant, staat uit
  richting:  {aanlandig: 22.5, schuin_aan: 67.5, zij: 112.5, schuin_af: 157.5}
  aflandig:  {score: 5, vanaf_kn: 8, klassen: [schuin_af, af]}
wave:
  hb:        {s2: 0.3, s3: 0.5, s4: 1.0, s5: 3.0}  # meter brekend
  s5_alternatief: 4.0                              # staat uit
  beginnersles_tot: 1.5
  k: 1.0
  periode:   {max2_onder_s: 6, nota_vanaf_s: 15}
  ipma_zeegang: {score: 5, vanaf: yellow}
surf_wind:   {beginner_max_kn: 11, gevorderd_max_kn: 19}
stil:        {sup_goed_tot_kn: 10, sup_verbod_boven_kn: 16}
```

- De berekening als pure functie: invoer één uur modeldata en één strand, uitvoer WIND, WAVE, label, redenen en nota's.
- **Klaar als** tests het volgende aantonen:
  - Elke grens uit de tabellen van 2.4 en 2.5 valt aan de juiste kant (7,9 en 8,0 kn; 0,99 en 1,00 m; enzovoort).
  - De rekenvoorbeelden kloppen: 1 m bij 12 s geeft Hb 1,66 m; 2 m bij 12 s geeft 2,90 m; 0,5 m bij 6 s geeft 0,72 m.
  - Aflandige wind van 8 kn of meer geeft altijd WIND 5, behalve op `besloten_water`.
  - Golven onder 0,5 m brekend geven nooit WAVE 3 of hoger; een IPMA-waarschuwing voor zeegang geeft altijd WAVE 5.
  - Een periode onder 6 s geeft hoogstens WAVE 2, tenzij Hb 3 m of meer is.
  - Alle elf regels van de labeltabel hebben een test, ook regel 3 en 4 (surfdag bij aflandige wind).
  - Het getij verandert geen enkele score.
  - Elke score toont zijn reden in woorden.

### M6. Nauwkeurigheid meten

- Elke dag voorspelling en meting naast elkaar leggen voor de beschikbare boeien en de kuststations.
- **Klaar als:** na 30 dagen een pagina de gemiddelde afwijking en spreiding per model toont, het model met de kleinste fout de standaard is, en die fout niet groter is dan die van GFS-Wave.

### M7. IJken op het water

- Een eenvoudig logboek: strand, uur, de geschatte golfhoogte, en welke score de eigenaar zelf zou geven voor WIND en voor WAVE.
- **Klaar als:** na 20 waarnemingen de drempels, de ijkfactor k en de blootstellingsfactoren naast de waarnemingen zijn gelegd en de eigenaar beslist wat hij aanpast. Eerst komen de drempels met het label "eigen keuze" aan bod.

## 8. Risico's

- **Hoogte op het strand blijft een schatting.** Bronnen geven een marge van de helft tot het dubbele door de zeebodem. Daarom een bereik en het logboek van M7.
- **Beschutte stranden.** Hoeveel deining om een kaap draait, staat nergens in cijfers. Het deiningsvenster en de blootstellingsfactor uit M1 zijn een meetkundige benadering. Omdat score 3 aan de westkust vooral op beschutte stranden valt, hangt de WAVE-score daar sterk van af.
- **De scores zijn geen veiligheidsadvies.** De sterktegrenzen voor wind komen van scholen en verhuurders, niet van een federatie. Stroming, rotsen, drukte en eigen niveau zitten niet in de cijfers. De site zegt dat bij de legende.
- **Eén WIND-cijfer voor twee sporten.** De beginnersbereiken van kite (12 tot 21 kn) en windsurf (7 tot 16 kn) overlappen maar half. Het cijfer volgt de kite; de fiche geeft de regel voor windsurf. Wil de eigenaar het anders, dan komt er een schakelaar.
- **Licenties.** Alles in dit plan geldt voor gratis, niet-commercieel gebruik. Komen er later advertenties of abonnementen, dan vervallen het gratis gebruik van Open-Meteo, de IPMA-metingen en vier van de zeven getijstations.
- **Kustlijn bij riviermondingen.** OSM trekt de kustlijn dwars over grote riviermonden; de kijkrichting is daar onbruikbaar.
- **Onbevestigde punten:** de verhouding tussen vlagen en gemiddelde wind in de modeldata, de koppeling van IPMA-waarschuwingsgebieden aan kuststroken, de model-id's van ECMWF bij Open-Meteo, of de boeimetingen van Nazaré en Madeira in EMODnet zitten, de licentie van de peilstations, en het aantal kuststranden na filteren.

## 9. Bronvermelding op de site

- "Weather data by Open-Meteo.com", met link.
- "Generated using E.U. Copernicus Marine Service Information; DOI 10.48670/moi-00025".
- "OpenFreeMap © OpenMapTiles Data from OpenStreetMap", met link naar openstreetmap.org/copyright.
- "Bathing water data: EEA / APA (CC BY 4.0)".
- Getijconstanten: TICON-4 (DOI 10.17882/109129).
- IPMA: bron vermelden, logo en link.

## 10. Bronnen

Surfwetenschap en forecasters:

- Scarfe e.a. 2003, The science of surfing waves and surfing breaks: https://escholarship.org/content/qt6h72j1fz/qt6h72j1fz.pdf
- Lewis e.a. 2015, met de tabel van Hutt, Black en Mead: https://www.coastalconference.com/2015/papers2015/James%20Lewis.pdf
- Walker 1975, Universiteit van Hawaii: https://repository.library.noaa.gov/view/noaa/36614/noaa_36614_DS1.pdf
- Komar en Gaughan, via Le Roux 2007: https://data-ww3.ifremer.fr/BIB/LeRoux_CE2007.pdf
- Douglass 1990, wind en brekende golven: https://ascelibrary.com/doi/10.1061/%28ASCE%290733-950X%281990%29116%3A6%28651%29
- Feddersen e.a. 2023, veldmeting wind en golfvorm: https://www.cambridge.org/core/journals/journal-of-fluid-mechanics/article/crossshore-windinduced-changes-to-fieldscale-overturning-wave-shape/4236FD21F9A9EA5AFCF6ED8966B93596
- Bureau of Meteorology, deining en windgolven optellen: https://www.bom.gov.au/marine/about/combinedseaswell.shtml
- Surfline, hoe ratings werken: https://support.surfline.com/hc/en-us/articles/36277684017819-Surf-Ratings-Colors
- Surfline, forecaster over grootte en kwaliteit: https://www.surfline.com/surfline/forecasts4/forecast_blog_entry.cfm?id=13680&sef=true
- Swellnet, golfperiode: https://www.swellnet.com/news/swellnet-analysis/2016/08/17/know-your-product-wave-period

Windscore (kite, windsurf, sup, kajak):

- RNLI, gids surfsporten (aflandige wind): https://rnli.org/-/media/rnli/downloads/in-the-surf-rnli-guide-to-surfsport-safety-english-version.pdf?rev=433ad63c48d745c1bf94fcc174a043c8
- IKO, zelfredding (aflandig en schuin aflandig alleen met boot): https://d8.ikointl.com/system/files/ecourses/files/selfrescue_packdown-v2.0_0.pdf
- RYA, Seven Common Senses: https://www.rya.org.uk/water-safety/seven-common-senses/
- Kite & Wing WA, weer en windrichting: https://kiteboardingwa.org.au/about-kiteboarding/weather/
- KiteWorldWide, hoeveel wind: https://kiteworldwide.com/blog/2024/05/how-much-wind-do-i-need-for-kitesurfing/
- MACkite, omstandigheden: https://www.mackiteboarding.com/kiteboarding-conditions.htm
- The Kitesurf Centre, verhuurvoorwaarden: https://www.thekitesurfcentre.com/pages/terms
- Cabrinha, handleiding 2020: https://cdn.shopify.com/s/files/1/2016/2457/files/2020_Kite_User_Manual_DE.pdf
- Hayling Island SC, procedures RYA-opleiding 2024: https://www.hisc.co.uk/media/17560/hisc-rya-training-sops-2024.pdf
- Windcraft, windsurf per windkracht: https://www.windcraftsurf.com/en/blog/beginners-guide-to-windsurfing
- World Sailing, Race Management Policies 2017: https://www.sailing.org/tools/documents/20171003Updatedto201720rulesandModifiedRaceManagementPoliciesFleetRacing-[23286].pdf
- Met Office, schaal van Beaufort: https://weather.metoffice.gov.uk/guides/coast-and-sea/beaufort-scale
- IPMA, criteria voor waarschuwingen (wind en zeegang): https://www.ipma.pt/pt/enciclopedia/otempo/sam/index.html?page=criterios.xml
- IPMA, waarschuwingen als JSON: https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json
- Capitania de Cascais, Edital 185/2016 (sup tot kracht 4, afstanden): https://www.amn.pt/DGAM/Capitanias/Cascais/Lists/Documentos_AMN/EDITAL%20185-2016%20da%20Capitania%20do%20Porto%20de%20CASCAIS%20-%20%20vers%C3%A3o%20consolidada.pdf
- AMN, nationaal strandedict: https://www.amn.pt/Documents/Editais%20Praia/Edital%20de%20Praia%20-%20Continente%20e%20Madeira%20-%20Lingua%20portuguesa.pdf
- Paddle UK, aflandige wind en sup: https://paddleuk.org.uk/offshore-winds-and-their-effects-on-stand-up-paddleboards/
- British Canoeing, sup-leiders: https://britishcanoeingawarding.org.uk/become-a-stand-up-paddleboard-leader-2/
- ACA, kajak niveau 2: https://americancanoe.org/wp-content/uploads/2025/02/L2-CK-Assessors-Guide-and-Field-Grids.pdf
- ASI, wind en sup: https://www.academyofsurfing.com/news/understanding-wind-direction-for-stand-up-paddleboarding
- Windguru, instelling van de sterren: https://www.windguru.net/forms/preferences.php

Golfscore:

- ASI, lesnormen beginners, halfgevorderden, gevorderden: https://www.academyofsurfing.com/surfing-instructor-standards-beginner-level , https://www.academyofsurfing.com/surfing-instructor-standards-intermediate-level , https://www.academyofsurfing.com/surfing-instructor-standards-advanced-level
- ISA, verplichtingen van een surfschool: https://isasurf.org/wp-content/uploads/2021/04/ISAOBLIGATIONSOFaregisteredsurfschool010308.pdf
- Surfing England, schoolreglement: https://www.surfingengland.org/wp-content/uploads/2017/03/Surfing-England-English-Surf-School-Scheme.pdf
- Federação Portuguesa de Surf, reglement surfscholen: https://www.surfingportugal.com/wp-content/uploads/2023/01/Regulamento-Escolas-de-Surf-.pdf
- Capitania de Lisboa, Aviso 22/2026: https://www.amn.pt/DGAM/Capitanias/Lisboa/Documentos_AMN/Aviso%20n%C2%BA%2022_2026_Agravamento%20condi%C3%A7%C3%B5es%20meteo%2001-04FEV_signed.pdf
- Energiestroom van golven, P = 0,491 · Hs² · Te: https://www.sciencedirect.com/science/article/pii/S2352484722008514
- Caldwell en Aucan 2007, branding voorspellen uit hoogte en periode: https://escholarship.org/content/qt61t4k7z7/qt61t4k7z7.pdf
- NWS Portland (Elson 2001), golfvermogen als drempel: https://www.weather.gov/media/wrh/online_publications/TAs/ta0116.pdf
- NWS Honolulu, San Diego, Wilmington, brandingsdrempels: https://www.weather.gov/hfo/highsurfinfo , https://www.weather.gov/media/sgx/documents/WWA_Criteria.pdf , https://www.weather.gov/media/ilm/ILMSurfProductsGuide.pdf
- Bureau of Meteorology, gevaarlijke branding en lange deining: https://www.bom.gov.au/weather-and-climate/specialised-forecasts-and-observations/coasts-and-oceans/marine-weather-safety/marine-weather-hazards-and-warnings
- surf-forecast.com, golfenergie in kJ: https://www.surf-forecast.com/pages/faq
- Stormsurf, periodes: http://www.stormsurf.com/page2/tutorials/wavebasics.shtml
- Golfklimaat Sines (thesis Zacarias): https://dspace.uevora.pt/rdpc/bitstream/10174/14068/1/Tese_NunoZacarias_Caracteriza%C3%A7%C3%A3o%20da%20agita%C3%A7%C3%A3o%20mar%C3%ADtima%20no%20arco%20litoral%20Tr%C3%B3ia-Sines%20e%20sua%20rela%C3%A7%C3%A3o%20com%20o%20pa.pdf
- Golfklimaat Faro (Rodrigues e.a. 2012): https://www.redalyc.org/pdf/505/50524834008.pdf
- Golfklimaat Leixões, Nazaré, Faro (boeien): https://www.sciencedirect.com/science/article/pii/S0029801821009380

Wind en golven:

- Open-Meteo Marine API: https://open-meteo.com/en/docs/marine-weather-api
- Open-Meteo voorwaarden en prijzen: https://open-meteo.com/en/terms en https://open-meteo.com/en/pricing
- Copernicus IBI golven: https://data.marine.copernicus.eu/product/IBI_ANALYSISFORECAST_WAV_005_005/description
- Copernicus IBI kwaliteitsdocument: https://catalogue.marine.copernicus.eu/documents/SQO/CMEMS-IBI-SQO-005-005.pdf
- Copernicus licentie: https://marine.copernicus.eu/user-corner/service-commitments-and-licence
- ECMWF, evaluatie van de voorspellingen 2025: https://www.ecmwf.int/sites/default/files/elibrary/092025/81680-evaluation-of-ecmwf-forecasts.pdf
- IPMA open data: https://api.ipma.pt/
- EMODnet Physics ERDDAP: https://data-erddap.emodnet-physics.eu/erddap/tabledap/
- Windguru, tabellen gebruikt voor de vergelijking: http://wap2.windguru.cz/view.php?sc=2296&m=84&from=search&start=0&full=1 en http://wap2.windguru.cz/view.php?sc=719&m=3&from=search&start=0&full=1

Getij:

- Tabela de Marés 2026, Instituto Hidrográfico: https://loja.hidrografico.pt/ln/web/wp-content/uploads/2023/11/TabelaMare_I_2026_signed.pdf
- Zero Hidrográfico: https://teste.hidrografico.pt/en/infoteca/areas-tecnico-cientificas/hidrografia/zero-hidrografico
- TICON-4: https://www.seanoe.org/data/00980/109129/
- Neaps: https://github.com/openwatersio/neaps
- FES2022: https://mobile.aviso.altimetry.fr/en/data/products/auxiliary-products/global-tide-fes.html
- Peilstations Instituto Hidrográfico: https://api-features.hidrografico.pt/collections?f=html

Stranden en kaart:

- OSM-telling Portugal: https://taginfo.geofabrik.de/europe:portugal/api/4/tag/stats?key=natural&value=beach
- Geofabrik Portugal: https://download.geofabrik.de/europe/portugal.html
- OSM-kustlijn: https://osmdata.openstreetmap.de/data/coastlines.html
- ODbL en bronvermelding: https://osmfoundation.org/wiki/Attribution en https://osmfoundation.org/wiki/Community_Guidelines/Collective_Database_Guideline_Guideline
- EEA zwemwateren: https://www.eea.europa.eu/en/datahub/datahubitem-view/c3858959-90da-4c1b-b9ca-492db0e514df
- APA, zwemseizoen 2026: https://apambiente.pt/en/node/728
- OpenFreeMap: https://openfreemap.org/
- Voorwaarden surf-forecast.com: https://www.surf-forecast.com/pages/terms
- Voorwaarden Surfline: https://www.surfline.com/terms-of-use
