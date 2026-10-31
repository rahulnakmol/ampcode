import { createHash, randomUUID } from 'node:crypto'
import { closeSync, existsSync, fsyncSync, mkdirSync, openSync, readFileSync, renameSync, statSync, unlinkSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { canonical } from './contracts'
import { parseMissionV2, type MissionV2 } from './mission-v2'

export type Risk = 'low' | 'medium' | 'high' | 'unknown'
export type Bundle = { spec: string; plan: string; technical: string; ux: string }
export type Candidate = { repo: string; pr: number; head: string; base: string; risk: Risk }
export type Review = { gate: number; fingerprint: string; passed: boolean; reviewer: string; record: string }
export type Mission = {
	version: 1; thread: string; requirements: string; phase: string; mode: 'auto' | 'ask'; generation: number
	design?: { bundle: Bundle; criteria: string[]; digest: string }
	approvedDesign?: string; defense?: string; candidate?: Candidate; riskFloor: Risk
	reviews: Review[]; evidence?: { results: string[]; tryIt: string; value: string; fingerprint: string }
	presented?: string; mergeApproval?: string; paused?: string; mergeCommit?: string
	events: { sequence: number; at: string; type: string; fingerprint: string }[]
}
export type Action =
	| { type: 'design'; bundle: Bundle; criteria: string[] }
	| { type: 'approve-design'; digest: string }
	| { type: 'defense'; digest: string; record: string }
	| { type: 'build' }
	| { type: 'mode'; mode: 'auto' | 'ask' }
	| { type: 'candidate'; candidate: Candidate }
	| ({ type: 'review' } & Review)
	| { type: 'evidence'; fingerprint: string; results: string[]; tryIt: string; value: string }
	| { type: 'presented' | 'approve-merge' | 'merge-requested'; fingerprint: string }
	| { type: 'merged'; fingerprint: string; commit: string }
	| { type: 'recover'; fingerprint: string }
	| { type: 'pause'; reason: string }
	| { type: 'resume' }

export function text(value: unknown): asserts value is string {
	if (typeof value !== 'string' || !value.trim()) throw new Error('Non-empty text required')
}
export function sha(value: unknown): asserts value is string {
	if (typeof value !== 'string' || !/^[a-f0-9]{40}$/.test(value)) throw new Error('Full Git SHA required')
}
export function digest(value: unknown) { return createHash('sha256').update(JSON.stringify(value)).digest('hex') }
export function fingerprint(s: Mission) { return digest([s.design?.digest, s.candidate, s.generation]) }
function event(s: Mission, type: string) {
	s.events.push({ sequence: s.events.length + 1, at: new Date().toISOString(), type, fingerprint: fingerprint(s) })
	return s
}
export function createMission(thread: string, requirements: string): Mission {
	text(thread); text(requirements)
	return event({ version: 1, thread, requirements, phase: 'requirements', mode: 'auto', generation: 0, riskFloor: 'unknown', reviews: [], events: [] }, 'start')
}
function invalidate(s: Mission) {
	s.reviews = []; delete s.evidence; delete s.presented; delete s.mergeApproval
}
function current(s: Mission, fp: string) {
	if (!s.candidate || fp !== fingerprint(s)) throw new Error('Missing or stale candidate')
}
export function blockers(s: Mission): string[] {
	const out: string[] = []
	if (s.paused) out.push('Paused: ' + s.paused)
	if (!s.design || s.approvedDesign !== s.design.digest) out.push('Owner design approval required')
	if (!s.defense) out.push('Whiteboard defense required')
	if (!s.candidate) out.push('Candidate required')
	if (s.candidate?.risk === 'unknown') out.push('Risk is unknown')
	const fp = fingerprint(s)
	for (const gate of [1, 2]) if (!s.reviews.some(r => r.gate === gate && r.passed && r.fingerprint === fp)) out.push(`Review ${gate} required`)
	if (!s.evidence || s.evidence.fingerprint !== fp) out.push('Acceptance evidence required')
	if (s.presented !== fp) out.push('Delivery evidence has not been presented')
	if ((s.mode === 'ask' || s.candidate?.risk === 'high') && s.mergeApproval !== fp) out.push('Owner merge acknowledgment required')
	return out
}

// Approval events are INTERNAL: the plugin produces them only after owner-restricted UI.
// These are local workflow gates, not tamper-resistant authorization against shell access.
export function advance(previous: Mission, action: Action): Mission {
	const s = structuredClone(previous)
	if (s.phase === 'merged') throw new Error('Mission is already merged')
	if (s.phase === 'merge-pending' && !['merged', 'recover', 'pause', 'resume'].includes(action.type)) throw new Error('Reconcile pending merge before changing the mission')
	if (s.paused && !['merged', 'recover', 'pause', 'resume'].includes(action.type)) throw new Error('Mission paused; resume explicitly before further work')
	switch (action.type) {
		case 'design': {
			const { spec, plan, technical, ux } = action.bundle
			for (const value of [spec, plan, technical, ux]) text(value)
			if (!Array.isArray(action.criteria) || action.criteria.length === 0) throw new Error('Acceptance criteria required')
			action.criteria.forEach(text)
			if (new Set(action.criteria).size !== action.criteria.length) throw new Error('Acceptance criteria must be unique')
			const bundle = { spec, plan, technical, ux }
			s.design = { bundle, criteria: [...action.criteria], digest: digest([s.requirements, bundle, action.criteria]) }
			delete s.approvedDesign; delete s.defense; delete s.candidate; invalidate(s)
			s.phase = 'awaiting-design-approval'; break
		}
		case 'approve-design':
			if (!s.design || action.digest !== s.design.digest) throw new Error('Missing or stale design')
			if (s.phase !== 'awaiting-design-approval') throw new Error('Design approval is not pending')
			s.approvedDesign = action.digest; s.phase = 'defense'; break
		case 'defense':
			if (!s.design || s.approvedDesign !== s.design.digest) throw new Error('Owner design approval required')
			if (action.digest !== s.design.digest) throw new Error('stale design')
			if (s.phase !== 'defense') throw new Error('Design defense is not pending; revise the design to reopen it')
			text(action.record); s.defense = action.record; s.phase = 'ready-to-build'; break
		case 'build':
			if (!s.design || s.approvedDesign !== s.design.digest || !s.defense) throw new Error('Approved design and whiteboard defense required')
			if (s.phase !== 'ready-to-build') throw new Error('Build entry already completed; register changed candidates for repair/review')
			s.phase = 'building'; break
		case 'mode':
			if (!['auto', 'ask'].includes(action.mode)) throw new Error('Invalid merge mode')
			s.mode = action.mode; delete s.presented; delete s.mergeApproval; break
		case 'candidate': {
			if (!['building', 'reviewing', 'evidence'].includes(s.phase)) throw new Error('Begin build first')
			const c = action.candidate
			sha(c.head); sha(c.base)
			if (!/^[\w.-]+\/[\w.-]+$/.test(c.repo) || !Number.isSafeInteger(c.pr) || c.pr <= 0 || !['low', 'medium', 'high', 'unknown'].includes(c.risk)) throw new Error('Invalid candidate')
			if (s.candidate && (c.repo !== s.candidate.repo || c.pr !== s.candidate.pr)) throw new Error('Cannot move a mission to another PR')
			s.riskFloor = s.riskFloor === 'high' || c.risk === 'high' ? 'high' : c.risk
			const risk = c.risk === 'unknown' ? 'unknown' : s.riskFloor
			s.candidate = { repo: c.repo, pr: c.pr, head: c.head, base: c.base, risk }; invalidate(s); s.phase = 'reviewing'; break
		}
		case 'review':
			current(s, action.fingerprint)
			if (![1, 2].includes(action.gate) || typeof action.passed !== 'boolean') throw new Error('Invalid review')
			text(action.reviewer); text(action.record)
			if (s.candidate!.risk === 'high' && action.reviewer === s.thread) throw new Error('High-risk review must be independent')
			if (action.gate === 2 && !s.reviews.some(r => r.gate === 1 && r.passed)) throw new Error('Passing first review required')
			s.reviews = s.reviews.filter(r => r.gate < action.gate)
			s.reviews.push({ gate: action.gate, fingerprint: action.fingerprint, passed: action.passed, reviewer: action.reviewer, record: action.record })
			delete s.evidence; delete s.presented; delete s.mergeApproval; s.phase = 'reviewing'; break
		case 'evidence':
			current(s, action.fingerprint)
			if (!Array.isArray(action.results) || action.results.length !== s.design!.criteria.length) throw new Error('Evidence must cover every acceptance criterion in order')
			action.results.forEach(text); text(action.tryIt); text(action.value)
			s.evidence = { results: action.results, tryIt: action.tryIt, value: action.value, fingerprint: action.fingerprint }
			delete s.presented; delete s.mergeApproval; s.phase = 'evidence'; break
		case 'presented':
			current(s, action.fingerprint)
			if (!s.evidence) throw new Error('Evidence required')
			s.presented = action.fingerprint; break
		case 'approve-merge':
			current(s, action.fingerprint)
			if (s.presented !== action.fingerprint) throw new Error('Present evidence first')
			s.mergeApproval = action.fingerprint; break
		case 'merge-requested': {
			current(s, action.fingerprint)
			const missing = blockers(s)
			if (missing.length) throw new Error(missing.join('; '))
			s.phase = 'merge-pending'; break
		}
		case 'merged':
			current(s, action.fingerprint); sha(action.commit)
			if (s.phase !== 'merge-pending') throw new Error('No merge request to reconcile')
			s.mergeCommit = action.commit; s.phase = 'merged'; break
		case 'recover':
			current(s, action.fingerprint)
			if (s.phase !== 'merge-pending') throw new Error('No pending request to recover')
			s.generation++; invalidate(s); delete s.paused; s.phase = 'reviewing'; break
		case 'pause': text(action.reason); s.paused = action.reason; break
		case 'resume': delete s.paused; break
		default: throw new Error('Unsupported mission action')
	}
	return event(s, action.type)
}

export function loadMission(path: string, thread: string): Mission | undefined {
	const raw = readRecordBytes(path)
	return raw === undefined ? undefined : parseMission(JSON.parse(raw), thread)
}
export function parseMission(value: unknown, thread: string): Mission {
	const s = value as Mission
	if (!s || typeof s !== 'object') throw new Error('Invalid mission state')
	if (s.version !== 1 || s.thread !== thread || !Array.isArray(s.events) || !Array.isArray(s.reviews) || !['auto', 'ask'].includes(s.mode)) throw new Error('Invalid mission state; preserve and investigate')
	text(s.requirements)
	if (!Number.isSafeInteger(s.generation) || s.generation < 0 || !['requirements', 'awaiting-design-approval', 'defense', 'ready-to-build', 'building', 'reviewing', 'evidence', 'merge-pending', 'merged'].includes(s.phase) || !['low', 'medium', 'high', 'unknown'].includes(s.riskFloor)) throw new Error('Invalid mission phase, generation or risk floor')
	if (s.candidate) {
		sha(s.candidate.head); sha(s.candidate.base)
		if (!['low', 'medium', 'high', 'unknown'].includes(s.candidate.risk) || !/^[\w.-]+\/[\w.-]+$/.test(s.candidate.repo) || !Number.isSafeInteger(s.candidate.pr) || s.candidate.pr <= 0) throw new Error('Invalid persisted candidate')
	}
	if (s.events.some((e, i) => e.sequence !== i + 1)) throw new Error('Invalid event sequence')
	if (s.design && s.design.digest !== digest([s.requirements, s.design.bundle, s.design.criteria])) throw new Error('Design changed outside mission workflow')
	return s
}
export function saveMission(path: string, state: Mission) {
	parseMission(state, state.thread)
	updateRecord(path, raw => {
		const old = raw === undefined ? undefined : parseMission(JSON.parse(raw), state.thread)
		if (old && (old.events.length !== state.events.length - 1 || canonical(old.events) !== canonical(state.events.slice(0, -1)))) throw new Error('Concurrent or stale mission update; reload')
		return JSON.stringify(state, null, 2) + '\n'
	})
}

export function readRecordBytes(path: string): string | undefined {
	if (!existsSync(path)) return undefined
	if (statSync(path).size > 16 * 1024 * 1024) throw new Error('Mission record exceeds 16 MiB; preserve and investigate')
	const bytes = readFileSync(path)
	if (bytes.length > 16 * 1024 * 1024) throw new Error('Mission record exceeds 16 MiB')
	const raw = bytes.toString('utf8')
	if (!Buffer.from(raw, 'utf8').equals(bytes)) throw new Error('Invalid UTF-8 mission bytes; preserve and investigate')
	return raw
}
// One lock/atomic-replacement owner for v1, v2, and explicit migration.
// An interrupted lock is never silently stolen. Inspect the writer first.
export function updateRecord(path: string, transform: (raw: string | undefined) => string) {
	mkdirSync(dirname(path), { recursive: true, mode: 0o700 })
	const lock = openSync(path + '.lock', 'wx', 0o600)
	const temporary = path + '.' + randomUUID()
	try {
		const next = transform(readRecordBytes(path))
		if (Buffer.byteLength(next) > 16 * 1024 * 1024) throw new Error('Mission record exceeds 16 MiB')
		const fd = openSync(temporary, 'wx', 0o600)
		try { writeFileSync(fd, next); fsyncSync(fd) } finally { closeSync(fd) }
		renameSync(temporary, path)
		const directory = openSync(dirname(path), 'r')
		try { fsyncSync(directory) } finally { closeSync(directory) }
	} finally {
		if (existsSync(temporary)) unlinkSync(temporary)
		closeSync(lock); unlinkSync(path + '.lock')
	}
}

export function loadRecord(path: string, thread: string): Mission | MissionV2 | undefined {
	const raw = readRecordBytes(path)
	if (raw === undefined) return undefined
	const value = JSON.parse(raw)
	if (value?.version === 1 && value.schemaVersion === undefined) return parseMission(value, thread)
	if (value?.schemaVersion !== 2 || value.thread !== thread) throw new Error('Invalid or unsupported mission schema/thread')
	return parseMissionV2(value)
}
export function saveRecord(path: string, state: Mission | MissionV2) {
	if ('version' in state) return saveMission(path, state)
	parseMissionV2(state)
	updateRecord(path, raw => {
		if (raw !== undefined) {
			const old = parseMissionV2(JSON.parse(raw))
			if (old.thread !== state.thread || old.events.length !== state.events.length - 1 || canonical(old.events) !== canonical(state.events.slice(0, -1))) throw new Error('Concurrent or stale mission update; reload')
		}
		return JSON.stringify(state, null, 2) + '\n'
	})
}
