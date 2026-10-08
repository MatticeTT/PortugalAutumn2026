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
async function nabootsen(ctx) {
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
  await nabootsen(ctx)
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
  check(`[${scheme}] suggesties terwijl je typt`, sugg.length === 2 && sugg[1] === 'Hotel Riomar', `(${sugg.join(', ')})`)
  if (shots) await page.screenshot({ path: `${shots}/verblijf-zoek-${scheme}.png` })
  await page.click('dialog .gevonden button')
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
  // Terug naar de kaart: het verblijf is onthouden, geen nieuwe vraag.
  await page.goto(base + '/')
  await page.waitForSelector('body[data-klaar="1"]', { timeout: 20000 })
  await page.waitForTimeout(800)
  const terug = await page.textContent('#verblijfknop')
  check(`[${scheme}] verblijf onthouden na planning`, !(await page.$('dialog.verblijfvraag[open]')) && terug.includes('Lagos'), `(${terug.trim()})`)
  await ctx.close()
}
check('OSRM nagebootst en gebruikt', osrm > 0, `(${osrm} vragen)`)
check('geen JavaScript-fouten', fouten.length === 0, fouten.slice(0, 3).join(' | '))
await browser.close()
process.exit(ok ? 0 : 1)
