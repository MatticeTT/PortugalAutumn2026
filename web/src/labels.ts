// Plaatsnamen (Natural Earth) op een eigen canvas boven de kaart: wit met donkere rand, zoals Windy.
// Hertekend alleen als het beeld verandert; namen die elkaar zouden overlappen worden weggelaten.

import type { Map as MlMap } from 'maplibre-gl'

interface Place { naam: string; z: number; hoofdstad: number; lon: number; lat: number }

export class Labels {
  private canvas = document.createElement('canvas')
  private ctx = this.canvas.getContext('2d')!
  private places: Place[] = []
  private key = ''

  constructor(private map: MlMap) {
    Object.assign(this.canvas.style, { position: 'absolute', inset: '0', pointerEvents: 'none', zIndex: '1' })
    map.getContainer().appendChild(this.canvas)
    map.on('render', () => this.draw())
    map.on('resize', () => { this.key = ''; this.draw() })
  }

  async load(url: string) {
    const geo = await (await fetch(url)).json()
    this.places = geo.features.map((f: { geometry: { coordinates: [number, number] }; properties: Place }) => ({
      ...f.properties, lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1],
    }))
    this.key = ''
    this.draw()
  }

  private draw() {
    const m = this.map
    const c = m.getCenter()
    const key = `${c.lng.toFixed(5)},${c.lat.toFixed(5)},${m.getZoom().toFixed(3)},${m.getCanvas().clientWidth}`
    if (key === this.key) return
    this.key = key
    const el = m.getContainer()
    const w = el.clientWidth, h = el.clientHeight
    const dpr = window.devicePixelRatio || 1
    if (this.canvas.width !== Math.round(w * dpr) || this.canvas.height !== Math.round(h * dpr)) {
      this.canvas.width = Math.round(w * dpr)
      this.canvas.height = Math.round(h * dpr)
      this.canvas.style.width = `${w}px`
      this.canvas.style.height = `${h}px`
    }
    const ctx = this.ctx
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)
    // Natural Earth rekent in zoomniveaus van 256-px tegels; MapLibre in 512-px tegels: één niveau verschil.
    const zMax = m.getZoom() + 1.3
    const placed: [number, number, number, number][] = []
    ctx.textBaseline = 'middle'
    ctx.lineJoin = 'round'
    for (const p of this.places) {
      if (p.z > zMax) break // gesorteerd op z
      let lon = p.lon
      while (lon - c.lng > 180) lon -= 360
      while (lon - c.lng < -180) lon += 360
      const pt = m.project([lon, p.lat])
      if (pt.x < -50 || pt.y < -20 || pt.x > w + 50 || pt.y > h + 20) continue
      const big = p.hoofdstad || p.z <= 3
      ctx.font = `${big ? 600 : 500} ${big ? 13 : 12}px system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif`
      const tw = ctx.measureText(p.naam).width
      const box: [number, number, number, number] = [pt.x - 4, pt.y - 9, pt.x + 8 + tw + 4, pt.y + 9]
      if (placed.some((b) => b[0] < box[2] && b[2] > box[0] && b[1] < box[3] && b[3] > box[1])) continue
      placed.push(box)
      ctx.lineWidth = 3
      ctx.strokeStyle = 'rgba(10, 14, 18, 0.85)'
      ctx.strokeText(p.naam, pt.x + 7, pt.y)
      ctx.fillStyle = 'rgba(255, 255, 255, 0.92)'
      ctx.fillText(p.naam, pt.x + 7, pt.y)
      ctx.beginPath()
      ctx.arc(pt.x, pt.y, 2.2, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()
      ctx.fill()
      if (placed.length > 120) break
    }
  }
}
