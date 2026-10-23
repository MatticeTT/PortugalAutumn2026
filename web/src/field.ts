// Wind- en golfvelden: PNG's laden, decoderen en bemonsteren op lengte/breedte.
// Codering: zie pipeline/build.py.

export interface Manifest {
  run: string
  source: string
  ext: string
  /** waves: of er deining is voor dit tijdstip, windsea: of er windzee is; *Fine: met fijne tegels. */
  times: { h: number; time: string; coarseDeg: number; fine: boolean; waves?: boolean; wavesFine?: boolean; windsea?: boolean; windseaFine?: boolean; wavesRegio?: boolean }[]
  /** Fijne tegels voor de rijen 0 .. rows-1 (vanaf 90 noord); zuidelijker alleen het wereldraster. */
  fine: { deg: number; tileDeg: number; tilePx: number; rows: number; cols: number }
  /** Deining rond Portugal uit IBI (1/36 graad), dezelfde golven als het kompas: <uur>/swell-regio.webp. */
  regio?: { lon0: number; lat0: number; deg: number; w: number; h: number } | null
  encoding: { windMax: number; waveHMax: number; wavePeriodMax: number }
}

/** wind van ECMWF; deining (swell) en windzee (windsea) van Copernicus */
export type Kind = 'wind' | 'swell' | 'windsea'

/** Een regelmatig raster: lon0/lat0 is de linkerbovenhoek (celmiddelpunt), stapgrootte deg. */
export interface Grid {
  lon0: number
  lat0: number
  deg: number
  width: number
  height: number
  wrap: boolean // kolom width volgt weer op kolom 0 (wereldraster)
  a: Float32Array // wind: u (m/s)      golf: looprichting oost (eenheid)
  b: Float32Array // wind: v (m/s)      golf: looprichting noord (eenheid)
  c?: Float32Array // golf: periode (s)
  d?: Float32Array // golf: hoogte (m)
  sea?: Uint8Array // golf: 1 = zee
}

export async function loadPixels(url: string): Promise<{ data: Uint8ClampedArray; width: number; height: number }> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url}: ${res.status}`)
  const bmp = await createImageBitmap(await res.blob(), { premultiplyAlpha: 'none', colorSpaceConversion: 'none' })
  const canvas = typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(bmp.width, bmp.height) : Object.assign(document.createElement('canvas'), { width: bmp.width, height: bmp.height })
  const ctx = canvas.getContext('2d', { willReadFrequently: true }) as CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D
  ctx.drawImage(bmp, 0, 0)
  const img = ctx.getImageData(0, 0, bmp.width, bmp.height)
  bmp.close()
  return { data: img.data, width: img.width, height: img.height }
}

export function decodeWind(px: Uint8ClampedArray, n: number, max: number): { u: Float32Array; v: Float32Array } {
  const u = new Float32Array(n)
  const v = new Float32Array(n)
  const dec = (byte: number) => {
    const s = byte / 127.5 - 1
    return Math.sign(s) * s * s * max
  }
  for (let i = 0; i < n; i++) {
    u[i] = dec(px[i * 4])
    v[i] = dec(px[i * 4 + 1])
  }
  return { u, v }
}

export function decodeWave(px: Uint8ClampedArray, n: number, hMax: number, tMax: number) {
  const ex = new Float32Array(n)
  const ny = new Float32Array(n)
  const per = new Float32Array(n)
  const hs = new Float32Array(n)
  const sea = new Uint8Array(n)
  for (let i = 0; i < n; i++) {
    const hb = px[i * 4 + 2]
    if (hb === 0) continue
    const x = px[i * 4] / 127.5 - 1
    const y = px[i * 4 + 1] / 127.5 - 1
    const len = Math.hypot(x, y) || 1
    ex[i] = x / len
    ny[i] = y / len
    per[i] = Math.max(0, ((len - 0.3) / 0.7) * tMax)
    const s = (hb - 1) / 254
    hs[i] = s * s * hMax
    sea[i] = 1
  }
  return { ex, ny, per, hs, sea }
}

async function loadGrid(url: string, kind: Kind, m: Manifest, geo: Omit<Grid, 'a' | 'b' | 'width' | 'height'>): Promise<Grid> {
  const { data, width, height } = await loadPixels(url)
  const n = width * height
  if (kind === 'wind') {
    const { u, v } = decodeWind(data, n, m.encoding.windMax)
    return { ...geo, width, height, a: u, b: v }
  }
  const w = decodeWave(data, n, m.encoding.waveHMax, m.encoding.wavePeriodMax)
  return { ...geo, width, height, a: w.ex, b: w.ny, c: w.per, d: w.hs, sea: w.sea }
}

/** Lengte in het bereik van het raster: wereldraster rondlopend, tegels 0..360, de regio rond Portugal -180..180. */
export function lonVoor(g: Grid, lon: number) {
  if (g.wrap) return lon
  return g.lon0 < 0 ? ((((lon + 180) % 360) + 360) % 360) - 180 : ((lon % 360) + 360) % 360
}

/** Index en gewichten van de vier buren (in een gedeeld object, om geheugenallocatie te vermijden). */
const C = { i00: 0, i10: 0, i01: 0, i11: 0, tx: 0, ty: 0 }
function cell(g: Grid, lon: number, lat: number): boolean {
  let fx = (lon - g.lon0) / g.deg
  const fy = (g.lat0 - lat) / g.deg
  if (g.wrap) {
    fx %= g.width
    if (fx < 0) fx += g.width
  }
  if (!(fy >= 0 && fy <= g.height - 1 && fx >= 0) || (!g.wrap && fx > g.width - 1)) return false
  let x0 = fx | 0
  let y0 = fy | 0
  if (y0 > g.height - 2) y0 = g.height - 2
  if (!g.wrap && x0 > g.width - 2) x0 = g.width - 2
  if (x0 > g.width - 1) x0 = g.width - 1
  const x1 = g.wrap && x0 === g.width - 1 ? 0 : x0 + 1
  const r0 = y0 * g.width
  C.i00 = r0 + x0
  C.i10 = r0 + x1
  C.i01 = r0 + g.width + x0
  C.i11 = r0 + g.width + x1
  C.tx = fx - x0
  C.ty = fy - y0
  return true
}

export interface WindSample { u: number; v: number }
export interface WaveSample { ex: number; ny: number; period: number; height: number }

export function sampleWind(g: Grid, lon: number, lat: number, out: WindSample): boolean {
  if (!cell(g, lon, lat)) return false
  const c = C
  const w00 = (1 - c.tx) * (1 - c.ty), w10 = c.tx * (1 - c.ty), w01 = (1 - c.tx) * c.ty, w11 = c.tx * c.ty
  out.u = g.a[c.i00] * w00 + g.a[c.i10] * w10 + g.a[c.i01] * w01 + g.a[c.i11] * w11
  out.v = g.b[c.i00] * w00 + g.b[c.i10] * w10 + g.b[c.i01] * w01 + g.b[c.i11] * w11
  return true
}

/** Alleen op zee: de dichtstbijzijnde cel moet zee zijn; er wordt alleen tussen zeecellen geïnterpoleerd. */
export function sampleWave(g: Grid, lon: number, lat: number, out: WaveSample): boolean {
  if (!cell(g, lon, lat)) return false
  const c = C
  const sea = g.sea!
  const near = c.ty < 0.5 ? (c.tx < 0.5 ? c.i00 : c.i10) : c.tx < 0.5 ? c.i01 : c.i11
  if (!sea[near]) return false
  let w00 = (1 - c.tx) * (1 - c.ty) * sea[c.i00], w10 = c.tx * (1 - c.ty) * sea[c.i10]
  let w01 = (1 - c.tx) * c.ty * sea[c.i01], w11 = c.tx * c.ty * sea[c.i11]
  const sum = w00 + w10 + w01 + w11
  w00 /= sum; w10 /= sum; w01 /= sum; w11 /= sum
  const ex = g.a[c.i00] * w00 + g.a[c.i10] * w10 + g.a[c.i01] * w01 + g.a[c.i11] * w11
  const ny = g.b[c.i00] * w00 + g.b[c.i10] * w10 + g.b[c.i01] * w01 + g.b[c.i11] * w11
  const len = Math.sqrt(ex * ex + ny * ny)
  if (len < 1e-3) return false
  out.ex = ex / len
  out.ny = ny / len
  out.period = g.c![c.i00] * w00 + g.c![c.i10] * w10 + g.c![c.i01] * w01 + g.c![c.i11] * w11
  out.height = g.d![c.i00] * w00 + g.d![c.i10] * w10 + g.d![c.i01] * w01 + g.d![c.i11] * w11
  return true
}

/** Of er voor dit tijdstip gegevens van deze soort zijn (golven stoppen na de horizon van het golfmodel). */
export function heeft(t: Manifest['times'][number], kind: Kind) {
  return kind === 'wind' || (kind === 'swell' ? !!t.waves : !!t.windsea)
}

/**
 * Velden van één soort voor één tijdstip: het grove wereldraster plus fijne tegels die voor het zichtbare
 * gebied worden bijgeladen. Bemonsteren gebruikt de fijne tegel als die er is, anders het grove raster.
 */
export class FieldSet {
  coarse: Grid | null = null
  /** Fijne deining rond Portugal (IBI); heeft voorrang op alle andere rasters waar ze zee heeft. */
  regio: Grid | null = null
  private heeftRegio: boolean
  private tiles: (Grid | 'loading' | 'error' | undefined)[] = []
  private fineOn = false

  readonly hour: number
  private hasFine: boolean
  private coarseDeg: number

  constructor(readonly kind: Kind, t: Manifest['times'][number], private m: Manifest, private base: string, private onTile: () => void) {
    this.hour = t.h
    this.hasFine = kind === 'wind' ? t.fine : kind === 'swell' ? !!t.wavesFine : !!t.windseaFine
    this.coarseDeg = t.coarseDeg
    this.heeftRegio = kind === 'swell' && !!t.wavesRegio && !!m.regio
  }

  private url(name: string) {
    return `${this.base}/${String(this.hour).padStart(3, '0')}/${name}.${this.m.ext}`
  }

  async loadCoarse(): Promise<this> {
    if (!this.coarse) {
      this.coarse = await loadGrid(this.url(this.kind), this.kind, this.m, { lon0: 0, lat0: 90, deg: this.coarseDeg, wrap: true })
    }
    if (this.heeftRegio && !this.regio) {
      const r = this.m.regio!
      // Klein bestand: altijd mee laden. Lukt het niet, dan gewoon het wereldraster.
      this.regio = await loadGrid(this.url(`${this.kind}-regio`), this.kind, this.m, { lon0: r.lon0, lat0: r.lat0, deg: r.deg, wrap: false })
        .catch(() => null)
    }
    return this
  }

  private inRegio(lon: number, lat: number) {
    const g = this.regio
    if (!g) return false
    const l = lonVoor(g, lon)
    return l >= g.lon0 && l <= g.lon0 + (g.width - 1) * g.deg && lat <= g.lat0 && lat >= g.lat0 - (g.height - 1) * g.deg
  }

  private rij(lat: number) {
    return Math.max(0, Math.floor((90 - lat) / this.m.fine.tileDeg))
  }

  /** Fijne tegels voor het gebied [west, zuid, oost, noord] (lengte mag buiten -180..180 liggen). */
  useFine(on: boolean, west = 0, south = 0, east = 0, north = 0) {
    this.fineOn = on && this.hasFine
    if (!this.fineOn) return
    const f = this.m.fine
    const r0 = Math.max(0, Math.floor((90 - north) / f.tileDeg)), r1 = Math.min(f.rows - 1, Math.floor((90 - south) / f.tileDeg))
    const c0 = Math.floor(west / f.tileDeg), c1 = Math.floor(east / f.tileDeg)
    if (c1 - c0 >= f.cols) return // te ver uitgezoomd voor tegels
    for (let r = r0; r <= r1; r++) {
      for (let cc = c0; cc <= c1; cc++) {
        const c = ((cc % f.cols) + f.cols) % f.cols
        const k = r * f.cols + c
        if (this.tiles[k]) continue
        this.tiles[k] = 'loading'
        loadGrid(this.url(`${this.kind}/${r}_${c}`), this.kind, this.m, { lon0: c * f.tileDeg, lat0: 90 - r * f.tileDeg, deg: f.deg, wrap: false })
          .then((g) => { this.tiles[k] = g; this.onTile() })
          .catch(() => { this.tiles[k] = 'error' })
      }
    }
  }

  /**
   * Het fijnste raster dat er voor dit punt bestaat, zo nodig eerst geladen (voor de waarde op één punt). Fijne
   * tegels zijn er tot een bepaald uur; daarna is het wereldraster het fijnste.
   */
  async exactGrid(lon: number, lat: number): Promise<{ grid: Grid; deg: number }> {
    await this.loadCoarse()
    if (this.inRegio(lon, lat)) return { grid: this.regio!, deg: this.regio!.deg }
    if (this.hasFine && this.rij(lat) < this.m.fine.rows) {
      const f = this.m.fine
      const l = ((lon % 360) + 360) % 360
      const c = Math.min(f.cols - 1, Math.floor(l / f.tileDeg))
      const r = Math.min(f.rows - 1, Math.max(0, Math.floor((90 - lat) / f.tileDeg)))
      const k = r * f.cols + c
      let t = this.tiles[k]
      if (!t || t === 'loading') {
        try {
          t = await loadGrid(this.url(`${this.kind}/${r}_${c}`), this.kind, this.m, { lon0: c * f.tileDeg, lat0: 90 - r * f.tileDeg, deg: f.deg, wrap: false })
          this.tiles[k] = t
        } catch {
          t = 'error'
        }
      }
      if (typeof t === 'object') return { grid: t, deg: f.deg }
    }
    return { grid: this.coarse!, deg: this.coarseDeg }
  }

  /** Het fijnste raster dat op dit punt beschikbaar is. */
  grid(lon: number, lat: number): Grid | null {
    if (this.inRegio(lon, lat)) return this.regio
    if (this.fineOn && this.rij(lat) < this.m.fine.rows) {
      const f = this.m.fine
      const l = ((lon % 360) + 360) % 360
      const c = Math.min(f.cols - 1, Math.floor(l / f.tileDeg))
      const r = Math.min(f.rows - 1, Math.max(0, Math.floor((90 - lat) / f.tileDeg)))
      const t = this.tiles[r * f.cols + c]
      if (t && typeof t === 'object') return t
    }
    return this.coarse
  }

  wind(lon: number, lat: number, out: WindSample): boolean {
    const g = this.grid(lon, lat)
    if (!g) return false
    return sampleWind(g, lonVoor(g, lon), lat, out)
  }

  wave(lon: number, lat: number, out: WaveSample): boolean {
    const g = this.grid(lon, lat)
    if (!g) return false
    return sampleWave(g, lonVoor(g, lon), lat, out)
  }
}
