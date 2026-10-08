// Weerwaarschuwing van MeteoAlarm voor het gekozen uur: een balk in de fiche (strand of klimplek).
import { lisDag, toonDag, toonTijd, utc } from './main'

export interface Waarschuwing { niveau: number; soort: string; van: string; tot: string }
const NAAM = ['', 'Gele', 'Oranje', 'Rode']

export function waarschuwingBalk(reeks: string | undefined, lijst: Waarschuwing[] | undefined, tijd: string): string {
  const n = Number(reeks ?? 0)
  if (!lijst?.length || !n) return ''
  const nu = lijst.filter((w) => w.van <= tijd && tijd < w.tot && w.niveau === n)
  if (!nu.length) return ''
  const soorten = [...new Set(nu.map((w) => w.soort))].join(', ')
  const tot = nu.map((w) => w.tot).sort()[0]
  const einde = utc(tot)
  const wanneer = lisDag(einde) === lisDag(utc(tijd)) ? toonTijd(einde) : `${toonDag(einde)} ${toonTijd(einde)}`
  return `<p class="waarschuwing w${n}"><b>${NAAM[n]} waarschuwing</b> ${soorten}
    <small>tot ${wanneer} · MeteoAlarm</small></p>`
}
