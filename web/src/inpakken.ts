// Compacte fiches van de andere landen terug uitpakken: zelfde regels als pipeline/site/inpakken.py.
import type { Detail } from './types'

// Compacte fiche (andere landen): de conclusietekst staat één keer in "conclusies", per uur een volgnummer in "c";
// getallen per uur als tekst in "p" (pipeline/site/inpakken.py: zelfde alfabet en schalen).
const ALFABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
const VELDEN: Record<string, [number, number, number?]> = {
  stroom: [10, 2], stroom_naar: [1, 2], stroom_pct: [1, 2, 500],
  wind: [10, 2], vlagen: [10, 2], windrichting: [1, 2], zee_h: [100, 2], zee_t: [10, 2], zee_r: [1, 2], E_zee: [1, 3],
  bereikt: [1, 2], E: [1, 3], periode: [10, 2], H: [100, 2], windhoek: [10, 2], tij: [1, 2], tijgewicht: [100, 2], verval: [100, 2],
}
export function ontpak(tekst: string, schaal: number, n: number, schuif = 0): (number | null)[] {
  const leeg = 64 ** n - 1
  const uit: (number | null)[] = []
  for (let i = 0; i < tekst.length; i += n) {
    let k = 0
    for (let j = 0; j < n; j++) k = k * 64 + ALFABET.indexOf(tekst[i + j])
    uit.push(k === leeg ? null : schaal === 1 ? k - schuif : (k - schuif) / schaal)
  }
  return uit
}
// Conclusie-sjabloon: "#" is de score van die activiteit op dat uur (pipeline/site/inpakken.py, terug()).
const KOLOM: [string, number][] = [['windsurfen op golven', 1], ['golfsurfen', 0], ['windsurfen', 2], ['stille waters', 3]]
const terug = (s: string, sc: number[] | null) => {
  if (!sc || !s.includes('#/100')) return s
  for (const [naam, kol] of KOLOM) if (s.includes(`${naam} #/100`)) return s.replace(`${naam} #/100`, `${naam} ${sc[kol]}/100`)
  return s
}
export const uitpakken = (d: any): Detail => {
  if (d.sc) {
    const v = ontpak(d.sc, 1, 2)
    d.scores = Array.from({ length: v.length / 5 }, (_, i) => (v.slice(5 * i, 5 * i + 5).every((x) => x == null) ? null : v.slice(5 * i, 5 * i + 5)))
  }
  if (d.c && d.conclusies) d.conclusie = d.c.map((k: number, i: number) => (k < 0 ? null : terug(d.conclusies[k], d.scores?.[i])))
  if (d.p) for (const [veld, tekst] of Object.entries(d.p as Record<string, string>)) d[veld] = ontpak(tekst, ...VELDEN[veld])
  d.ipma ??= []
  return d as Detail
}
