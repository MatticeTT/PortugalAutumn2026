// Geanimeerde wind- en golflijntjes als MapLibre custom layer (WebGL).
//
// De deeltjes leven in Web Mercator-coördinaten (0..1), zodat ze bij pannen en zoomen met de kaart
// meeschuiven; de matrix van MapLibre zet ze in hetzelfde frame op het scherm als de basiskaart.
// Snelheden zijn in schermpixels per seconde, zodat de animatie op elk zoomniveau even vlot oogt.

import type { CustomLayerInterface, Map as MlMap } from 'maplibre-gl'
type mat4 = Parameters<CustomLayerInterface['render']>[1]
import type { FieldSet, WaveSample, WindSample } from './field'

// Wind
const WIND_TRAIL = 10 // punten in het staartje (kop meegerekend)
const WIND_TRAIL_DT = 1 / 16 // seconden tussen twee staartpunten
const WIND_PX_PER_MS = 5 // schermsnelheid in px/s per m/s wind
const WIND_WIDTH = 1.1 // css px
const WIND_DENSITY = 120 // één deeltje per zoveel css px²
const WIND_MAX = 8000
// Golven
const WAVE_PTS = 7 // punten langs een golfkam
const WAVE_PX_PER_S = 2.4 // schermsnelheid in px/s per seconde golfperiode
const WAVE_WIDTH = 1.6
const WAVE_DENSITY = 2000
const WAVE_MAX = 2600

const VERT = `
attribute vec4 a_vert; // x, y (mercator), alfa, zijde (-1..1 dwars op de lijn)
uniform mat4 u_matrix;
varying float v_alpha;
varying float v_side;
void main() {
  v_alpha = a_vert.z;
  v_side = a_vert.w;
  gl_Position = u_matrix * vec4(a_vert.xy, 0.0, 1.0);
}`

const FRAG = `
precision mediump float;
uniform vec3 u_color;
varying float v_alpha;
varying float v_side;
void main() {
  float a = v_alpha * (1.0 - smoothstep(0.35, 1.0, abs(v_side)));
  gl_FragColor = vec4(u_color * a, a);
}`

const mercX = (lon: number) => (lon + 180) / 360
const mercY = (lat: number) => {
  const s = Math.sin((Math.max(-85.06, Math.min(85.06, lat)) * Math.PI) / 180)
  return 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)
}
const lonOf = (x: number) => x * 360 - 180
const latOf = (y: number) => (Math.atan(Math.sinh(Math.PI * (1 - 2 * y))) * 180) / Math.PI

interface Batch {
  buf: WebGLBuffer
  idx: WebGLBuffer
  data: Float32Array
  count: number // aantal indices om te tekenen
}

export class ParticleLayer implements CustomLayerInterface {
  readonly id = 'deeltjes'
  readonly type = 'custom' as const
  readonly renderingMode = '2d' as const

  wind: FieldSet | null = null
  wave: FieldSet | null = null
  showWind = true
  showWaves = true

  private map!: MlMap
  private gl!: WebGLRenderingContext
  private prog!: WebGLProgram
  private uMatrix!: WebGLUniformLocation
  private uColor!: WebGLUniformLocation
  private aVert = 0
  private windBatch!: Batch
  private waveBatch!: Batch
  private last = 0
  private lastZoom = -1
  private view = { x0: 0, x1: 1, y0: 0, y1: 1, world: 512, area: 1 }

  // Wind: kop + ringbuffer met eerdere posities
  private wx = new Float64Array(WIND_MAX)
  private wy = new Float64Array(WIND_MAX)
  private wHist = new Float64Array(WIND_MAX * (WIND_TRAIL - 1) * 2)
  private wRing = 0
  private wTimer = 0
  private wAge = new Float32Array(WIND_MAX)
  private wLife = new Float32Array(WIND_MAX)
  private wSpeed = new Float32Array(WIND_MAX)
  private wCount = 0
  // Golven
  private gx = new Float64Array(WAVE_MAX)
  private gy = new Float64Array(WAVE_MAX)
  private gAge = new Float32Array(WAVE_MAX)
  private gLife = new Float32Array(WAVE_MAX)
  private gCount = 0

  private trailPx = new Float64Array(WIND_TRAIL * 2)
  private tailFade = Float32Array.from({ length: WIND_TRAIL }, (_, t) => Math.pow(1 - t / (WIND_TRAIL - 1), 1.3))
  private waveScale = 1 // kammen iets langer bij inzoomen
  private ws: WindSample = { u: 0, v: 0 }
  private gs: WaveSample = { ex: 0, ny: 0, period: 0, height: 0 }
  private gs2: WaveSample = { ex: 0, ny: 0, period: 0, height: 0 }

  onAdd(map: MlMap, gl: WebGLRenderingContext) {
    this.map = map
    this.gl = gl
    const sh = (type: number, src: string) => {
      const s = gl.createShader(type)!
      gl.shaderSource(s, src)
      gl.compileShader(s)
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) ?? 'shader')
      return s
    }
    const p = gl.createProgram()!
    gl.attachShader(p, sh(gl.VERTEX_SHADER, VERT))
    gl.attachShader(p, sh(gl.FRAGMENT_SHADER, FRAG))
    gl.linkProgram(p)
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p) ?? 'program')
    this.prog = p
    this.uMatrix = gl.getUniformLocation(p, 'u_matrix')!
    this.uColor = gl.getUniformLocation(p, 'u_color')!
    this.aVert = gl.getAttribLocation(p, 'a_vert')
    // 32-bits indices: in WebGL2 standaard, in WebGL1 via de extensie.
    if (!(typeof WebGL2RenderingContext !== 'undefined' && gl instanceof WebGL2RenderingContext)) gl.getExtension('OES_element_index_uint')
    this.windBatch = this.makeBatch(WIND_MAX, WIND_TRAIL)
    this.waveBatch = this.makeBatch(WAVE_MAX, WAVE_PTS)
  }

  /** Buffers voor strips van `pts` punten (twee hoekpunten per punt), indices liggen vast. */
  private makeBatch(max: number, pts: number): Batch {
    const gl = this.gl
    const idx = new Uint32Array(max * (pts - 1) * 6)
    let k = 0
    for (let p = 0; p < max; p++) {
      const b = p * pts * 2
      for (let s = 0; s < pts - 1; s++) {
        const v = b + s * 2
        idx.set([v, v + 1, v + 2, v + 1, v + 3, v + 2], k)
        k += 6
      }
    }
    const ib = gl.createBuffer()!
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib)
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW)
    const data = new Float32Array(max * pts * 2 * 4)
    const buf = gl.createBuffer()!
    gl.bindBuffer(gl.ARRAY_BUFFER, buf)
    gl.bufferData(gl.ARRAY_BUFFER, data.byteLength, gl.DYNAMIC_DRAW)
    return { buf, idx: ib, data, count: 0 }
  }

  onRemove() {
    const gl = this.gl
    for (const b of [this.windBatch, this.waveBatch]) {
      gl.deleteBuffer(b.buf)
      gl.deleteBuffer(b.idx)
    }
    gl.deleteProgram(this.prog)
  }

  /** Zichtbaar gebied in mercator, met een kleine rand. */
  private updateView() {
    const b = this.map.getBounds()
    const c = this.map.getCanvas()
    const w = c.clientWidth, h = c.clientHeight
    const x0 = mercX(b.getWest()), x1 = mercX(b.getEast())
    const y0 = mercY(b.getNorth()), y1 = mercY(b.getSouth())
    const mx = (x1 - x0) * 0.03, my = (y1 - y0) * 0.03
    this.view = { x0: x0 - mx, x1: x1 + mx, y0: y0 - my, y1: y1 + my, world: 512 * Math.pow(2, this.map.getZoom()), area: w * h }
  }

  private inView(x: number, y: number) {
    const v = this.view
    return x >= v.x0 && x <= v.x1 && y >= v.y0 && y <= v.y1
  }

  /** Wis alle deeltjes en begin opnieuw (bv. na een nieuw tijdstip niet nodig; wel na een sprong). */
  reset() {
    this.wCount = 0
    this.gCount = 0
  }

  // ---- Wind ----

  private spawnWind(i: number, fresh: boolean) {
    const v = this.view
    const x = v.x0 + Math.random() * (v.x1 - v.x0)
    const y = Math.max(0, Math.min(1, v.y0 + Math.random() * (v.y1 - v.y0)))
    this.wx[i] = x
    this.wy[i] = y
    const n = WIND_TRAIL - 1
    for (let k = 0; k < n; k++) {
      this.wHist[(i * n + k) * 2] = x
      this.wHist[(i * n + k) * 2 + 1] = y
    }
    this.wLife[i] = 1 + Math.random() * 2.5
    this.wAge[i] = fresh ? Math.random() * this.wLife[i] : 0
    this.wSpeed[i] = 0
  }

  private stepWind(dt: number) {
    const f = this.wind!
    const target = Math.min(WIND_MAX, Math.max(500, Math.round(this.view.area / WIND_DENSITY)))
    for (let i = this.wCount; i < target; i++) this.spawnWind(i, true)
    this.wCount = target

    const n = WIND_TRAIL - 1
    this.wTimer += dt
    if (this.wTimer >= WIND_TRAIL_DT) {
      this.wTimer %= WIND_TRAIL_DT
      this.wRing = (this.wRing + n - 1) % n // nieuwste staartpunt op wRing
      for (let i = 0; i < this.wCount; i++) {
        this.wHist[(i * n + this.wRing) * 2] = this.wx[i]
        this.wHist[(i * n + this.wRing) * 2 + 1] = this.wy[i]
      }
    }
    const k = (WIND_PX_PER_MS * dt) / this.view.world
    const s = this.ws
    for (let i = 0; i < this.wCount; i++) {
      this.wAge[i] += dt
      if (this.wAge[i] > this.wLife[i] || !this.inView(this.wx[i], this.wy[i]) || !f.wind(lonOf(this.wx[i]), latOf(this.wy[i]), s)) {
        this.spawnWind(i, false)
        continue
      }
      // Mercator is hoekgetrouw: oost = +x, noord = -y, met dezelfde schaal in beide richtingen.
      this.wx[i] += s.u * k
      this.wy[i] -= s.v * k
      this.wSpeed[i] = Math.sqrt(s.u * s.u + s.v * s.v)
    }
  }

  private buildWind(): number {
    const d = this.windBatch.data
    const n = WIND_TRAIL - 1
    const half = (WIND_WIDTH + 1) / 2 / this.view.world // +1 px voor de zachte rand
    const px = this.trailPx
    const tail = this.tailFade
    let o = 0
    for (let i = 0; i < this.wCount; i++) {
      px[0] = this.wx[i]
      px[1] = this.wy[i]
      const hb = i * n * 2
      for (let t = 0, r = this.wRing; t < n; t++, r = r + 1 === n ? 0 : r + 1) {
        px[t * 2 + 2] = this.wHist[hb + r * 2]
        px[t * 2 + 3] = this.wHist[hb + r * 2 + 1]
      }
      const age = this.wAge[i], life = this.wLife[i]
      const fade = Math.max(0, Math.min(1, age / 0.35, (life - age) / 0.7))
      const a0 = fade * Math.min(0.9, 0.3 + this.wSpeed[i] / 14)
      for (let t = 0; t < WIND_TRAIL; t++) {
        const p = t > 0 ? t - 1 : 0, q = t < WIND_TRAIL - 1 ? t + 1 : t
        const dx = px[p * 2] - px[q * 2], dy = px[p * 2 + 1] - px[q * 2 + 1]
        const len2 = dx * dx + dy * dy
        const f = len2 > 0 ? half / Math.sqrt(len2) : 0
        const nx = -dy * f, ny = dx * f
        const a = a0 * tail[t]
        const x = px[t * 2], y = px[t * 2 + 1]
        d[o++] = x + nx; d[o++] = y + ny; d[o++] = a; d[o++] = 1
        d[o++] = x - nx; d[o++] = y - ny; d[o++] = a; d[o++] = -1
      }
    }
    return this.wCount * (WIND_TRAIL - 1) * 6
  }

  // ---- Golven ----

  private spawnWave(i: number, fresh: boolean) {
    const v = this.view
    const f = this.wave!
    let x = 0, y = 0
    for (let t = 0; t < 6; t++) {
      x = v.x0 + Math.random() * (v.x1 - v.x0)
      y = Math.max(0, Math.min(1, v.y0 + Math.random() * (v.y1 - v.y0)))
      if (f.wave(lonOf(x), latOf(y), this.gs)) break
    }
    this.gx[i] = x
    this.gy[i] = y
    this.gLife[i] = 2.5 + Math.random() * 3
    this.gAge[i] = fresh ? Math.random() * this.gLife[i] : 0
  }

  private stepWaves(dt: number) {
    const f = this.wave!
    const target = Math.min(WAVE_MAX, Math.max(120, Math.round(this.view.area / WAVE_DENSITY)))
    for (let i = this.gCount; i < target; i++) this.spawnWave(i, true)
    this.gCount = target
    const k = (WAVE_PX_PER_S * dt) / this.view.world
    for (let i = 0; i < this.gCount; i++) {
      this.gAge[i] += dt
      if (this.gAge[i] > this.gLife[i] || !this.inView(this.gx[i], this.gy[i])) {
        this.spawnWave(i, false)
        continue
      }
      if (!f.wave(lonOf(this.gx[i]), latOf(this.gy[i]), this.gs)) continue // op land: niet bewegen, niet tekenen
      const sp = Math.max(this.gs.period, 3) * k
      this.gx[i] += this.gs.ex * sp
      this.gy[i] -= this.gs.ny * sp
    }
  }

  private buildWaves(): number {
    const d = this.waveBatch.data
    const f = this.wave!
    const w = this.view.world
    const half = (WAVE_WIDTH + 1) / 2 / w
    let o = 0
    let drawn = 0
    for (let i = 0; i < this.gCount; i++) {
      const s = this.gs
      if (!f.wave(lonOf(this.gx[i]), latOf(this.gy[i]), s)) continue
      const age = this.gAge[i], life = this.gLife[i]
      const fade = Math.max(0, Math.min(1, age / 0.8, (life - age) / 1.2))
      const a0 = fade * Math.min(0.85, 0.3 + s.height / 4)
      // Looprichting op het scherm (y naar beneden) en de kam er dwars op.
      const dx = s.ex, dy = -s.ny
      const qx = -dy, qy = dx
      const L = (Math.min(20, 6 + 3 * s.height) * this.waveScale) / w // halve kamlengte
      for (let t = 0; t < WAVE_PTS; t++) {
        const u = (t / (WAVE_PTS - 1)) * 2 - 1
        const bow = -0.15 * L * u * u // kam licht gebogen: midden loopt voorop
        const x = this.gx[i] + qx * u * L + dx * bow
        const y = this.gy[i] + qy * u * L + dy * bow
        // Raaklijn van de gebogen kam voor de dikte.
        let tx = qx - dx * 0.3 * u, ty = qy - dy * 0.3 * u
        const tl = Math.sqrt(tx * tx + ty * ty)
        tx /= tl; ty /= tl
        const onSea = t === (WAVE_PTS - 1) / 2 || f.wave(lonOf(x), latOf(y), this.gs2)
        const a = onSea ? a0 * Math.sqrt(1 - u * u * 0.85) : 0
        const nx = -ty * half, ny = tx * half
        d[o++] = x + nx; d[o++] = y + ny; d[o++] = a; d[o++] = 1
        d[o++] = x - nx; d[o++] = y - ny; d[o++] = a; d[o++] = -1
      }
      drawn++
    }
    return drawn * (WAVE_PTS - 1) * 6
  }

  // ---- Tekenen ----

  private draw(b: Batch, verts: number, pts: number, count: number, matrix: Float32List, color: [number, number, number]) {
    if (!count) return
    const gl = this.gl
    gl.bindBuffer(gl.ARRAY_BUFFER, b.buf)
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, b.data.subarray(0, verts * pts * 2 * 4))
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, b.idx)
    gl.enableVertexAttribArray(this.aVert)
    gl.vertexAttribPointer(this.aVert, 4, gl.FLOAT, false, 16, 0)
    gl.uniformMatrix4fv(this.uMatrix, false, matrix)
    gl.uniform3fv(this.uColor, color)
    gl.drawElements(gl.TRIANGLES, count, gl.UNSIGNED_INT, 0)
  }

  render(gl: WebGLRenderingContext | WebGL2RenderingContext, matrix: mat4) {
    const now = performance.now() / 1000
    const dt = this.last ? Math.min(0.05, now - this.last) : 0
    this.last = now
    this.updateView()

    // Na zoomen kloppen de oude staartjes niet meer met de schermsnelheid: inkorten.
    const z = this.map.getZoom()
    if (Math.abs(z - this.lastZoom) > 1e-3) {
      const n = WIND_TRAIL - 1
      for (let i = 0; i < this.wCount; i++)
        for (let k = 0; k < n; k++) {
          this.wHist[(i * n + k) * 2] = this.wx[i]
          this.wHist[(i * n + k) * 2 + 1] = this.wy[i]
        }
      this.lastZoom = z
      this.waveScale = 1 + Math.max(0, Math.min(4, z - 3)) * 0.2
    }

    const wind = this.showWind && this.wind?.coarse
    const wave = this.showWaves && this.wave?.coarse
    if (!wind && !wave) return

    // MapLibre gebruikt in WebGL2 vertex array objects: die van de kaart niet aanpassen.
    if ('bindVertexArray' in gl) gl.bindVertexArray(null)
    gl.useProgram(this.prog)
    gl.disable(gl.DEPTH_TEST)
    gl.disable(gl.STENCIL_TEST)
    gl.disable(gl.CULL_FACE)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)

    if (wave) {
      this.stepWaves(dt)
      const n = this.buildWaves()
      this.draw(this.waveBatch, n / ((WAVE_PTS - 1) * 6), WAVE_PTS, n, matrix as Float32List, [0.55, 0.86, 1.0])
    }
    if (wind) {
      this.stepWind(dt)
      const n = this.buildWind()
      this.draw(this.windBatch, this.wCount, WIND_TRAIL, n, matrix as Float32List, [1, 1, 1])
    }
    gl.disableVertexAttribArray(this.aVert)
    gl.bindBuffer(gl.ARRAY_BUFFER, null)
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, null)
    this.map.triggerRepaint()
  }
}
