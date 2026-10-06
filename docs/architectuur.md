# Architectuurkeuzes

Keuzes die het plan aan Claude Code overlaat, met de reden.

## Hoe de databestanden bij de site komen (M0)

De pijplijn draait elke 6 uur. Elke run bewaren in `main` zou de geschiedenis snel laten vollopen (honderden stranden × 10 dagen × uren, vier keer per dag).

Keuze (bijgewerkt in M4):

1. De hoofdtak bevat alleen code, `rules.yaml`, de strandentabel (GeoJSON, ODbL) en de getijbestanden.
2. De workflow `forecast` draait elke 6 uur. Hij haalt de voorspelling op en zet die op de tak `data`. Daarna rekent hij de scores uit, bouwt hij de site (`web/dist`) en zet die op de tak `site`. Beide takken bestaan uit één commit die telkens met `--force` wordt overschreven, zodat er geen geschiedenis vol data ontstaat.
3. Vercel publiceert alleen de tak `site` (`vercel.json` in de hoofdtak: `git.deploymentEnabled`). In de instellingen van het Vercel-project staat `site` als productietak, met framework "Other" en zonder buildcommando: de tak bevat al de gebouwde site.

Zo is er geen Vercel-sleutel nodig in GitHub; Vercel volgt de tak `site` zelf.

## Talen

- Pijplijn: Python (CI op 3.12, lokaal werkt 3.11).
- Getij: Node met Neaps. De constanten van TICON-4 zitten in het npm-pakket `@neaps/tide-database`; er is geen netwerk nodig om te rekenen.
- Site: TypeScript, Vite, MapLibre GL JS (vanaf M4).
