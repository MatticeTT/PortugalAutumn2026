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
    return (await (await fetch('data/sport/ww.json' + v)).json())[k].slice(3 * i, 3 * i + 3)
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
  await ctx.close()
}
check('geen JavaScript-fouten', fouten.length === 0, fouten.slice(0, 3).join(' | '))
await browser.close()
process.exit(ok ? 0 : 1)
