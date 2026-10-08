// M4-acceptatie: telefoon van 400 px, licht en donker, fiche binnen een seconde, noindex.
// Gebruik (in web/): node tests/smoke.mjs http://localhost:4173 [map-voor-schermafbeeldingen]
import { chromium } from 'playwright'
import { existsSync } from 'node:fs'

const base = process.argv[2] ?? 'http://localhost:4173'
const shots = process.argv[3]
const exe = ['/opt/pw-browsers/chromium'].find(existsSync)
const browser = await chromium.launch(exe ? { executablePath: exe } : {})
const fouten = []
let ok = true
// Photon, Nominatim en OSRM nagebootst (geen internet in de test): de nagebootste rijtijd = afstand aan 60 km/h.
const km = ([a, b], [c, d]) => {
  const t = Math.PI / 180, h = Math.sin((d - b) * t / 2) ** 2 + Math.cos(b * t) * Math.cos(d * t) * Math.sin((c - a) * t / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(h))
}
let osrm = 0
const PNG = 'iVBORw0KGgoAAAANSUhEUgAAAEAAAAAwCAIAAAAuKetIAAAAU0lEQVR4nO3PQQ3AIADAQMAOrnCNm4ngcVnSU9DOe/b4s6UDXjWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaB9iYkBxtqsWxgAAAAASUVORK5CYII='
async function nabootsen(ctx, google) {
  // Donker thema: Esri (hoofdbron) nagebootst; licht thema: Esri faalt, terugval op Photon.
  if (google) await ctx.route('https://geocode.arcgis.com/**', (r) => {
    const u = new URL(r.request().url())
    if (u.pathname.endsWith('/suggest')) return r.fulfill({ json: { suggestions: [
      { text: 'One2Seven, Urbanização da Cerca do Moinho, 8400-205, Ferragudo, Lagoa, Faro, PRT', magicKey: 'k1', isCollection: false },
      { text: 'Lagos, Faro, PRT', magicKey: 'k2', isCollection: false }] } })
    return r.fulfill({ json: { candidates: [{ location: u.searchParams.get('magicKey') === 'k1' ? { x: -8.5196, y: 37.1236 } : { x: -8.673, y: 37.102 } }] } })
  })
  else await ctx.route('https://geocode.arcgis.com/**', (r) => r.abort())
  await ctx.route('https://photon.komoot.io/**', (r) => r.fulfill({ json: { type: 'FeatureCollection', features: [
    { geometry: { type: 'Point', coordinates: [-8.6730, 37.1020] }, properties: { name: 'Lagos', postcode: '8600', state: 'Faro', osm_key: 'place' } },
    { geometry: { type: 'Point', coordinates: [-8.6745, 37.0990] }, properties: { name: 'Hotel Riomar', street: 'Rua Cândido dos Reis', housenumber: '83', city: 'Lagos', state: 'Faro' } }] } }))
  await ctx.route('https://router.project-osrm.org/**', (r) => {
    osrm++
    const u = new URL(r.request().url())
    const pts = decodeURIComponent(u.pathname.split('/').pop()).split(';').map((p) => p.split(',').map(Number))
    if (u.pathname.includes('/table/')) return r.fulfill({ json: { code: 'Ok', durations: [pts.map((p) => km(pts[0], p) / 60 * 3600)] } })
    return r.fulfill({ json: { code: 'Ok', routes: [{ geometry: { type: 'LineString', coordinates: pts } }] } })
  })
}
const check = (naam, voorwaarde, extra = '') => {
  console.log(`${voorwaarde ? 'OK  ' : 'FOUT'} ${naam} ${extra}`)
  if (!voorwaarde) ok = false
}

for (const scheme of ['light', 'dark']) {
  const ctx = await browser.newContext({ viewport: { width: 400, height: 820 }, deviceScaleFactor: 2, colorScheme: scheme, isMobile: true, hasTouch: true })
  await nabootsen(ctx, scheme === 'dark')
  const page = await ctx.newPage()
  page.on('pageerror', (e) => fouten.push(String(e)))
  const resp = await page.goto(base + '/', { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('body[data-klaar="1"]', { timeout: 20000 })
  // Eerst de vraag: waar verblijf je, hoe lang wil je rijden. Daarna zoomt de kaart in en komen de routes.
  await page.waitForSelector('dialog.verblijfvraag[open]', { timeout: 5000 })
  if (shots) await page.screenshot({ path: `${shots}/verblijf-vraag-${scheme}.png` })
  await page.locator('dialog input[name=q]').pressSequentially('Lag', { delay: 60 })
  await page.waitForSelector('dialog .gevonden button', { timeout: 5000 })
  const sugg = await page.$$eval('dialog .gevonden b', (els) => els.map((e) => e.textContent))
  check(`[${scheme}] suggesties terwijl je typt (${scheme === 'dark' ? 'Esri' : 'Photon'})`,
    sugg.length === 2 && sugg[1] === (scheme === 'dark' ? 'Lagos' : 'Hotel Riomar'), `(${sugg.join(', ')})`)
  if (shots) await page.screenshot({ path: `${shots}/verblijf-zoek-${scheme}.png` })
  await page.click(scheme === 'dark' ? 'dialog .gevonden li:nth-child(2) button' : 'dialog .gevonden button')
  await page.fill('dialog input[name=uren]', '1')
  await page.fill('dialog input[name=min]', '0')
  await page.click('dialog button[value=ok]')
  await page.waitForSelector('#routes:not([hidden])', { timeout: 10000 })
  const knop = await page.textContent('#verblijfknop')
  check(`[${scheme}] verblijf gekozen`, knop.includes('Lagos') && knop.includes('1u'), `(${knop.trim()})`)
  const routes = await page.$$eval('#routes li', (els) => els.map((e) => e.textContent.replace(/\s+/g, ' ').trim()))
  const rijMin = await page.$$eval('#routes em', (els) => els.map((e) => e.textContent))
  check(`[${scheme}] routes binnen 1 uur (of melding)`, routes.length > 0 && rijMin.every((t) => !t.includes('u') || t === '1u'), `(${routes.join(' | ')})`)
  check(`[${scheme}] punt van het verblijf op de kaart`, !!(await page.$('.verblijfpunt')))
  await page.waitForTimeout(1600)
  const midden = await page.evaluate(() => { const c = (window).__kaart.getCenter(); return [c.lng, c.lat] })
  const doel = scheme === 'dark' ? [-8.673, 37.102] : [-8.673, 37.102]
  check(`[${scheme}] verblijf in het midden van de kaart`, Math.abs(midden[0] - doel[0]) < 0.01 && Math.abs(midden[1] - doel[1]) < 0.01, `(${midden.map((x) => x.toFixed(3))})`)
  await page.waitForTimeout(1500)

  if (scheme === 'light') {
    check('noindex in de pagina', (await page.getAttribute('meta[name=robots]', 'content'))?.includes('noindex'))
    const robots = await (await page.request.get(base + '/robots.txt')).text()
    check('robots.txt weigert alles', /Disallow: \/\s*$/m.test(robots))
    check('pagina laadt', resp.ok())
  }
  const nDag = await page.$$eval('#datum option', (o) => o.length)
  check(`[${scheme}] enkel dag en uur, 10 dagen`, nDag >= 9 && !(await page.$('#sport')), `(${nDag})`)
  const breed = await page.evaluate(() => document.documentElement.scrollWidth)
  check(`[${scheme}] geen horizontale scroll op 400 px`, breed <= 400, `(${breed}px)`)
  if (shots) await page.screenshot({ path: `${shots}/kaart-${scheme}.png` })
  // Zoeken: "rocha" vindt Praia da Rocha; kiezen opent de fiche.
  await page.fill('#zoek', 'rocha')
  const gevonden = await page.$$eval('#zoeklijst li b', (els) => els.map((e) => e.textContent))
  check(`[${scheme}] zoeken vindt Praia da Rocha`, gevonden.includes('Praia da Rocha'), `(${gevonden.join(', ')})`)
  await page.locator('#zoeklijst li b', { hasText: /^Praia da Rocha$/ }).first().dispatchEvent('pointerdown')
  await page.waitForSelector('#fiche h2')
  check(`[${scheme}] zoeken opent de fiche`, (await page.textContent('#fiche h2')) === 'Praia da Rocha')
  if (shots) {
    await page.fill('#zoek', 'sao')
    await page.screenshot({ path: `${shots}/zoek-${scheme}.png` })
    await page.fill('#zoek', '')
  }
  // Andere landen (als er stranden van België zijn): zoeken toont het land, de fiche de vaste nota.
  const be = await page.evaluate(async () => (await (await fetch('data/kaart.json')).json()).find((s) => s.l === 'be'))
  if (be) {
    await page.fill('#zoek', 'oostende')
    const regel = await page.textContent('#zoeklijst li')
    await page.locator('#zoeklijst li').first().dispatchEvent('pointerdown')
    await page.waitForSelector('#fiche .vastenota', { timeout: 5000 })
    const nota = await page.textContent('#fiche .vastenota')
    check(`[${scheme}] Belgisch strand: land in de zoeklijst en vaste nota`, /België/.test(regel) && nota === 'Sterke getijstroom aan deze kust; die zit niet in de berekening.', `(${regel.trim()})`)
    if (shots) await page.screenshot({ path: `${shots}/belgie-${scheme}.png` })
  }
  // Een klimplek openen (als er klimdata is): discipline, soort, graad, aantal routes.
  const klimId = await page.evaluate(async () => {
    const g = await (await fetch('data/index.json')).json()
    const r = await fetch(`data/klim/kaart.json?v=${encodeURIComponent(g.gemaakt)}`)
    return r.ok ? (await r.json())[0]?.id : null
  })
  if (klimId) {
    await page.goto(base + '/#' + encodeURIComponent('klim:' + klimId))
    await page.waitForSelector('#fiche .klimtabel', { timeout: 10000 })
    const kop = await page.$$eval('#fiche .klimtabel th', (els) => els.map((e) => e.textContent))
    check(`[${scheme}] klimplek: discipline, soort, graad, aantal routes`,
      ['Discipline', 'Soort plek', 'Aantal routes'].every((k) => kop.includes(k)) && kop.some((k) => k.startsWith('Graad')))
  }
  // Een strand bij Ferragudo openen.
  const id = await page.evaluate(async () => (await (await fetch('data/kaart.json')).json()).find((s) => s.n === 'Praia dos Caneiros')?.id)
  await page.goto(base + '/#' + encodeURIComponent(id))
  await page.waitForSelector('body[data-klaar="1"]')
  const t1 = Date.now()
  await page.waitForSelector('#fiche .tegel b', { timeout: 5000 })
  const ms = Date.now() - t1
  check(`[${scheme}] fiche open`, ms < 1000, `(${ms} ms na het laden van de kaart)`)
  const tegels = await page.$$eval('#fiche .tegel .soort', (els) => els.map((e) => e.textContent))
  check(`[${scheme}] fiche: WAVE en WIND`, tegels.join() === 'WAVE,WIND', `(${tegels.join(', ')})`)
  // Het bolletje op de kaart en de fiche tonen hetzelfde WIND- en WAVE-cijfer.
  const i = Number(await page.getAttribute('#fiche .dag td.nu a[data-i]', 'data-i'))
  const kaartCijfers = await page.evaluate(async ([id, i]) => {
    const g = await (await fetch('data/index.json')).json()
    const v = `?v=${encodeURIComponent(g.gemaakt)}`
    const k = (await (await fetch('data/kaart.json' + v)).json()).findIndex((s) => s.id === id)
    return (await (await fetch('data/sport/ww.json' + v)).json())[k].slice(5 * i, 5 * i + 3)
  }, [id, i])
  const ficheCijfers = (await page.$$eval('#fiche .tegel > b', (els) => els.map((e) => e.textContent))).reverse().join('')
    + await page.$$eval('#fiche .tegel', (els) => String((els[1].classList.contains('verkeerd') ? 1 : 0) + (els[0].classList.contains('verkeerd') ? 2 : 0)))
  check(`[${scheme}] kaart en fiche gelijk (WIND, WAVE, rood kader)`, kaartCijfers === ficheCijfers, `(kaart ${kaartCijfers}, fiche ${ficheCijfers})`)
  const rijen = await page.$$eval('#fiche .dag th', (els) => els.map((e) => e.textContent))
  const uren = await page.$$eval('#fiche .dag a[data-i]', (els) => els.length)
  check(`[${scheme}] fiche: de dag met WAVE, WIND en getij`, ['WAVE', 'WIND', 'getij'].every((r) => rijen.includes(r)) && uren >= 20, `(${uren} uren)`)
  const held = await page.textContent('#fiche .held .zin')
  const rest = await page.$$eval('#fiche .rest li', (els) => els.length)
  check(`[${scheme}] fiche: bovenaan wat je vandaag kan, met de andere eronder`, !!held && rest >= 3, `(${held}; ${rest} andere)`)
  if (shots) {
    await page.screenshot({ path: `${shots}/fiche-${scheme}.png` })
    await page.locator('#fiche').screenshot({ path: `${shots}/fiche-vol-${scheme}.png` }).catch(() => {})
  }
  // De planning rekent vanaf het gekozen verblijf.
  await page.goto(base + '/planning')
  await page.waitForFunction(() => /Lagos/.test(document.getElementById('planvan')?.textContent ?? '') && !/berekenen/.test(document.getElementById('planvan').textContent), null, { timeout: 15000 })
  const van = (await page.textContent('#planvan')).replace(/\s+/g, ' ').trim()
  const plannen = await page.$$eval('.plandag .waar em', (els) => els.map((e) => e.textContent))
  check(`[${scheme}] planning vanaf het verblijf, max 1 uur`, van.includes('max 1u') && plannen.every((t) => !/1u0[1-9]|1u[1-5]\d|[2-9]u/.test(t)), `(${van}; ${plannen.join(', ')})`)
  if (shots) await page.screenshot({ path: `${shots}/planning-${scheme}.png` })
  if (shots) await page.screenshot({ path: `${shots}/planning-vol-${scheme}.png`, fullPage: true })
  const regels = await page.$$eval('.daglijst li', (els) => els.map((e) => e.textContent.replace(/\s+/g, ' ').trim()))
  check(`[${scheme}] dagen zonder plan als regels per week`, regels.some((r) => /Aankomst/.test(r)) && regels.some((r) => /Nog geen voorspelling/.test(r)), `(${regels.length} regels)`)
  // Eigen activiteit: plusje op de eerste dagkaart, formulier invullen met foto en locatie, kaart verschijnt, verwijderen.
  check(`[${scheme}] plusje bij elke dag`, (await page.$$('#dagen [data-plus]')).length >= 10)
  if (scheme === 'dark') {
    const opslag = []
    await page.route('**/api/activiteiten**', async (r) => {
      const m = r.request().method()
      if (m === 'GET') return r.fulfill({ json: opslag })
      if (m === 'POST') {
        const b = JSON.parse(r.request().postData())
        const a = { ...b, id: 'a' + (opslag.length + 1), foto: b.foto ? 'data:image/png;base64,' + PNG : null }
        opslag.push(a); return r.fulfill({ json: a })
      }
      if (m === 'DELETE') { opslag.length = 0; return r.fulfill({ json: { ok: true } }) }
    })
    const dagPlus = await page.getAttribute('.plandag [data-plus]', 'data-plus')
    await page.click('.plandag [data-plus]')
    await page.waitForSelector('dialog.activiteitvraag[open]')
    await page.fill('dialog input[name=titel]', 'Kajakken Benagil')
    await page.fill('dialog input[name=van]', '14:00')
    await page.fill('dialog input[name=tot]', '16:30')
    await page.locator('dialog input[name=plek]').pressSequentially('One2', { delay: 40 })
    await page.waitForSelector('dialog .gevonden button')
    await page.click('dialog .gevonden button')
    await page.setInputFiles('dialog input[name=foto]', { name: 'f.png', mimeType: 'image/png', buffer: Buffer.from(PNG, 'base64') })
    await page.waitForSelector('dialog .fotokeuze img:not([hidden])')
    if (shots) await page.screenshot({ path: `${shots}/activiteit-form-${scheme}.png` })
    await page.click('dialog button[value=ok]')
    await page.waitForSelector('.plandag.eigen', { timeout: 5000 })
    const kaart = (await page.textContent('.plandag.eigen')).replace(/\s+/g, ' ')
    check(`[${scheme}] activiteit toegevoegd op de juiste dag`, opslag[0]?.dag === dagPlus && /Kajakken Benagil/.test(kaart) && /14–16:30u/.test(kaart) && /One2Seven/.test(kaart) && !!opslag[0]?.plek,
      `(${kaart.trim().slice(0, 80)})`)
    if (shots) { await page.locator('.plandag.eigen').scrollIntoViewIfNeeded(); await page.screenshot({ path: `${shots}/activiteit-${scheme}.png` }) }
    page.once('dialog', (dl) => dl.accept())
    await page.click('.plandag.eigen [data-wis]')
    await page.waitForFunction(() => !document.querySelector('.plandag.eigen'))
    check(`[${scheme}] activiteit verwijderd`, opslag.length === 0)
  }
  // Knop dag/nacht: wisselt het thema en onthoudt de keuze.
  const bgVoor = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
  await page.click('#thema')
  const bgNa = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
  const bewaard = await page.evaluate(() => localStorage.getItem('thema'))
  check(`[${scheme}] knop dag/nacht`, bgVoor !== bgNa && bewaard === (scheme === 'dark' ? 'licht' : 'donker'), `(${bgVoor} → ${bgNa})`)
  if (shots) await page.screenshot({ path: `${shots}/thema-${scheme}.png` })
  await page.click('#thema')
  await page.evaluate(() => localStorage.removeItem('thema'))
  // Volgorde van voorrang: Klimmen naar boven zetten.
  const vooraf = await page.$$eval('.plandag .wat', (els) => els.map((e) => e.textContent))
  for (let k = 0; k < 3; k++) await page.click('#voorrang li:has-text("Klimmen") button[data-r="-1"]')
  const volg = await page.$$eval('#voorrang li span', (els) => els.map((e) => e.textContent.replace(/\d/, '').trim()))
  const achteraf = await page.$$eval('.plandag .wat', (els) => els.map((e) => e.textContent))
  check(`[${scheme}] voorrang aanpassen: klimmen eerst`, volg[0] === 'Klimmen' && achteraf.filter((t) => t === 'Klimmen').length > vooraf.filter((t) => t === 'Klimmen').length,
    `(${volg.join(' > ')}; klimdagen ${vooraf.filter((t) => t === 'Klimmen').length} → ${achteraf.filter((t) => t === 'Klimmen').length})`)
  if (shots) await page.screenshot({ path: `${shots}/voorrang-${scheme}.png` })
  await page.click('#voorrang [data-a=standaard]')
  // Terug naar de kaart via het tabblad: het verblijf is onthouden, geen nieuwe vraag.
  await page.click('.tabs a[href="./"]')
  await page.waitForSelector('body[data-klaar="1"]', { timeout: 20000 })
  await page.waitForTimeout(800)
  const terug = await page.textContent('#verblijfknop')
  check(`[${scheme}] verblijf onthouden na planning`, !(await page.$('dialog.verblijfvraag[open]')) && terug.includes('Lagos'), `(${terug.trim()})`)
  // Nog eens heen en terug via de tabbladen.
  await page.click('.tabs a[href="planning"]')
  await page.waitForSelector('.plandag, .daglijst', { timeout: 15000 })
  await page.click('.tabs a[href="./"]')
  await page.waitForSelector('body[data-klaar="1"]', { timeout: 20000 })
  await page.waitForTimeout(800)
  check(`[${scheme}] tweede keer heen en terug: geen vraag`, !(await page.$('dialog.verblijfvraag[open]')))
  // Knop Surfen: uitleg en filters.
  await page.click('#laagknoppen .surf')
  const uitleg = await page.textContent('.surfpaneel')
  const tel = () => page.evaluate(async () => (await (window).__kaart.getSource('stranden').getData()).features.length)
  const voor = await tel()
  await page.check('.surfpaneel input[name=surfkeuze][value="R"]')
  await page.waitForTimeout(300)
  const na = await tel()
  const keuzes = await page.$$eval('.surfpaneel .keuzes label', (els) => els.map((e) => e.textContent.trim()))
  check(`[${scheme}] knop Surfen: 5 keuzes en filter werkt`, keuzes.join('|') === 'Alles|Ideale golfsurfdag|Ideale windsurfdag|Windsurfen op golven|Ideale stille waters'
    && /Links WIND/.test(uitleg) && na < voor, `(${voor} → ${na} stranden)`)
  if (shots) await page.screenshot({ path: `${shots}/surfpaneel-${scheme}.png` })
  await page.check('.surfpaneel input[name=surfkeuze][value="alles"]')
  // Herladen: de vraag komt terug, leeg.
  await page.reload()
  await page.waitForSelector('dialog.verblijfvraag[open]', { timeout: 10000 })
  check(`[${scheme}] herladen vraagt opnieuw (leeg)`, (await page.inputValue('dialog input[name=q]')) === '')
  await ctx.close()
}
check('OSRM nagebootst en gebruikt', osrm > 0, `(${osrm} vragen)`)
check('geen JavaScript-fouten', fouten.length === 0, fouten.slice(0, 3).join(' | '))
await browser.close()
process.exit(ok ? 0 : 1)
