# Open punten

Wat in een mijlpaal niet werkte of nog niet bevestigd is, met een voorstel. Een punt verdwijnt pas als het opgelost is.

## M0 (5 oktober 2026)

### 1. De ontwikkelomgeving kan de databronnen niet bereiken

Het netwerkbeleid van de cloudomgeving waarin Claude Code werkt, weigert `api.open-meteo.com`, `marine-api.open-meteo.com`, `api.ipma.pt`, `data-erddap.emodnet-physics.eu`, `api-features.hidrografico.pt`, `tiles.openfreemap.org` en de Copernicus-servers. npm en PyPI werken wel.

Wat er gebeurd is:

- Open-Meteo (wind en golven) en de IPMA-waarschuwingen zijn één keer opgehaald via Firecrawl. Die antwoorden staan als `firecrawl_*.json`.
- Neaps rekent offline en is lokaal echt aangeroepen.
- Voor de rest draait `pipeline/probe/probe.py` in GitHub Actions (`.github/workflows/probe.yml`), waar het netwerk open is. De workflow schrijft de antwoorden terug naar `tests/fixtures/probe/`.

**Voorstel:** de eigenaar voegt die hosts toe aan de toegelaten domeinen van de omgeving (Network access → Custom). Anders werkt Claude Code verder via GitHub Actions, wat trager is maar volstaat.

### 2. `copernicus_ibi`: nog geen account

De proef voor Copernicus IBI is geschreven maar overgeslagen: er zijn nog geen sleutels.

**Voorstel:** de eigenaar maakt een gratis account op data.marine.copernicus.eu/register en zet `COPERNICUSMARINE_SERVICE_USERNAME` en `COPERNICUSMARINE_SERVICE_PASSWORD` als geheimen in GitHub (Settings → Secrets and variables → Actions). Daarna de workflow `probe` opnieuw starten.

### 3. `emodnet_buoy`: dataset-ID onbekend

De ID van de golfdataset met de Portugese boeien staat nergens in het plan. De proef zoekt zelf in de ERDDAP-catalogus op "wave" binnen de kaderrechthoek van Portugal en probeert de eerste datasets met `VHM0`. Wacht op de eerste run in GitHub Actions. Of Nazaré erin zit, blijft **[onbevestigd]**.

**Terugval:** Copernicus In-Situ (`INSITU_IBI_PHYBGCWAV_DISCRETE_MYNRT_013_033`), met hetzelfde account als punt 2.

### 4. `ipma_observations`, `ipma_stations`, `hidrografico_collections`, `openfreemap_style`

Wachten op de eerste run in GitHub Actions (zie punt 1). De IPMA-observaties zijn groot (24 uur × alle stations); de proef bewaart alleen het laatste tijdstip.

### 5. GFS-Wave geeft geen piekperiode per deining

`swell_wave_peak_period` komt terug als `null`, met eenheid `"undefined"`. Er is wel `swell_wave_period`, `secondary_swell_wave_period` en `wind_wave_period`. Welke periode dat is (gemiddeld of piek) staat niet in het antwoord **[onbevestigd]**.

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

### 10. Firecrawl-tegoed

Het Firecrawl-account dat voor punt 1 gebruikt is, meldde bij elke aanroep dat het tegoed bijna op is. Verdere proeven lopen daarom via GitHub Actions.
