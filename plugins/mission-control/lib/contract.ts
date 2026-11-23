import { canonical, identity, intentDigest } from './contracts'
import { LINK, validateBrief } from './brief'
import { readRecordBytes, sha, updateRecord } from './mission'
import contractText from './contract-text.json'

// Schema 3: one contract, approved once at kickoff, delivered milestone by milestone.
// The reducer checks local consistency; approval and effect records come only from the
// plugin's own dialogs. It is a workflow coordinator, not a security boundary.

export const STOP_REASONS: readonly string[] = contractText.stopReasons
const SIZES = ['XS', 'S', 'M', 'L']
const TOP = ['schemaVersion', 'missionId', 'repository', 'outcome', 'scope', 'spec', 'design', 'ux', 'defense', 'cases', 'openQuestions', 'effects', 'readiness', 'milestones', 'items', 'brief']
const ITEM = ['id', 'title', 'milestone', 'size', 'outcome', 'inScope', 'outOfScope', 'dependsOn', 'done', 'automatedTest', 'humanTest', 'trace']
// Action fields: [required, optional].
const PUBLIC: Record<string, [string[], string[]?]> = {
	amend: [['contract', 'reason']], replan: [['itemId', 'into']], file: [[], ['item', 'followUp']],
	delegate: [['itemId', 'executor']], 'item-done': [['itemId', 'evidence', 'review']],
	candidate: [['milestoneId', 'pr', 'head', 'base']],
	review: [['milestoneId', 'gate', 'fingerprint', 'passed', 'reviewer', 'record']],
	disposition: [['milestoneId', 'gate', 'outcome', 'record'], ['itemIds']],
	evidence: [['milestoneId', 'fingerprint', 'results', 'humanTest']],
	assume: [['question', 'assumption', 'why']], stop: [['reason', 'question', 'options', 'recommendation', 'blocks']],
	resume: [['stopId', 'answer', 'source']],
}
// Produced only by the plugin's own tools and dialogs, never by mission_update.
const INTERNAL: Record<string, [string[], string[]?]> = {
	'approval-pending': [['kind', 'digest'], ['effectId', 'effect', 'why']], approve: [['digest', 'responder']],
	preflight: [['digest', 'results']], effect: [[], ['effectId', 'effect', 'why', 'responder']],
	'merge-requested': [['milestoneId', 'fingerprint']], merged: [['milestoneId', 'fingerprint', 'commit']],
	recover: [['milestoneId', 'fingerprint']],
}

export type Item = {
	id: string; title: string; milestone: string; size: 'XS' | 'S' | 'M' | 'L'; outcome: string; inScope: string[]; outOfScope: string[]
	dependsOn: string[]; done: string[]; automatedTest: string; humanTest: string; trace: string[]
}
export type Contract = {
	schemaVersion: 3; missionId: string; repository: string; outcome: string; scope: { in: string[]; out: string[] }; spec: string
	design: { high: string; low: string }; ux: string[]; defense: string
	cases: { id: string; case: string; mitigation: string }[]
	openQuestions: { id: string; question: string; default: string }[]
	effects: { id: string; effect: string; preAuthorized: boolean; source: string }[]
	readiness: { id: string; check: string; evidence: string }[]
	milestones: { id: string; title: string; exit: string[] }[]
	items: Item[]; brief: { markdown: string; url: string }
}
export type Candidate = { repo: string; pr: number; head: string; base: string }
export type Result = { criterion: string; result: string }
export type ItemState = {
	id: string; origin: 'contract' | 'finding'; status: 'planned' | 'delegated' | 'done'
	executor?: { kind: 'thread' | 'subagent'; id: string }; evidence?: Result[]; review?: { reviewer: string; record: string }
}
export type Review = { gate: 1 | 2; fingerprint: string; passed: boolean; reviewer: string; record: string }
export type MilestoneState = {
	id: string; status: 'open' | 'candidate' | 'merge-pending' | 'merged'; generation: number; failed: [number, number]
	reviews: Review[]; dispositions: { gate: 1 | 2; outcome: 'fixed' | 'replanned' | 'filed'; record: string; itemIds: string[]; at: string }[]
	candidate?: Candidate; evidence?: { fingerprint: string; results: Result[]; humanTest: string }; mergeCommit?: string
}
export type Stop = {
	id: string; reason: string; question: string; options: string[]; recommendation: string; blocks: string[]; at: string
	resolved?: { answer: string; source: string; at: string }
}
export type Pending = { kind: 'kickoff' | 'effect'; digest: string; effectId?: string; effect?: string; why?: string }
export type ContractRecord = {
	schemaVersion: 3; thread: string; contract: Contract; items: ItemState[]; filed: Item[]; followUps: { id: string; text: string }[]
	milestones: MilestoneState[]; stops: Stop[]; assumptions: { question: string; assumption: string; why: string; at: string }[]
	amendments: { reason: string; digest: string; approvalKept: boolean; at: string }[]
	performed: { effectId?: string; effect: string; why?: string; preAuthorized: boolean; responder?: string; at: string }[]
	approval?: { digest: string; responder: string; at: string }
	preflight?: { digest: string; results: { check: string; passed: boolean; detail: string }[]; passed: boolean; at: string }
	pendingApproval?: Pending
	events: { sequence: number; at: string; action: Action }[]
}
export type Action = { type: string; [field: string]: any }

function fail(path: string, detail: string): never { throw new Error(`Refused (${path}): ${detail}`) }
const at = (path: string, key: string) => path ? `${path}.${key}` : key
function shape(value: any, path: string, required: string[], optional: string[] = []) {
	if (!value || typeof value !== 'object' || Array.isArray(value) || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) fail(path || 'input', 'an object is required')
	for (const key of required) if (!Object.hasOwn(value, key)) fail(at(path, key), 'missing')
	for (const key of Object.keys(value)) if (!required.includes(key) && !optional.includes(key)) fail(at(path, key), 'unknown field')
}
function str(value: unknown, path: string): string {
	if (typeof value !== 'string' || !value.trim()) fail(path, 'non-empty text is required')
	return value
}
function strs(value: unknown, path: string, empty = false): string[] {
	if (!Array.isArray(value) || (!empty && !value.length)) fail(path, empty ? 'a list is required' : 'a non-empty list is required')
	value.forEach((v, i) => str(v, `${path}[${i}]`))
	if (new Set(value).size !== value.length) fail(path, 'duplicate entries')
	return value
}
function list(value: unknown, path: string, empty: boolean): any[] {
	if (!Array.isArray(value) || (!empty && !value.length)) fail(path, empty ? 'a list is required' : 'a non-empty list is required')
	return value
}
function id(value: unknown, path: string): string {
	try { identity(value) } catch { fail(path, 'an ID of letters, digits, ".", "_" or "-" is required') }
	return value as string
}
function link(value: unknown, path: string) {
	if (typeof value !== 'string' || !LINK.test(value) || /[\s\p{Cc}\p{Cf}]/u.test(value)) fail(path, 'an https link on ampcode.com or github.com is required')
}
function gitSha(value: unknown, path: string): string {
	try { sha(value) } catch { fail(path, 'a full Git SHA is required') }
	return value as string
}
const sorted = (values: string[]) => canonical([...values].sort())

function parseItem(value: any, path: string): Item {
	shape(value, path, ITEM)
	id(value.id, at(path, 'id')); str(value.title, at(path, 'title')); id(value.milestone, at(path, 'milestone'))
	if (!SIZES.includes(value.size)) fail(at(path, 'size'), value.size === 'XL' ? 'XL is not allowed; split the item into items of size L or smaller' : 'XS, S, M or L is required')
	str(value.outcome, at(path, 'outcome')); strs(value.inScope, at(path, 'inScope')); strs(value.outOfScope, at(path, 'outOfScope'), true)
	strs(value.dependsOn, at(path, 'dependsOn'), true); strs(value.done, at(path, 'done'))
	str(value.automatedTest, at(path, 'automatedTest')); str(value.humanTest, at(path, 'humanTest')); strs(value.trace, at(path, 'trace'), true)
	return structuredClone(value)
}
// Milestone membership, dependencies (known, same or earlier milestone) and cycles.
function graph(milestones: Contract['milestones'], items: { item: Item; path: string }[]) {
	const order = new Map(milestones.map((m, i) => [m.id, i]))
	const byId = new Map(items.map(x => [x.item.id, x.item]))
	for (const { item, path } of items) if (!order.has(item.milestone)) fail(at(path, 'milestone'), `unknown milestone ${item.milestone}`)
	for (const { item, path } of items) for (const dep of item.dependsOn) {
		const other = byId.get(dep)
		if (!other) fail(at(path, 'dependsOn'), `unknown item ${dep}`)
		if (order.get(other.milestone)! > order.get(item.milestone)!) fail(at(path, 'dependsOn'), `${dep} is in a later milestone`)
	}
	for (const { item, path } of items) {
		const seen = new Set<string>(), stack = [...item.dependsOn]
		while (stack.length) {
			const dep = stack.pop()!
			if (dep === item.id) fail(at(path, 'dependsOn'), `dependency cycle through ${item.id}`)
			if (!seen.has(dep)) { seen.add(dep); stack.push(...byId.get(dep)!.dependsOn) }
		}
	}
}
const contractIds = (c: Contract) => [...c.cases, ...c.openQuestions, ...c.effects, ...c.readiness, ...c.milestones, ...c.items].map(x => x.id)

/** Validate a schema 3 contract. Each refusal names the field, such as "Refused (items[1].done)". */
export function parseContract(value: unknown): Contract {
	let bytes: number
	try { bytes = Buffer.byteLength(canonical(value)) } catch { fail('contract', 'JSON values only') }
	if (bytes > 1024 * 1024) fail('contract', 'exceeds 1 MiB')
	const c = value as any
	shape(c, '', TOP)
	if (c.schemaVersion !== 3) fail('schemaVersion', 'must be 3')
	id(c.missionId, 'missionId')
	if (typeof c.repository !== 'string' || !/^[\w.-]+\/[\w.-]+$/.test(c.repository)) fail('repository', '"owner/name" is required')
	str(c.outcome, 'outcome')
	shape(c.scope, 'scope', ['in', 'out']); strs(c.scope.in, 'scope.in'); strs(c.scope.out, 'scope.out', true)
	str(c.spec, 'spec')
	shape(c.design, 'design', ['high', 'low']); str(c.design.high, 'design.high'); str(c.design.low, 'design.low')
	list(c.ux, 'ux', true).forEach((u, i) => link(u, `ux[${i}]`))
	str(c.defense, 'defense')
	const ids = new Set<string>()
	const unique = (value: unknown, path: string) => {
		if (ids.has(id(value, path))) fail(path, `duplicate ID ${value}`)
		ids.add(value as string)
	}
	const rows = (key: string, fields: string[], empty: boolean) => list(c[key], key, empty).forEach((row, i) => {
		const path = `${key}[${i}]`
		shape(row, path, ['id', ...fields]); unique(row.id, `${path}.id`)
		for (const field of fields) str(row[field], `${path}.${field}`)
	})
	rows('cases', ['case', 'mitigation'], false)
	rows('openQuestions', ['question', 'default'], true)
	list(c.effects, 'effects', true).forEach((e, i) => {
		const path = `effects[${i}]`
		shape(e, path, ['id', 'effect', 'preAuthorized', 'source']); unique(e.id, `${path}.id`)
		str(e.effect, `${path}.effect`); str(e.source, `${path}.source`)
		if (typeof e.preAuthorized !== 'boolean') fail(`${path}.preAuthorized`, 'true or false is required')
	})
	rows('readiness', ['check', 'evidence'], true)
	list(c.milestones, 'milestones', false).forEach((m, i) => {
		const path = `milestones[${i}]`
		shape(m, path, ['id', 'title', 'exit']); unique(m.id, `${path}.id`); str(m.title, `${path}.title`); strs(m.exit, `${path}.exit`)
	})
	list(c.items, 'items', false).forEach((item, i) => { parseItem(item, `items[${i}]`); unique(item.id, `items[${i}].id`) })
	graph(c.milestones, c.items.map((item: Item, i: number) => ({ item, path: `items[${i}]` })))
	c.milestones.forEach((m: any, i: number) => { if (!c.items.some((item: Item) => item.milestone === m.id)) fail(`milestones[${i}]`, `milestone ${m.id} has no item`) })
	shape(c.brief, 'brief', ['markdown', 'url'])
	try { validateBrief(c.brief.markdown) } catch (error) { fail('brief.markdown', (error as Error).message) }
	link(c.brief.url, 'brief.url')
	return structuredClone(c)
}

/** The kickoff approval binds to this digest of the 13 baseline parts. A milestone's criteria are
 * the sorted done criteria of its baseline items, so a re-plan that keeps them keeps the digest. */
export function approvalDigest(c: Contract): string {
	const { missionId, repository, outcome, scope, spec, design, ux, defense, cases, openQuestions, effects, brief } = c
	const milestones = c.milestones.map(m => ({ id: m.id, title: m.title, exit: m.exit, criteria: c.items.filter(i => i.milestone === m.id).flatMap(i => i.done).sort() }))
	return intentDigest({ missionId, repository, outcome, scope, spec, design, ux, defense, cases, openQuestions, effects, brief: { markdown: brief.markdown, url: brief.url }, milestones })
}
function milestoneOf(s: ContractRecord, milestoneId: unknown, path = 'milestoneId'): MilestoneState {
	const m = s.milestones.find(m => m.id === milestoneId)
	if (!m) fail(path, `unknown milestone ${milestoneId}`)
	return m
}
/** Reviews and evidence bind to this fingerprint of the contract, milestone, candidate and generation. */
export function fingerprint(record: ContractRecord, milestoneId: string): string {
	const m = milestoneOf(record, milestoneId)
	return intentDigest([approvalDigest(record.contract), milestoneId, m.candidate ?? null, m.generation])
}
const allItems = (s: ContractRecord) => [...s.contract.items, ...s.filed]
const itemsIn = (s: ContractRecord, milestoneId: string) => allItems(s).filter(i => i.milestone === milestoneId)
const stateOf = (s: ContractRecord, itemId: string) => s.items.find(i => i.id === itemId)!
const openStops = (s: ContractRecord, milestoneId: string) => {
	const names = [milestoneId, ...itemsIn(s, milestoneId).map(i => i.id)]
	return s.stops.filter(stop => !stop.resolved && stop.blocks.some(b => names.includes(b)))
}
/** A milestone is blocked when an open stop names it or one of its items. */
export function blocked(record: ContractRecord, milestoneId: string): boolean {
	milestoneOf(record, milestoneId)
	return openStops(record, milestoneId).length > 0
}
/** Every merge blocker the record knows. GitHub's merge readiness is checked by the merge tool. */
export function blockers(record: ContractRecord, milestoneId: string): string[] {
	const m = milestoneOf(record, milestoneId)
	if (m.status === 'merged') return ['Milestone is merged']
	const out: string[] = []
	if (m.status === 'merge-pending') out.push('Merge already requested; reconcile it')
	if (record.approval?.digest !== approvalDigest(record.contract)) out.push('Kickoff approval on the current contract required')
	const stops = openStops(record, milestoneId)
	if (stops.length) out.push(`Blocked by stop ${stops.map(s => s.id).join(', ')}`)
	const open = itemsIn(record, milestoneId).filter(i => stateOf(record, i.id).status !== 'done')
	if (open.length) out.push(`Items not done: ${open.map(i => i.id).join(', ')}`)
	const index = record.milestones.indexOf(m)
	const earlier = record.milestones.slice(0, index).filter(e => e.status !== 'merged')
	if (earlier.length) out.push(`Earlier milestones not merged: ${earlier.map(e => e.id).join(', ')}`)
	if (!m.candidate) out.push('Candidate required')
	else {
		const fp = fingerprint(record, milestoneId)
		for (const gate of [1, 2]) if (!m.reviews.findLast(r => r.gate === gate && r.fingerprint === fp)?.passed) out.push(`Review ${gate} must pass on the current fingerprint`)
		if (m.evidence?.fingerprint !== fp) out.push('Evidence required on the current fingerprint')
	}
	return out
}

const now = () => new Date().toISOString()
function initial(thread: string): ContractRecord {
	return { schemaVersion: 3, thread, contract: null as any, items: [], filed: [], followUps: [], milestones: [], stops: [], assumptions: [], amendments: [], performed: [], events: [] }
}
const fresh = (milestoneId: string): MilestoneState => ({ id: milestoneId, status: 'open', generation: 0, failed: [0, 0], reviews: [], dispositions: [] })

export function createRecord(thread: string, contract: unknown, time = now()): ContractRecord {
	str(thread, 'thread')
	return apply(initial(thread), { type: 'start', contract }, time)
}
/** The public dispatch behind mission_update: the 12 public actions only. */
export function update(record: ContractRecord, action: Action, time = now()): ContractRecord {
	const type = action?.type
	if (Object.hasOwn(INTERNAL, type)) fail('type', `"${type}" is an internal action, produced only by the plugin's own tools and dialogs`)
	if (!Object.hasOwn(PUBLIC, type)) fail('type', `use one of ${Object.keys(PUBLIC).join(', ')}`)
	return apply(structuredClone(record), action, time)
}
/** The plugin's own dispatch: public and internal actions. Never expose it to agent input. */
export function advance(record: ContractRecord, action: Action, time = now()): ContractRecord {
	if (!Object.hasOwn(PUBLIC, action?.type) && !Object.hasOwn(INTERNAL, action?.type)) fail('type', 'unknown action')
	return apply(structuredClone(record), action, time)
}

// Rebuilt plan checks: filed items and follow-ups fit the contract and keep IDs unique.
function plan(c: Contract, filed: Item[], followUps: { id: string }[]) {
	const ids = new Set(contractIds(c))
	for (const [i, x] of [...filed, ...followUps].entries()) {
		if (ids.has(x.id)) fail(i < filed.length ? `filed[${i}].id` : `followUps[${i - filed.length}].id`, `duplicate ID ${x.id}`)
		ids.add(x.id)
	}
	graph(c.milestones, [...c.items.map((item, i) => ({ item, path: `items[${i}]` })), ...filed.map((item, i) => ({ item, path: `filed[${i}]` }))])
}
function results(value: unknown, path: string, criteria: string[]): Result[] {
	const out = list(value, path, false).map((r, i) => {
		shape(r, `${path}[${i}]`, ['criterion', 'result']); str(r.criterion, `${path}[${i}].criterion`); str(r.result, `${path}[${i}].result`)
		return { criterion: r.criterion, result: r.result }
	})
	if (sorted(out.map(r => r.criterion)) !== sorted(criteria)) fail(path, `one result per criterion is required, for: ${criteria.join('; ')}`)
	return out
}
function itemFor(s: ContractRecord, itemId: unknown) {
	const def = allItems(s).find(i => i.id === itemId)
	if (!def) fail('itemId', `unknown item ${itemId}`)
	return { def, state: stateOf(s, def.id) }
}
function open(s: ContractRecord, milestoneId: string, path = 'milestoneId') {
	const m = milestoneOf(s, milestoneId, path)
	if (m.status === 'merged') fail(path, `${m.id} is merged`)
	if (m.status === 'merge-pending') fail(path, `reconcile the pending merge of ${m.id} first`)
	return m
}
function current(s: ContractRecord, m: MilestoneState, value: unknown) {
	if (!m.candidate || value !== fingerprint(s, m.id)) fail('fingerprint', `missing or stale fingerprint for ${m.id}; read the current one from the status`)
}
function gate(value: unknown): 1 | 2 {
	if (value !== 1 && value !== 2) fail('gate', '1 or 2 is required')
	return value
}
function preflighted(s: ContractRecord, digest: string) {
	if (s.preflight?.digest !== digest) fail('preflight', 'run the readiness preflight on the current contract first')
	if (!s.preflight.passed) fail('preflight', 'the readiness preflight failed; fix it and run it again')
}
function pending(s: ContractRecord, match: Partial<Pending>) {
	const p = s.pendingApproval
	if (!p || p.digest !== approvalDigest(s.contract) || Object.entries(match).some(([k, v]) => (p as any)[k] !== v)) fail('approval', 'no matching approval dialog is pending on the current contract')
}

// Replay calls apply on its own accumulator; public transitions pass a clone.
function apply(s: ContractRecord, action: Action, time: string): ContractRecord {
	const fields = action?.type === 'start' ? [['contract']] : (PUBLIC[action?.type] ?? INTERNAL[action?.type])
	if (!fields) fail('type', 'unknown action')
	shape(action, '', ['type', ...fields[0]], fields[1])
	const a = action as any
	const digest = s.contract && approvalDigest(s.contract)
	switch (a.type) {
		case 'start': {
			if (s.events.length) fail('type', 'start only creates a record')
			s.contract = parseContract(a.contract)
			s.items = s.contract.items.map(i => ({ id: i.id, origin: 'contract', status: 'planned' }))
			s.milestones = s.contract.milestones.map(m => fresh(m.id))
			break
		}
		case 'amend': {
			str(a.reason, 'reason')
			const c = parseContract(a.contract)
			if (s.milestones.some(m => m.status === 'merge-pending')) fail('contract', 'reconcile the pending merge first')
			s.milestones.filter(m => m.status === 'merged').forEach((m, i) => {
				const items = (x: Contract) => canonical(x.items.filter(item => item.milestone === m.id))
				if (canonical(c.milestones[i]) !== canonical(s.contract.milestones[i]) || items(c) !== items(s.contract)) fail(`milestones[${i}]`, `${m.id} is merged and cannot change`)
			})
			plan(c, s.filed, s.followUps)
			const kept = new Set([...c.milestones.map(m => m.id), ...c.items.map(i => i.id), ...s.filed.map(i => i.id)])
			for (const stop of s.stops) for (const name of stop.blocks) if (!stop.resolved && !kept.has(name)) fail('contract', `open stop ${stop.id} names ${name}, which this amend removes; resume the stop first`)
			const after = approvalDigest(c)
			// With the digest kept, only the item fields section 3 lists may change: IDs, outcomes,
			// milestones and done criteria are baseline.
			if (after === digest) {
				if (sorted(c.items.map(i => i.id)) !== sorted(s.contract.items.map(i => i.id))) fail('items', 'item IDs are part of the baseline; rename an item with replan, or change a criterion (a new digest)')
				c.items.forEach((item, i) => {
					const old = s.contract.items.find(o => o.id === item.id)!
					if (old.outcome !== item.outcome) fail(`items[${i}].outcome`, 'an item outcome is part of the baseline; change a criterion (a new digest) or file a new item')
					if (old.milestone !== item.milestone) fail(`items[${i}].milestone`, 'an item milestone is part of the baseline; move work with replan or a new digest')
					if (sorted(old.done) !== sorted(item.done)) fail(`items[${i}].done`, 'item criteria are part of the baseline; split them with replan or change them with a new digest')
				})
			}
			// Failed-round counters survive: a milestone that failed a review stays the earliest unmerged
			// one and keeps its ID, items, outcomes and criteria. Record a "replanned" disposition first to change them.
			// A candidate also stays the earliest unmerged milestone, so no copy can be put ahead of it.
			for (const m of s.milestones) {
				const failed = m.failed.some(n => n > 0)
				if (!failed && m.status !== 'candidate') continue
				const index = c.milestones.findIndex(x => x.id === m.id)
				if (index > 0 && c.milestones.slice(0, index).some(x => s.milestones.find(y => y.id === x.id)?.status !== 'merged')) fail('milestones', failed ? `${m.id} has failed review rounds and must stay the earliest unmerged milestone; record a "replanned" disposition first to change the order` : `${m.id} is a candidate and must stay the earliest unmerged milestone`)
				if (!failed) continue
				const held = s.contract.items.filter(i => i.milestone === m.id)
				const criteria = (x: Contract) => new Set([...x.items.filter(i => i.milestone === m.id).flatMap(i => i.done), ...(x.milestones.find(y => y.id === m.id)?.exit ?? [])])
				const kept = criteria(c), before = criteria(s.contract)
				if (index < 0 || held.some(i => !c.items.some(x => x.id === i.id && x.milestone === m.id && x.outcome === i.outcome)) || [...before].some(k => !kept.has(k))) fail('milestones', `${m.id} has failed review rounds; it keeps its ID, items, outcomes and criteria; record a "replanned" disposition first to change them`)
			}
			const readinessChanged = canonical(c.readiness) !== canonical(s.contract.readiness)
			s.items = [
				...c.items.map(item => {
					const old = s.contract.items.find(o => o.id === item.id)
					return old && canonical(old) === canonical(item) ? stateOf(s, item.id) : { id: item.id, origin: 'contract' as const, status: 'planned' as const }
				}),
				...s.items.filter(i => i.origin === 'finding'),
			]
			s.milestones = c.milestones.map(m => s.milestones.find(x => x.id === m.id) ?? fresh(m.id))
			s.contract = c
			if (after !== digest) { delete s.approval; delete s.preflight; delete s.pendingApproval }
			else if (readinessChanged) delete s.preflight
			s.amendments.push({ reason: a.reason, digest: after, approvalKept: after === digest, at: time })
			break
		}
		case 'replan': {
			const { def, state } = itemFor(s, a.itemId)
			const m = open(s, def.milestone, 'itemId')
			// Only a "replanned" disposition on each failing gate resets its counter and so allows a replan.
			if (m.failed.some(n => n > 0)) fail('itemId', `${m.id} has failed review rounds; record a "replanned" disposition on each failing gate first`)
			if (state.status === 'done') fail('itemId', `${def.id} is done; reopen it first with a "replanned" disposition`)
			const into = list(a.into, 'into', false).map((x, i) => parseItem(x, `into[${i}]`))
			if (sorted(into.flatMap(i => i.done)) !== sorted(def.done) || into.some(i => i.milestone !== def.milestone)) fail('into', 'the new items must hold exactly the original criteria, verbatim, in the same milestone; put extra checks in automatedTest')
			const ids = into.map(i => i.id)
			const rewrite = (i: Item) => i.dependsOn.includes(def.id) ? { ...i, dependsOn: [...new Set(i.dependsOn.flatMap(d => d === def.id ? ids : [d]))] } : i
			const splice = (items: Item[]) => items.flatMap(i => i.id === def.id ? into : [rewrite(i)])
			const c = state.origin === 'contract' ? parseContract({ ...s.contract, items: splice(s.contract.items) }) : { ...s.contract, items: s.contract.items.map(rewrite) }
			const filed = state.origin === 'finding' ? splice(s.filed) : s.filed.map(rewrite)
			plan(c, filed, s.followUps)
			s.contract = c; s.filed = filed
			s.items = s.items.flatMap(i => i.id === def.id ? ids.map(id => ({ id, origin: state.origin, status: 'planned' as const })) : [i])
			// An open stop on the original item keeps blocking its replacements.
			for (const stop of s.stops) if (!stop.resolved && stop.blocks.includes(def.id)) stop.blocks = [...new Set(stop.blocks.flatMap(b => b === def.id ? ids : [b]))]
			break
		}
		case 'file': {
			const keys = ['item', 'followUp'].filter(k => Object.hasOwn(a, k))
			if (keys.length !== 1) fail('file', 'give exactly one of item or followUp')
			const first = s.milestones.findIndex(m => m.status !== 'merged')
			if (first < 0) fail('file', 'the mission is complete')
			const taken = new Set([...contractIds(s.contract), ...s.filed.map(i => i.id), ...s.followUps.map(f => f.id)])
			if (keys[0] === 'followUp') {
				shape(a.followUp, 'followUp', ['id', 'text']); id(a.followUp.id, 'followUp.id'); str(a.followUp.text, 'followUp.text')
				if (first !== s.milestones.length - 1) fail('followUp', 'a follow-up is filed only when the earliest unmerged milestone is the last one; file an item in a later milestone instead')
				if (taken.has(a.followUp.id)) fail('followUp.id', `duplicate ID ${a.followUp.id}`)
				s.followUps.push({ id: a.followUp.id, text: a.followUp.text })
			} else {
				const item = parseItem(a.item, 'item')
				const index = s.milestones.findIndex(m => m.id === item.milestone)
				if (index < 0) fail('item.milestone', `unknown milestone ${item.milestone}`)
				if (index <= first) fail('item.milestone', `file into a milestone after the earliest unmerged milestone (${s.milestones[first].id}), so a current candidate is never voided`)
				if (taken.has(item.id)) fail('item.id', `duplicate ID ${item.id}`)
				plan(s.contract, [...s.filed, item], s.followUps)
				s.filed.push(item); s.items.push({ id: item.id, origin: 'finding', status: 'planned' })
			}
			break
		}
		case 'delegate': {
			const { def, state } = itemFor(s, a.itemId)
			open(s, def.milestone, 'itemId')
			if (state.status === 'done') fail('itemId', `${def.id} is done`)
			shape(a.executor, 'executor', ['kind', 'id'])
			if (a.executor.kind === 'thread') { if (typeof a.executor.id !== 'string' || !/^T-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(a.executor.id)) fail('executor.id', 'a thread ID such as T-01a2… is required') }
			else if (a.executor.kind === 'subagent') str(a.executor.id, 'executor.id')
			else fail('executor.kind', 'thread or subagent is required')
			state.status = 'delegated'; state.executor = { kind: a.executor.kind, id: a.executor.id }
			break
		}
		case 'item-done': {
			const { def, state } = itemFor(s, a.itemId)
			const m = open(s, def.milestone, 'itemId')
			if (state.status === 'done') fail('itemId', `${def.id} is already done`)
			const evidence = results(a.evidence, 'evidence', def.done)
			shape(a.review, 'review', ['reviewer', 'record']); str(a.review.reviewer, 'review.reviewer'); str(a.review.record, 'review.record')
			if (a.review.reviewer === s.thread) fail('review.reviewer', 'the review must be fresh, not by the mission thread')
			state.status = 'done'; state.evidence = evidence; state.review = { reviewer: a.review.reviewer, record: a.review.record }
			// Work done after a candidate (a reopened or amended item) voids the milestone's reviews and evidence.
			if (m.candidate) { m.generation++; m.reviews = []; delete m.evidence }
			break
		}
		case 'candidate': {
			const m = open(s, a.milestoneId)
			const earlier = s.milestones.slice(0, s.milestones.indexOf(m)).filter(e => e.status !== 'merged')
			if (earlier.length) fail('milestoneId', `earlier milestones are not merged: ${earlier.map(e => e.id).join(', ')}`)
			const notDone = itemsIn(s, m.id).filter(i => stateOf(s, i.id).status !== 'done')
			if (notDone.length) fail('milestoneId', `items not done: ${notDone.map(i => i.id).join(', ')}`)
			if (!Number.isSafeInteger(a.pr) || a.pr <= 0) fail('pr', 'a pull request number is required')
			const c: Candidate = { repo: s.contract.repository, pr: a.pr, head: gitSha(a.head, 'head'), base: gitSha(a.base, 'base') }
			// A new candidate voids reviews and evidence; failed-round counters survive.
			if (!m.candidate || canonical(m.candidate) !== canonical(c)) { m.reviews = []; delete m.evidence }
			m.candidate = c; m.status = 'candidate'
			break
		}
		case 'review': {
			const m = open(s, a.milestoneId)
			current(s, m, a.fingerprint)
			const g = gate(a.gate)
			if (typeof a.passed !== 'boolean') fail('passed', 'true or false is required')
			str(a.reviewer, 'reviewer'); str(a.record, 'record')
			if (a.reviewer === s.thread) fail('reviewer', 'the reviewer must not be the mission thread')
			if (g === 2) {
				const first = m.reviews.findLast(r => r.gate === 1 && r.fingerprint === a.fingerprint)
				if (!first?.passed) fail('gate', 'gate 2 needs a passing gate 1 review on the same fingerprint')
				if (first.reviewer === a.reviewer) fail('reviewer', 'gate 2 needs a second, independent reviewer')
			}
			if (!a.passed && m.failed[g - 1] >= 3) fail('passed', `gate ${g} has 3 failed rounds; under the disposition policy, record a "replanned" disposition that reopens the items first ("fixed" and "filed" are records only)`)
			m.reviews.push({ gate: g, fingerprint: a.fingerprint, passed: a.passed, reviewer: a.reviewer, record: a.record })
			if (!a.passed) m.failed[g - 1]++
			break
		}
		case 'disposition': {
			const m = open(s, a.milestoneId)
			const g = gate(a.gate)
			if (!['fixed', 'replanned', 'filed'].includes(a.outcome)) fail('outcome', 'fixed, replanned or filed is required')
			str(a.record, 'record')
			const itemIds: string[] = a.outcome === 'fixed' ? [] : strs(a.itemIds, 'itemIds')
			if (a.outcome === 'fixed') { if (Object.hasOwn(a, 'itemIds')) fail('itemIds', 'a "fixed" disposition names no items') }
			else if (a.outcome === 'replanned') {
				for (const itemId of itemIds) {
					if (!itemsIn(s, m.id).some(i => i.id === itemId)) fail('itemIds', `${itemId} is not an item of ${m.id}`)
					if (stateOf(s, itemId).status === 'planned') fail('itemIds', `${itemId} is not done or delegated, so there is nothing to reopen`)
				}
				for (const itemId of itemIds) {
					const state = stateOf(s, itemId)
					state.status = 'planned'; delete state.executor; delete state.evidence; delete state.review
				}
				// Reopened work voids the milestone's reviews and evidence, even on the same head.
				m.generation++; m.reviews = []; delete m.evidence
				m.failed[g - 1] = 0
			} else {
				for (const itemId of itemIds) if (!s.filed.some(i => i.id === itemId) && !s.followUps.some(f => f.id === itemId)) fail('itemIds', `${itemId} is not a filed item or follow-up`)
			}
			m.dispositions.push({ gate: g, outcome: a.outcome, record: a.record, itemIds, at: time })
			break
		}
		case 'evidence': {
			const m = open(s, a.milestoneId)
			current(s, m, a.fingerprint)
			const criteria = [...itemsIn(s, m.id).flatMap(i => i.done), ...s.contract.milestones.find(x => x.id === m.id)!.exit]
			m.evidence = { fingerprint: a.fingerprint, results: results(a.results, 'results', criteria), humanTest: str(a.humanTest, 'humanTest') }
			break
		}
		case 'assume':
			s.assumptions.push({ question: str(a.question, 'question'), assumption: str(a.assumption, 'assumption'), why: str(a.why, 'why'), at: time })
			break
		case 'stop': {
			const reason = Number.isInteger(a.reason) && a.reason >= 1 && a.reason <= 5 ? STOP_REASONS[a.reason - 1] : STOP_REASONS.find(r => r === a.reason)
			if (!reason) fail('reason', `a stop names one of the five stop reasons, by number or exact text:\n${STOP_REASONS.map((r, i) => `${i + 1}. ${r}`).join('\n')}`)
			if (reason === STOP_REASONS[1]) fail('reason', 'with the plugin, an outside effect not in the contract is asked through mission_effect, not a stop')
			const question = str(a.question, 'question'), options = strs(a.options, 'options'), recommendation = str(a.recommendation, 'recommendation')
			const blocks = strs(a.blocks, 'blocks')
			const known = [...s.milestones.map(m => m.id), ...s.items.map(i => i.id)]
			blocks.forEach((b, i) => { if (!known.includes(b)) fail(`blocks[${i}]`, `unknown item or milestone ${b}`) })
			s.stops.push({ id: `S-${s.stops.length + 1}`, reason, question, options: [...options], recommendation, blocks: [...blocks], at: time })
			break
		}
		case 'resume': {
			const stop = s.stops.find(x => x.id === a.stopId && !x.resolved)
			if (!stop) fail('stopId', `no open stop ${a.stopId}`)
			stop.resolved = { answer: str(a.answer, 'answer'), source: str(a.source, 'source'), at: time }
			break
		}
		case 'approval-pending': {
			if (a.digest !== digest) fail('digest', 'stale: the contract changed')
			if (a.kind === 'kickoff') {
				if (['effectId', 'effect', 'why'].some(k => Object.hasOwn(a, k))) fail('kind', 'a kickoff approval names no effect')
				if (s.approval?.digest === digest) fail('kind', 'kickoff is already approved on this contract')
				preflighted(s, digest)
				s.pendingApproval = { kind: 'kickoff', digest }
			} else if (a.kind === 'effect') {
				if (Object.hasOwn(a, 'effectId')) {
					if (Object.hasOwn(a, 'effect') || Object.hasOwn(a, 'why')) fail('effectId', 'name a contract effect or describe a new one, not both')
					const e = s.contract.effects.find(e => e.id === a.effectId)
					if (!e) fail('effectId', `unknown effect ${a.effectId}`)
					if (e.preAuthorized) fail('effectId', `${e.id} is pre-authorized and needs no dialog`)
					s.pendingApproval = { kind: 'effect', digest, effectId: e.id }
				} else s.pendingApproval = { kind: 'effect', digest, effect: str(a.effect, 'effect'), why: str(a.why, 'why') }
			} else fail('kind', 'kickoff or effect is required')
			break
		}
		case 'approve':
			if (a.digest !== digest) fail('digest', 'stale: the contract changed while the dialog was open')
			pending(s, { kind: 'kickoff' })
			preflighted(s, digest)
			s.approval = { digest, responder: str(a.responder, 'responder'), at: time }
			delete s.pendingApproval
			break
		case 'preflight': {
			if (a.digest !== digest) fail('digest', 'stale: the contract changed')
			const checks = list(a.results, 'results', false).map((r, i) => {
				shape(r, `results[${i}]`, ['check', 'passed', 'detail'])
				if (typeof r.passed !== 'boolean') fail(`results[${i}].passed`, 'true or false is required')
				return { check: str(r.check, `results[${i}].check`), passed: r.passed, detail: str(r.detail, `results[${i}].detail`) }
			})
			s.preflight = { digest, results: checks, passed: checks.every(r => r.passed), at: time }
			break
		}
		case 'effect': {
			// Records a performed effect; the contract itself never changes here.
			if (Object.hasOwn(a, 'effectId')) {
				if (Object.hasOwn(a, 'effect') || Object.hasOwn(a, 'why')) fail('effectId', 'name a contract effect or describe a new one, not both')
				const e = s.contract.effects.find(e => e.id === a.effectId)
				if (!e) fail('effectId', `unknown effect ${a.effectId}`)
				if (e.preAuthorized) {
					// Pre-authorization comes from the approved contract, not from an amend since.
					if (s.approval?.digest !== digest) fail('effectId', `${e.id} is pre-authorized only by the approved contract; get kickoff approval on the current contract first`)
					if (Object.hasOwn(a, 'responder')) fail('responder', `${e.id} is pre-authorized; no dialog answers it`)
					s.performed.push({ effectId: e.id, effect: e.effect, preAuthorized: true, at: time })
				} else {
					pending(s, { kind: 'effect', effectId: e.id })
					s.performed.push({ effectId: e.id, effect: e.effect, preAuthorized: false, responder: str(a.responder, 'responder'), at: time })
					delete s.pendingApproval
				}
			} else {
				const effect = str(a.effect, 'effect'), why = str(a.why, 'why')
				pending(s, { kind: 'effect', effect, why })
				s.performed.push({ effect, why, preAuthorized: false, responder: str(a.responder, 'responder'), at: time })
				delete s.pendingApproval
			}
			break
		}
		case 'merge-requested': {
			const m = open(s, a.milestoneId)
			current(s, m, a.fingerprint)
			const missing = blockers(s, m.id)
			if (missing.length) fail('milestoneId', missing.join('; '))
			m.status = 'merge-pending'
			break
		}
		case 'merged': case 'recover': {
			const m = milestoneOf(s, a.milestoneId)
			if (m.status !== 'merge-pending') fail('milestoneId', `no merge of ${m.id} is pending`)
			current(s, m, a.fingerprint)
			if (a.type === 'merged') { m.mergeCommit = gitSha(a.commit, 'commit'); m.status = 'merged' }
			else { m.generation++; m.reviews = []; delete m.evidence; m.status = 'candidate' }
			break
		}
	}
	s.events.push({ sequence: s.events.length + 1, at: time, action: structuredClone(action) })
	return s
}

/** A record of a retired schema (the v1 single-PR flow or the v2 shadow flow). Nothing reads,
 * replays or rewrites it; the tools and hooks report this message and leave its bytes unchanged. */
export class RetiredSchema extends Error {
	constructor(schema: 'v1' | 'v2') {
		// Only v1 sent merges, so only a v1 record can have a merge request still open.
		const flow = schema === 'v1' ? 'single-PR mission' : 'shadow mission'
		const merge = schema === 'v1' ? ' If that mission requested a merge, check its pull request on GitHub first.' : ''
		super(`Retired schema: this thread's mission record is a ${schema} ${flow}, which mission-control no longer runs. Nothing was changed: the record stays on disk as it was.${merge} To continue the work, start a contract mission with mission_start { contract } in a new thread.`)
	}
}

/** Rebuild a record by replaying its events. A projection that differs from the replay is refused. */
export function parseRecord(value: unknown, thread: string): ContractRecord {
	const v = value as any
	if (v?.version === 1 && v.schemaVersion === undefined) throw new RetiredSchema('v1')
	if (v?.schemaVersion === 2) throw new RetiredSchema('v2')
	if (!v || typeof v !== 'object' || v.schemaVersion !== 3) throw new Error('Not a schema 3 contract mission record; preserve and investigate')
	if (v.thread !== thread) throw new Error('Mission record belongs to another thread')
	if (!Array.isArray(v.events) || !v.events.length) throw new Error('Mission record has no events')
	const s = initial(thread)
	v.events.forEach((e: any, i: number) => {
		shape(e, `events[${i}]`, ['sequence', 'at', 'action'])
		if (e.sequence !== i + 1 || (i === 0) !== (e.action?.type === 'start')) throw new Error(`Invalid event sequence at event ${i + 1}`)
		try { apply(s, e.action, str(e.at, `events[${i}].at`)) } catch (error) { throw new Error(`Event ${i + 1} does not replay: ${(error as Error).message}`) }
	})
	if (canonical(s) !== canonical(v)) throw new Error('Mission record projection differs from its replayed events; preserve and investigate')
	return s
}
export function loadContractRecord(path: string, thread: string): ContractRecord | undefined {
	const raw = readRecordBytes(path)
	return raw === undefined ? undefined : parseRecord(JSON.parse(raw), thread)
}
/** Save under the record lock. The record on disk must be this record minus its last event. */
export function saveContractRecord(path: string, record: ContractRecord) {
	parseRecord(record, record.thread)
	updateRecord(path, raw => {
		if (raw !== undefined) {
			const old = parseRecord(JSON.parse(raw), record.thread)
			if (old.events.length !== record.events.length - 1 || canonical(old.events) !== canonical(record.events.slice(0, -1))) throw new Error('Concurrent or stale mission update; reload')
		}
		return JSON.stringify(record, null, 2) + '\n'
	})
}
