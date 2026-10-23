// Schermafdrukken van de kaart (stranden en wegen uit OpenFreeMap) op een telefoonscherm, voor controle.
import { chromium } from 'playwright'
const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] })
const p = await (await b.newContext({ viewport: { width: 390, height: 844 }, colorScheme: 'dark' })).newPage()
p.on('pageerror', (e) => console.log('FOUT', e.message))
p.on('requestfailed', (r) => r.url().includes('openfreemap') && console.log('MISLUKT', r.url()))
await p.goto('http://localhost:4300/', { waitUntil: 'load' }); await p.waitForTimeout(4000)
await p.getByText('Overslaan').click().catch(() => {})
for (const [naam, c, z] of [['ericeira', [-9.415, 38.97], 12], ['rocha', [-8.535, 37.12], 11], ['lagos', [-8.68, 37.11], 9]]) {
  await p.evaluate(([c, z]) => window.kaart.map.jumpTo({ center: c, zoom: z }), [c, z]); await p.waitForTimeout(9000)
  const n = await p.evaluate(() => ({ stranden: window.kaart.map.queryRenderedFeatures({ layers: ['stranden'] }).length, wegen: window.kaart.map.queryRenderedFeatures({ layers: ['wegen'] }).length }))
  console.log(naam, JSON.stringify(n))
  await p.screenshot({ path: `proef/beeld/${naam}.png` })
}
await b.close()
