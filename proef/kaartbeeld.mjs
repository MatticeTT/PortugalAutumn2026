// Controle van de kaart: onze kaart en de kaart van de eerste versie (OpenFreeMap liberty) op dezelfde plek, naast
// elkaar, op een telefoonscherm. Zo zie je of kust, stranden en wegen op elkaar passen. Beelden in proef/beeld.
import { chromium } from 'playwright'
const PLEKKEN = [['ericeira', [-9.415, 38.975], 12], ['rocha', [-8.535, 37.118], 12], ['castelejo', [-8.945, 37.10], 12],
  ['peniche', [-9.37, 39.355], 11], ['lagos', [-8.66, 37.10], 10], ['aveiro', [-8.75, 40.64], 10]]
const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] })
const ctx = await b.newContext({ viewport: { width: 390, height: 700 }, colorScheme: 'dark' })
const ons = await ctx.newPage()
ons.on('pageerror', (e) => console.log('FOUT', e.message))
await ons.goto('http://localhost:4300/', { waitUntil: 'load' }); await ons.waitForTimeout(4000)
await ons.getByText('Overslaan').click().catch(() => {})
const oud = await ctx.newPage()
await oud.setContent(`<html><head><link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script></head>
  <body style="margin:0"><div id="k" style="width:390px;height:700px"></div><script>
  window.k = new maplibregl.Map({ container: 'k', style: 'https://tiles.openfreemap.org/styles/liberty', center: [0, 0], zoom: 2 })
  </script></body></html>`)
await oud.waitForTimeout(4000)
for (const [naam, c, z] of PLEKKEN) {
  await ons.evaluate(([c, z]) => window.kaart.map.jumpTo({ center: c, zoom: z, padding: 0 }), [c, z])
  await oud.evaluate(([c, z]) => window.k.jumpTo({ center: c, zoom: z }), [c, z])
  await ons.waitForTimeout(9000)
  await ons.screenshot({ path: `proef/beeld/${naam}-ons.png` })
  await oud.screenshot({ path: `proef/beeld/${naam}-oud.png` })
}
await b.close()
