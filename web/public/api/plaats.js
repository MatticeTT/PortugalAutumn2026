// Vercel-functie: plaatsen zoeken via Google Places (New), zodat ook hotels en vakantieappartementen gevonden worden.
// De sleutel staat alleen in de Vercel-omgevingsvariabele GOOGLE_PLACES_KEY, nooit in de code of op de site.
//   /api/plaats?q=one2&s=<sessie>   -> suggesties [{ id, titel, adres }]
//   /api/plaats?id=<placeId>&s=<sessie> -> { naam, lat, lon }
// Zonder sleutel antwoordt de functie 501; de site valt dan terug op OpenStreetMap (Photon).
const API = 'https://places.googleapis.com/v1'

module.exports = async (req, res) => {
  const sleutel = process.env.GOOGLE_PLACES_KEY
  res.setHeader('Cache-Control', 'no-store')
  if (!sleutel) return res.status(501).json({ fout: 'geen sleutel' })
  // Alleen voor deze site: andere herkomst weigeren.
  const herkomst = req.headers.origin || req.headers.referer || ''
  const host = req.headers['x-forwarded-host'] || req.headers.host || ''
  if (herkomst && !herkomst.includes(host)) return res.status(403).json({ fout: 'herkomst' })
  const url = new URL(req.url, 'http://x')
  const q = (url.searchParams.get('q') || '').slice(0, 120)
  const id = (url.searchParams.get('id') || '').slice(0, 300)
  const sessie = (url.searchParams.get('s') || '').slice(0, 64)
  try {
    if (id) {
      const r = await fetch(`${API}/places/${encodeURIComponent(id)}?languageCode=nl${sessie ? `&sessionToken=${encodeURIComponent(sessie)}` : ''}`, {
        headers: { 'X-Goog-Api-Key': sleutel, 'X-Goog-FieldMask': 'displayName,formattedAddress,location' } })
      const p = await r.json()
      if (!r.ok || !p.location) return res.status(502).json({ fout: p.error?.message || 'geen plaats' })
      return res.status(200).json({ naam: `${p.displayName?.text ?? ''}, ${p.formattedAddress ?? ''}`, lat: p.location.latitude, lon: p.location.longitude })
    }
    if (q.length < 2) return res.status(200).json([])
    const r = await fetch(`${API}/places:autocomplete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Key': sleutel },
      body: JSON.stringify({ input: q, sessionToken: sessie || undefined, includedRegionCodes: ['pt'], languageCode: 'nl',
        locationBias: { circle: { center: { latitude: 37.12, longitude: -8.5 }, radius: 50000 } } }),
    })
    const d = await r.json()
    if (!r.ok) return res.status(502).json({ fout: d.error?.message || 'google' })
    return res.status(200).json((d.suggestions ?? []).flatMap((s) => s.placePrediction ? [{
      id: s.placePrediction.placeId,
      titel: s.placePrediction.structuredFormat?.mainText?.text ?? s.placePrediction.text?.text ?? '',
      adres: s.placePrediction.structuredFormat?.secondaryText?.text ?? '',
    }] : []))
  } catch (e) {
    return res.status(502).json({ fout: String(e) })
  }
}
