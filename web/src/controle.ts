// Controlescherm voor de stranddata (rekenmodel v2, "Controles op de stranddata").
import './style.css'

interface Rij {
  id: string; naam: string; district: string; kust: number; venster: number[][]
  blokkerend: string[]; nakijken: string[]; aandeel16?: number[]
}
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
const plat = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

async function start() {
  const { kompas, stranden } = (await (await fetch('data/controle.json', { cache: 'no-store' })).json()) as
    { kompas: string[]; stranden: Rij[] }
  const tabel = document.getElementById('lijst')!
  const zoek = document.getElementById('zoek') as HTMLInputElement
  const doel = decodeURIComponent(location.hash.slice(1))
  if (doel) zoek.value = stranden.find((s) => s.id === doel)?.naam ?? ''

  const cel = (a: number) => `<td class="aandeel" style="--a:${a}">${a ? a.toFixed(2).replace('.', ',') : '0'}</td>`
  const rij = (s: Rij) => `<tr id="${esc(s.id)}" class="${s.blokkerend.length ? 'blok' : s.nakijken.length ? 'kijk' : ''}">
    <td><b>${esc(s.naam)}</b><small>${esc(s.district)}</small></td><td>${s.kust}°</td>
    <td>${s.venster.length ? s.venster.map((v) => `${v[0]}–${v[1]}°`).join(', ') : '–'}</td>
    ${s.aandeel16 ? s.aandeel16.map(cel).join('') : `<td colspan="16"></td>`}
    <td>${esc([...s.blokkerend, ...s.nakijken].join('; '))}</td></tr>`

  const toon = () => {
    const f = (document.querySelector('input[name=f]:checked') as HTMLInputElement).value
    const q = plat(zoek.value.trim())
    const zicht = stranden.filter((s) => (f === 'alle' || (s as any)[f].length) && (!q || plat(`${s.naam} ${s.district}`).includes(q)))
    document.getElementById('teller')!.textContent = `${zicht.length} van ${stranden.length} stranden`
    tabel.innerHTML = `<tr><th>Strand</th><th>Kust</th><th>Venster</th>${kompas.map((k) => `<th>${k}</th>`).join('')}<th>Controle</th></tr>`
      + zicht.slice(0, 300).map(rij).join('')
  }
  zoek.addEventListener('input', toon)
  document.querySelectorAll('input[name=f]').forEach((r) => r.addEventListener('change', toon))
  toon()
}
start()
