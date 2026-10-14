// Geanimeerde wind- en golflijntjes als MapLibre custom layer (WebGL).
//
// Werkwijze zoals earth.nullschool, Windy en de WebGL-windkaart van Mapbox: elk deeltje tekent per frame
// alleen het stukje dat het net heeft afgelegd, in een eigen beeldbuffer (textuur). Die buffer wordt elk
// frame een beetje doorzichtiger. Zo ontstaan vanzelf lange, vloeiende staarten die uitdoven.
//
// Bij pannen en zoomen wordt de buffer van het vorige frame verschoven en geschaald naar het nieuwe beeld,
// zodat de staarten met de kaart meebewegen in plaats van te verdwijnen of uit te smeren.
//
// De deeltjes zelf leven in Web Mercator-coördinaten (0..1) en bewegen met een vaste schermsnelheid, zodat
// de animatie op elk zoomniveau even vlot oogt.

import type { CustomLayerInterface, Map as MlMap } from 'maplibre-gl'
import type { FieldSet, WaveSample, WindSample } from './field'

type Mat4 = Parameters<CustomLayerInterface['render']>[1]

// ---- Instellingen ----
// Wind: dunne witte lijntjes met lange staart.
const WIND = {
  density: 520, // één deeltje per zoveel css px²
  max: 6000,
  pxPerMs: 7, // schermsnelheid in px/s per m/s wind
  width: 1.15, // css px
  fade: 0.955, // per frame van 1/60 s: hoeveel van de staart blijft staan
  minLife: 1.6,
  maxLife: 4.5,
}
// Golven: korte, brede kammen dwars op de looprichting; de vervaging maakt er blokjes met een vage achterkant van.
const WAVE = {
  density: 380,
  max: 6000,
  pxPerS: 1.6, // schermsnelheid in px/s per seconde golfperiode
  width: 2.4,
  fade: 0.86,
  minLife: 2,
  maxLife: 5,
}

const SEG_VERT = `
attribute vec4 a_vert; // x, y (mercator), alfa, zijde (-1..1 dwars op de lijn)
uniform mat4 u_matrix;
varying float v_alpha;
varying float v_side;
void main() {
  v_alpha = a_vert.z;
  v_side = a_vert.w;
  gl_Position = u_matrix * vec4(a_vert.xy, 0.0, 1.0);
}`
const SEG_FRAG = `
precision mediump float;
uniform vec3 u_color;
varying float v_alpha;
varying float v_side;
void main() {
  float a = v_alpha * (1.0 - smoothstep(0.4, 1.0, abs(v_side)));
  gl_FragColor = vec4(u_color * a, a);
}`
const QUAD_VERT = `
attribute vec2 a_pos;
void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }`
// Vorig frame, verschoven naar het huidige beeld en doorzichtiger gemaakt.
const FADE_FRAG = `
precision highp float;
uniform sampler2D u_prev;
uniform vec2 u_size;
uniform vec3 u_affine; // vorige pixel = a * huidige pixel + (bx, by)
uniform float u_fade;
void main() {
  vec2 p = gl_FragCoord.xy * u_affine.x + u_affine.yz;
  vec2 uv = p / u_size;
  vec4 c = vec4(0.0);
  if (uv.x >= 0.0 && uv.y >= 0.0 && uv.x <= 1.0 && uv.y <= 1.0) c = texture2D(u_prev, uv);
  // Afronding naar 8 bit zou zwakke resten laten hangen: daarom een vaste stap eraf.
  gl_FragColor = max(c * u_fade - vec4(1.5 / 255.0), vec4(0.0));
}`
const DRAW_FRAG = `
precision mediump float;
uniform sampler2D u_tex;
uniform vec2 u_size;
uniform float u_opacity;
void main() { gl_FragColor = texture2D(u_tex, gl_FragCoord.xy / u_size) * u_opacity; }`

// Afwisselen: zoveel seconden per laag, waarvan de laatste ALT_FADE als zachte overgang.
const ALT_HOLD = 6
const ALT_FADE = 1.2

const mercX = (lon: number) => (lon + 180) / 360
const mercY = (lat: number) => {
  const s = Math.sin((Math.max(-85.06, Math.min(85.06, lat)) * Math.PI) / 180)
  return 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)
}
const lonOf = (x: number) => x * 360 - 180
const latOf = (y: number) => (Math.atan(Math.sinh(Math.PI * (1 - 2 * y))) * 180) / Math.PI

interface View { x0: number; x1: number; y0: number; y1: number; cx: number; cy: number; world: number; area: number }

/** Twee texturen die om beurt vorig en huidig frame zijn. */
class Trails {
  tex: WebGLTexture[] = []
  fbo: WebGLFramebuffer[] = []
  w = 0
  h = 0
  cur = 0
  empty = true

  constructor(private gl: WebGLRenderingContext) {}

  resize(w: number, h: number) {
    if (w === this.w && h === this.h) return
    const gl = this.gl
    this.dispose()
    this.w = w
    this.h = h
    for (let i = 0; i < 2; i++) {
      const t = gl.createTexture()!
      gl.bindTexture(gl.TEXTURE_2D, t)
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null)
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
      const f = gl.createFramebuffer()!
      gl.bindFramebuffer(gl.FRAMEBUFFER, f)
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0)
      gl.clearColor(0, 0, 0, 0)
      gl.clear(gl.COLOR_BUFFER_BIT)
      this.tex.push(t)
      this.fbo.push(f)
    }
    this.empty = true
  }

  clear() {
    if (this.empty || !this.fbo.length) return
    const gl = this.gl
    for (const f of this.fbo) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, f)
      gl.clearColor(0, 0, 0, 0)
      gl.clear(gl.COLOR_BUFFER_BIT)
    }
    this.empty = true
  }

  dispose() {
    for (const t of this.tex) this.gl.deleteTexture(t)
    for (const f of this.fbo) this.gl.deleteFramebuffer(f)
    this.tex = []
    this.fbo = []
    this.w = this.h = 0
  }
}

function program(gl: WebGLRenderingContext, vs: string, fs: string) {
  const sh = (type: number, src: string) => {
    const s = gl.createShader(type)!
    gl.shaderSource(s, src)
    gl.compileShader(s)
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) ?? 'shader')
    return s
  }
  const p = gl.createProgram()!
  gl.attachShader(p, sh(gl.VERTEX_SHADER, vs))
  gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs))
  gl.linkProgram(p)
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p) ?? 'program')
  const cache = new Map<string, WebGLUniformLocation>()
  const u = (n: string) => {
    let l = cache.get(n)
    if (!l) cache.set(n, (l = gl.getUniformLocation(p, n)!))
    return l
  }
  return { p, u, attr: (n: string) => gl.getAttribLocation(p, n) }
}

export class ParticleLayer implements CustomLayerInterface {
  readonly id = 'golven'
  readonly type = 'custom' as const
  readonly renderingMode = '2d' as const

  wind: FieldSet | null = null
  wave: FieldSet | null = null
  showWind = true
  showWaves = true
  /** Met beide lagen aan: om beurt wind en golven tonen in plaats van tegelijk. */
  alternate = false
  private altStart = performance.now() / 1000

  private map!: MlMap
  private gl!: WebGLRenderingContext
  private seg!: ReturnType<typeof program>
  private fade!: ReturnType<typeof program>
  private draw!: ReturnType<typeof program>
  private quad!: WebGLBuffer
  private segBuf!: WebGLBuffer
  private segData = new Float32Array(Math.max(WIND.max, WAVE.max) * 6 * 4)
  private windTrails!: Trails
  private waveTrails!: Trails
  private last = 0
  private dpr = 1
  private prev: View | null = null
  private view: View = { x0: 0, x1: 1, y0: 0, y1: 1, cx: 0.5, cy: 0.5, world: 512, area: 1 }

  // Wind
  private wx = new Float64Array(WIND.max)
  private wy = new Float64Array(WIND.max)
  private wpx = new Float64Array(WIND.max) // positie in het vorige frame
  private wpy = new Float64Array(WIND.max)
  private wAge = new Float32Array(WIND.max)
  private wLife = new Float32Array(WIND.max)
  private wSpeed = new Float32Array(WIND.max)
  private wCount = 0
  // Golven
  private gx = new Float64Array(WAVE.max)
  private gy = new Float64Array(WAVE.max)
  private gAge = new Float32Array(WAVE.max)
  private gLife = new Float32Array(WAVE.max)
  private gEx = new Float32Array(WAVE.max) // looprichting (oost, noord)
  private gNy = new Float32Array(WAVE.max)
  private gH = new Float32Array(WAVE.max)
  private gSea = new Uint8Array(WAVE.max)
  private gCount = 0

  private ws: WindSample = { u: 0, v: 0 }
  private gs: WaveSample = { ex: 0, ny: 0, period: 0, height: 0 }

  onAdd(map: MlMap, gl: WebGLRenderingContext) {
    this.map = map
    this.gl = gl
    this.seg = program(gl, SEG_VERT, SEG_FRAG)
    this.fade = program(gl, QUAD_VERT, FADE_FRAG)
    this.draw = program(gl, QUAD_VERT, DRAW_FRAG)
    this.quad = gl.createBuffer()!
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quad)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW)
    this.segBuf = gl.createBuffer()!
    gl.bindBuffer(gl.ARRAY_BUFFER, this.segBuf)
    gl.bufferData(gl.ARRAY_BUFFER, this.segData.byteLength, gl.DYNAMIC_DRAW)
    this.windTrails = new Trails(gl)
    this.waveTrails = new Trails(gl)
  }

  onRemove() {
    const gl = this.gl
    this.windTrails.dispose()
    this.waveTrails.dispose()
    gl.deleteBuffer(this.quad)
    gl.deleteBuffer(this.segBuf)
    for (const p of [this.seg, this.fade, this.draw]) gl.deleteProgram(p.p)
  }

  private updateView() {
    const b = this.map.getBounds()
    const c = this.map.getCenter()
    const cv = this.map.getCanvas()
    this.prev = this.view
    this.view = {
      x0: mercX(b.getWest()), x1: mercX(b.getEast()), y0: mercY(b.getNorth()), y1: mercY(b.getSouth()),
      cx: mercX(c.lng), cy: mercY(c.lat),
      world: 512 * Math.pow(2, this.map.getZoom()), area: cv.clientWidth * cv.clientHeight,
    }
  }

  /** Gebied waarover de deeltjes het laatst gelijkmatig verdeeld zijn. */
  private dist: View | null = null

  /**
   * Na uitzoomen of een grote verplaatsing zitten de deeltjes opeengepakt in het oude beeld. Een deel ervan
   * (evenredig met het nieuwe, lege gebied) springt dan naar een willekeurige plek in het nieuwe beeld.
   */
  private redistribute() {
    const v = this.view, d = this.dist
    if (!d) { this.dist = v; return }
    const ix = Math.max(0, Math.min(v.x1, d.x1) - Math.max(v.x0, d.x0))
    const iy = Math.max(0, Math.min(v.y1, d.y1) - Math.max(v.y0, d.y0))
    const covered = (ix * iy) / ((v.x1 - v.x0) * (v.y1 - v.y0))
    if (covered > 0.85) return
    const p = 1 - covered
    for (let i = 0; i < this.wCount; i++) if (Math.random() < p) this.spawnWind(i, true)
    for (let i = 0; i < this.gCount; i++) if (Math.random() < p) this.spawnWave(i, true)
    this.dist = v
  }

  private inView(x: number, y: number) {
    const v = this.view
    return x >= v.x0 && x <= v.x1 && y >= v.y0 && y <= v.y1
  }

  private rx = 0
  private ry = 0
  private randomPos() {
    const v = this.view
    this.rx = v.x0 + Math.random() * (v.x1 - v.x0)
    this.ry = Math.max(0, Math.min(1, v.y0 + Math.random() * (v.y1 - v.y0)))
  }

  // ---- Wind ----

  private spawnWind(i: number, fresh: boolean) {
    this.randomPos()
    this.wx[i] = this.wpx[i] = this.rx
    this.wy[i] = this.wpy[i] = this.ry
    this.wLife[i] = WIND.minLife + Math.random() * (WIND.maxLife - WIND.minLife)
    this.wAge[i] = fresh ? Math.random() * this.wLife[i] : 0
  }

  private stepWind(dt: number) {
    const f = this.wind!
    const target = Math.min(WIND.max, Math.max(300, Math.round(this.view.area / WIND.density)))
    for (let i = this.wCount; i < target; i++) this.spawnWind(i, true)
    this.wCount = target
    const k = (WIND.pxPerMs * dt) / this.view.world
    const s = this.ws
    for (let i = 0; i < this.wCount; i++) {
      this.wpx[i] = this.wx[i]
      this.wpy[i] = this.wy[i]
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

  /** Per deeltje één kort lijnstuk: van de vorige naar de huidige positie. */
  private buildWind(): number {
    const d = this.segData
    const half = (WIND.width + 1) / 2 / this.view.world // +1 px voor de zachte rand
    let o = 0
    let n = 0
    for (let i = 0; i < this.wCount; i++) {
      const ax = this.wpx[i], ay = this.wpy[i], bx = this.wx[i], by = this.wy[i]
      const dx = bx - ax, dy = by - ay
      const len2 = dx * dx + dy * dy
      if (len2 === 0) continue
      const age = this.wAge[i], life = this.wLife[i]
      const fade = Math.max(0, Math.min(1, age / 0.4, (life - age) / 0.8))
      // Zwakke wind iets zachter, harde wind helder.
      const a = fade * Math.min(0.95, 0.35 + this.wSpeed[i] / 12)
      const f = half / Math.sqrt(len2)
      o = quad(d, o, ax, ay, bx, by, -dy * f, dx * f, a)
      n++
    }
    return n
  }

  // ---- Golven ----

  private spawnWave(i: number, fresh: boolean) {
    const f = this.wave!
    let sea = false
    for (let t = 0; t < 8 && !sea; t++) {
      this.randomPos()
      sea = f.wave(lonOf(this.rx), latOf(this.ry), this.gs)
    }
    this.gx[i] = this.rx
    this.gy[i] = this.ry
    this.gSea[i] = 0 // pas tekenen na de eerste stap
    this.gLife[i] = WAVE.minLife + Math.random() * (WAVE.maxLife - WAVE.minLife)
    this.gAge[i] = fresh ? Math.random() * this.gLife[i] : 0
  }

  private stepWaves(dt: number) {
    const f = this.wave!
    const target = Math.min(WAVE.max, Math.max(200, Math.round(this.view.area / WAVE.density)))
    for (let i = this.gCount; i < target; i++) this.spawnWave(i, true)
    this.gCount = target
    const k = (WAVE.pxPerS * dt) / this.view.world
    const s = this.gs
    for (let i = 0; i < this.gCount; i++) {
      this.gAge[i] += dt
      if (this.gAge[i] > this.gLife[i] || !this.inView(this.gx[i], this.gy[i])) {
        this.spawnWave(i, false)
        continue
      }
      if (!f.wave(lonOf(this.gx[i]), latOf(this.gy[i]), s)) {
        this.gSea[i] = 0 // op land of buiten het golfmodel: niet tekenen
        continue
      }
      this.gSea[i] = 1
      this.gEx[i] = s.ex
      this.gNy[i] = s.ny
      this.gH[i] = s.height
      const sp = Math.max(s.period, 3) * k
      this.gx[i] += s.ex * sp
      this.gy[i] -= s.ny * sp
    }
  }

  /** Per golf een korte kam dwars op de looprichting, op de huidige positie. */
  private buildWaves(): number {
    const d = this.segData
    const w = this.view.world
    // Uitgezoomd kleinere kammen, anders overheersen ze de wind.
    const zs = Math.max(0.55, Math.min(1, (this.map.getZoom() - 0.5) / 3))
    const half = (WAVE.width * zs + 1) / 2 / w
    let o = 0
    let n = 0
    for (let i = 0; i < this.gCount; i++) {
      if (!this.gSea[i]) continue
      const age = this.gAge[i], life = this.gLife[i]
      const h = this.gH[i]
      const fade = Math.max(0, Math.min(1, age / 0.6, (life - age) / 1))
      // Hogere golven: langere en fellere kammen.
      const a = fade * Math.min(0.9, 0.3 + h / 4) * (0.6 + 0.4 * zs)
      const L = (Math.min(6, 2.6 + 0.9 * h) * zs) / w
      // Looprichting op het scherm (y naar beneden); de kam ligt er dwars op.
      const dx = this.gEx[i], dy = -this.gNy[i]
      const qx = -dy * L, qy = dx * L
      const cx = this.gx[i], cy = this.gy[i]
      o = quad(d, o, cx - qx, cy - qy, cx + qx, cy + qy, dx * half, dy * half, a)
      n++
    }
    return n
  }

  // ---- Tekenen ----

  private bindQuad(prog: ReturnType<typeof program>) {
    const gl = this.gl
    const loc = prog.attr('a_pos')
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quad)
    gl.enableVertexAttribArray(loc)
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 8, 0)
    return loc
  }

  /** Eén laag: vorig beeld vervagen en verschuiven, dan de nieuwe stukjes erbovenop. */
  private paint(t: Trails, fadePerFrame: number, segs: number, matrix: Mat4, color: [number, number, number], dt: number) {
    const gl = this.gl
    const prev = t.cur, next = 1 - t.cur
    gl.bindFramebuffer(gl.FRAMEBUFFER, t.fbo[next])
    gl.viewport(0, 0, t.w, t.h)

    // 1. vorig frame, verschoven naar het nieuwe beeld en doorzichtiger
    const p = this.prev ?? this.view, v = this.view
    const W0 = p.world * this.dpr, W1 = v.world * this.dpr
    const a = W0 / W1
    const bx = t.w / 2 - (a * t.w) / 2 + (v.cx - p.cx) * W0
    const by = t.h / 2 - (a * t.h) / 2 - (v.cy - p.cy) * W0
    gl.disable(gl.BLEND)
    gl.useProgram(this.fade.p)
    const loc = this.bindQuad(this.fade)
    gl.activeTexture(gl.TEXTURE0)
    gl.bindTexture(gl.TEXTURE_2D, t.tex[prev])
    gl.uniform1i(this.fade.u('u_prev'), 0)
    gl.uniform2f(this.fade.u('u_size'), t.w, t.h)
    gl.uniform3f(this.fade.u('u_affine'), a, bx, by)
    gl.uniform1f(this.fade.u('u_fade'), Math.pow(fadePerFrame, dt * 60))
    gl.drawArrays(gl.TRIANGLES, 0, 6)
    gl.disableVertexAttribArray(loc)

    // 2. nieuwe stukjes
    if (segs) {
      gl.enable(gl.BLEND)
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
      gl.useProgram(this.seg.p)
      const sl = this.seg.attr('a_vert')
      gl.bindBuffer(gl.ARRAY_BUFFER, this.segBuf)
      gl.bufferSubData(gl.ARRAY_BUFFER, 0, this.segData.subarray(0, segs * 6 * 4))
      gl.enableVertexAttribArray(sl)
      gl.vertexAttribPointer(sl, 4, gl.FLOAT, false, 16, 0)
      gl.uniformMatrix4fv(this.seg.u('u_matrix'), false, matrix as Float32List)
      gl.uniform3fv(this.seg.u('u_color'), color)
      gl.drawArrays(gl.TRIANGLES, 0, segs * 6)
      gl.disableVertexAttribArray(sl)
    }
    t.cur = next
    t.empty = false
  }

  prerender(gl: WebGLRenderingContext | WebGL2RenderingContext, matrix: Mat4) {
    const now = performance.now() / 1000
    const dt = this.last ? Math.min(0.05, now - this.last) : 1 / 60
    this.last = now
    this.updateView()
    this.dpr = gl.drawingBufferWidth / Math.max(1, this.map.getCanvas().clientWidth)

    // Over de datumgrens springt het middelpunt een hele wereld: dan opnieuw beginnen.
    if (this.prev && Math.abs(this.view.cx - this.prev.cx) > 0.5) {
      this.prev = this.view
      this.windTrails.clear()
      this.waveTrails.clear()
      this.wCount = this.gCount = 0
    }

    if (this.wave?.coarse || this.wind?.coarse) this.redistribute()

    if ('bindVertexArray' in gl) gl.bindVertexArray(null) // de VAO's van MapLibre niet aanpassen
    gl.disable(gl.DEPTH_TEST)
    gl.disable(gl.STENCIL_TEST)
    gl.disable(gl.CULL_FACE)
    const w = gl.drawingBufferWidth, h = gl.drawingBufferHeight

    if (this.showWaves && this.wave?.coarse) {
      this.waveTrails.resize(w, h)
      this.stepWaves(dt)
      this.paint(this.waveTrails, WAVE.fade, this.buildWaves(), matrix, [0.88, 0.96, 1], dt)
    } else {
      this.waveTrails.clear()
      this.gCount = 0
    }
    if (this.showWind && this.wind?.coarse) {
      this.windTrails.resize(w, h)
      this.stepWind(dt)
      this.paint(this.windTrails, WIND.fade, this.buildWind(), matrix, [1, 1, 1], dt)
    } else {
      this.windTrails.clear()
      this.wCount = 0
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
    gl.viewport(0, 0, w, h)
  }

  /** Afwisselen opnieuw laten beginnen met wind. */
  restartAlternation() {
    this.altStart = performance.now() / 1000
  }

  /** Zichtbaarheid van golven en wind (0..1). Beide lagen blijven doorrekenen, zodat een wissel direct vol oogt. */
  private opacities(): [number, number] {
    if (!this.alternate || !this.showWind || !this.showWaves) return [1, 1]
    const t = (performance.now() / 1000 - this.altStart) % (2 * ALT_HOLD)
    const ramp = (x: number) => Math.max(0, Math.min(1, x / ALT_FADE))
    // Eerst wind, dan golven; elke overgang duurt ALT_FADE seconden.
    const wind = t < ALT_HOLD ? 1 - ramp(t - (ALT_HOLD - ALT_FADE)) : ramp(t - (2 * ALT_HOLD - ALT_FADE))
    const s = (x: number) => x * x * (3 - 2 * x)
    return [s(1 - wind), s(wind)]
  }

  /**
   * Eén beeldbuffer op de kaart leggen. De golven liggen onder de landlaag: MapLibre tekent land in een eerdere,
   * ondoorzichtige ronde met dieptebuffer, zodat de diepetest golven op land precies langs de kustlijn wegsnijdt.
   */
  drawTrails(gl: WebGLRenderingContext | WebGL2RenderingContext, kind: 'wind' | 'wave') {
    const t = kind === 'wind' ? this.windTrails : this.waveTrails
    const op = this.opacities()[kind === 'wind' ? 1 : 0]
    if (!t || t.empty || op <= 0) return
    if ('bindVertexArray' in gl) gl.bindVertexArray(null)
    if (kind === 'wind') gl.disable(gl.DEPTH_TEST) // wind ligt bovenop alles
    gl.disable(gl.STENCIL_TEST)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
    gl.useProgram(this.draw.p)
    const loc = this.bindQuad(this.draw)
    gl.activeTexture(gl.TEXTURE0)
    gl.uniform1i(this.draw.u('u_tex'), 0)
    gl.uniform2f(this.draw.u('u_size'), gl.drawingBufferWidth, gl.drawingBufferHeight)
    gl.uniform1f(this.draw.u('u_opacity'), op)
    gl.bindTexture(gl.TEXTURE_2D, t.tex[t.cur])
    gl.drawArrays(gl.TRIANGLES, 0, 6)
    gl.disableVertexAttribArray(loc)
    gl.bindBuffer(gl.ARRAY_BUFFER, null)
  }

  /** Deze laag (onder het land) tekent de golven en houdt de animatie gaande. */
  render(gl: WebGLRenderingContext | WebGL2RenderingContext) {
    this.drawTrails(gl, 'wave')
    if ((this.showWind && this.wind) || (this.showWaves && this.wave) || !this.windTrails.empty || !this.waveTrails.empty) this.map.triggerRepaint()
  }

  /** Aparte laag bovenop de kaart voor de wind, die ook over land loopt. */
  windLayer(): CustomLayerInterface {
    return {
      id: 'wind',
      type: 'custom',
      renderingMode: '2d',
      render: (gl) => this.drawTrails(gl, 'wind'),
    }
  }
}

/** Rechthoek van a naar b, halve breedte (nx, ny), als twee driehoeken: x, y, alfa, zijde per hoekpunt. */
function quad(d: Float32Array, o: number, ax: number, ay: number, bx: number, by: number, nx: number, ny: number, a: number) {
  d[o++] = ax + nx; d[o++] = ay + ny; d[o++] = a; d[o++] = 1
  d[o++] = ax - nx; d[o++] = ay - ny; d[o++] = a; d[o++] = -1
  d[o++] = bx + nx; d[o++] = by + ny; d[o++] = a; d[o++] = 1
  d[o++] = ax - nx; d[o++] = ay - ny; d[o++] = a; d[o++] = -1
  d[o++] = bx - nx; d[o++] = by - ny; d[o++] = a; d[o++] = -1
  d[o++] = bx + nx; d[o++] = by + ny; d[o++] = a; d[o++] = 1
  return o
}
