import { expect, test } from 'bun:test'
import { evaluateGate, riskFloor } from '../plugins/mission-control/lib/gate'

function valid() {
	return {
		repo: 'acme/app', pr: 7, owner: 'owner', implementer: 'worker', mode: 'auto', risk: 'low',
		design: 'a'.repeat(64), head: 'b'.repeat(40), base: 'c'.repeat(40), generation: 0,
		live: { repo: 'acme/app', pr: 7, head: 'b'.repeat(40), base: 'c'.repeat(40), target: 'dev', state: 'open' },
		approval: { actor: 'owner', design: 'a'.repeat(64), sequence: 1 },
		defense: { design: 'a'.repeat(64), sequence: 2 }, buildSequence: 3,
		paths: ['src/export.ts'], criteria: ['rows', 'preservation'],
		evidence: { head: 'b'.repeat(40), base: 'c'.repeat(40), design: 'a'.repeat(64), generation: 0, passed: ['rows', 'preservation'], published: true },
		reviews: [1, 2].map(gate => ({ gate, reviewer: 'reviewer', head: 'b'.repeat(40), base: 'c'.repeat(40), generation: 0, passed: true, sequence: gate + 3 })),
		requiredChecks: ['test'], checks: [{ name: 'test', head: 'b'.repeat(40), conclusion: 'success' }],
		mergeApproval: undefined as undefined | { actor: string; head: string; base: string; design: string; mode: string; generation: number },
	}
}
test('trusted gate permits default low/medium delivery only after complete evidence', () => {
	for (const risk of ['low', 'medium']) expect(evaluateGate({ ...valid(), risk })).toEqual([])
	for (const change of [
		{ requiredChecks: [] }, { checks: [] }, { risk: 'unknown' },
		{ evidence: { ...valid().evidence, published: false } },
		{ reviews: [valid().reviews[0]] }, { approval: { ...valid().approval, actor: 'someone-else' } },
		{ defense: { ...valid().defense, sequence: 0 } },
		{ live: { ...valid().live, target: 'main' } },
		{ live: { ...valid().live, base: 'd'.repeat(40) } },
	]) expect(evaluateGate({ ...valid(), ...change }).length).toBeGreaterThan(0)
})
test('high risk floors and ask mode need the actual owner on the exact candidate', () => {
	expect(riskFloor(['db/migrations/001.sql'])).toBe('high')
	expect(riskFloor(['.github/workflows/check.yml'])).toBe('high')
	for (const change of [{ risk: 'high' }, { mode: 'ask' }, { paths: ['src/auth/token.ts'] }]) {
		const input = { ...valid(), ...change }
		expect(evaluateGate(input)).toContain('Owner candidate acknowledgment required')
		const approval = { actor: 'owner', head: input.head, base: input.base, design: input.design, mode: input.mode, generation: input.generation }
		expect(evaluateGate({ ...input, mergeApproval: approval })).toEqual([])
		expect(evaluateGate({ ...input, mergeApproval: { ...approval, actor: 'worker' } }).length).toBeGreaterThan(0)
		expect(evaluateGate({ ...input, mergeApproval: { ...approval, head: 'd'.repeat(40) } }).length).toBeGreaterThan(0)
	}
})
test('a stale green, skipped check, reordered reviews or missing criterion cannot pass', () => {
	for (const change of [
		{ generation: 1 },
		{ evidence: { ...valid().evidence, passed: 'not rows; not preservation' } },
		{ reviews: valid().reviews.map(r => ({ ...r, generation: 1 })) },
		{ evidence: { ...valid().evidence, generation: 1 } },
	]) expect(evaluateGate({ ...valid(), ...change } as any).length).toBeGreaterThan(0)
	const fresh = { ...valid(), generation: 1, mode: 'ask', evidence: { ...valid().evidence, generation: 1 }, reviews: valid().reviews.map(r => ({ ...r, generation: 1 })) }
	const approval = { actor: 'owner', head: fresh.head, base: fresh.base, design: fresh.design, mode: fresh.mode, generation: 0 }
	expect(evaluateGate({ ...fresh, mergeApproval: approval })).toContain('Owner candidate acknowledgment required')
	expect(evaluateGate({ ...fresh, mergeApproval: { ...approval, generation: 1 } })).toEqual([])
	for (const sequences of [['10', '9'], [4.5, 5.5], [4, Infinity]]) {
		expect(evaluateGate({ ...valid(), reviews: valid().reviews.map((r, i) => ({ ...r, sequence: sequences[i] as number })) }).length).toBeGreaterThan(0)
	}
	for (const change of [
		{ checks: [{ ...valid().checks[0], conclusion: 'skipped' }] },
		{ checks: [{ ...valid().checks[0], head: 'd'.repeat(40) }] },
		{ evidence: { ...valid().evidence, passed: ['rows'] } },
		{ reviews: valid().reviews.map(r => ({ ...r, sequence: 7 - r.gate })) },
		{ reviews: valid().reviews.map(r => ({ ...r, base: 'd'.repeat(40) })) },
	]) expect(evaluateGate({ ...valid(), ...change }).length).toBeGreaterThan(0)
})
