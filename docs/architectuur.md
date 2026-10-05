# Architectuurkeuzes

Keuzes die het plan aan Claude Code overlaat, met de reden.

## Hoe de databestanden bij de site komen (M0)

De pijplijn draait elke 6 uur. Elke run bewaren in `main` zou de geschiedenis snel laten vollopen (honderden stranden × 10 dagen × uren, vier keer per dag).

Keuze:

1. `main` bevat alleen code, `rules.yaml`, de strandentabel (GeoJSON, ODbL) en de jaarlijkse getijbestanden.
2. De geplande workflow rekent de voorspelling uit, bouwt de site en publiceert ze met `vercel deploy --prebuilt --prod`. De voorspellingsdata gaan zo rechtstreeks naar Vercel en komen niet in git.
3. Dezelfde workflow zet de laatste data ook op een tak `data` als één weescommit die telkens met `--force` wordt overschreven. Dat geeft een controleerbare kopie van de laatste run zonder geschiedenis.
4. Automatische publicatie van Vercel bij elke push wordt voor de tak `data` uitgezet (`vercel.json` → `git.deploymentEnabled`), zodat er niet twee keer gepubliceerd wordt.

Nodig: de geheimen `VERCEL_TOKEN`, `VERCEL_ORG_ID` en `VERCEL_PROJECT_ID` (zie `.env.example`). Wordt ingericht in M4.

## Talen

- Pijplijn: Python (CI op 3.12, lokaal werkt 3.11).
- Getij: Node met Neaps. De constanten van TICON-4 zitten in het npm-pakket `@neaps/tide-database`; er is geen netwerk nodig om te rekenen.
- Site: TypeScript, Vite, MapLibre GL JS (vanaf M4).
