// Neaps rekent offline: de TICON-4-constanten zitten in @neaps/tide-database.
import test from 'node:test'
import assert from 'node:assert/strict'
import { findStation } from 'neaps'

test('Lagos: hoog- en laagwater wisselen af, getijslag past bij springtij/doodtij', () => {
  const s = findStation('ticon/lagos_algarve-723a-prt-uhslc_rq')
  const { extremes } = s.getExtremesPrediction({
    start: new Date('2026-10-01T00:00:00Z'), end: new Date('2026-10-31T00:00:00Z'), datum: 'MSL',
  })
  assert.ok(extremes.length > 100)
  for (let i = 1; i < extremes.length; i++) assert.notEqual(extremes[i].high, extremes[i - 1].high)
  const range = extremes.slice(1).map((e, i) => Math.abs(e.level - extremes[i].level))
  assert.ok(Math.max(...range) > 2.5 && Math.max(...range) < 4.5, `max ${Math.max(...range)}`)
  assert.ok(Math.min(...range) > 0.5 && Math.min(...range) < 2.0, `min ${Math.min(...range)}`)
})
