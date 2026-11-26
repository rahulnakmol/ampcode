import { describe, expect, test } from 'bun:test'
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import {
	advance, approvalDigest, blocked, blockers, createRecord, fingerprint, loadContractRecord, parseContract,
	parseRecord, saveContractRecord, update, variant, type ContractRecord,
} from '../plugins/mission-control/lib/contract'
import { banned, effectDialog, kickoffDialog, readAnswer } from '../plugins/mission-control/lib/brief'
import { checkpointReport, closeOutReport } from '../plugins/mission-control/lib/report'

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
		{ id: 'E3', effect: 'Squash-merge each milestone into dev when green', preAuthorized: true, source: 'Global AGENTS.md', kind: 'dev-merge' },
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
function approved(c: unknown = contract, start = createRecord(THREAD, c)) {
	let r = start
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
	test('P3.13c editing the brief text voids approval; re-sending the same contract with its keys in another order keeps it', () => {
		const c = clone(); c.brief.markdown = c.brief.markdown.replace('<details>', 'This line is new.\n\n<details>')
		expect(c.brief.markdown).not.toBe(contract.brief.markdown)
		expect(amend(approved(), c).approval).toBeUndefined()
		const reversed = (v: any): any => Array.isArray(v) ? v.map(reversed) : v && typeof v === 'object' ? Object.fromEntries(Object.entries(v).reverse().map(([k, x]) => [k, reversed(x)])) : v
		expect(Object.keys(reversed(contract))[0]).toBe('brief')
		expect(isApproved(amend(approved(), reversed(contract)))).toBe(true)
	})
	test('P3.13d a merged milestone and its items cannot be amended', () => {
		const r = merged(approved(), 'M1')
		const c = clone(); c.milestones[0].exit = ['M1 exit green', 'Docs updated']
		expect(() => amend(r, c)).toThrow('M1 is merged and cannot change')
		const d = clone(); d.items[1].humanTest = 'Another human test'
		expect(() => amend(r, d)).toThrow('M1 is merged and cannot change')
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
	test('P5.2 a follow-up is recorded only when the earliest unfinished milestone is the last one', () => {
		const followUp = { id: 'F1', text: 'Tidy the report wording' }
		expect(() => update(approved(), { type: 'file', followUp })).toThrow('follow-up')
		const r = update(merged(merged(approved(), 'M1'), 'M2'), { type: 'file', followUp })
		expect(r.followUps).toEqual([followUp])
		expect(isApproved(r)).toBe(true)
		expect(() => update(r, { type: 'file', item: item('X1', 'M3', ['X1 criterion']) })).toThrow('after the earliest unfinished milestone')
	})
	test('P5.3 a filed item aimed at the current or a merged milestone is refused', () => {
		const r = merged(approved(), 'M1')
		expect(() => update(r, { type: 'file', item: item('X1', 'M1', ['X1 criterion']) })).toThrow('after the earliest unfinished milestone')
		expect(() => update(r, { type: 'file', item: item('X1', 'M2', ['X1 criterion']) })).toThrow('after the earliest unfinished milestone')
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
		expect(itemOf(r, 'W1')).toEqual({ id: 'W1', origin: 'contract', status: 'planned', reopened: [2] })
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
		// Item IDs are not in section 3's list of fields amend may change; renaming goes through replan.
		expect(() => amend(approved(), c)).toThrow('Refused (items)')
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
	test('Amend changing an item outcome without a new criterion is refused, naming the field', () => {
		const c = clone(); c.items[1].outcome = 'W2 does something wider'
		expect(() => amend(approved(), c)).toThrow('Refused (items[1].outcome)')
	})
	test('Amend changing readiness voids an earlier preflight, so kickoff needs a new one', () => {
		let r = createRecord(THREAD, contract)
		const digest = approvalDigest(r.contract)
		r = advance(r, { type: 'preflight', digest, results: [{ check: 'dev exists', passed: true, detail: 'found' }] })
		const c = clone(); c.readiness[0].evidence = 'HTTP 503'
		r = amend(r, c)
		expect(r.preflight).toBeUndefined()
		expect(() => advance(r, { type: 'approval-pending', kind: 'kickoff', digest })).toThrow('preflight')
		// The same change while the kickoff dialog is open keeps the dialog but refuses its approval.
		let open = createRecord(THREAD, contract)
		open = advance(open, { type: 'preflight', digest, results: [{ check: 'dev exists', passed: true, detail: 'found' }] })
		open = amend(advance(open, { type: 'approval-pending', kind: 'kickoff', digest }), c)
		expect(open.pendingApproval?.digest).toBe(digest)
		expect(() => advance(open, { type: 'approve', digest, responder: 'user-owner' })).toThrow('preflight')
	})
	test('A milestone review by the mission thread is refused, and a candidate needs every earlier milestone merged', () => {
		const r = withCandidate(itemsDone(approved(), 'M1'), 'M1')
		expect(() => review(r, 'M1', 1, true, THREAD)).toThrow('must not be the mission thread')
		expect(() => withCandidate(itemsDone(approved(), 'M2'), 'M2')).toThrow('earlier milestones are not merged: M1')
	})
	test('Gate 2 must come from a reviewer other than the gate 1 reviewer', () => {
		const r = review(withCandidate(itemsDone(approved(), 'M1'), 'M1'), 'M1', 1, true, 'TU-same')
		expect(() => review(r, 'M1', 2, true, 'TU-same')).toThrow('independent')
		expect(milestoneOf(review(r, 'M1', 2, true, 'TU-other'), 'M1').reviews).toHaveLength(2)
	})
	test('Amend renaming an item while keeping the digest is refused, so its outcome cannot change that way', () => {
		const c = clone(); c.items[1].id = 'W2x'; c.items[1].outcome = 'W2 does something wider'
		expect(() => amend(approved(), c)).toThrow('Refused (items)')
	})
	test('Amend that changes the digest closes an open kickoff dialog, so reverting cannot reuse it', () => {
		let r = createRecord(THREAD, contract)
		const digest = approvalDigest(r.contract)
		const pass = (x: ContractRecord) => advance(x, { type: 'preflight', digest: approvalDigest(x.contract), results: [{ check: 'dev exists', passed: true, detail: 'found' }] })
		r = advance(pass(r), { type: 'approval-pending', kind: 'kickoff', digest })
		const c = clone(); c.items[1].outcome = 'wider'; c.items[1].done = ['W2 changed criterion']
		r = amend(r, c)
		expect(r.pendingApproval).toBeUndefined()
		const back = clone(); back.items[1].outcome = 'wider'
		r = pass(amend(r, back))
		expect(() => advance(r, { type: 'approve', digest, responder: 'user-owner' })).toThrow('approval')
	})
	const failedOnce = (gate: 1 | 2) => {
		let r = withCandidate(itemsDone(approved(), 'M1'), 'M1')
		if (gate === 2) r = review(r, 'M1', 1, true)
		return review(r, 'M1', gate, false)
	}
	const moveM1 = (c: any, to: string) => c.items.forEach((i: any) => { if (i.milestone === 'M1') i.milestone = to })
	test('Amend renaming a milestone with a failed gate 1 or gate 2 round is refused', () => {
		for (const g of [1, 2] as const) {
			const c = clone(); c.milestones[0].id = 'M1b'; moveM1(c, 'M1b')
			expect(() => amend(failedOnce(g), c)).toThrow('failed review rounds')
		}
	})
	test('Amend removing a milestone with failed review rounds is refused', () => {
		const c = clone(); c.milestones.splice(0, 1); moveM1(c, 'M2')
		expect(() => amend(failedOnce(1), c)).toThrow('failed review rounds')
	})
	test('Amend moving a failed milestone\'s criteria or exit criteria away while keeping its IDs is refused', () => {
		const c = clone()
		c.milestones[0].exit = ['Decoy exit']
		c.items.forEach((i: any) => { if (i.milestone === 'M1') i.done = [`${i.id} decoy criterion`] })
		c.milestones.splice(1, 0, { id: 'M1b', title: 'First', exit: ['M1 exit green'] })
		c.items.push(item('W1b', 'M1b', ['W1 criterion a', 'W1 criterion b']), item('W2b', 'M1b', ['W2 criterion']))
		expect(() => amend(failedOnce(1), c)).toThrow('failed review rounds')
	})
	test('Amend putting a new milestone ahead of a failed one, or moving the failed one later, is refused', () => {
		const ahead = clone()
		ahead.milestones.unshift({ id: 'M1b', title: 'First again', exit: ['M1 exit green'] })
		ahead.items.push(item('W1b', 'M1b', ['W1 criterion a', 'W1 criterion b']))
		expect(() => amend(failedOnce(1), ahead)).toThrow('earliest unfinished')
		const later = clone(); later.milestones = [later.milestones[1], later.milestones[0], later.milestones[2]]
		expect(() => amend(failedOnce(1), later)).toThrow('earliest unfinished')
	})
	test('Amend putting a copy ahead of a candidate that has not failed yet is refused', () => {
		const ahead = clone()
		ahead.milestones.unshift({ id: 'M1b', title: 'First again', exit: ['M1 exit green'] })
		ahead.items.push(item('W1b', 'M1b', ['W1 criterion a', 'W1 criterion b']))
		expect(() => amend(withCandidate(itemsDone(approved(), 'M1'), 'M1'), ahead)).toThrow('M1 is a candidate and must stay the earliest unfinished')
		expect(amend(itemsDone(approved(), 'M1'), ahead).milestones.map(m => m.id)).toEqual(['M1b', 'M1', 'M2', 'M3'])
	})
	test('Replan of an item in a failed milestone needs a "replanned" disposition on each failing gate', () => {
		const c = clone(); c.items[0].title = 'Retitled'
		const r = amend(failedOnce(1), c)
		expect(itemOf(r, 'W1').status).toBe('planned')
		const into = [{ ...item('W1x', 'M1', ['W1 criterion a', 'W1 criterion b']), outcome: 'Something else entirely' }]
		expect(() => update(r, { type: 'replan', itemId: 'W1', into })).toThrow('record a "replanned" disposition on each failing gate')
		const reopened = update(failedOnce(1), { type: 'disposition', milestoneId: 'M1', gate: 1, outcome: 'replanned', record: 'Cap', itemIds: ['W1'] })
		expect(update(reopened, { type: 'replan', itemId: 'W1', into }).contract.items.map(i => i.id)).toContain('W1x')
		// A disposition from before the latest failed review does not count.
		let later = withCandidate(done(reopened, 'W1', ['W1 criterion a', 'W1 criterion b']), 'M1', C)
		later = amend(review(later, 'M1', 1, false), c)
		expect(() => update(later, { type: 'replan', itemId: 'W1', into })).toThrow('on each failing gate')
		// A replanned disposition on the other gate does not answer gate 1's failed round.
		const other = update(failedOnce(1), { type: 'disposition', milestoneId: 'M1', gate: 2, outcome: 'replanned', record: 'Wrong gate', itemIds: ['W1'] })
		expect(milestoneOf(other, 'M1').failed).toEqual([1, 0])
		expect(() => update(other, { type: 'replan', itemId: 'W1', into })).toThrow('on each failing gate')
	})
	test('Replan after failed rounds on both gates: a replanned disposition on each gate, naming the same reopened item, allows it', () => {
		let r = withCandidate(itemsDone(approved(), 'M1'), 'M1')
		r = review(r, 'M1', 1, false)
		r = review(review(r, 'M1', 1, true), 'M1', 2, false, 'TU-other')
		expect(milestoneOf(r, 'M1').failed).toEqual([1, 1])
		const into = [item('W1x', 'M1', ['W1 criterion a', 'W1 criterion b'])]
		r = update(r, { type: 'disposition', milestoneId: 'M1', gate: 2, outcome: 'replanned', record: 'Gate 2', itemIds: ['W1'] })
		expect(() => update(r, { type: 'replan', itemId: 'W1', into })).toThrow('on each failing gate')
		r = update(r, { type: 'disposition', milestoneId: 'M1', gate: 1, outcome: 'replanned', record: 'Gate 1', itemIds: ['W1'] })
		expect(milestoneOf(r, 'M1').failed).toEqual([0, 0])
		expect(update(r, { type: 'replan', itemId: 'W1', into }).contract.items.map(i => i.id)).toContain('W1x')
		// An item that was never reopened still has nothing to reopen.
		expect(() => update(update(approved(), { type: 'file', item: item('X1', 'M2', ['X1 criterion']) }), { type: 'disposition', milestoneId: 'M1', gate: 1, outcome: 'replanned', record: 'r', itemIds: ['W1'] })).toThrow('nothing to reopen')
	})
	test('Amend changing the digest may not rewrite an item outcome in a failed milestone', () => {
		const c = clone(); c.items[0].outcome = 'W1 does something else'; c.spec = `${c.spec} (revised)`
		expect(() => amend(failedOnce(1), c)).toThrow('outcomes and criteria')
	})
	test('Delegating a new item added to a failed milestone is accepted', () => {
		const c = clone(); c.items.push(item('W5', 'M1', ['W5 criterion']))
		let r = amend(failedOnce(1), c)
		const digest = approvalDigest(r.contract)
		r = advance(r, { type: 'preflight', digest, results: [{ check: 'dev exists', passed: true, detail: 'found' }] })
		r = advance(advance(r, { type: 'approval-pending', kind: 'kickoff', digest }), { type: 'approve', digest, responder: 'user-owner' })
		expect(itemOf(update(r, { type: 'delegate', itemId: 'W5', executor: { kind: 'subagent', id: 'TU-x' } }), 'W5').status).toBe('delegated')
	})
	test('Amend keeping the digest may not move a criterion between items, or swap items between milestones', () => {
		const moved = clone(); moved.items[0].done = ['W1 criterion a']; moved.items[1].done = ['W2 criterion', 'W1 criterion b']
		expect(() => amend(approved(), moved)).toThrow('Refused (items[0].done)')
		const swapped = clone()
		const [w3, w4] = [swapped.items[2], swapped.items[3]]
		;[w3.milestone, w4.milestone, w3.done, w4.done] = [w4.milestone, w3.milestone, w4.done, w3.done]
		expect(() => amend(approved(), swapped)).toThrow('Refused (items[2]')
	})
	test('Amend swapping milestone IDs, or renaming one and adding a decoy with its old ID, is refused', () => {
		const swap = clone(); swap.milestones[0].id = 'M2'; swap.milestones[1].id = 'M1'
		swap.items.forEach((i: any) => { i.milestone = i.milestone === 'M1' ? 'M2' : i.milestone === 'M2' ? 'M1' : i.milestone })
		expect(() => amend(failedOnce(1), swap)).toThrow('failed review rounds')
		const decoy = clone(); decoy.milestones[0].id = 'M1b'; moveM1(decoy, 'M1b')
		decoy.milestones.unshift({ id: 'M1', title: 'Decoy', exit: ['Decoy exit'] }); decoy.items.push(item('D1', 'M1', ['Decoy criterion']))
		expect(() => amend(failedOnce(1), decoy)).toThrow('failed review rounds')
	})
})

describe('Ship or stop: a pre-authorized dev-merge effect picks ship; without it milestones chain unmerged', () => {
	const stopContract = () => { const c = clone(); c.effects = c.effects.filter((e: any) => e.kind !== 'dev-merge'); return c }
	// Items done, a candidate on head over base, both gates passed and evidence on the current fingerprint.
	const gated = (r: ContractRecord, m: string, head: string, base: string) => {
		r = update(itemsDone(r, m), { type: 'candidate', milestoneId: m, pr: 7, head, base })
		return evidence(review(review(r, m, 1, true), m, 2, true), m)
	}
	const ready = (r: ContractRecord, m: string) => advance(r, { type: 'ready', milestoneId: m, fingerprint: fingerprint(r, m) })
	test('the variant: ship only with a pre-authorized dev-merge effect', () => {
		expect(variant(createRecord(THREAD, contract))).toBe('ship')
		expect(variant(createRecord(THREAD, stopContract()))).toBe('stop')
		const listed = clone(); listed.effects[2].preAuthorized = false
		expect(variant(createRecord(THREAD, listed))).toBe('stop')
	})
	test('the kickoff dialog tells the owner whether milestones merge', () => {
		const ship = kickoffDialog(createRecord(THREAD, contract)).message
		const stop = kickoffDialog(createRecord(THREAD, stopContract())).message
		expect(ship).toContain('Each milestone merges into dev once its gates pass.')
		expect(ship).not.toContain('No milestone merges')
		expect(stop).toContain('No milestone merges: each pull request stays open for you, and the next milestone builds on it.')
		expect(stop).not.toContain('Each milestone merges')
	})
	test('a start event carries variants only as true', () => {
		const r = JSON.parse(JSON.stringify(createRecord(THREAD, contract)))
		r.events[0].action.variants = false
		expect(() => parseRecord(r, THREAD)).toThrow('Refused (variants)')
	})
	test('a record started before effect kinds existed stays ship: its merges replay and it still merges', () => {
		// What the earlier plugin wrote: a merge effect with no kind, and no variants marker on the start event.
		const legacy = stopContract(); legacy.effects.push({ id: 'E3', effect: 'Squash-merge each milestone into dev when green', preAuthorized: true, source: 'Global AGENTS.md' })
		const start = createRecord(THREAD, legacy) as any
		delete start.variants; delete start.events[0].action.variants
		const gatedM1 = gated(approved(legacy, parseRecord(start, THREAD)), 'M1', A, B)
		expect(gatedM1.variants).toBeUndefined()
		expect(variant(gatedM1)).toBe('ship')
		const pending = advance(gatedM1, { type: 'merge-requested', milestoneId: 'M1', fingerprint: fingerprint(gatedM1, 'M1') })
		const merged = advance(pending, { type: 'merged', milestoneId: 'M1', fingerprint: fingerprint(pending, 'M1'), commit: MERGE })
		expect(milestoneOf(parseRecord(JSON.parse(JSON.stringify(pending)), THREAD), 'M1').status).toBe('merge-pending')
		expect(milestoneOf(parseRecord(JSON.parse(JSON.stringify(merged)), THREAD), 'M1').status).toBe('merged')
		expect(() => advance(gatedM1, { type: 'ready', milestoneId: 'M1', fingerprint: fingerprint(gatedM1, 'M1') })).toThrow('ship variant')
		// The same contract in a new record is stop.
		expect(variant(createRecord(THREAD, legacy))).toBe('stop')
	})
	test('an effect kind other than dev-merge, or two dev-merge effects, is refused', () => {
		const other = clone(); other.effects[0].kind = 'push'
		expect(() => parseContract(other)).toThrow('Refused (effects[0].kind)')
		const two = clone(); two.effects[0].kind = 'dev-merge'
		expect(() => parseContract(two)).toThrow('Refused (effects[2].kind)')
	})
	test('stop: no merge is requested; a gated milestone becomes ready and the next candidate builds on its head', () => {
		let r = gated(approved(stopContract()), 'M1', A, B)
		expect(() => advance(r, { type: 'merge-requested', milestoneId: 'M1', fingerprint: fingerprint(r, 'M1') })).toThrow('stop variant')
		r = ready(r, 'M1')
		expect(milestoneOf(r, 'M1').status).toBe('ready')
		expect(blockers(r, 'M1')).toEqual(['Milestone is ready; its pull request stays open'])
		r = itemsDone(r, 'M2')
		expect(() => update(r, { type: 'candidate', milestoneId: 'M2', pr: 8, head: C, base: B })).toThrow(`base must be ${A}`)
		r = update(r, { type: 'candidate', milestoneId: 'M2', pr: 8, head: C, base: A })
		expect(blockers(r, 'M2')).not.toContain('Earlier milestones not ready: M1')
	})
	test('stop: the next candidate waits until the earlier milestone is ready, and ready needs every blocker cleared', () => {
		let r = update(itemsDone(approved(stopContract()), 'M1'), { type: 'candidate', milestoneId: 'M1', pr: 7, head: A, base: B })
		expect(() => ready(r, 'M1')).toThrow('Review 1 must pass')
		r = itemsDone(r, 'M2')
		expect(() => update(r, { type: 'candidate', milestoneId: 'M2', pr: 8, head: C, base: A })).toThrow('earlier milestones are not ready: M1')
		expect(blockers(r, 'M2')).toContain('Earlier milestones not ready: M1')
	})
	test('ship: ready is refused, and merging still needs the earlier milestone merged', () => {
		const r = gated(approved(), 'M1', A, B)
		expect(() => ready(r, 'M1')).toThrow('ship variant')
		expect(() => update(itemsDone(r, 'M2'), { type: 'candidate', milestoneId: 'M2', pr: 8, head: C, base: A })).toThrow('earlier milestones are not merged: M1')
	})
	test('stop: a ready milestone is frozen like a merged one, and new work is filed after it', () => {
		const r = ready(gated(approved(stopContract()), 'M1', A, B), 'M1')
		expect(() => review(r, 'M1', 1, false)).toThrow('M1 is ready')
		const c = stopContract(); c.milestones[0].exit = ['M1 exit green', 'Docs updated']
		expect(() => amend(r, c)).toThrow('M1 is ready and cannot change')
		expect(() => update(r, { type: 'file', item: item('X1', 'M1', ['X1 criterion']) })).toThrow('after the earliest unfinished milestone')
		expect(() => update(r, { type: 'file', item: item('X1', 'M2', ['X1 criterion']) })).toThrow('earliest unfinished milestone (M2)')
		expect(update(r, { type: 'file', item: item('X1', 'M3', ['X1 criterion']) }).filed).toHaveLength(1)
	})
	test('the variant cannot change once a milestone is ready or merged', () => {
		const shipped = merged(approved(), 'M1')
		expect(() => amend(shipped, stopContract())).toThrow('merge variant')
		const held = ready(gated(approved(stopContract()), 'M1', A, B), 'M1')
		expect(() => amend(held, clone())).toThrow('merge variant')
		expect(amend(approved(), stopContract()).approval).toBeUndefined()
	})
	test('stop: with every milestone ready the mission is complete: nothing more to file, and the close-out builds', () => {
		let r = ready(gated(approved(stopContract()), 'M1', A, B), 'M1')
		r = ready(gated(r, 'M2', C, A), 'M2')
		r = ready(gated(r, 'M3', MERGE, C), 'M3')
		expect(() => update(r, { type: 'file', followUp: { id: 'F1', text: 'Later' } })).toThrow('the mission is complete')
		const report = closeOutReport(r)
		expect(report).toContain('pull requests left open')
		expect(report).toContain('| Milestone M1 merge into dev | agent | ready, not merged |')
		expect(checkpointReport(r, 'M2')).toContain('ready; its pull request stays open')
		expect(parseRecord(JSON.parse(JSON.stringify(r)), THREAD)).toEqual(r)
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
		ready: { milestoneId: 'M1', fingerprint: 'f'.repeat(64) },
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

// W3: dialogs and reports, built from records that W1's reducer produced.
const W3 = JSON.parse(readFileSync(join(import.meta.dir, '../plugins/mission-control/fixtures/contract-mission.json'), 'utf8'))
const OWNER = 'user-owner'
const W3_TEXT = JSON.parse(readFileSync(join(import.meta.dir, '../plugins/mission-control/lib/contract-text.json'), 'utf8'))
const TECHNICAL = '<details><summary>Technical record</summary>'
const prose = (report: string) => report.slice(0, report.indexOf(TECHNICAL))
const sections = (report: string) => [...report.matchAll(/^### (.+)$/gm)].map(m => m[1])
const fieldsOf = (d: any, type: string) => d.fields.filter((f: any) => (f.type ?? 'text') === type)
// Every box ticked, Changes as given.
const ticked = (d: any, changes = '') => ({ ...Object.fromEntries(fieldsOf(d, 'checkbox').map((f: any) => [f.name, 'true'])), changes })
const criteriaOf = (r: ContractRecord, m: string) => [...r.contract.items, ...r.filed].filter(i => i.milestone === m).flatMap(i => i.done)
// One milestone through W1's reducer: items done, candidate, both reviews, evidence, merge.
function land(r: ContractRecord, m: string, pr: number) {
	for (const i of [...r.contract.items, ...r.filed].filter(i => i.milestone === m)) {
		r = update(r, { type: 'delegate', itemId: i.id, executor: { kind: 'subagent', id: `helper for ${i.id}` } })
		r = update(r, { type: 'item-done', itemId: i.id, evidence: i.done.map(criterion => ({ criterion, result: `Passed in bun test for ${i.id}` })), review: { reviewer: 'fresh item reviewer', record: 'No findings' } })
	}
	r = update(r, { type: 'candidate', milestoneId: m, pr, head: A, base: B })
	r = review(review(r, m, 1, true, 'first fresh reviewer'), m, 2, true, 'second fresh reviewer')
	const exit = r.contract.milestones.find(x => x.id === m)!.exit
	r = update(r, { type: 'evidence', milestoneId: m, fingerprint: fingerprint(r, m), results: [...criteriaOf(r, m), ...exit].map(criterion => ({ criterion, result: `Shown on pull request ${pr}` })), humanTest: `Ran the ${m} human tests by hand` })
	r = advance(r, { type: 'merge-requested', milestoneId: m, fingerprint: fingerprint(r, m) })
	return advance(r, { type: 'merged', milestoneId: m, fingerprint: fingerprint(r, m), commit: MERGE })
}
// The fixture after M2 merged: an assumption, a filed item for M3, and a pre-authorized push.
function afterM2() {
	let r = update(approved(W3), { type: 'assume', question: 'Which reviewer runs gate 2?', assumption: 'A second fresh subagent runs gate 2', why: 'Gate 2 must be independent of gate 1' })
	r = advance(r, { type: 'effect', effectId: 'E3' })
	r = update(r, { type: 'file', item: { ...W3.items[2], id: 'W13', title: 'Show the time since each child last reported', done: ['Status shows the minutes since each child reported'], dependsOn: [] } })
	return land(r, 'M2', 61)
}
function complete() {
	let r = update(afterM2(), { type: 'assume', question: 'Which guide gets the kickoff prompt?', assumption: 'docs/mission-control.md holds the kickoff prompts', why: 'It already lists the ways to kick off a mission' })
	r = land(r, 'M3', 62)
	return advance(r, { type: 'effect', effectId: 'E2' })
}

describe('W3 kickoff dialog from a contract with 6 questions and 3 effects', () => {
	test('W3.1 the fixture contract passes parseContract with 6 questions, 3 effects, 2 milestones and 3 items', () => {
		const c = parseContract(W3)
		expect([c.openQuestions.length, c.effects.length, c.milestones.length, c.items.length]).toEqual([6, 3, 2, 3])
		expect(c.effects.every(e => e.preAuthorized)).toBe(true)
	})
	test('W3.2 the kickoff dialog has 1 brief link, 9 unticked checkboxes, 1 optional Changes field, Submit, and no secret field', () => {
		const d = kickoffDialog(createRecord(THREAD, W3))
		expect(d.confirmButtonText).toBe('Submit')
		expect([d.requireHuman, d.endTurnOnDecline]).toEqual([true, true])
		expect(fieldsOf(d, 'link')).toEqual([{ type: 'link', name: 'brief', label: 'Open the contract brief', value: W3.brief.url }])
		const boxes = fieldsOf(d, 'checkbox')
		expect(boxes).toHaveLength(9)
		expect(boxes.every((f: any) => f.value === 'false')).toBe(true)
		W3.openQuestions.forEach((q: any, i: number) => expect(boxes[i].label).toContain(q.default))
		W3.effects.forEach((e: any, i: number) => expect(boxes[6 + i].label).toContain(e.effect))
		expect(fieldsOf(d, 'text')).toEqual([expect.objectContaining({ name: 'changes', value: '', optional: true })])
		expect(d.fields).toHaveLength(11)
		expect(d.fields.some((f: any) => f.secret)).toBe(false)
	})
	test('W3.3 an effect that is not pre-authorized is not a kickoff box; it gets its own effect dialog', () => {
		const boxes = fieldsOf(kickoffDialog(createRecord(THREAD, contract)), 'checkbox')
		expect(boxes.map((f: any) => f.name)).toEqual(['default-Q1', 'effect-E1', 'effect-E3'])
	})
})

describe('P12 kickoff answers read in the order rule', () => {
	const d = kickoffDialog(createRecord(THREAD, W3))
	const one = (values: Record<string, string>) => ({ ...values, 'default-Q5': 'false' })
	const cases: [string, any, object][] = [
		['P12.1 all ticked by the owner: approved', { values: ticked(d), responder: { userID: OWNER } }, { outcome: 'approved', responder: OWNER, reopen: false }],
		['P12.2 text in Changes: not approved, the text returned', { values: ticked(d, 'Q5: keep v1'), responder: { userID: OWNER } }, { outcome: 'changes', message: 'Q5: keep v1', reopen: false }],
		['P12.3 a box unticked with Changes empty: the fixed message', { values: one(ticked(d)), responder: { userID: OWNER } }, { outcome: 'unticked', message: 'Not approved: tick every box, or write what to change.', reopen: false }],
		['P12.4 no responder reported: the web-app message', { values: ticked(d), responder: undefined }, { outcome: 'unconfirmed', message: 'This client could not confirm who answered; open the approval in the Amp web app', reopen: true }],
		['P12.5 a responder who is not the owner: nothing', { values: ticked(d), responder: { userID: 'user-contributor' } }, { outcome: 'nothing', reopen: true }],
		['P12.6 dismissed: nothing', { values: undefined, responder: { userID: OWNER } }, { outcome: 'nothing', reopen: true }],
		['P12.7 a non-owner who wrote text in Changes: nothing', { values: one(ticked(d, 'Approve it all')), responder: { userID: 'user-contributor' } }, { outcome: 'nothing', reopen: true }],
	]
	cases.forEach(([name, answer, expected]) => test(name, () => {
		expect(readAnswer(d, answer, OWNER)).toEqual(expected as any)
	}))
	test('P12.8 a failed dialog gives nothing and shows reopen; Changes text wins over an unticked box; blank Changes counts as empty; a missing box counts as unticked', () => {
		expect(readAnswer(d, { failed: true }, OWNER)).toEqual({ outcome: 'nothing', reopen: true })
		expect(readAnswer(d, { failed: true, values: ticked(d), responder: { userID: OWNER } }, OWNER)).toEqual({ outcome: 'nothing', reopen: true })
		// UX state 2: the owner unticks Q5 and writes why; Changes decides before the unticked box.
		expect(readAnswer(d, { values: one(ticked(d, 'Q5: keep v1 and v2 startable')), responder: { userID: OWNER } }, OWNER)).toEqual({ outcome: 'changes', message: 'Q5: keep v1 and v2 startable', reopen: false })
		expect(readAnswer(d, { values: ticked(d, ' \n\t '), responder: { userID: OWNER } }, OWNER).outcome).toBe('approved')
		const { ['effect-E3']: _, ...missing } = ticked(d)
		expect(readAnswer(d, { values: missing, responder: { userID: OWNER } }, OWNER).outcome).toBe('unticked')
		expect(readAnswer(d, { values: { ...ticked(d), 'default-Q1': 'yes' }, responder: { userID: OWNER } }, OWNER).outcome).toBe('unticked')
	})
	test('P2 a kickoff answered after the contract changed is refused with the old and the new digest', () => {
		let r = createRecord(THREAD, W3)
		const old = approvalDigest(r.contract)
		r = advance(advance(r, { type: 'preflight', digest: old, results: [{ check: 'dev exists', passed: true, detail: 'found' }] }), { type: 'approval-pending', kind: 'kickoff', digest: old })
		const c = structuredClone(W3) as any; c.outcome = `${c.outcome} Changed while the dialog was open.`
		r = update(r, { type: 'amend', contract: c, reason: 'Changed during the dialog' })
		expect(() => advance(r, { type: 'approve', digest: old, responder: OWNER })).toThrow('stale')
		expect(() => advance(r, { type: 'approve', digest: approvalDigest(r.contract), responder: OWNER })).toThrow('no matching approval dialog')
	})
	test('P12.9 an approved reading records approval through the reducer', () => {
		let r = createRecord(THREAD, W3)
		const digest = approvalDigest(r.contract)
		r = advance(advance(r, { type: 'preflight', digest, results: [{ check: 'dev exists', passed: true, detail: 'found' }] }), { type: 'approval-pending', kind: 'kickoff', digest })
		const reading = readAnswer(kickoffDialog(r), { values: ticked(kickoffDialog(r)), responder: { userID: OWNER } }, OWNER)
		expect(isApproved(advance(r, { type: 'approve', digest, responder: reading.responder }))).toBe(true)
	})
})

describe('W3 effect dialog: the same pattern with one checkbox', () => {
	test('W3.4 a listed effect that is not pre-authorized: 1 link, 1 unticked box, 1 optional Changes field, Submit', () => {
		const r = approved()
		const d = effectDialog(r, { kind: 'effect', digest: approvalDigest(r.contract), effectId: 'E2' })
		expect([d.confirmButtonText, d.requireHuman, d.endTurnOnDecline]).toEqual(['Submit', true, true])
		expect(fieldsOf(d, 'link')).toHaveLength(1)
		expect(fieldsOf(d, 'checkbox')).toEqual([expect.objectContaining({ name: 'effect-E2', value: 'false', label: expect.stringContaining('Publish the plugin') })])
		expect(fieldsOf(d, 'text')).toEqual([expect.objectContaining({ name: 'changes', value: '', optional: true })])
		expect(d.fields.some((f: any) => f.secret)).toBe(false)
		expect(readAnswer(d, { values: ticked(d), responder: { userID: OWNER } }, OWNER)).toEqual({ outcome: 'approved', responder: OWNER, reopen: false })
		expect(readAnswer(d, { values: { 'effect-E2': 'false', changes: '' }, responder: { userID: OWNER } }, OWNER).outcome).toBe('unticked')
		expect(readAnswer(d, { values: undefined }, OWNER)).toEqual({ outcome: 'nothing', reopen: true })
	})
	test('W3.5 an effect not in the contract shows the effect and why in its one box', () => {
		const r = approved()
		const d = effectDialog(r, { kind: 'effect', digest: approvalDigest(r.contract), effect: 'Merge dev into rolling', why: 'The owner asked for a snapshot' })
		const boxes = fieldsOf(d, 'checkbox')
		expect(boxes).toHaveLength(1)
		expect(boxes[0].label).toContain('Merge dev into rolling')
		expect(boxes[0].label).toContain('The owner asked for a snapshot')
	})
	test('W3.6 a pre-authorized or unknown effect gets no dialog', () => {
		const r = approved(), digest = approvalDigest(r.contract)
		expect(() => effectDialog(r, { kind: 'effect', digest, effectId: 'E1' })).toThrow('pre-authorized')
		expect(() => effectDialog(r, { kind: 'effect', digest, effectId: 'E9' })).toThrow('unknown effect')
		expect(() => effectDialog(r, { kind: 'kickoff', digest })).toThrow('effect')
	})
})

describe('W3 checkpoint report after 1 merged milestone', () => {
	test('W3.7 it uses the checkpoint sections and lists the merged PR, evidence, assumptions, filed items and the next milestone', () => {
		const report = checkpointReport(afterM2())
		expect(sections(report)).toEqual(W3_TEXT.reportSections.checkpoint)
		expect(report).toContain('https://github.com/rahulnakmol/ampcode/pull/61')
		for (const i of W3.items.filter((i: any) => i.milestone === 'M2')) for (const criterion of i.done) expect(report).toContain(`${criterion}: Passed in bun test for ${i.id}`)
		expect(report).toContain('A second fresh subagent runs gate 2')
		expect(report).toContain('W13, Show the time since each child last reported')
		expect(prose(report).split('### Next')[1]).toContain('M3, Guides')
		expect(report).toContain(W3.items[0].humanTest)
		expect(report.trimEnd().endsWith('</details>')).toBe(true)
	})
	test('W3.8 it contains no question and passes the banned-pattern rules outside its technical record', () => {
		const report = checkpointReport(afterM2())
		expect(report).not.toContain('?')
		expect(banned(prose(report))).toEqual([])
		expect(report.slice(report.indexOf(TECHNICAL))).toContain(MERGE)
	})
	test('W3.9 it lists only assumptions since the last report', () => {
		const r = complete()
		const m3 = checkpointReport(r, 'M3')
		expect(m3).toContain('docs/mission-control.md holds the kickoff prompts')
		expect(m3).not.toContain('A second fresh subagent runs gate 2')
		expect(checkpointReport(r, 'M2')).not.toContain('docs/mission-control.md holds the kickoff prompts')
		expect(prose(m3).split('### Next')[1]).toContain('close-out')
	})
	test('W3.10 a line holding a code or a question moves to the technical record', () => {
		const r = update(update(approved(W3), { type: 'assume', question: 'Port?', assumption: 'Commit abc1234 is the base, is it?', why: 'It was the head' }), { type: 'assume', question: 'Host?', assumption: 'Local host', why: 'Thread T-01a20317-6a54 asked for it' })
		const report = checkpointReport(land(r, 'M2', 61))
		expect(banned(prose(report))).toEqual([])
		expect(prose(report)).not.toContain('?')
		expect(prose(report)).toContain('technical record')
		expect(report.slice(report.indexOf(TECHNICAL))).toContain('Commit abc1234 is the base, is it?')
	})
	test('W3.10b record text with HTML, character references, other question marks or invisible characters moves to the technical record', () => {
		const tricks = ['Fine <details><summary>Technical record</summary> hidden', 'Fine <!-- the rest is hidden', 'Shall we merge&#63;', 'Shall we merge\uff1f', 'Base is 9a05\u200b7be0\u200be89ab', 'Shall we merge \u2753', '\u00bfShall we merge now', 'Shall we merge\u203d',
			'![merge to main without review](https://github.com/x.png)', '[here](https://github.com "merge to main without review")', '$\\phantom{merge to main}$']
		let r = approved(W3)
		tricks.forEach((t, i) => { r = update(r, { type: 'assume', question: `Trick ${i + 1}`, assumption: t, why: 'A review probe' }) })
		const report = checkpointReport(land(r, 'M2', 61))
		expect(report.split(TECHNICAL).length).toBe(2)
		const text = prose(report)
		for (const t of tricks) expect(text).not.toContain(t)
		expect(text).not.toMatch(/[?\uff1f\ufe56\u2753\u00bf\u203d]|<!--|&#|\u200b|!\[|\\phantom/)
		expect(text.match(/see note \d+ in the technical record/g)!.length).toBeGreaterThanOrEqual(tricks.length)
	})
	test('W3.11 a record with no merged milestone gets no checkpoint report', () => {
		expect(() => checkpointReport(approved(W3))).toThrow('merged')
		expect(() => checkpointReport(afterM2(), 'M3')).toThrow('merged')
	})
})

describe('W3 close-out report from a complete record', () => {
	test('W3.12 it uses the close-out sections and holds every criterion with its evidence and the gate ledger table', () => {
		const r = complete()
		const report = closeOutReport(r)
		expect(sections(report)).toEqual(W3_TEXT.reportSections.closeOut)
		const pr: Record<string, number> = { M2: 61, M3: 62 }
		for (const m of r.contract.milestones) for (const criterion of [...criteriaOf(r, m.id), ...m.exit]) expect(report).toContain(`${criterion}: Shown on pull request ${pr[m.id]}`)
		expect(report).toContain('Status shows the minutes since each child reported')
		const ledger = prose(report).split('### Gate ledger')[1].split('###')[0]
		expect(ledger).toContain('| Gate | Kind | State | Decider | Source |')
		for (const row of ['| Readiness preflight | agent | passed |', '| Kickoff | human | approved | the owner |', '| Milestone M2 merge into dev | agent | merged |', '| Milestone M3 merge into dev | agent | merged |', '| Effect E3 | agent | performed |', '| Effect E2 | agent | performed |']) expect(ledger).toContain(row)
		expect(report).toContain('docs/mission-control.md holds the kickoff prompts')
		expect(report).toContain('A second fresh subagent runs gate 2')
		expect(report).toContain(W3.items[2].humanTest)
	})
	test('W3.13 it contains no question and passes the banned-pattern rules outside its technical record', () => {
		const report = closeOutReport(complete())
		expect(report).not.toContain('?')
		expect(banned(prose(report))).toEqual([])
		expect(report.slice(report.indexOf(TECHNICAL))).toContain(OWNER)
	})
	test('W3.14 an incomplete record gets no close-out', () => {
		expect(() => closeOutReport(afterM2())).toThrow('every milestone')
	})
})
