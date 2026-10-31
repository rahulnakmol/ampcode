import { parseManifest, intentDigest, canonical, object, prose, identity, strings, type ManifestV2 } from './contracts'
import { sha, type Candidate } from './mission'

type Report = { id: string; criterionIds: string[]; outcome: 'passed' | 'failed' | 'blocked'; record: string; producer: 'reported' }
type Attempt = { id: string; candidate: Candidate; designDigest: string; stale: boolean; reports: Report[]; integration?: { commit: string; origin: 'adapter-observed' } }
type Unit = { id: string; status: 'planned' | 'building' | 'reviewing' | 'integrated'; pr?: number; attempts: Attempt[] }
export type MissionV2 = {
	schemaVersion: 2; thread: string; manifest: ManifestV2; intentAuthority: 'local-reported'
	status: 'framing' | 'defending' | 'active'; snapshots: { digest: string; manifest: ManifestV2 }[]
	approvedDesign?: string; defense?: string; units: Unit[]
	events: { sequence: number; action: ActionV2 }[]
}
export type ActionV2 =
	| { type: 'design'; manifest: unknown }
	| { type: 'approve-design'; digest: string }
	| { type: 'defense'; digest: string; record: string }
	| { type: 'build'; unitId: string }
	| { type: 'candidate'; unitId: string; attemptId: string; candidate: Candidate; manifest: unknown }
	| { type: 'report'; unitId: string; attemptId: string; fingerprint: string; evidence: Omit<Report, 'producer'> }
	| { type: 'observe-integration'; unitId: string; attemptId: string; commit: string; remoteHead: string; targetRef: string; repository: string }

function initial(thread: string): MissionV2 {
	prose(thread)
	return { schemaVersion: 2, thread, manifest: undefined as any, intentAuthority: 'local-reported', status: 'framing', snapshots: [], units: [], events: [] }
}
export function createMissionV2(thread: string, manifest: unknown): MissionV2 {
	return advanceV2(initial(thread), { type: 'design', manifest })
}
function unitFor(s: MissionV2, id: string): Unit {
	const unit = s.units.find(u => u.id === id)
	if (!unit) throw new Error('Unknown delivery unit')
	return unit
}
function attemptFor(s: MissionV2, unitId: string, attemptId: string): Attempt {
	const unit = unitFor(s, unitId)
	const attempt = unit.attempts.at(-1)
	if (!attempt || attempt.id !== attemptId || attempt.stale) throw new Error('Missing or stale attempt')
	return attempt
}
export function fingerprintV2(s: MissionV2, unitId: string, attemptId: string): string {
	const a = attemptFor(s, unitId, attemptId)
	return intentDigest([s.manifest.missionId, unitId, attemptId, a.designDigest, a.candidate])
}
export function blockersV2(s: MissionV2, unitId?: string): string[] {
	const out = ['remote-verification-unqualified']
	if (s.approvedDesign !== intentDigest(s.manifest)) out.push('Owner design approval required')
	if (!s.defense) out.push('Whiteboard defense required')
	for (const c of s.manifest.criteria) if (c.authority === 'policy') out.push(`Policy authority unqualified: ${c.id}`)
	for (const u of unitId ? [unitFor(s, unitId)] : s.units) {
		const a = u.attempts.at(-1)
		if (!a || a.stale) { out.push(`${u.id}: current candidate required`); continue }
		if (a.candidate.risk === 'unknown') out.push(`${u.id}: risk is unknown`)
		for (const id of s.manifest.deliveries.find(d => d.id === u.id)?.criterionIds ?? []) {
			out.push(`${u.id}/${id}: qualified acceptance evidence required`)
			if (a.reports.some(r => r.criterionIds.includes(id) && r.outcome !== 'passed')) out.push(`${u.id}/${id}: reported failure or blocker`)
		}
		if (!a.integration) out.push(`${u.id}: integration not observed`)
	}
	return out
}

// Public tool dispatch excludes internal approval and observation actions. This
// reducer validates local consistency, not authenticity against a hostile shell.
export function advanceV2(previous: MissionV2, action: ActionV2): MissionV2 {
	const s = structuredClone(previous)
	const fields: Record<string, string[]> = {
		design: ['manifest'], 'approve-design': ['digest'], defense: ['digest', 'record'], build: ['unitId'],
		candidate: ['unitId', 'attemptId', 'candidate', 'manifest'], report: ['unitId', 'attemptId', 'fingerprint', 'evidence'],
		'observe-integration': ['unitId', 'attemptId', 'commit', 'remoteHead', 'targetRef', 'repository'],
	}
	if (!action || !Object.hasOwn(fields, action.type)) throw new Error('Unsupported v2 action')
	object(action, ['type', ...fields[action.type]])
	switch (action.type) {
		case 'design': {
			const m = parseManifest(action.manifest)
			if (s.manifest && (m.missionId !== s.manifest.missionId || m.repository !== s.manifest.repository)) throw new Error('Cannot change mission identity')
			if (s.units.some(u => !m.deliveries.some(d => d.id === u.id))) throw new Error('Preserve unit allocation history; use a corrective unit')
			if (s.manifest?.criteria.some(c => !m.criteria.some(n => n.id === c.id))) throw new Error('Preserve criterion history; removal requires a disposition workflow')
			for (const u of s.units) if (u.status !== 'integrated') {
				u.attempts.forEach(a => { a.stale = true }); u.status = 'planned'
			}
			for (const d of m.deliveries) if (!s.units.some(u => u.id === d.id)) s.units.push({ id: d.id, status: 'planned', attempts: [] })
			s.manifest = m; s.snapshots.push({ digest: intentDigest(m), manifest: structuredClone(m) })
			delete s.approvedDesign; delete s.defense; s.status = 'framing'; break
		}
		case 'approve-design':
			if (action.digest !== intentDigest(s.manifest) || s.status !== 'framing') throw new Error('Missing or stale design')
			s.approvedDesign = action.digest; s.status = 'defending'; break
		case 'defense':
			if (s.status !== 'defending' || action.digest !== s.approvedDesign || action.digest !== intentDigest(s.manifest)) throw new Error('Approved design required')
			prose(action.record); s.defense = action.record; s.status = 'active'; break
		case 'build': {
			if (s.approvedDesign !== intentDigest(s.manifest) || !s.defense) throw new Error('Approval and defense required')
			const u = unitFor(s, action.unitId)
			if (u.status !== 'planned') throw new Error('Build entry already completed')
			u.status = 'building'; break
		}
		case 'candidate': {
			if (intentDigest(parseManifest(action.manifest)) !== s.approvedDesign || s.approvedDesign !== intentDigest(s.manifest) || !s.defense) throw new Error('Candidate intent differs from approved design')
			const u = unitFor(s, action.unitId)
			if (!['building', 'reviewing'].includes(u.status)) throw new Error('Begin build first; integrated history cannot be replaced')
			identity(action.attemptId)
			if (s.units.some(unit => unit.attempts.some(a => a.id === action.attemptId))) throw new Error('Attempt identity already used')
			const c = action.candidate
			object(c, ['repo', 'pr', 'head', 'base', 'risk']); sha(c.head); sha(c.base)
			if (c.repo !== s.manifest.repository || !Number.isSafeInteger(c.pr) || c.pr <= 0 || !['low', 'medium', 'high', 'unknown'].includes(c.risk)) throw new Error('Invalid candidate')
			if ((u.pr && u.pr !== c.pr) || s.units.some(other => other.id !== u.id && other.pr === c.pr)) throw new Error('PR binding cannot change or overlap')
			const risk = u.attempts.some(a => a.candidate.risk === 'high') && c.risk !== 'unknown' ? 'high' : c.risk
			u.pr = c.pr; u.attempts.forEach(a => { a.stale = true })
			u.attempts.push({ id: action.attemptId, candidate: { ...c, risk }, designDigest: s.approvedDesign, stale: false, reports: [] })
			u.status = 'reviewing'; break
		}
		case 'report': {
			const a = attemptFor(s, action.unitId, action.attemptId)
			if (action.fingerprint !== fingerprintV2(s, action.unitId, action.attemptId)) throw new Error('Missing or stale fingerprint')
			const r = action.evidence
			object(r, ['id', 'criterionIds', 'outcome', 'record']); identity(r.id); prose(r.record); strings(r.criterionIds)
			if (!['passed', 'failed', 'blocked'].includes(r.outcome)) throw new Error('Invalid report outcome')
			const ids = s.manifest.deliveries.find(u => u.id === action.unitId)!.criterionIds
			if (r.criterionIds.some(id => !ids.includes(id)) || a.reports.some(old => old.id === r.id)) throw new Error('Unresolved criterion or duplicate evidence')
			a.reports.push({ ...structuredClone(r), producer: 'reported' }); break
		}
		case 'observe-integration': {
			const a = attemptFor(s, action.unitId, action.attemptId)
			sha(action.commit)
			if (a.integration || action.remoteHead !== a.candidate.head || action.targetRef !== 'dev' || action.repository !== s.manifest.repository) throw new Error('Integration does not match recorded candidate')
			a.integration = { commit: action.commit, origin: 'adapter-observed' }; unitFor(s, action.unitId).status = 'integrated'; break
		}
	}
	s.events.push({ sequence: s.events.length + 1, action: structuredClone(action) })
	if (s.events.length > 1000 || Buffer.byteLength(canonical(s)) > 16 * 1024 * 1024) throw new Error('Mission record capacity reached; preserve and split future work')
	return s
}

// Replay validates every stored transition and its projection. It detects drift
// and corruption; it is deliberately not an authentication or tamper-proof log.
export function parseMissionV2(value: unknown): MissionV2 {
	object(value, ['schemaVersion', 'thread', 'manifest', 'intentAuthority', 'status', 'snapshots', 'units', 'events'], ['approvedDesign', 'defense'])
	if (value.schemaVersion !== 2 || !Array.isArray(value.events) || !value.events.length || value.events.length > 1000 || Buffer.byteLength(canonical(value)) > 16 * 1024 * 1024) throw new Error('Invalid v2 mission')
	let s = initial(value.thread)
	for (const [i, event] of value.events.entries()) {
		object(event, ['sequence', 'action'])
		if (event.sequence !== i + 1 || (i === 0 && event.action?.type !== 'design')) throw new Error('Invalid event sequence')
		s = advanceV2(s, event.action)
	}
	if (canonical(s) !== canonical(value)) throw new Error('Mission projection differs from recorded transitions')
	return s
}
