// Vercel-functie: eigen activiteiten in de planning, gedeeld met iedereen die de site gebruikt.
// Opslag: Vercel Blob van dit project (token BLOB_READ_WRITE_TOKEN zet Vercel zelf, nooit in de code).
//   GET                      -> [{ id, dag, titel, van, tot, plek, foto, gemaakt }]
//   POST { dag, titel, van, tot, plek?, foto? (data-URL webp/jpeg) } -> de nieuwe activiteit
//   DELETE ?id=<id>          -> { ok: true }
// Elke activiteit is een eigen bestand (activiteiten/<id>.json), foto's staan in fotos/<id>.webp.
const { put, list, del } = require('@vercel/blob')

const MAP = 'activiteiten/'
const tekst = (x, n) => String(x ?? '').trim().slice(0, n)
const geldigDag = (d) => /^\d{4}-\d{2}-\d{2}$/.test(d)
const geldigUur = (u) => /^([01]\d|2[0-3]):[0-5]\d$/.test(u)

async function lees(req) {
  if (req.body && typeof req.body === 'object') return req.body
  const delen = []
  for await (const d of req) delen.push(d)
  return JSON.parse(Buffer.concat(delen).toString('utf8') || '{}')
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store')
  if (!process.env.BLOB_READ_WRITE_TOKEN) return res.status(501).json({ fout: 'opslag staat nog niet aan' })
  try {
    if (req.method === 'GET') {
      const uit = []
      let cursor
      do {
        const r = await list({ prefix: MAP, cursor, limit: 1000 })
        uit.push(...r.blobs)
        cursor = r.hasMore ? r.cursor : undefined
      } while (cursor)
      const items = await Promise.all(uit.map((b) => fetch(b.url).then((r) => r.json()).catch(() => null)))
      return res.status(200).json(items.filter(Boolean).sort((a, b) => (a.dag + a.van).localeCompare(b.dag + b.van)))
    }
    if (req.method === 'POST') {
      const b = await lees(req)
      const a = { id: `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`,
        dag: tekst(b.dag, 10), titel: tekst(b.titel, 80), van: tekst(b.van, 5), tot: tekst(b.tot, 5),
        plek: null, foto: null, gemaakt: new Date().toISOString() }
      if (!geldigDag(a.dag) || !a.titel || !geldigUur(a.van) || !geldigUur(a.tot)) return res.status(400).json({ fout: 'dag, wat, van en tot zijn nodig' })
      if (b.plek && Number.isFinite(b.plek.lat) && Number.isFinite(b.plek.lon)) a.plek = { naam: tekst(b.plek.naam, 160), lat: b.plek.lat, lon: b.plek.lon }
      const m = /^data:image\/(webp|jpeg|png);base64,(.+)$/.exec(String(b.foto ?? ''))
      if (m) {
        const bytes = Buffer.from(m[2], 'base64')
        if (bytes.length > 3 * 1024 * 1024) return res.status(413).json({ fout: 'foto te groot' })
        const f = await put(`fotos/${a.id}.${m[1] === 'jpeg' ? 'jpg' : m[1]}`, bytes, { access: 'public', contentType: `image/${m[1]}`, addRandomSuffix: false })
        a.foto = f.url
      }
      await put(`${MAP}${a.id}.json`, JSON.stringify(a), { access: 'public', contentType: 'application/json', addRandomSuffix: false })
      return res.status(200).json(a)
    }
    if (req.method === 'DELETE') {
      const id = tekst(new URL(req.url, 'http://x').searchParams.get('id'), 40)
      if (!/^[a-z0-9]+$/.test(id)) return res.status(400).json({ fout: 'id' })
      const r = await list({ prefix: `fotos/${id}.` })
      await del([...r.blobs.map((x) => x.url), ...(await list({ prefix: `${MAP}${id}.json` })).blobs.map((x) => x.url)])
      return res.status(200).json({ ok: true })
    }
    return res.status(405).json({ fout: 'methode' })
  } catch (e) {
    return res.status(502).json({ fout: String(e && e.message || e) })
  }
}
