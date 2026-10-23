// Knop dag/nacht in de balk. Zonder keuze volgt de site het toestel; een keuze blijft bewaard
// (localStorage "thema") en wordt al in de <head> toegepast, zodat de pagina niet eerst in het andere thema flitst.
const ZON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2.5M12 19.5V22M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8 6 18M18 6l1.8-1.8"/></svg>'
const MAAN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/></svg>'

const donker = () => document.documentElement.dataset.theme
  ? document.documentElement.dataset.theme === 'dark'
  : matchMedia('(prefers-color-scheme: dark)').matches

export function themaKnop(naWissel?: () => void) {
  const k = document.getElementById('thema')
  if (!k) return
  // De knop toont waar je naartoe gaat: in het donker een zon, bij dag een maan.
  const toon = () => {
    const d = donker()
    k.innerHTML = d ? ZON : MAAN
    k.setAttribute('aria-label', d ? 'Dagthema' : 'Nachtthema')
    k.title = d ? 'Dagthema' : 'Nachtthema'
  }
  toon()
  k.onclick = () => {
    const nieuw = donker() ? 'light' : 'dark'
    document.documentElement.dataset.theme = nieuw
    try { localStorage.setItem('thema', nieuw === 'light' ? 'licht' : 'donker') } catch { /* niet bewaard */ }
    toon()
    naWissel?.()
  }
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', toon)
}
