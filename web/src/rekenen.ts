import './style.css'
import { KLEUR, tekstKleur } from './kleuren'
import type { Index, Sport } from './types'

const nl = (x: number) => String(x).replace('.', ',')
const vanTot = (g: number[], eenheid: string) => [
  `onder ${nl(g[0])}`, `${nl(g[0])} tot ${nl(g[1])}`, `${nl(g[1])} tot ${nl(g[2])}`, `${nl(g[2])} tot ${nl(g[3])}`, `vanaf ${nl(g[3])} ${eenheid}`]
const rij = (naam: string, cellen: string[]) => `<tr><td>${naam}</td>${cellen.map((c) => `<td>${c}</td>`).join('')}</tr>`

fetch('data/index.json').then((r) => r.json()).then((ix: Index) => {
  document.getElementById('schaal')!.innerHTML = ix.schaal.map((n, k) =>
    `<tr><th style="background:${KLEUR[k]};color:${tekstKleur(k + 1)};width:2em;text-align:center">${k + 1}</th><td>${n}</td></tr>`).join('')
  const S = (g: string) => ix.sporten.filter((s) => s.groep === g)
  const kop = `<tr><th>Sport</th>${ix.schaal.map((n, k) => `<th>${k + 1} ${n}</th>`).join('')}</tr>`
  const richting: Record<string, string> = {
    kite: 'wind langs het strand of verder van land (a boven 90°): zwaarder; boven 112,5°: 5',
    zeil: 'wind van land (a boven 112,5°) en W vanaf 10 kn: zwaarder',
    land: 'wind van land (a boven 112,5°): zwaarder',
  }
  const html = `
  <h2>Golfsporten</h2>
  <p>De golf (GOLF) zet het cijfer. Wind en getij kunnen het alleen slechter maken: wind van zee maakt de golven rommelig (lager cijfer), harde wind van land maakt ze zwaar (hoger cijfer). Bij surfen leren en SUP-surfen telt wind altijd als zwaarder. Bij een periode onder 6 s wordt een 3 een 2 (behalve bij surfen leren en bodyboard).</p>
  <table>${kop}${S('A').map((s: Sport) => rij(s.naam, vanTot(s.golf, 'm'))).join('')}</table>
  <table><tr><th>Sport</th><th>Wind stoort vanaf (zee / opzij / land)</th><th>Wind te veel vanaf</th></tr>
    ${S('A').map((s: Sport) => rij(s.naam, [s.wind1.join(' / ') + ' kn', s.wind2.join(' / ') + ' kn'])).join('')}</table>
  <h2>Windsporten</h2>
  <p>De wind zet het cijfer (de onderkant met de gemiddelde wind, de bovenkant met het windgetal W). Ruw water, wind van land en vlagerige wind kunnen het alleen zwaarder maken. Kiten op land: bij hoog water een 1.</p>
  <table>${kop}${S('B').map((s: Sport) => rij(s.naam, vanTot(s.wind, 'kn'))).join('')}</table>
  <table><tr><th>Sport</th><th>Ruw water zwaarder vanaf</th><th>Windrichting</th></tr>
    ${S('B').map((s: Sport) => rij(s.naam, [s.ruw ? `${nl(s.ruw[0])} m, veel zwaarder vanaf ${nl(s.ruw[1])} m` : 'telt niet', richting[s.richting]])).join('')}</table>
  <h2>Wind en golf samen</h2>
  <p>Een windcijfer (grenzen hieronder) en een golfcijfer (3 vanaf GOLF 0,8 m, 4 vanaf RUW 2 m, 5 vanaf RUW 3 m) worden samengevoegd. Wind van land (a boven 112,5°) maakt het zwaarder.</p>
  <table>${kop}${S('C').map((s: Sport) => rij(s.naam, vanTot(s.wind, 'kn'))).join('')}</table>
  <h2>Rustig water</h2>
  <p>Hoe kalmer, hoe beter: het cijfer begint bij 3 en gaat omhoog door ruw water of te veel wind.</p>
  <table><tr><th>Sport</th><th>RUW: 4 vanaf / 5 vanaf</th><th>Wind: 4 vanaf / 5 vanaf</th><th>Wind van land: 4 vanaf / 5 vanaf</th></tr>
    ${S('D').map((s: Sport) => rij(s.naam, [`${nl(s.ruw[0])} / ${nl(s.ruw[1])} m`, `${s.wind[0]} / ${s.wind[1]} kn`, `${s.land[0]} / ${s.land[1]} kn`])).join('')}</table>
  <h2>Uitleg bij het cijfer</h2>
  <p>De fiche van een strand zegt per sport waarom het cijfer is wat het is: hoe groot de golf aan het strand is, hoeveel wind er telt, en welke regel het cijfer hoger of lager zette (ruw water, windrichting, vlagen, korte periode of getij).</p>`
  document.getElementById('inhoud')!.innerHTML = html

  const N = ix.nauwkeurigheid
  const nk = document.getElementById('nauwkeurigheid')!
  if (!N) { nk.innerHTML = '<p>Nog geen meting.</p>'; return }
  const rows: string[] = []
  for (const [boei, r] of Object.entries<any>(N.boeien)) {
    const v = r.vergelijking
    if (!v) continue
    const cel = (m: string, k: string) => {
      const s = v[m]?.[k]
      return s ? `${nl(s.rmse.toFixed(2))} (${s.afwijking >= 0 ? '+' : ''}${nl(s.afwijking.toFixed(2))})` : '–'
    }
    rows.push(`<tr><td>${boei}<br><span class="klein">${r.periode?.[0]?.slice(0, 10)} tot ${r.periode?.[1]?.slice(0, 10)}, ${r.uren_gemeten} uur</span></td>
      <td>${cel('GFS-Wave', 'VHM0')}</td><td>${cel('IBI', 'VHM0')}</td><td>${cel('GFS-Wave', 'VTPK')}</td><td>${cel('IBI', 'VTPK')}</td></tr>`)
  }
  nk.innerHTML = `<p>Golfhoogte en piekperiode van de modellen naast de metingen van de boeien (Copernicus In-Situ).
    Per cel: de gemiddelde fout (RMSE) en tussen haakjes de gemiddelde afwijking (+ = model te hoog).
    Het gaat om de beste schatting van het model voor dat uur, nog niet om een voorspelling van dagen vooraf.</p>
    <table><tr><th>Boei</th><th>Golfhoogte (m), GFS-Wave</th><th>Golfhoogte (m), Copernicus IBI</th>
    <th>Piekperiode (s), GFS-Wave</th><th>Piekperiode (s), Copernicus IBI</th></tr>${rows.join('')}</table>
    <p class="klein">Gemeten op ${N.gemaakt.slice(0, 10)}. Daarom gebruikt de kaart IBI voor de golven (GFS-Wave waar IBI ophoudt) en ECMWF voor de wind. De wind wordt gemeten zodra er genoeg IPMA-metingen gearchiveerd zijn.</p>`
})
