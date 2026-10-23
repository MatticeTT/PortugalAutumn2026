// Waarden op één punt: tik of klik op de kaart. Zo kun je per coördinaat en per uur vergelijken met Windy.

import maplibregl from 'maplibre-gl'
import { lonVoor, sampleWave, sampleWind, type FieldSet, type WaveSample, type WindSample } from './field'
import { wavePower } from './particles'

const KOMPAS = ['N', 'NNO', 'NO', 'ONO', 'O', 'OZO', 'ZO', 'ZZO', 'Z', 'ZZW', 'ZW', 'WZW', 'W', 'WNW', 'NW', 'NNW']
const kompas = (deg: number) => KOMPAS[Math.round(deg / 22.5) % 16]
const BEAUFORT = [0.3, 1.6, 3.4, 5.5, 8, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7] // ondergrenzen in m/s, bft 1..12
const beaufort = (ms: number) => BEAUFORT.filter((g) => ms >= g).length

const fmt = (x: number, d = 1) => x.toLocaleString('nl-NL', { minimumFractionDigits: d, maximumFractionDigits: d })

export interface PointContext {
  wind: () => FieldSet
  swell: () => FieldSet | null
  windsea: () => FieldSet | null
  time: () => string // ISO-tijd van het getoonde tijdstip
  run: () => string
}

export function enablePointInfo(map: maplibregl.Map, ctx: PointContext) {
  const popup = new maplibregl.Popup({ className: 'punt', maxWidth: '260px', closeOnClick: true })
  const dateFmt = new Intl.DateTimeFormat('nl-NL', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

  async function show(lngLat: maplibregl.LngLat) {
    const lon = lngLat.wrap().lng, lat = lngLat.lat
    const onLand = map.queryRenderedFeatures(map.project(lngLat), { layers: ['land', 'land-buiten', 'land-fijn', 'land-osm'].filter((l) => map.getLayer(l)) }).length > 0
      && map.queryRenderedFeatures(map.project(lngLat), { layers: ['meren'] }).length === 0
    const sw = ctx.swell(), ws2 = ctx.windsea()
    const [w, g, z] = await Promise.all([ctx.wind().exactGrid(lon, lat), sw?.exactGrid(lon, lat), ws2?.exactGrid(lon, lat)])
    const ws: WindSample = { u: 0, v: 0 }
    const gs: WaveSample = { ex: 0, ny: 0, period: 0, height: 0 }
    const zs: WaveSample = { ex: 0, ny: 0, period: 0, height: 0 }
    const hasWind = sampleWind(w.grid, lonVoor(w.grid, lon), lat, ws)
    const hasWave = !onLand && !!g && sampleWave(g.grid, lonVoor(g.grid, lon), lat, gs)
    const hasSea = !onLand && !!z && sampleWave(z.grid, lonVoor(z.grid, lon), lat, zs)

    const rows: string[] = []
    if (hasWind) {
      const ms = Math.hypot(ws.u, ws.v)
      const from = ((Math.atan2(-ws.u, -ws.v) * 180) / Math.PI + 360) % 360
      rows.push(`<tr><th>Wind</th><td><b>${fmt(ms * 1.94384, 0)} kn</b> · ${fmt(ms)} m/s · ${beaufort(ms)} bft</td></tr>`,
        `<tr><th></th><td>uit ${kompas(from)} (${fmt(from, 0)}°)</td></tr>`)
    }
    const golf = (naam: string, x: WaveSample) => {
      const from = ((Math.atan2(-x.ex, -x.ny) * 180) / Math.PI + 360) % 360
      rows.push(`<tr><th>${naam}</th><td><b>${fmt(x.height)} m</b> · ${fmt(x.period, 0)} s · uit ${kompas(from)} (${fmt(from, 0)}°)</td></tr>`,
        `<tr><th></th><td>energie ${fmt(wavePower(x.height, x.period), 0)} kW/m</td></tr>`)
    }
    if (hasWave) golf('Deining', gs)
    if (hasSea) golf('Windzee', zs)
    if (!hasWave && !hasSea) rows.push(`<tr><th>Golven</th><td>${onLand ? 'land' : g ? 'geen' : 'na de horizon van het golfmodel'}</td></tr>`)
    const res = Math.min(w.deg, g?.deg ?? w.deg)
    popup.setLngLat(lngLat).setHTML(`
      <div class="punt-kop">${dateFmt.format(new Date(ctx.time()))}</div>
      <div class="punt-coord">${fmt(Math.abs(lat), 3)}° ${lat >= 0 ? 'N' : 'Z'}, ${fmt(Math.abs(lon), 3)}° ${lon >= 0 ? 'O' : 'W'}</div>
      <table>${rows.join('')}</table>
      <div class="punt-bron">wind: ECMWF, run ${ctx.run().replace('T', ' ').replace(':00Z', ' UTC')} · golven: Copernicus Marine · raster ${fmt(res, 2)}°<br>golven: significante hoogte en piekperiode per golfsysteem; vlak aan de kust aangevuld vanuit de dichtstbijzijnde zeecellen</div>`).addTo(map)
  }

  map.on('click', (e) => { show(e.lngLat).catch(() => {}) })
}
