import './style.css'
import { KLEUR, tekstKleur } from './kleuren'
import type { Index, Sport } from './types'

const nl = (x: number) => String(x).replace('.', ',')
const bewijsKlasse = (b: string) => (b.startsWith('sterk') ? 'sterk' : b.startsWith('praktijk') ? 'praktijk' : 'eigen')

// WIND en WAVE (M5): drempels en bewijs uit pipeline/rules/rules.yaml.
function wwUitleg(ix: any): string {
  const R = ix.regels
  const B = R.bronnen as Record<string, { bron: string; bewijs: string }>
  const tag = (k: string) => {
    const b = B[k]
    if (!b) return ''
    const link = b.bron.startsWith('http') ? `<a href="${b.bron}">bron</a>` : b.bron
    return `<span class="bewijs ${bewijsKlasse(b.bewijs)}">${b.bewijs}</span> ${link}`
  }
  const k = R.wind.kite
  const h = R.wave.hb
  const html = `
  <h3>WIND</h3>
  <h4>Stap 1: sterkte (gemiddelde wind op 10 m)</h4>
  <table><tr><th>Score</th><th>Wind</th><th>Bewijs</th></tr>
    <tr><td>1</td><td>onder ${k.s2} kn</td><td>${tag('wind.kite.s2')}</td></tr>
    <tr><td>2</td><td>${k.s2} tot ${k.s3 - 1} kn</td><td>${tag('wind.kite.s2')}</td></tr>
    <tr><td>3</td><td>${k.s3} tot ${k.s4 - 1} kn</td><td>${tag('wind.kite.s3')}</td></tr>
    <tr><td>4</td><td>${k.s4} tot ${k.s5 - 1} kn</td><td>${tag('wind.kite.s4')}</td></tr>
    <tr><td>5</td><td>${k.s5} kn of meer, of vlagen van ${R.wind.vlagen.s5} kn of meer</td><td>${tag('wind.kite.s5')}</td></tr></table>
  <h4>Stap 2: richting tegenover het strand</h4>
  <table><tr><th>Klasse</th><th>Hoek met de kijkrichting</th><th>Effect</th></tr>
    <tr><td>Aanlandig</td><td>0 tot ${nl(R.wind.richting.aanlandig)}°</td><td>score blijft; voor kite alleen met ervaring</td></tr>
    <tr><td>Schuin aanlandig</td><td>tot ${nl(R.wind.richting.schuin_aan)}°</td><td>score blijft; ideale richting</td></tr>
    <tr><td>Zijwind</td><td>tot ${nl(R.wind.richting.zij)}°</td><td>score blijft; ideale richting</td></tr>
    <tr><td>Schuin aflandig</td><td>tot ${nl(R.wind.richting.schuin_af)}°</td><td rowspan="2">vanaf ${R.wind.aflandig.vanaf_kn} kn wordt de score ${R.wind.aflandig.score} (niet op besloten water) ${tag('wind.aflandig')}</td></tr>
    <tr><td>Aflandig</td><td>tot 180°</td></tr></table>
  <p>Sectorgrenzen: ${tag('wind.richting')}. Vlagen boven ${R.wind.vlagen.min4} kn geven minstens 4 (${tag('wind.vlagen.min4')}).</p>
  <h4>Windsurf</h4>
  <ul>${R.wind.windsurf_regels.map((r: any) => `<li>${r.van} tot ${r.tot} kn: ${r.tekst.replace(/^windsurf: /, '')}</li>`).join('')}</ul>
  <h3>WAVE</h3>
  <p>De maat is de geschatte brekende golfhoogte op het strand, Hb = k · 0,39 · g<sup>0,2</sup> · (som van f² · H² · T)<sup>0,4</sup> (Komar en Gaughan), per deelgolf (deining 1, deining 2, windgolf) met de blootstellingsfactor f van het strand. k = ${nl(R.wave.k)} ${tag('wave.k')}. Wat de deelgolven tekortkomen op de totale golfhoogte telt als windgolf ${tag('wave.restdeel_als_windgolf')}.</p>
  <table><tr><th>Score</th><th>Hb op het strand</th><th>Bewijs</th></tr>
    <tr><td>1</td><td>onder ${nl(h.s2)} m</td><td><span class="bewijs eigen">eigen keuze</span></td></tr>
    <tr><td>2</td><td>${nl(h.s2)} tot ${nl(h.s3)} m</td><td>${tag('wave.hb.s2')}</td></tr>
    <tr><td>3</td><td>${nl(h.s3)} tot ${nl(h.s4)} m</td><td>${tag('wave.hb.s3')}</td></tr>
    <tr><td>4</td><td>${nl(h.s4)} tot ${nl(h.s5)} m</td><td>${tag('wave.hb.s4')}</td></tr>
    <tr><td>5</td><td>${nl(h.s5)} m of meer</td><td>${tag('wave.hb.s5')}</td></tr></table>
  <ul>
    <li>IPMA-waarschuwing voor zeegang (geel of hoger) in het district: score 5. ${tag('wave.ipma_zeegang')}</li>
    <li>Periode van de grootste deelgolf onder ${R.wave.periode.max2_onder_s} s: hoogstens 2. ${tag('wave.periode.max2_onder_s')}</li>
    <li>Periode van ${R.wave.periode.nota_vanaf_s} s of meer: nota over lange pauzes en stroming. ${tag('wave.periode.nota_vanaf_s')}</li>
    <li>${nl(h.s4)} tot ${nl(R.wave.beginnersles_tot)} m: les voor beginners kan nog. ${tag('wave.beginnersles_tot')}</li>
  </ul>
  <h3>Label</h3>
  <p>De eerste regel die past:</p>
  <ol>
    <li>WAVE 5: Gevaarlijke zee</li>
    <li>WIND 5 door sterkte of vlagen: Gevaarlijk: storm</li>
    <li>WIND 5 door aflandige wind, WAVE 3 en wind tot ${R.surf_wind.beginner_max_kn} kn: Surfdag voor beginners, met waarschuwing</li>
    <li>WIND 5 door aflandige wind, WAVE 4 en wind tot ${R.surf_wind.gevorderd_max_kn} kn: Surfdag voor gevorderden, met waarschuwing</li>
    <li>WIND 5 door aflandige wind, in de andere gevallen: Aflandige wind: gevaarlijk voor kite, windsurf en sup</li>
    <li>WIND 3 of 4 en WAVE 3 of 4: Winddag met golven (gevorderd)</li>
    <li>WIND 4: Winddag voor gevorderden</li>
    <li>WIND 3: Winddag voor beginners</li>
    <li>WAVE 4: Surfdag voor gevorderden</li>
    <li>WAVE 3: Surfdag voor beginners</li>
    <li>Allebei onder 3: Stille dag (sup, kayak, wakeboard)</li>
  </ol>`
  return html
}

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
  <h2>Surfweer</h2>
  <p>De golf (GOLF) zet het cijfer. Wind en getij kunnen het alleen slechter maken: wind van zee maakt de golven rommelig (lager cijfer), harde wind van land maakt ze zwaar (hoger cijfer). Bij surfen leren en SUP-surfen telt wind altijd als zwaarder. Bij een periode onder 6 s wordt een 3 een 2 (behalve bij surfen leren en bodyboard).</p>
  <table>${kop}${S('A').map((s: Sport) => rij(s.naam, vanTot(s.golf, 'm'))).join('')}</table>
  <table><tr><th>Sport</th><th>Wind stoort vanaf (zee / opzij / land)</th><th>Wind te veel vanaf</th></tr>
    ${S('A').map((s: Sport) => rij(s.naam, [s.wind1.join(' / ') + ' kn', s.wind2.join(' / ') + ' kn'])).join('')}</table>
  <h2>Windweer</h2>
  <p>De wind zet het cijfer (de onderkant met de gemiddelde wind, de bovenkant met het windgetal W). Ruw water, wind van land en vlagerige wind kunnen het alleen zwaarder maken. Kiten op land: bij hoog water een 1.</p>
  <table>${kop}${S('B').map((s: Sport) => rij(s.naam, vanTot(s.wind, 'kn'))).join('')}</table>
  <table><tr><th>Sport</th><th>Ruw water zwaarder vanaf</th><th>Windrichting</th></tr>
    ${S('B').map((s: Sport) => rij(s.naam, [s.ruw ? `${nl(s.ruw[0])} m, veel zwaarder vanaf ${nl(s.ruw[1])} m` : 'telt niet', richting[s.richting]])).join('')}</table>
  <h2>Wind-golven</h2>
  <p>Een windcijfer (grenzen hieronder) en een golfcijfer (3 vanaf GOLF 0,8 m, 4 vanaf RUW 2 m, 5 vanaf RUW 3 m) worden samengevoegd. Wind van land (a boven 112,5°) maakt het zwaarder.</p>
  <table>${kop}${S('C').map((s: Sport) => rij(s.naam, vanTot(s.wind, 'kn'))).join('')}</table>
  <h2>Stille waters</h2>
  <p>Hoe kalmer, hoe beter: het cijfer begint bij 3 en gaat omhoog door ruw water of te veel wind.</p>
  <table><tr><th>Sport</th><th>RUW: 4 vanaf / 5 vanaf</th><th>Wind: 4 vanaf / 5 vanaf</th><th>Wind van land: 4 vanaf / 5 vanaf</th></tr>
    ${S('D').map((s: Sport) => rij(s.naam, [`${nl(s.ruw[0])} / ${nl(s.ruw[1])} m`, `${s.wind[0]} / ${s.wind[1]} kn`, `${s.land[0]} / ${s.land[1]} kn`])).join('')}</table>
  <h2>Uitleg bij het cijfer</h2>
  <p>De fiche van een strand zegt per sport waarom het cijfer is wat het is: hoe groot de golf aan het strand is, hoeveel wind er telt, en welke regel het cijfer hoger of lager zette (ruw water, windrichting, vlagen, korte periode of getij).</p>`
  document.getElementById('inhoud')!.innerHTML = html
  document.getElementById('ww-inhoud')!.innerHTML = wwUitleg(ix)

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
