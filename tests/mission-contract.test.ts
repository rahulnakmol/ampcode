import { describe, expect, test } from 'bun:test'
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import {
	advance, approvalDigest, blocked, blockers, createRecord, fingerprint, loadContractRecord, parseContract,
	saveContractRecord, update, type ContractRecord,
} from '../plugins/mission-control/lib/contract'

// The canonical stop text of the mission contract, section 8, copied exactly.
const FIVE = [
	'Change to the baseline: a criterion, scope item or design decision is wrong or conflicts, and no reading inside the contract works.',
	'Outside effect not in the contract: an irreversible or outside effect that the contract does not pre-authorize.',
	'A fact only a person holds, with no safe, reversible default.',
	'A red line: security, legal or safety.',
	'A milestone cannot meet its exit criteria after the work was re-planned and split.',
]
const THREAD = 'T-00000000-0000-0000-0000-000000000001'
const A = 'a'.repeat(40), B = 'b'.repeat(40), C = 'c'.repeat(40), MERGE = 'd'.repeat(40)
const brief = {
	markdown: readFileSync(join(import.meta.dir, '../evals/briefing-decisions/brief.md'), 'utf8'),
	url: 'https://github.com/rahulnakmol/ampcode/blob/main/evals/briefing-decisions/brief.md',
}
const item = (id: string, milestone: string, done: string[], dependsOn: string[] = []) => ({
	id, title: `Item ${id}`, milestone, size: 'S', outcome: `${id} works`, inScope: [`${id} code`], outOfScope: ['Other code'],
	dependsOn, done, automatedTest: `bun test ${id}`, humanTest: `Run ${id} by hand`, trace: ['SC1'],
})
const contract = {
	schemaVersion: 3, missionId: 'one-approval', repository: 'acme/app',
	outcome: 'Missions need one approval.', scope: { in: ['The plugin'], out: ['The skills'] },
	spec: 'One approval at kickoff, then milestones.', design: { high: 'A contract record.', low: 'A replayed reducer.' },
	ux: ['https://ampcode.com/artifacts/visuals/contract-mission-ux'], defense: 'Approval binds to the digest.',
	cases: [{ id: 'P1', case: 'An agent supplies an internal action', mitigation: 'Refused' }],
	openQuestions: [{ id: 'Q1', question: 'Merge into dev without asking?', default: 'Yes' }],
	effects: [
		{ id: 'E1', effect: 'Push item branches', preAuthorized: true, source: 'Global AGENTS.md' },
		{ id: 'E2', effect: 'Publish the plugin', preAuthorized: false, source: 'Not authorized' },
	],
	readiness: [{ id: 'R1', check: 'Box reachable', evidence: 'HTTP 200' }],
	milestones: [
		{ id: 'M1', title: 'First', exit: ['M1 exit green'] },
		{ id: 'M2', title: 'Second', exit: ['M2 exit green'] },
		{ id: 'M3', title: 'Third', exit: ['M3 exit green'] },
	],
	items: [
		item('W1', 'M1', ['W1 criterion a', 'W1 criterion b']),
		item('W2', 'M1', ['W2 criterion'], ['W1']),
		item('W3', 'M2', ['W3 criterion']),
		item('W4', 'M3', ['W4 criterion']),
	],
	brief,
}
const TOP = ['schemaVersion', 'missionId', 'repository', 'outcome', 'scope', 'spec', 'design', 'ux', 'defense', 'cases', 'openQuestions', 'effects', 'readiness', 'milestones', 'items', 'brief']
const ITEM = ['id', 'title', 'milestone', 'size', 'outcome', 'inScope', 'outOfScope', 'dependsOn', 'done', 'automatedTest', 'humanTest', 'trace']
// Each milestone's criteria, written out by hand: its items' done lists, then its exit criteria.
const CRITERIA: Record<string, string[]> = {
	M1: ['W1 criterion a', 'W1 criterion b', 'W2 criterion', 'M1 exit green'],
	M2: ['W3 criterion', 'M2 exit green'],
	M3: ['W4 criterion', 'M3 exit green'],
}
const ITEMS: Record<string, string[]> = { M1: ['W1', 'W2'], M2: ['W3'], M3: ['W4'] }

const clone = () => structuredClone(contract) as any
const isApproved = (r: ContractRecord) => r.approval?.digest === approvalDigest(r.contract)
const itemOf = (r: ContractRecord, id: string) => r.items.find(i => i.id === id)!
const milestoneOf = (r: ContractRecord, id: string) => r.milestones.find(m => m.id === id)!
function approved(c: unknown = contract) {
	let r = createRecord(THREAD, c)
	const digest = approvalDigest(r.contract)
	r = advance(r, { type: 'preflight', digest, results: [{ check: 'dev exists', passed: true, detail: 'found' }] })
	r = advance(r, { type: 'approval-pending', kind: 'kickoff', digest })
	return advance(r, { type: 'approve', digest, responder: 'user-owner' })
}
function done(r: ContractRecord, id: string, criteria: string[]) {
	return update(r, { type: 'item-done', itemId: id, evidence: criteria.map(criterion => ({ criterion, result: `${criterion}: passed` })), review: { reviewer: 'TU-item-review', record: 'No findings' } })
}
function itemsDone(r: ContractRecord, milestone: string) {
	for (const id of ITEMS[milestone]) r = done(r, id, contract.items.find(i => i.id === id)!.done)
	return r
}
const review = (r: ContractRecord, m: string, gate: 1 | 2, passed: boolean, reviewer = `TU-gate-${gate}`) =>
	update(r, { type: 'review', milestoneId: m, gate, fingerprint: fingerprint(r, m), passed, reviewer, record: passed ? 'Passed' : 'Open Major inside section 6' })
const evidence = (r: ContractRecord, m: string, criteria = CRITERIA[m]) =>
	update(r, { type: 'evidence', milestoneId: m, fingerprint: fingerprint(r, m), results: criteria.map(criterion => ({ criterion, result: 'passed' })), humanTest: 'Ran it; it works' })
function withCandidate(r: ContractRecord, m: string, head = A) {
	return update(r, { type: 'candidate', milestoneId: m, pr: 7, head, base: B })
}
function merged(r: ContractRecord, m: string) {
	r = withCandidate(itemsDone(r, m), m)
	r = evidence(review(review(r, m, 1, true), m, 2, true), m)
	r = advance(r, { type: 'merge-requested', milestoneId: m, fingerprint: fingerprint(r, m) })
	return advance(r, { type: 'merged', milestoneId: m, fingerprint: fingerprint(r, m), commit: MERGE })
}
const amend = (r: ContractRecord, c: unknown, reason = 'Owner asked') => update(r, { type: 'amend', contract: c, reason })

describe('P16 invalid contracts are refused, naming the field', () => {
	test('P16 control: the fixture contract is valid', () => {
		expect(parseContract(contract).items.map(i => i.id)).toEqual(['W1', 'W2', 'W3', 'W4'])
	})
	TOP.forEach((field, i) => test(`P16.${String(i + 1).padStart(2, '0')} missing top-level field ${field}`, () => {
		const c = clone(); delete c[field]
		expect(() => parseContract(c)).toThrow(`(${field})`)
	}))
	ITEM.forEach((field, i) => test(`P16.${i + 17} missing item field ${field}`, () => {
		const c = clone(); delete c.items[1][field]
		expect(() => parseContract(c)).toThrow(`(items[1].${field})`)
	}))
	const cases: [string, (c: any) => void, string][] = [
		['size XL', c => { c.items[0].size = 'XL' }, '(items[0].size)'],
		['an unknown dependency', c => { c.items[1].dependsOn = ['W9'] }, '(items[1].dependsOn)'],
		['a dependency in a later milestone', c => { c.items[0].dependsOn = ['W3'] }, '(items[0].dependsOn)'],
		['a dependency cycle', c => { c.items[0].dependsOn = ['W2'] }, '(items[0].dependsOn)'],
		['a duplicate ID', c => { c.items[1].id = 'W1' }, '(items[1].id)'],
		['an item in an unknown milestone', c => { c.items[3].milestone = 'M9' }, '(items[3].milestone)'],
		['a milestone with no item', c => { c.milestones.push({ id: 'M4', title: 'Empty', exit: ['Nothing'] }) }, '(milestones[3])'],
		['an empty done list', c => { c.items[2].done = [] }, '(items[2].done)'],
		['a ux link that is not https on ampcode.com or github.com', c => { c.ux = ['http://ampcode.com/x'] }, '(ux[0])'],
	]
	cases.forEach(([name, change, field], i) => test(`P16.${i + 29} ${name}`, () => {
		const c = clone(); change(c)
		expect(() => parseContract(c)).toThrow(field)
		if (field === '(ux[0])') {
			const d = clone(); d.brief.url = 'https://example.com/brief'
			expect(() => parseContract(d)).toThrow('(brief.url)')
		}
	}))
})

describe('P3 P4 P5 approval: a baseline change voids it, a re-plan and a filed item keep it', () => {
	const parts: [string, (c: any) => void][] = [
		['missionId', c => { c.missionId = 'another-mission' }],
		['repository', c => { c.repository = 'acme/other' }],
		['outcome', c => { c.outcome += ' Faster.' }],
		['scope', c => { c.scope.in.push('The guides') }],
		['spec', c => { c.spec += ' Also reports.' }],
		['design', c => { c.design.low = 'A different reducer.' }],
		['ux', c => { c.ux.push('https://github.com/acme/app/pull/1') }],
		['defense', c => { c.defense = 'Another defense.' }],
		['cases', c => { c.cases[0].mitigation = 'Accepted' }],
		['openQuestions', c => { c.openQuestions[0].default = 'No' }],
		['effects', c => { c.effects[1].preAuthorized = true }],
		['brief', c => { c.brief.url = 'https://ampcode.com/artifacts/other-brief' }],
		['milestones', c => { c.milestones[0].exit = ['M1 exit green', 'Docs updated'] }],
	]
	parts.forEach(([part, change], i) => test(`P3.${String(i + 1).padStart(2, '0')} changing ${part} voids approval and preflight and blocks the merge`, () => {
		const r0 = approved()
		const c = clone(); change(c)
		const r = amend(r0, c)
		expect(isApproved(r0)).toBe(true)
		expect(approvalDigest(r.contract)).not.toBe(approvalDigest(r0.contract))
		expect(r.approval).toBeUndefined()
		expect(r.preflight).toBeUndefined()
		expect(blockers(r, 'M1')).toContain('Kickoff approval on the current contract required')
	}))
	test('P3.13b editing a done criterion through amend changes the milestones part and voids approval', () => {
		const c = clone(); c.items[2].done = ['W3 criterion, stricter']
		expect(amend(approved(), c).approval).toBeUndefined()
		const d = clone(); d.milestones[1].title = 'Second, renamed'
		expect(amend(approved(), d).approval).toBeUndefined()
	})
	test('P4.1 a re-plan that keeps the criteria in the same milestone keeps approval', () => {
		const r0 = approved()
		const r = update(r0, { type: 'replan', itemId: 'W1', into: [item('W1a', 'M1', ['W1 criterion b']), item('W1b', 'M1', ['W1 criterion a'])] })
		expect(isApproved(r)).toBe(true)
		expect(approvalDigest(r.contract)).toBe(approvalDigest(r0.contract))
		expect(r.contract.items.map(i => i.id)).toEqual(['W1a', 'W1b', 'W2', 'W3', 'W4'])
		expect(r.contract.items.find(i => i.id === 'W2')!.dependsOn).toEqual(['W1a', 'W1b'])
		expect(itemOf(r, 'W1a').status).toBe('planned')
	})
	test('P4.2 a re-plan that adds, drops or edits a criterion, or moves it to another milestone, is refused', () => {
		const r = approved()
		for (const into of [
			[item('W1a', 'M1', ['W1 criterion a']), item('W1b', 'M1', ['W1 criterion b', 'An extra check'])],
			[item('W1a', 'M1', ['W1 criterion a'])],
			[item('W1a', 'M1', ['W1 criterion a']), item('W1b', 'M1', ['W1 criterion B'])],
			[item('W1a', 'M1', ['W1 criterion a']), item('W1b', 'M2', ['W1 criterion b'])],
		]) expect(() => update(r, { type: 'replan', itemId: 'W1', into })).toThrow('exactly the original criteria')
	})
	test('P4.3 a re-plan of a done item that was not reopened is refused', () => {
		const r = done(approved(), 'W1', ['W1 criterion a', 'W1 criterion b'])
		expect(() => update(r, { type: 'replan', itemId: 'W1', into: [item('W1a', 'M1', ['W1 criterion a', 'W1 criterion b'])] })).toThrow('reopen')
	})
	test('P5 a filed item keeps approval and joins a later unmerged milestone', () => {
		const r = update(approved(), { type: 'file', item: item('X1', 'M2', ['X1 criterion']) })
		expect(isApproved(r)).toBe(true)
		expect(r.filed.map(i => [i.id, i.milestone])).toEqual([['X1', 'M2']])
		expect(itemOf(r, 'X1')).toEqual({ id: 'X1', origin: 'finding', status: 'planned' })
	})
})

describe('P7 a new candidate head voids reviews and evidence and keeps counters', () => {
	test('P7 a new head after reviews and evidence', () => {
		let r = withCandidate(itemsDone(approved(), 'M1'), 'M1')
		r = evidence(review(review(review(r, 'M1', 1, false), 'M1', 1, true), 'M1', 2, true), 'M1')
		expect(blockers(r, 'M1')).toEqual([])
		const before = fingerprint(r, 'M1')
		r = withCandidate(r, 'M1', C)
		const m = milestoneOf(r, 'M1')
		expect(m.reviews).toEqual([])
		expect(m.evidence).toBeUndefined()
		expect(m.failed).toEqual([1, 0])
		expect(m.candidate).toEqual({ repo: 'acme/app', pr: 7, head: C, base: B })
		expect(fingerprint(r, 'M1')).not.toBe(before)
		expect(blockers(r, 'M1')).toEqual(['Review 1 must pass on the current fingerprint', 'Review 2 must pass on the current fingerprint', 'Evidence required on the current fingerprint'])
	})
})

describe('P5 filing', () => {
	test('P5.1 a filed item keeps approval, joins a later milestone, and its criteria join that milestone', () => {
		let r = update(approved(), { type: 'file', item: item('X1', 'M2', ['X1 criterion']) })
		r = itemsDone(merged(r, 'M1'), 'M2')
		expect(isApproved(r)).toBe(true)
		expect(() => withCandidate(r, 'M2')).toThrow('X1')
		r = withCandidate(done(r, 'X1', ['X1 criterion']), 'M2')
		expect(() => evidence(r, 'M2')).toThrow('one result per criterion')
		r = evidence(r, 'M2', ['W3 criterion', 'X1 criterion', 'M2 exit green'])
		expect(milestoneOf(r, 'M2').evidence?.results.map(e => e.criterion)).toEqual(['W3 criterion', 'X1 criterion', 'M2 exit green'])
	})
	test('P5.2 a follow-up is recorded only when the earliest unmerged milestone is the last one', () => {
		const followUp = { id: 'F1', text: 'Tidy the report wording' }
		expect(() => update(approved(), { type: 'file', followUp })).toThrow('follow-up')
		const r = update(merged(merged(approved(), 'M1'), 'M2'), { type: 'file', followUp })
		expect(r.followUps).toEqual([followUp])
		expect(isApproved(r)).toBe(true)
		expect(() => update(r, { type: 'file', item: item('X1', 'M3', ['X1 criterion']) })).toThrow('after the earliest unmerged milestone')
	})
	test('P5.3 a filed item aimed at the current or a merged milestone is refused', () => {
		const r = merged(approved(), 'M1')
		expect(() => update(r, { type: 'file', item: item('X1', 'M1', ['X1 criterion']) })).toThrow('after the earliest unmerged milestone')
		expect(() => update(r, { type: 'file', item: item('X1', 'M2', ['X1 criterion']) })).toThrow('after the earliest unmerged milestone')
		expect(update(r, { type: 'file', item: item('X1', 'M3', ['X1 criterion']) }).filed).toHaveLength(1)
	})
})

describe('P13 review cap: only a replanned disposition resets a gate', () => {
	const capped = () => {
		let r = withCandidate(itemsDone(approved(), 'M1'), 'M1')
		for (let i = 0; i < 3; i++) r = review(r, 'M1', 1, false)
		expect(milestoneOf(r, 'M1').failed).toEqual([3, 0])
		return r
	}
	const disposition = (r: ContractRecord, outcome: string, itemIds?: string[]) =>
		update(r, { type: 'disposition', milestoneId: 'M1', gate: 1, outcome, record: `Cap: ${outcome}`, ...(itemIds ? { itemIds } : {}) })
	test('P13.1 a 4th failed review at a gate without replanned is refused', () => {
		expect(() => review(capped(), 'M1', 1, false)).toThrow('replanned')
	})
	test('P13.2 the same after a filed or fixed disposition is refused', () => {
		let r = update(capped(), { type: 'file', item: item('X1', 'M2', ['X1 criterion']) })
		r = disposition(disposition(r, 'filed', ['X1']), 'fixed')
		expect(milestoneOf(r, 'M1').failed).toEqual([3, 0])
		expect(milestoneOf(r, 'M1').dispositions.map(d => d.outcome)).toEqual(['filed', 'fixed'])
		expect(() => review(r, 'M1', 1, false)).toThrow('replanned')
	})
	test('P13.3 the same after replanned is accepted', () => {
		const r = review(disposition(capped(), 'replanned', ['W1']), 'M1', 1, false)
		expect(milestoneOf(r, 'M1').failed).toEqual([1, 0])
	})
	test('P13.4 replanned reopens done items: back to planned, item and milestone evidence and reviews voided', () => {
		let r = evidence(review(withCandidate(itemsDone(approved(), 'M1'), 'M1'), 'M1', 1, true), 'M1')
		for (let i = 0; i < 3; i++) r = review(r, 'M1', 2, false)
		r = update(r, { type: 'disposition', milestoneId: 'M1', gate: 2, outcome: 'replanned', record: 'Cap: replanned', itemIds: ['W1'] })
		expect(itemOf(r, 'W1')).toEqual({ id: 'W1', origin: 'contract', status: 'planned' })
		expect(itemOf(r, 'W2').status).toBe('done')
		expect(milestoneOf(r, 'M1').evidence).toBeUndefined()
		expect(milestoneOf(r, 'M1').failed).toEqual([0, 0])
		// Redoing W1 on the same head does not revive the gate 1 pass or the evidence from before the reopen.
		const redone = done(r, 'W1', ['W1 criterion a', 'W1 criterion b'])
		expect(blockers(redone, 'M1')).toEqual(['Review 1 must pass on the current fingerprint', 'Review 2 must pass on the current fingerprint', 'Evidence required on the current fingerprint'])
		const split = update(r, { type: 'replan', itemId: 'W1', into: [item('W1a', 'M1', ['W1 criterion a']), item('W1b', 'M1', ['W1 criterion b'])] })
		expect(isApproved(split)).toBe(true)
		// Reviews and evidence recorded while W1 was reopened do not survive W1 being done again.
		const early = evidence(review(review(review(r, 'M1', 1, false), 'M1', 1, true), 'M1', 2, true), 'M1')
		const redoneLate = done(early, 'W1', ['W1 criterion a', 'W1 criterion b'])
		expect(blockers(redoneLate, 'M1')).toEqual(['Review 1 must pass on the current fingerprint', 'Review 2 must pass on the current fingerprint', 'Evidence required on the current fingerprint'])
		expect(milestoneOf(redoneLate, 'M1').failed).toEqual([1, 0])
		// A replanned disposition must reopen something: a planned item cannot reset the cap again.
		expect(() => update(r, { type: 'disposition', milestoneId: 'M1', gate: 2, outcome: 'replanned', record: 'Again', itemIds: ['W1'] })).toThrow('not done or delegated')
	})
	test('P13.5 a passing review after 3 failures is accepted and leaves the counter unchanged', () => {
		const r = review(capped(), 'M1', 1, true)
		expect(milestoneOf(r, 'M1').failed).toEqual([3, 0])
		expect(milestoneOf(r, 'M1').reviews.at(-1)?.passed).toBe(true)
	})
})

describe('P10 stop reasons', () => {
	const stop = (r: ContractRecord, reason: unknown, blocks: string[]) =>
		update(r, { type: 'stop', reason, question: 'Which way?', options: ['Keep', 'Change'], recommendation: 'Keep', blocks })
	test('P10.1 a reason outside the five is refused, listing the five from contract-text.json', () => {
		const text = JSON.parse(readFileSync(join(import.meta.dir, '../plugins/mission-control/lib/contract-text.json'), 'utf8'))
		expect(text.stopReasons).toEqual(FIVE)
		for (const reason of ['The token allowance ran out', 6, 0]) {
			let message = ''
			try { stop(approved(), reason, ['M1']) } catch (error) { message = (error as Error).message }
			for (const line of FIVE) expect(message).toContain(line)
		}
		const r = stop(approved(), FIVE[3], ['W3'])
		expect(r.stops.map(s => [s.id, s.reason, s.blocks])).toEqual([['S-1', FIVE[3], ['W3']]])
		expect([blocked(r, 'M1'), blocked(r, 'M2')]).toEqual([false, true])
		expect(stop(approved(), 1, ['M1']).stops[0].reason).toBe(FIVE[0])
		// With the plugin, reason 2 is asked only through mission_effect's dialog (contract section 8).
		expect(() => stop(approved(), 2, ['M1'])).toThrow('mission_effect')
		expect(blocked(update(r, { type: 'resume', stopId: 'S-1', answer: 'Keep', source: 'Owner reply in the mission thread' }), 'M2')).toBe(false)
	})
	test('P10.2 an empty blocks list is refused', () => {
		expect(() => stop(approved(), FIVE[0], [])).toThrow('blocks')
	})
	test('P10.3 an open stop keeps blocking after its item is replanned, and an amend cannot drop an ID it names', () => {
		const r = update(stop(approved(), FIVE[0], ['W1']), { type: 'replan', itemId: 'W1', into: [item('W1a', 'M1', ['W1 criterion a']), item('W1b', 'M1', ['W1 criterion b'])] })
		expect(r.stops[0].blocks).toEqual(['W1a', 'W1b'])
		expect(blocked(r, 'M1')).toBe(true)
		const c = clone(); c.items[1].id = 'W2x'
		expect(() => amend(stop(approved(), FIVE[0], ['W2']), c)).toThrow('open stop S-1')
		expect(amend(approved(), c).contract.items[1].id).toBe('W2x')
	})
})

describe('P9 P15 reducer side: effects and the kickoff dialog need the approved, preflighted contract', () => {
	test('P9 a pre-authorized effect is recorded without a dialog only on the approved contract', () => {
		expect(() => advance(createRecord(THREAD, contract), { type: 'effect', effectId: 'E1' })).toThrow('approved')
		expect(advance(approved(), { type: 'effect', effectId: 'E1' }).performed).toEqual([{ effectId: 'E1', effect: 'Push item branches', preAuthorized: true, at: expect.any(String) }])
		const c = clone(); c.effects[1].preAuthorized = true
		expect(() => advance(amend(approved(), c), { type: 'effect', effectId: 'E2' })).toThrow('approved')
	})
	test('P15 the kickoff dialog does not open before a passing preflight on the current contract', () => {
		const r = createRecord(THREAD, contract), digest = approvalDigest(r.contract)
		expect(() => advance(r, { type: 'approval-pending', kind: 'kickoff', digest })).toThrow('preflight')
		const failed = advance(r, { type: 'preflight', digest, results: [{ check: 'dev exists', passed: false, detail: 'missing' }] })
		expect(() => advance(failed, { type: 'approval-pending', kind: 'kickoff', digest })).toThrow('preflight failed')
		const passed = advance(r, { type: 'preflight', digest, results: [{ check: 'dev exists', passed: true, detail: 'found' }] })
		const c = clone(); c.spec += ' Changed after preflight.'
		const changed = amend(passed, c)
		expect(() => advance(changed, { type: 'approval-pending', kind: 'kickoff', digest: approvalDigest(changed.contract) })).toThrow('preflight on the current contract')
	})
})

describe('Amend: a non-digest item field keeps approval', () => {
	test('Amend changing an item humanTest keeps approval, records the reason and keeps unchanged progress', () => {
		const r0 = done(approved(), 'W1', ['W1 criterion a', 'W1 criterion b'])
		const c = clone(); c.items[2].humanTest = 'Open the report and read three rows'
		const r = amend(r0, c, 'Clearer human test for W3')
		expect(isApproved(r)).toBe(true)
		expect(r.preflight?.digest).toBe(approvalDigest(r.contract))
		expect(r.amendments.map(a => [a.reason, a.approvalKept])).toEqual([['Clearer human test for W3', true]])
		expect(r.contract.items[2].humanTest).toBe('Open the report and read three rows')
		expect(itemOf(r, 'W1').status).toBe('done')
	})
})

describe('P1 internal actions are not accepted through the public dispatch', () => {
	const actions: Record<string, object> = {
		'approval-pending': { kind: 'kickoff', digest: approvalDigest(parseContract(contract)) },
		approve: { digest: approvalDigest(parseContract(contract)), responder: 'user-owner' },
		preflight: { digest: approvalDigest(parseContract(contract)), results: [{ check: 'dev exists', passed: true, detail: 'found' }] },
		effect: { effectId: 'E1' },
		'merge-requested': { milestoneId: 'M1', fingerprint: 'f'.repeat(64) },
		merged: { milestoneId: 'M1', fingerprint: 'f'.repeat(64), commit: MERGE },
		recover: { milestoneId: 'M1', fingerprint: 'f'.repeat(64) },
	}
	Object.entries(actions).forEach(([type, fields], i) => test(`P1.${i + 1} ${type} is refused`, () => {
		const r = createRecord(THREAD, contract)
		expect(() => update(r, { type, ...fields } as any)).toThrow('internal action')
	}))
})

describe('P18 replay and writes', () => {
	const path = () => join(mkdtempSync(join(tmpdir(), 'mission-contract-')), 'mission.json')
	const saved = () => {
		const p = path()
		let r = createRecord(THREAD, contract); saveContractRecord(p, r)
		for (const next of [
			(x: ContractRecord) => advance(x, { type: 'preflight', digest: approvalDigest(x.contract), results: [{ check: 'dev exists', passed: true, detail: 'found' }] }),
			(x: ContractRecord) => advance(x, { type: 'approval-pending', kind: 'kickoff', digest: approvalDigest(x.contract) }),
			(x: ContractRecord) => advance(x, { type: 'approve', digest: approvalDigest(x.contract), responder: 'user-owner' }),
			(x: ContractRecord) => update(x, { type: 'assume', question: 'Port?', assumption: '8080', why: 'The default' }),
		]) { r = next(r); saveContractRecord(p, r) }
		return { p, r }
	}
	const tamper = (p: string, change: (value: any) => void) => {
		const value = JSON.parse(readFileSync(p, 'utf8')); change(value); writeFileSync(p, JSON.stringify(value))
	}
	test('P18.1 a reloaded record replays to itself', () => {
		const { p, r } = saved()
		expect(loadContractRecord(p, THREAD)).toEqual(r)
		expect(loadContractRecord(p, THREAD)!.events.map(e => e.action.type)).toEqual(['start', 'preflight', 'approval-pending', 'approve', 'assume'])
	})
	test('P18.2 a tampered event is refused', () => {
		const { p } = saved()
		tamper(p, v => { v.events[4].action.assumption = '9090' })
		expect(() => loadContractRecord(p, THREAD)).toThrow('projection differs')
		tamper(p, v => { v.events[3].action.digest = '0'.repeat(64) })
		expect(() => loadContractRecord(p, THREAD)).toThrow('Event 4 does not replay')
	})
	test('P18.3 a projection that differs from the replay is refused', () => {
		const { p } = saved()
		tamper(p, v => { v.approval.responder = 'someone-else' })
		expect(() => loadContractRecord(p, THREAD)).toThrow('projection differs')
	})
	test('P18.4 a save from a stale copy (a concurrent write) or while the lock is held is refused', () => {
		const { p } = saved()
		const first = loadContractRecord(p, THREAD)!, second = loadContractRecord(p, THREAD)!
		saveContractRecord(p, update(first, { type: 'assume', question: 'Host?', assumption: 'localhost', why: 'Local run' }))
		expect(() => saveContractRecord(p, update(second, { type: 'assume', question: 'Host?', assumption: '0.0.0.0', why: 'Remote run' }))).toThrow('stale')
		const bytes = readFileSync(p, 'utf8')
		writeFileSync(p + '.lock', '')
		expect(() => saveContractRecord(p, update(loadContractRecord(p, THREAD)!, { type: 'assume', question: 'A?', assumption: 'B', why: 'C' }))).toThrow()
		expect(readFileSync(p, 'utf8')).toBe(bytes)
		expect(existsSync(p + '.lock')).toBe(true)
		expect(() => loadContractRecord(p, 'T-00000000-0000-0000-0000-000000000002')).toThrow('thread')
	})
})
