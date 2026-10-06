# Open punten

Wat in een mijlpaal niet werkte of nog niet bevestigd is, met een voorstel. Een punt verdwijnt pas als het opgelost is.

## M0 (5 oktober 2026)

### 1. De ontwikkelomgeving kan de databronnen niet bereiken

Het netwerkbeleid van de cloudomgeving waarin Claude Code werkt, weigert `api.open-meteo.com`, `marine-api.open-meteo.com`, `api.ipma.pt`, `data-erddap.emodnet-physics.eu`, `api-features.hidrografico.pt`, `tiles.openfreemap.org` en de Copernicus-servers. npm en PyPI werken wel.

Wat er gebeurd is:

- Open-Meteo (wind en golven) en de IPMA-waarschuwingen zijn één keer opgehaald via Firecrawl. Die antwoorden staan als `firecrawl_*.json`.
- Neaps rekent offline en is lokaal echt aangeroepen.
- Alle overige bronnen draaien via `pipeline/probe/probe.py` in GitHub Actions; de eerste run (5 oktober, 14:40 UTC) slaagde voor Open-Meteo (drie modellen), IPMA (waarschuwingen, stations, observaties), OpenFreeMap en Neaps.
- Voor de rest draait `pipeline/probe/probe.py` in GitHub Actions (`.github/workflows/probe.yml`), waar het netwerk open is. De workflow schrijft de antwoorden terug naar `tests/fixtures/probe/`.

**Voorstel:** de eigenaar voegt die hosts toe aan de toegelaten domeinen van de omgeving (Network access → Custom). Anders werkt Claude Code verder via GitHub Actions, wat trager is maar volstaat.

### 2. `copernicus_ibi`: opgelost op 6 oktober 2026

Het account staat als geheim in GitHub. De proef haalde 24 uur IBI-golven op voor het zeevak bij Arrifana. Anders dan GFS-Wave geeft IBI wel een piekperiode (`VTPK`), plus hoogte, periode en richting voor eerste deining, tweede deining en windgolf. Zie `docs/bronnen.md`.

### 3. `emodnet_buoy`: EMODnet heeft geen recente metingen van de Portugese boeien

Tweede run in GitHub Actions (5 oktober 2026, 14:50 UTC). De catalogus `ERD_EP_WAVES_INSITU_METADATA` kent tien golfplatformen in de kaderrechthoek (opgeslagen als `emodnet_platforms.json`):

| Platform | Code | Ligging | Laatste meting |
|---|---|---|---|
| Sines (open zee) | 6201081 | 37,68 N 9,73 W | 20-10-2025 |
| Sines kustboei | Sines-coast-buoy | 37,92 N 8,93 W | 20-10-2025 |
| Leixões kustboei | Leixoes-coast-buoy (ook 6201077) | 41,32 N 8,98 W | 20-10-2025 |
| Faro kustboei | Faro-coast-buoy (ook 6201079) | 36,90 N 7,90 W | 20-10-2025 |
| Monican01 (bij Nazaré) | 6200192 | 39,51 N 9,64 W | 01-10-2025 |
| Monican02 (bij Nazaré) | 6200199 | 39,56 N 9,21 W | 22-05-2025 |
| Raia01 | 6200191 | 41,15 N 9,58 W | 12-02-2025 |
| Cabo Silleiro (Spanje) | 6200084 | 42,12 N 9,43 W | 20-10-2025 |

Sinds 20 oktober 2025 komen er via EMODnet geen metingen meer binnen van de Portugese boeien. Een boei bij Nazaré bestaat (MONICAN), maar levert evenmin recente data. Per platform een dataset met metingen zoeken gaf niets (de zoekfunctie geeft 404).

**Voorstel voor M6:** Copernicus In-Situ (`INSITU_IBI_PHYBGCWAV_DISCRETE_MYNRT_013_033`) proberen, met het account uit punt 2. Levert dat ook niets recents, dan de boeidata van het Instituto Hidrográfico zelf zoeken (zie ook punt 4). Zonder recente boeimetingen kan M6 niet starten.

### 4. `hidrografico_collections`: de host bestaat niet

`api-features.hidrografico.pt` geeft in GitHub Actions `Name or service not known`: de naam bestaat niet in DNS. Het adres uit het plan (3.4 en 10) klopt dus niet of de dienst is verhuisd.

**Voorstel:** voor M2 en M6 is het niet nodig (de getijtafel komt uit Neaps, de controle uit de pdf). De juiste OGC-API zoeken op hidrografico.pt zodra de waterstanden nodig zijn (M6). De IPMA-observaties, de IPMA-stations en OpenFreeMap werken wel.

### 5. GFS-Wave geeft geen piekperiode per deining

`wave_peak_period`, `swell_wave_peak_period` en `wind_wave_peak_period` komen alle drie terug als `null`, met eenheid `"undefined"`. Ontbrekende deelgolven staan op `0` (hoogte, periode én richting), niet op `null`. Er is wel `swell_wave_period`, `secondary_swell_wave_period` en `wind_wave_period`. Welke periode dat is (gemiddeld of piek) staat niet in het antwoord **[onbevestigd]**.

De formule van Komar en Gaughan (2.5) gebruikt de piekperiode. Een gemiddelde periode ligt doorgaans 10 tot 20 procent lager, wat Hb met ongeveer 4 tot 8 procent laat zakken (Hb hangt af van T^0,4).

**Voorstel:** in M3 de documentatie van Open-Meteo lezen en GFS-Wave naast Windguru leggen (Windguru toont ook de GFS-Wave-periode). Copernicus IBI geeft wel piekperiodes (`VTPK`) voor de totale zee. De ijkfactor k in M7 vangt een vaste afwijking op. Het plan zelf verandert niet zonder akkoord van de eigenaar.

### 6. IPMA-waarschuwingsgebieden zijn districten

Bevestigd op 5 oktober 2026: `idAreaAviso` is een code van drie letters per district (bv. `FAR`, `LSB`, `STB`), plus Madeira (`MCN`, `MCS`, `MPS`, `MRM`) en de Azoren (`ACE`, `AOC`, `AOR`). Elk district krijgt een record "Agitação Marítima", ook districten in het binnenland zoals `BGC` (Bragança).

Kustdistricten op het vasteland: `VCT`, `BRG`, `PTO`, `AVR`, `CBR`, `LRA`, `LSB`, `STB`, `BJA`, `FAR`.

Nog **[onbevestigd]**: of een zeegangwaarschuwing voor een district precies de kust van dat district dekt. Let op Beja (`BJA`): Odemira ligt in dat district en heeft een kust van ongeveer 50 km.

**Voorstel voor M1:** elk strand krijgt zijn district via een punt-in-veelhoek met de officiële grenzen (CAOP van de DGT, open licentie). De regel uit 2.5 gebruikt dan het record "Agitação Marítima" van dat district.

### 7. Vlagen soms lager dan de gemiddelde wind

In het GFS-antwoord voor Praia da Rocha ligt de vlaag op een paar uren onder de gemiddelde wind (00:00 UTC: 2,7 kn vlagen bij 3,1 kn gemiddeld; 21:00 tot 23:00 ook). ECMWF doet dat in hetzelfde antwoord niet. Dit bevestigt dat de verhouding vlagen/gemiddelde in M6 eerst gemeten moet worden voor de nota "vlagerig" aan gaat.

### 8. Hoogtes: LAT van Neaps is niet het Zero Hidrográfico

Neaps geeft per station een LAT die 1,79 m (Nazaré) tot 1,92 m (Lagos) onder MSL ligt. Het Zero Hidrográfico ligt 2,00 m onder MSL (plan 3.2).

**Voorstel voor M2:** voorspellen tegenover `MSL` en zelf 2,00 m optellen. LAT niet gebruiken.

### 9. Vercel: wat het gratis plan afschermt

**[onbevestigd]**, uit kennis en niet live gelezen (vercel.com is vanuit de omgeving niet bereikbaar):

- Het gratis plan (Hobby) is bedoeld voor persoonlijk, niet-commercieel gebruik. Dat past bij beslissing 1.
- Hobby biedt "Vercel Authentication": alleen ingelogde Vercel-gebruikers met toegang tot het project zien de site. Dat geldt standaard voor de previewlinks, niet voor het productiedomein. Bekenden zouden dan elk een Vercel-account nodig hebben en aan het team moeten worden toegevoegd, wat op Hobby niet kan.
- Afscherming met een wachtwoord kost geld (Pro-plan met een betaalde optie).

**Voorstel:** blijven bij wat beslissing 3 al zegt: `noindex`, een `robots.txt` die alles weigert en een link die niet te raden is. Is een echte login nodig, dan kan Cloudflare Pages met Cloudflare Access gratis tot 50 gebruikers met een code per e-mail (**[onbevestigd]**). De eigenaar beslist; tot dan bouwt M4 voor Vercel.

### 10. Deelgolven tellen niet op tot de totale hoogte

In 48 uren GFS-Wave voor Arrifana ligt de wortel van de som van de kwadraten van de drie deelgolven tot 12 procent onder `wave_height` (gemiddeld een paar procent). De rest van de energie zit kennelijk niet in de drie deelgolven die Open-Meteo doorgeeft. De WAVE-score (2.5) rekent met de deelgolven en schat Hb dan iets te laag.

**Voorstel voor M5:** als de deelgolven samen minder geven dan het totaal, het verschil bij de windgolf tellen (met de windgolfperiode, of de totale periode als die 0 is). Dat is een eigen keuze en gaat eerst naar de eigenaar.

### 11. IPMA-stations geven de windrichting als sector

`idDireccVento` is een klasse van 0 tot 9, geen hoek. Vermoedelijk 1 tot 8 = N, NO, O, ZO, Z, ZW, W, NW, en 0 of 9 = windstil of veranderlijk **[onbevestigd]**. Wind staat in m/s (`intensidadeVento`) en km/u (`intensidadeVentoKM`); `-99` betekent ontbrekend. Om 14:00 UTC hadden 116 van de 227 stations geen waarneming (`null`).

**Voorstel voor M6:** windsnelheid vergelijken per uur; richting alleen per sector van 45 graden.

### 12. Firecrawl-tegoed

Het Firecrawl-account dat voor punt 1 gebruikt is, meldde bij elke aanroep dat het tegoed bijna op is. Verdere proeven lopen daarom via GitHub Actions. Zodra de live proeven daar slagen, zijn de `firecrawl_*`-bestanden alleen nog een tweede steekproef.

## M1 (6 oktober 2026)

### 13. Steekproef: door Claude Code nagekeken in plaats van door de eigenaar

De eigenaar vroeg om de controle zelf te doen. Satellietbeelden zijn vanuit de ontwikkelomgeving niet te openen, dus de controle gebeurde op twee andere manieren:

1. **Regiotoets voor alle stranden.** Per kuststuk (Minho, Costa de Prata, Peniche, Cascais, Caparica, Alentejo, Algarve) staat een verwachte richting; 577 stranden vallen in zo'n kuststuk. Wie meer dan 40 tot 60 graden afwijkt, is één voor één nagekeken. Bijna alle afwijkers kijken echt anders dan hun kust (Nazaré naar het zuidwesten, Baleal-Lagido naar het noorden, de baaien van Cascais en Lagos naar het oosten, de westelijke Algarve naar het zuiden).
2. **De steekproef van 30** in `docs/steekproef/`, op het oog.

Daarbij kwam één fout in de methode boven: het rekenpunt was het dichtste kustpunt bij de hele omtrek van het strand, en dat kan een uiteinde tegen een dam zijn. Matosinhos kreeg zo 183° (zuid) in plaats van ongeveer 230° (zuidwest). Nu is het het kustpunt bij het midden van het strand. Twintig stranden veranderden daardoor meer dan 30°, telkens naar een aannemelijker richting (bv. Culatra van 31° naar 154°).

Wat niet nagekeken is: de kijkrichting op het satellietbeeld zelf. De eigenaar kan stranden die hij kent nog altijd nakijken via de links in `docs/steekproef/README.md` en `data/beaches/onzeker.csv`.

### 14. 103 stranden met onzekere kijkrichting

Staan in `data/beaches/onzeker.csv`, met de reden en een link. De meeste liggen in de Ria Formosa, het estuarium van de Sado en de Taag, de Ria de Aveiro, of in kleine baaien. Daar is de kijkrichting uit de kustlijn niet betrouwbaar. Ze krijgen voorlopig wel een score, maar de fiche zegt "richting niet beoordeeld" (PLAN.md 2.4).

**Voorstel:** de eigenaar kijkt eerst de stranden na waar hij zelf komt, en vult `besloten_water` in waar dat past. 38 stranden zijn al aangeduid als kandidaat (`kandidaat_besloten_water`).

### 15. Officiële lijst: via de kaartdienst, niet via de databank

De databank van het EEA (discodata) weigert de vraag naar haar tabellen ("system tables are not allowed"). De kaartdienst `water.discomap.eea.europa.eu/arcgis/rest/services/BathingWater/BathingWater_Dyna_WM_2025` geeft wel alle zwemwateren met naam, code, soort water en coördinaten. Seizoen 2025: 366 kust- en overgangswateren op het vasteland. Alle 366 zijn teruggevonden: 346 bij een OSM-strand, 20 toegevoegd vanuit de officiële lijst.

### 16. Wat werd weggelaten

- Stranden met "fluvial" in de naam (rivierstranden).
- Stranden zonder naam, tenzij ze bij een officieel zwemwater horen.
- Stranden buiten Portugal. Het uitsnijden rond Portugal haalde enkele Spaanse stranden aan de Minho en de Douro binnen; die vallen in geen enkel Portugees district.
- Land smaller dan 50 m (havendammen, pieren, strandhoofden) telt niet als afscherming. Zonder die regel leek de open zee bij onder meer Costa da Caparica dicht.
