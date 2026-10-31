import { describe, expect, test } from 'bun:test'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createMission, advance, blockers, fingerprint, saveMission, loadMission } from '../plugins/mission-control/lib/mission'
import { parseManifest, intentDigest } from '../plugins/mission-control/lib/contracts'
import { createMissionV2, advanceV2, blockersV2, fingerprintV2, parseMissionV2 } from '../plugins/mission-control/lib/mission-v2'

const manifest = {
	schemaVersion: 2, missionId: 'M-1', repository: 'acme/app',
	requirements: [{ id: 'R-1', need: 'Recover edits', scope: 'Local documents', nonGoals: 'Cloud sync' }],
	criteria: [{ id: 'C-1', requirementIds: ['R-1'], outcome: 'Recover after interruption', authority: 'mission', method: 'journey', checks: ['recovery'], threshold: 'Latest durable edit survives' }],
	decisions: [{ id: 'D-1', requirementIds: ['R-1'], rationale: 'Journal before acknowledgment', alternatives: 'Full file copies', revisit: 'Latency exceeds acceptance threshold' }],
	slices: [{ id: 'S-1', criterionIds: ['C-1'], paths: ['src/recovery.ts'] }],
	deliveries: [{ id: 'U-1', sliceIds: ['S-1'], criterionIds: ['C-1'] }],
	allocations: [{ criterionId: 'C-1', contributors: ['U-1'], finalUnitId: 'U-1' }],
}

describe('v2 manifest contracts', () => {
	test('intent identity ignores object key order but detects weaker outcomes', () => {
		const parsed = parseManifest(manifest)
		expect(intentDigest(Object.fromEntries(Object.entries(parsed).reverse()) as any)).toBe(intentDigest(parsed))
		const changed = structuredClone(parsed)
		changed.criteria[0].outcome = 'Recover after clean shutdown'
		expect(intentDigest(changed)).not.toBe(intentDigest(parsed))
		expect(parsed.criteria[0].id).toBe('C-1')
	})
	test('rejects duplicate identities, dangling references and unrecognized authority', () => {
		for (const change of [
			{ schemaVersion: 99 },
			{ criteria: [...manifest.criteria, manifest.criteria[0]] },
			{ criteria: [{ ...manifest.criteria[0], requirementIds: ['R-2'] }] },
			{ criteria: [{ ...manifest.criteria[0], authority: 'owner-signed' }] },
			{ slices: [{ ...manifest.slices[0], paths: ['../secrets'] }] },
			{ allocations: [{ ...manifest.allocations[0], finalUnitId: 'U-2' }] },
			{ receipts: [{ producer: 'independent-executed' }] },
		]) expect(() => parseManifest({ ...manifest, ...change })).toThrow()
	})
})

const bundle = { spec: 'Export exact rows; reject changed source.', plan: 'Add failure harness, then repair.', technical: 'Checkpoint byte offsets.', ux: 'CLI errors preserve prior files.' }
const candidate = { repo: 'acme/app', pr: 7, head: 'a'.repeat(40), base: 'b'.repeat(40), risk: 'low' as const }
function v2Built(two = false) {
	const m = structuredClone(manifest)
	if (two) {
		m.deliveries.push({ id: 'U-2', sliceIds: ['S-1'], criterionIds: ['C-1'] })
		m.allocations[0] = { criterionId: 'C-1', contributors: ['U-1', 'U-2'], finalUnitId: 'U-2' }
	}
	let s = createMissionV2('T-test', parseManifest(m))
	s = advanceV2(s, { type: 'approve-design', digest: intentDigest(m) })
	s = advanceV2(s, { type: 'defense', digest: intentDigest(m), record: 'Journal ownership and interruption boundary explained.' })
	s = advanceV2(s, { type: 'build', unitId: 'U-1' })
	return advanceV2(s, { type: 'candidate', unitId: 'U-1', attemptId: 'A-1', candidate, manifest: m })
}

describe('v2 local mission workflow', () => {
	test('removing criteria requires acknowledged dispositions and integrated changes need corrective allocation', () => {
		let s = v2Built()
		s = advanceV2(s, { type: 'observe-integration', unitId: 'U-1', attemptId: 'A-1', commit: 'c'.repeat(40), remoteHead: candidate.head, targetRef: 'dev', repository: candidate.repo })
		const m = structuredClone(s.manifest)
		m.criteria[0].outcome = 'Recover latest acknowledged edit'
		expect(() => advanceV2(s, { type: 'design', manifest: m })).toThrow('corrective')
		m.deliveries.push({ id: 'U-fix', sliceIds: ['S-1'], criterionIds: ['C-1'] })
		m.allocations[0] = { criterionId: 'C-1', contributors: ['U-1', 'U-fix'], finalUnitId: 'U-fix' }
		s = advanceV2(s, { type: 'design', manifest: m })
		expect(s.units[0].attempts[0].integration!.commit).toBe('c'.repeat(40))
		expect(s.approvedDesign).toBeUndefined()
		const replaced = structuredClone(m)
		replaced.criteria[0].id = 'C-2'
		replaced.slices[0].criterionIds = ['C-2']
		replaced.deliveries.forEach(d => { d.criterionIds = ['C-2'] })
		replaced.allocations[0].criterionId = 'C-2'
		expect(() => advanceV2(s, { type: 'design', manifest: replaced })).toThrow('disposition')
		const withDisposition = { ...replaced, dispositions: [{ criterionId: 'C-1', reason: 'Replaced by explicitly stronger C-2', owner: 'mission owner', replacementIds: ['C-2'] }] }
		s = advanceV2(s, { type: 'design', manifest: withDisposition })
		expect(blockersV2(s)).toContain('Owner design approval required')
		expect(s.snapshots[0].manifest.criteria[0].id).toBe('C-1')
		expect(parseMissionV2(JSON.parse(JSON.stringify(s)))).toEqual(s)
	})
	test('reviews bind to current evidence and failed first review cannot advance', () => {
		let s = v2Built()
		const fp = fingerprintV2(s, 'U-1', 'A-1')
		const review = { type: 'review', unitId: 'U-1', attemptId: 'A-1', gate: 1, fingerprint: fp, evidenceDigest: intentDigest([]), reviewer: 'T-reviewer', passed: false, record: 'Missing restart evidence.', findingIds: [] }
		s = advanceV2(s, review as any)
		expect(s.units[0].attempts[0].reviews[0].passed).toBe(false)
		expect(() => advanceV2(s, { ...review, gate: 2, passed: true } as any)).toThrow('first review')
		expect(() => advanceV2(s, { ...review, passed: true } as any)).toThrow('new attempt')
		s = advanceV2(s, { type: 'candidate', unitId: 'U-1', attemptId: 'A-2', candidate: { ...candidate, head: 'e'.repeat(40), risk: 'high' }, manifest: s.manifest })
		const renewed = { ...review, attemptId: 'A-2', fingerprint: fingerprintV2(s, 'U-1', 'A-2'), passed: true }
		expect(() => advanceV2(s, { ...renewed, reviewer: 'T-test' } as any)).toThrow('independent')
		s = advanceV2(s, renewed as any)
		s = advanceV2(s, { type: 'report', unitId: 'U-1', attemptId: 'A-2', fingerprint: renewed.fingerprint, evidence: { id: 'E-failed', criterionIds: ['C-1'], outcome: 'failed', record: 'Interrupted journal loses newest durable edit.' } })
		expect(() => advanceV2(s, { ...renewed, gate: 2 } as any)).toThrow('evidence')
		expect(blockersV2(s)).toContain('U-1: Review 1 required for current evidence')
		expect(s.units[0].attempts[0].reviews[0].passed).toBe(false)
	})
	test('findings survive attempts and pause blocks mutation without erasing history', () => {
		let s = v2Built()
		const finding = { id: 'F-1', criterionIds: ['C-1'], severity: 'high', confidence: 'source-supported', location: 'src/recovery.ts:12', record: 'Journal truncate precedes durable snapshot.', owner: 'T-repair' }
		s = advanceV2(s, { type: 'finding', unitId: 'U-1', attemptId: 'A-1', fingerprint: fingerprintV2(s, 'U-1', 'A-1'), finding } as any)
		s = advanceV2(s, { type: 'pause', reason: 'Need reproduction on Mac' } as any)
		expect(() => advanceV2(s, { type: 'candidate', unitId: 'U-1', attemptId: 'A-2', candidate, manifest: s.manifest })).toThrow('paused')
		s = advanceV2(s, { type: 'resume' } as any)
		s = advanceV2(s, { type: 'candidate', unitId: 'U-1', attemptId: 'A-2', candidate, manifest: s.manifest })
		expect(blockersV2(s)).toContain('U-1/F-1: unresolved finding')
		expect(parseMissionV2(JSON.parse(JSON.stringify(s)))).toEqual(s)
	})
	test('whole-mission reports cannot reuse partial or pre-integration evidence as closure', () => {
		let s = v2Built(true)
		const post = { type: 'post-delivery', unitId: 'U-1', package: { baseline: 'c'.repeat(40), designDigest: intentDigest(s.manifest), policyDigest: 'unqualified', unitIds: ['U-1'], evidenceIds: ['E-post'], results: [{ criterionId: 'C-1', outcome: 'passed', record: 'Recovered edit in synthetic journey.' }], findings: [], record: 'Fresh-context reported review, not authenticated execution.' } }
		expect(() => advanceV2(s, post as any)).toThrow('integration')
		s = advanceV2(s, { type: 'observe-integration', unitId: 'U-1', attemptId: 'A-1', commit: 'c'.repeat(40), remoteHead: candidate.head, targetRef: 'dev', repository: candidate.repo })
		s = advanceV2(s, post as any)
		expect(s.units[0].status).toBe('adversarial-review')
		expect(() => advanceV2(s, { type: 'closure-report', package: post.package } as any)).toThrow('whole mission')
		s = advanceV2(s, { type: 'build', unitId: 'U-2' })
		s = advanceV2(s, { type: 'candidate', unitId: 'U-2', attemptId: 'A-2', candidate: { ...candidate, pr: 8 }, manifest: s.manifest })
		s = advanceV2(s, { type: 'observe-integration', unitId: 'U-2', attemptId: 'A-2', commit: 'd'.repeat(40), remoteHead: candidate.head, targetRef: 'dev', repository: candidate.repo })
		const combined = { ...post.package, baseline: 'd'.repeat(40), unitIds: ['U-1', 'U-2'], results: [{ criterionId: 'C-1', outcome: 'failed', record: 'Unit B regressed interrupted recovery from A.' }] }
		s = advanceV2(s, { type: 'closure-report', package: combined } as any)
		expect(s.status).toBe('active')
		expect(blockersV2(s)).toContain('C-1: assembled-baseline report failed')
		expect(s.units[0].attempts[0].integration!.commit).toBe('c'.repeat(40))
		expect(blockersV2(s)).toContain('remote-verification-unqualified')
		expect(parseMissionV2(JSON.parse(JSON.stringify(s)))).toEqual(s)
	})
	test('retains acknowledged intent and rejects candidate-selected weakening', () => {
		const start = createMissionV2('T-test', parseManifest(manifest))
		expect(() => advanceV2(start, { type: 'build', unitId: 'U-1' })).toThrow()
		const original = v2Built()
		const changed = structuredClone(manifest)
		changed.criteria[0].outcome = 'Recover after clean shutdown'
		expect(() => advanceV2(original, { type: 'candidate', unitId: 'U-1', attemptId: 'A-2', candidate, manifest: changed })).toThrow('intent')
		const amended = advanceV2(original, { type: 'design', manifest: changed })
		expect(blockersV2(amended)).toContain('Owner design approval required')
		expect(amended.snapshots[0].manifest.criteria[0].outcome).toBe('Recover after interruption')
		expect(amended.units[0].attempts[0].stale).toBe(true)
	})
	test('binds reports to unit and attempt, retains superseded history and refuses fabricated receipts', () => {
		let s = v2Built(true)
		s = advanceV2(s, { type: 'build', unitId: 'U-2' })
		s = advanceV2(s, { type: 'candidate', unitId: 'U-2', attemptId: 'A-2', candidate: { ...candidate, pr: 8 }, manifest: s.manifest })
		const fp = fingerprintV2(s, 'U-1', 'A-1')
		const report = { id: 'E-1', criterionIds: ['C-1'], outcome: 'passed', record: 'Scratch recovery journey report, not an independent receipt.' }
		expect(() => advanceV2(s, { type: 'report', unitId: 'U-2', attemptId: 'A-2', fingerprint: fp, evidence: report })).toThrow('stale')
		expect(() => advanceV2(s, { type: 'report', unitId: 'U-1', attemptId: 'A-1', fingerprint: fp, evidence: { ...report, producer: 'independent-executed' } })).toThrow()
		s = advanceV2(s, { type: 'report', unitId: 'U-1', attemptId: 'A-1', fingerprint: fp, evidence: report })
		expect(s.units[0].attempts[0].reports[0].producer).toBe('reported')
		expect(blockersV2(s, 'U-1')).toContain('remote-verification-unqualified')
		s = advanceV2(s, { type: 'candidate', unitId: 'U-1', attemptId: 'A-3', candidate: { ...candidate, base: 'd'.repeat(40) }, manifest: s.manifest })
		expect(s.units[0].attempts[0].reports).toHaveLength(1)
		expect(s.units[0].attempts[0].stale).toBe(true)
		expect(s.units[0].attempts[1].reports).toHaveLength(0)
		expect(() => advanceV2(s, { type: 'candidate', unitId: 'U-1', attemptId: 'A-4', candidate: { ...candidate, pr: 8 }, manifest: s.manifest })).toThrow('PR')
	})
	test('observed partial integration is not whole-mission closure and corrupt persisted projections reject', () => {
		let s = v2Built(true)
		s = advanceV2(s, { type: 'observe-integration', unitId: 'U-1', attemptId: 'A-1', commit: 'c'.repeat(40), remoteHead: candidate.head, targetRef: 'dev', repository: candidate.repo })
		expect(s.units[0].status).toBe('integrated')
		expect(s.units[1].status).toBe('planned')
		expect(s.status).toBe('active')
		expect(blockersV2(s)).toContain('remote-verification-unqualified')
		expect(parseMissionV2(JSON.parse(JSON.stringify(s)))).toEqual(s)
		expect(() => parseMissionV2({ ...s, status: 'closed' })).toThrow()
		const changed = structuredClone(manifest)
		expect(() => advanceV2(s, { type: 'design', manifest: changed })).toThrow('allocation')
	})
})

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
