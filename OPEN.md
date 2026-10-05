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

### 2. `copernicus_ibi`: nog geen account

De proef voor Copernicus IBI is geschreven maar overgeslagen: er zijn nog geen sleutels.

**Voorstel:** de eigenaar maakt een gratis account op data.marine.copernicus.eu/register en zet `COPERNICUSMARINE_SERVICE_USERNAME` en `COPERNICUSMARINE_SERVICE_PASSWORD` als geheimen in GitHub (Settings → Secrets and variables → Actions). Daarna de workflow `probe` opnieuw starten.

### 3. `emodnet_buoy`: nog geen metingen

Eerste run in GitHub Actions (5 oktober 2026, 14:40 UTC): de zoekfunctie van ERDDAP geeft voor Portugal alleen catalogi terug (`ERD_EP_TS_*_NRT_METADATA`, `ERD_EP_WAVES_INSITU_METADATA`). Die bevatten per platform `PLATFORMCODE`, `call_name`, `latitude`, `longitude`, `lastDateObservation` en de gemeten parameters, maar geen metingen.

De proef is aangepast: eerst de platformen in Portugal uit de VHM0-catalogus, dan per platform de dataset met de metingen zoeken. Wacht op de volgende run. Of Nazaré erin zit, blijft **[onbevestigd]**.

**Terugval:** Copernicus In-Situ (`INSITU_IBI_PHYBGCWAV_DISCRETE_MYNRT_013_033`), met hetzelfde account als punt 2.

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
