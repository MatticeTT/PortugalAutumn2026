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
  const nDag = await page.$$eval('#datum option', (o) => o.length)
  check(`[${scheme}] enkel dag en uur, 10 dagen`, nDag >= 9 && !(await page.$('#sport')), `(${nDag})`)
  const breed = await page.evaluate(() => document.documentElement.scrollWidth)
  check(`[${scheme}] geen horizontale scroll op 400 px`, breed <= 400, `(${breed}px)`)
  if (shots) await page.screenshot({ path: `${shots}/kaart-${scheme}.png` })
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
  const rijen = await page.$$eval('#fiche .dag th', (els) => els.map((e) => e.textContent))
  const uren = await page.$$eval('#fiche .dag a[data-i]', (els) => els.length)
  check(`[${scheme}] fiche: de dag met WAVE, WIND en getij`, ['WAVE', 'WIND', 'getij'].every((r) => rijen.includes(r)) && uren >= 20, `(${uren} uren)`)
  const plan = await page.$$eval('#fiche .wanneer li', (els) => els.map((e) => e.textContent.replace(/\s+/g, ' ').trim()))
  check(`[${scheme}] fiche: golfsurfen, windsurfen, wind-golven, stille waters`, plan.length === 4, `(${plan.join(' | ')})`)
  if (shots) {
    await page.screenshot({ path: `${shots}/fiche-${scheme}.png` })
    await page.locator('#fiche').screenshot({ path: `${shots}/fiche-vol-${scheme}.png` }).catch(() => {})
  }
  await ctx.close()
}
check('geen JavaScript-fouten', fouten.length === 0, fouten.slice(0, 3).join(' | '))
await browser.close()
process.exit(ok ? 0 : 1)
