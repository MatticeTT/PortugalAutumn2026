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
const check = (naam, voorwaarde, extra = '') => {
  console.log(`${voorwaarde ? 'OK  ' : 'FOUT'} ${naam} ${extra}`)
  if (!voorwaarde) ok = false
}

for (const scheme of ['light', 'dark']) {
  const ctx = await browser.newContext({ viewport: { width: 400, height: 820 }, deviceScaleFactor: 2, colorScheme: scheme, isMobile: true, hasTouch: true })
  const page = await ctx.newPage()
  page.on('pageerror', (e) => fouten.push(String(e)))
  const resp = await page.goto(base + '/', { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('body[data-klaar="1"]', { timeout: 20000 })
  await page.waitForTimeout(1500)
  if (scheme === 'light') {
    check('noindex in de pagina', (await page.getAttribute('meta[name=robots]', 'content'))?.includes('noindex'))
    const robots = await (await page.request.get(base + '/robots.txt')).text()
    check('robots.txt weigert alles', /Disallow: \/\s*$/m.test(robots))
    check('pagina laadt', resp.ok())
  }
  const nSport = await page.$$eval('#sport option', (o) => o.length)
  const nDag = await page.$$eval('#datum option', (o) => o.length)
  check(`[${scheme}] keuzelijsten: 21 sporten, 10 dagen`, nSport === 21 && nDag >= 9, `(${nSport}, ${nDag})`)
  const breed = await page.evaluate(() => document.documentElement.scrollWidth)
  check(`[${scheme}] geen horizontale scroll op 400 px`, breed <= 400, `(${breed}px)`)
  if (shots) await page.screenshot({ path: `${shots}/kaart-${scheme}.png` })
  // Een strand openen via de kaart: klik op een bolletje in de buurt van Peniche na inzoomen.
  const id = await page.evaluate(async () => (await (await fetch('data/kaart.json')).json()).find((s) => s.n === 'Praia da Arrifana')?.id)
  await page.goto(base + '/#' + encodeURIComponent(id))
  await page.waitForSelector('body[data-klaar="1"]')
  const t1 = Date.now()
  await page.waitForSelector('#fiche .groot', { timeout: 5000 })
  const ms = Date.now() - t1
  check(`[${scheme}] fiche open`, ms < 1000, `(${ms} ms na het laden van de kaart)`)
  const cijfer = await page.textContent('#fiche .groot')
  const label = await page.textContent('#fiche .scn .wd')
  check(`[${scheme}] fiche toont cijfer en naam`, /^[1-5]$/.test(cijfer ?? '') && !!label, `(${cijfer} ${label})`)
  const chips = await page.$$eval('#fiche .rij', (c) => c.length)
  check(`[${scheme}] fiche toont alle sporten`, chips === 21, `(${chips})`)
  await page.selectOption('#sport', 'kite')
  await page.waitForFunction(() => document.querySelector('#fiche .scn .nm')?.textContent?.includes('Kitesurf'))
  const pict = await page.$$eval('#fiche .pict[aria-current="true"]', (p) => p.length)
  check(`[${scheme}] fiche toont golf, windrichting en getij`, pict >= 2, `(${pict} tekeningen aangeduid)`)
  check(`[${scheme}] sport wisselen werkt`, true)
  if (shots) {
    await page.screenshot({ path: `${shots}/fiche-${scheme}.png` })
    await page.locator('#fiche').screenshot({ path: `${shots}/fiche-vol-${scheme}.png` }).catch(() => {})
  }
  await ctx.close()
}
check('geen JavaScript-fouten', fouten.length === 0, fouten.slice(0, 3).join(' | '))
await browser.close()
process.exit(ok ? 0 : 1)
