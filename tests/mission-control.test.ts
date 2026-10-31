import { describe, expect, test } from 'bun:test'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createMission, advance, blockers, fingerprint, saveMission, loadMission } from '../plugins/mission-control/lib/mission'

const bundle = { spec: 'Export exact rows; reject changed source.', plan: 'Add failure harness, then repair.', technical: 'Checkpoint byte offsets.', ux: 'CLI errors preserve prior files.' }
const candidate = { repo: 'acme/app', pr: 7, head: 'a'.repeat(40), base: 'b'.repeat(40), risk: 'low' as const }
function built(risk = 'low') {
	let state = createMission('T-test', 'Recover interrupted CSV exports')
	state = advance(state, { type: 'design', bundle, criteria: ['Exact rows', 'Preserve previous data'] })
	state = advance(state, { type: 'approve-design', digest: state.design!.digest })
	state = advance(state, { type: 'defense', digest: state.design!.digest, record: 'Offsets preserve committed rows; changed inputs fail closed.' })
	state = advance(state, { type: 'build' })
	return advance(state, { type: 'candidate', candidate: { ...candidate, risk } })
}
function verified(risk = 'low') {
	let state = built(risk)
	for (const gate of [1, 2]) state = advance(state, { type: 'review', gate, fingerprint: fingerprint(state), passed: true, reviewer: 'T-reviewer', record: 'Read the diff and recovery tests; no findings.' })
	return advance(state, { type: 'evidence', fingerprint: fingerprint(state), results: ['Exact rows: subprocess assertions passed', 'Preservation: before/after bytes equal'], tryIt: 'Run the interruption CLI journey.', value: 'No duplicate-row repair needed.' })
}

describe('mission public lifecycle', () => {
	test('owner approval precedes defense and build; concrete criteria are mandatory', () => {
		const start = createMission('T-test', 'Build an export')
		expect(() => advance(start, { type: 'build' })).toThrow()
		expect(() => advance(start, { type: 'design', bundle, criteria: [] })).toThrow()
		const designed = advance(start, { type: 'design', bundle, criteria: ['Exact rows'] })
		expect(() => advance(designed, { type: 'defense', digest: designed.design!.digest, record: 'A proposal' })).toThrow('approval')
		expect(() => advance(designed, { type: 'approve-design', digest: 'stale' })).toThrow('stale')
		const approved = advance(designed, { type: 'approve-design', digest: designed.design!.digest })
		expect(() => advance(approved, { type: 'build' })).toThrow('defense')
		expect(built().mode).toBe('auto')
	})

	test('paused work and completed entry gates cannot be reentered with stale evidence', () => {
		const state = verified()
		for (const action of [
			{ type: 'build' },
			{ type: 'defense', digest: state.design!.digest, record: 'Changed defense' },
			{ type: 'approve-design', digest: state.design!.digest },
		]) expect(() => advance(state, action as any)).toThrow()
		const paused = advance(state, { type: 'pause', reason: 'Customer changed requirements' })
		expect(() => advance(paused, { type: 'candidate', candidate })).toThrow('paused')
		expect(() => advance(createMission('T-test', 'Outcome'), { type: 'design', bundle, criteria: ['same', 'same'] })).toThrow()
	})

	test('design changes invalidate approval, defense and candidate evidence', () => {
		const original = verified()
		const changed = advance(original, { type: 'design', bundle: { ...bundle, ux: 'A new web interface' }, criteria: ['Exact rows'] })
		expect(changed.approvedDesign).toBeUndefined()
		expect(changed.candidate).toBeUndefined()
		expect(() => advance(changed, { type: 'build' })).toThrow()
		expect(original.design!.bundle.ux).toBe(bundle.ux)
	})

	test('two reviews and presented evidence are required, including for low risk', () => {
		let state = built()
		expect(() => advance(state, { type: 'review', gate: 2, fingerprint: fingerprint(state), passed: true, reviewer: 'T-reviewer', record: 'Review' })).toThrow('first review')
		expect(blockers(state).length).toBeGreaterThan(0)
		state = verified()
		expect(blockers(state)).toContain('Delivery evidence has not been presented')
		state = advance(state, { type: 'presented', fingerprint: fingerprint(state) })
		expect(blockers(state)).toEqual([])
	})

	test('risk and owner-selected ask mode require candidate-bound acknowledgment', () => {
		for (const risk of ['medium', 'high', 'unknown']) {
			let state = verified(risk)
			state = advance(state, { type: 'presented', fingerprint: fingerprint(state) })
			if (risk === 'medium') expect(blockers(state)).toEqual([])
			else expect(blockers(state).length).toBeGreaterThan(0)
			if (risk === 'high') {
				state = advance(state, { type: 'approve-merge', fingerprint: fingerprint(state) })
				expect(blockers(state)).toEqual([])
			}
		}
		let state = advance(verified(), { type: 'mode', mode: 'ask' })
		state = advance(state, { type: 'presented', fingerprint: fingerprint(state) })
		expect(blockers(state)).toContain('Owner merge acknowledgment required')
		expect(() => advance(state, { type: 'approve-merge', fingerprint: 'old' })).toThrow('stale')
	})

	test('head or base changes discard reviews; high risk cannot be downgraded', () => {
		const old = verified('high')
		const unknown = advance(old, { type: 'candidate', candidate: { ...candidate, head: 'e'.repeat(40), risk: 'unknown' } })
		expect(unknown.candidate!.risk).toBe('unknown')
		expect(blockers(unknown)).toContain('Risk is unknown')
		expect(advance(unknown, { type: 'candidate', candidate }).candidate!.risk).toBe('high')
		const changed = advance(old, { type: 'candidate', candidate: { ...candidate, head: 'c'.repeat(40), risk: 'low' } })
		expect(changed.candidate!.risk).toBe('high')
		expect(changed.reviews).toEqual([])
		expect(() => advance(changed, { type: 'review', gate: 1, fingerprint: fingerprint(old), passed: true, reviewer: 'T-other', record: 'stale review' })).toThrow('stale')
		const rebased = advance(old, { type: 'candidate', candidate: { ...candidate, base: 'c'.repeat(40), risk: 'high' } })
		expect(rebased.evidence).toBeUndefined()
		expect(() => advance(rebased, { type: 'review', gate: 1, fingerprint: fingerprint(rebased), passed: true, reviewer: 'T-test', record: 'self review' })).toThrow('independent')
	})

	test('requesting merge is not completion; pause and failures remain visible', () => {
		let state = verified()
		state = advance(state, { type: 'presented', fingerprint: fingerprint(state) })
		state = advance(state, { type: 'merge-requested', fingerprint: fingerprint(state) })
		expect(state.phase).toBe('merge-pending')
		state = advance(state, { type: 'pause', reason: 'Connection lost; inspect remote before retry' })
		expect(blockers(state)).toContain('Paused: Connection lost; inspect remote before retry')
		expect(() => advance(state, { type: 'merged', fingerprint: 'wrong', commit: 'd'.repeat(40) })).toThrow('stale')
	})

	test('real disk reload preserves ordered records and rejects corruption', () => {
		const dir = mkdtempSync(join(tmpdir(), 'mission-'))
		try {
			const path = join(dir, 'state.json')
			const state = verified()
			saveMission(path, state)
			expect(loadMission(path, 'T-test')).toEqual(state)
			expect(() => loadMission(path, 'T-other')).toThrow()
			expect(state.events.map(e => e.sequence)).toEqual(state.events.map((_, i) => i + 1))
			expect(readFileSync(path, 'utf8')).not.toContain('credential')
			for (const change of [{ phase: 'typo' }, { generation: -1 }, { riskFloor: 'typo' }, { candidate: { ...candidate, risk: 'typo' } }]) {
				writeFileSync(path, JSON.stringify({ ...state, ...change }))
				expect(() => loadMission(path, 'T-test')).toThrow()
			}
			writeFileSync(path, '{broken')
			expect(() => loadMission(path, 'T-test')).toThrow()
		} finally { rmSync(dir, { recursive: true }) }
	})
})
