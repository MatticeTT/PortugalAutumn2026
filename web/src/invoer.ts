// De invoer voor de score van één uur, uit de fiche van een strand. Zelfde regels als
// pipeline/site/invoer.py (condities + afronden): zo rekent de fiche exact wat de kaart toont,
// maar dan met het gewicht en het niveau van de gebruiker.
import type { Cond } from './score'
import type { Detail } from './types'

const TOV = { t: 'tegen', m: 'mee', d: 'dwars' } as const

export function conditiesUur(d: Detail, i: number): Cond | null {
  const st = d.st?.[i]
  if (st === undefined || st === '-' || d.wind[i] == null || d.wh?.[i] == null) return null
  const c: Cond = {
    wind: d.wind[i]!, vlaag: d.vlagen[i]!, windhoek: d.wh[i]!,
    golfhoogte: d.gh![i]!, periode: d.gt![i]!, golfhoek: d.gk![i]!, aandeel_hoofdgolf: d.ga![i],
    golf_aan_strand: d.gs![i]!,
  }
  if (st in TOV) {
    c.stroming = d.stroom![i]!
    c.stroming_tov_wind = TOV[st as keyof typeof TOV]
  }
  if (d.ns?.[i] != null) c.neerslag = d.ns[i]!
  const od = Number(d.od?.[i] ?? 0)
  if (od & 1) c.onweer = true
  if (od & 2) c.donker = true
  if (d.ud?.[i] != null) c.uur_tot_donker = d.ud[i]!
  if (d.wt?.[i] != null) c.watertemperatuur = d.wt[i]!
  return c
}
