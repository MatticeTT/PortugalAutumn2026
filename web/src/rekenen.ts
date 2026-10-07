import './style.css'
import type { Index } from './types'

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

fetch('data/index.json').then((r) => r.json()).then((ix: Index) => {
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
