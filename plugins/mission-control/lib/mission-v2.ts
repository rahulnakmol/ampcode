import { parseManifest, intentDigest, canonical, object, prose, identity, strings, list, type ManifestV2 } from './contracts'
import { sha, parseMission, type Mission, type Candidate, type Risk } from './mission'

type Report = { id: string; criterionIds: string[]; outcome: 'passed' | 'failed' | 'blocked'; record: string; producer: 'reported' }
type Finding = { id: string; criterionIds: string[]; severity: 'low' | 'medium' | 'high' | 'critical'; confidence: 'hypothesis' | 'source-supported' | 'runtime-reproduced'; location: string; record: string; owner: string }
type Review = { gate: 1 | 2; fingerprint: string; evidenceDigest: string; reviewer: string; passed: boolean; record: string; findingIds: string[] }
type PostDelivery = { baseline: string; designDigest: string; policyDigest: string; unitIds: string[]; evidenceIds: string[]; results: { criterionId: string; outcome: 'passed' | 'failed' | 'blocked'; record: string }[]; findings: Finding[]; record: string }
type PostReport = Omit<PostDelivery, 'evidenceIds' | 'findings'> & { id: string }
type Disposition = { findingId: string; outcome: 'fixed' | 'rejected' | 'deferred'; evidenceIds: string[]; owner: string; reviewer: string; record: string; correctiveUnitId?: string }
type Attempt = { id: string; candidate: Candidate; designDigest: string; stale: boolean; reports: Report[]; reviews: Review[]; findings: Finding[]; integration?: { commit: string; origin: 'adapter-observed' | 'legacy-reported' } }
type Unit = { id: string; status: 'planned' | 'building' | 'reviewing' | 'integrated' | 'adversarial-review'; riskFloor: Risk; pr?: number; attempts: Attempt[]; postDelivery: PostDelivery[] }
export type MissionV2 = {
	schemaVersion: 2; thread: string; manifest: ManifestV2; intentAuthority: 'local-reported'
	status: 'framing' | 'defending' | 'active'; snapshots: { digest: string; manifest: ManifestV2 }[]
	approvedDesign?: string; defense?: string; paused?: string; units: Unit[]; closureReports: PostDelivery[]
	postReports: (PostReport & { producer: 'reported'; integrationDigest: string; sequence: number; baselineInclusion: 'unverified' })[]
	dispositions: (Disposition & { producer: 'reported'; sequence: number })[]
	legacy?: Mission
	events: { sequence: number; action: ActionV2 }[]
}
export type ActionV2 =
	| { type: 'design'; manifest: unknown }
	| { type: 'approve-design'; digest: string }
	| { type: 'defense'; digest: string; record: string }
	| { type: 'build'; unitId: string }
	| { type: 'candidate'; unitId: string; attemptId: string; candidate: Candidate; manifest: unknown }
	| { type: 'report'; unitId: string; attemptId: string; fingerprint: string; evidence: Omit<Report, 'producer'> }
	| ({ type: 'review'; unitId: string; attemptId: string } & Review)
	| { type: 'finding'; unitId: string; attemptId: string; fingerprint: string; finding: Finding }
	| { type: 'pause'; reason: string }
	| { type: 'resume' }
	| { type: 'post-delivery'; unitId: string; package: PostDelivery }
	| { type: 'closure-report'; package: PostDelivery }
	| { type: 'post-report'; evidence: PostReport }
	| { type: 'disposition'; disposition: Disposition }
	| { type: 'import-v1'; record: Mission }
	| { type: 'observe-integration'; unitId: string; attemptId: string; commit: string; remoteHead: string; targetRef: string; repository: string }

function initial(thread: string): MissionV2 {
	prose(thread)
	return { schemaVersion: 2, thread, manifest: undefined as any, intentAuthority: 'local-reported', status: 'framing', snapshots: [], units: [], closureReports: [], postReports: [], dispositions: [], events: [] }
}
export function createMissionV2(thread: string, manifest: unknown): MissionV2 {
	return advanceV2(initial(thread), { type: 'design', manifest })
}
export function legacyManifest(previous: Mission, repository?: string): ManifestV2 {
	parseMission(previous, previous.thread)
	if (previous.phase === 'merge-pending') throw new Error('Reconcile pending v1 effects before migration')
	const criteria = (previous.design?.criteria ?? [previous.requirements]).map((outcome, i) => ({ id: `C-${i + 1}`, requirementIds: ['R-1'], outcome, authority: 'mission', method: 'judgment', checks: [], threshold: 'Not specified by v1; requires v2 design review' }))
	return parseManifest({
		schemaVersion: 2, missionId: 'M-' + intentDigest(previous.thread).slice(0, 24), repository: previous.candidate?.repo ?? repository,
		requirements: [{ id: 'R-1', need: previous.requirements, scope: previous.design?.bundle.spec ?? 'Not specified by v1', nonGoals: 'Not specified by v1' }],
		criteria, decisions: [], slices: [{ id: 'S-1', criterionIds: criteria.map(c => c.id), paths: ['UNSPECIFIED'] }],
		deliveries: [{ id: 'U-1', sliceIds: ['S-1'], criterionIds: criteria.map(c => c.id) }],
		allocations: criteria.map(c => ({ criterionId: c.id, contributors: ['U-1'], finalUnitId: 'U-1' })),
	})
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
function attemptCriteria(s: MissionV2, unitId: string, a: Attempt): string[] {
	const snapshot = s.snapshots.find(snapshot => snapshot.digest === a.designDigest)
	const unit = snapshot?.manifest.deliveries.find(u => u.id === unitId)
	if (!unit) throw new Error('Attempt design snapshot missing')
	return unit.criterionIds
}
export function fingerprintV2(s: MissionV2, unitId: string, attemptId: string): string {
	const a = attemptFor(s, unitId, attemptId)
	return intentDigest([s.manifest.missionId, unitId, attemptId, a.designDigest, a.candidate])
}
export function evidenceDigestV2(s: MissionV2, unitId: string, attemptId: string): string {
	const a = attemptFor(s, unitId, attemptId)
	// Findings also invalidate reviews without introducing a review/hash cycle.
	const findings = allFindings(s).filter(f => f.unitIds.includes(unitId))
	return intentDigest([...a.reports, ...findings.map(f => f.finding), ...s.dispositions.filter(d => findings.some(f => f.finding.id === d.findingId))])
}
function allFindings(s: MissionV2): { finding: Finding; unitIds: string[]; sequence: number }[] {
	const found = new Map<string, { finding: Finding; unitIds: string[]; sequence: number }>()
	for (const e of s.events) {
		const a = e.action
		const entries = a.type === 'finding' ? [{ f: a.finding, units: [a.unitId] }] : a.type === 'post-delivery' || a.type === 'closure-report' ? a.package.findings.map(f => ({ f, units: a.package.unitIds })) : []
		for (const { f, units } of entries) {
			const old = found.get(f.id)
			if (old) old.unitIds = [...new Set([...old.unitIds, ...units])]
			else found.set(f.id, { finding: f, unitIds: [...units], sequence: e.sequence })
		}
	}
	return [...found.values()]
}
function evidenceExists(s: MissionV2, id: string) {
	return s.postReports.some(r => r.id === id) || s.units.some(u => u.attempts.some(a => a.reports.some(r => r.id === id)))
}
function integrationDigest(s: MissionV2, unitIds: string[]) {
	return intentDigest(unitIds.map(id => {
		const a = unitFor(s, id).attempts.at(-1)
		if (!a?.integration) throw new Error('Observed integration required before post-delivery')
		return [id, a.id, a.integration.commit]
	}))
}
function finding(value: Finding, criteria: string[]) {
	object(value, ['id', 'criterionIds', 'severity', 'confidence', 'location', 'record', 'owner'])
	identity(value.id); strings(value.criterionIds)
	for (const key of ['location', 'record', 'owner'] as const) prose(value[key])
	if (value.criterionIds.some(id => !criteria.includes(id)) || !['low', 'medium', 'high', 'critical'].includes(value.severity) || !['hypothesis', 'source-supported', 'runtime-reproduced'].includes(value.confidence)) throw new Error('Invalid finding')
}
function postScope(s: MissionV2, p: PostReport | PostDelivery) {
	sha(p.baseline); prose(p.record); strings(p.unitIds)
	if (p.policyDigest !== 'unqualified' && !/^[a-f0-9]{64}$/.test(p.policyDigest)) throw new Error('Policy digest or explicit unqualified required')
	if (p.designDigest !== s.approvedDesign || p.designDigest !== intentDigest(s.manifest)) throw new Error('Stale post-delivery design')
	integrationDigest(s, p.unitIds)
	if (p.unitIds.some(id => unitFor(s, id).attempts.at(-1)!.candidate.base === p.baseline) && !p.unitIds.some(id => unitFor(s, id).attempts.at(-1)!.integration!.commit === p.baseline)) throw new Error('Pre-integration baseline cannot supply post-delivery evidence')
	// Baseline inclusion is deliberately unqualified: a reported SHA is not an ancestry proof.
	const ids = [...new Set(s.manifest.deliveries.filter(d => p.unitIds.includes(d.id)).flatMap(d => d.criterionIds))]
	list(p.results)
	const covered = new Set<string>()
	for (const r of p.results) {
		object(r, ['criterionId', 'outcome', 'record']); prose(r.record)
		if (!ids.includes(r.criterionId) || covered.has(r.criterionId) || !['passed', 'failed', 'blocked'].includes(r.outcome)) throw new Error('Invalid post-delivery result')
		covered.add(r.criterionId)
	}
	if (covered.size !== ids.length) throw new Error('Post-delivery criteria incomplete')
	return ids
}
function newerPostEvidence(s: MissionV2, p: PostDelivery): boolean {
	const sequence = Math.max(0, ...s.postReports.filter(e => p.evidenceIds.includes(e.id)).map(e => e.sequence))
	return s.postReports.some(e => e.sequence > sequence && e.designDigest === p.designDigest && e.baseline === p.baseline && e.policyDigest === p.policyDigest && e.unitIds.some(id => p.unitIds.includes(id)))
}
function postPackage(s: MissionV2, p: PostDelivery, unitId?: string) {
	object(p, ['baseline', 'designDigest', 'policyDigest', 'unitIds', 'evidenceIds', 'results', 'findings', 'record'])
	const ids = postScope(s, p)
	if (!unitId && (p.unitIds.length !== s.units.length || s.units.some(u => !p.unitIds.includes(u.id)))) throw new Error('Closure report must cover the whole mission')
	if (unitId && !p.unitIds.includes(unitId)) throw new Error('Post-delivery unit omitted')
	strings(p.evidenceIds); list(p.findings, true)
	const evidence = p.evidenceIds.map(id => {
		const e = s.postReports.find(r => r.id === id)
		if (!e || e.baseline !== p.baseline || e.designDigest !== p.designDigest || e.policyDigest !== p.policyDigest || canonical(e.unitIds) !== canonical(p.unitIds) || e.integrationDigest !== integrationDigest(s, p.unitIds)) throw new Error('Missing, wrong-stage or stale post-delivery evidence')
		return e
	})
	if (newerPostEvidence(s, p)) throw new Error('Package omits newer relevant post-delivery evidence')
	for (const r of p.results) {
		const outcomes = evidence.flatMap(e => e.results.filter(result => result.criterionId === r.criterionId).map(result => result.outcome))
		const outcome = outcomes.includes('failed') ? 'failed' : outcomes.includes('blocked') ? 'blocked' : 'passed'
		if (!outcomes.length || r.outcome !== outcome) throw new Error('Package contradicts referenced evidence')
	}
	const findingIds = new Set<string>()
	for (const f of p.findings) {
		finding(f, ids)
		const old = allFindings(s).find(old => old.finding.id === f.id)
		if (old && canonical(old.finding) !== canonical(f)) throw new Error('Finding identity cannot be rewritten')
		if (findingIds.has(f.id)) throw new Error('Duplicate finding')
		findingIds.add(f.id)
	}
}
export function blockersV2(s: MissionV2, unitId?: string): string[] {
	const out = ['remote-verification-unqualified']
	if (s.paused) out.push('Paused: ' + s.paused)
	if (s.approvedDesign !== intentDigest(s.manifest)) out.push('Owner design approval required')
	if (!s.defense) out.push('Whiteboard defense required')
	for (const c of s.manifest.criteria) if (c.authority === 'policy') out.push(`Policy authority unqualified: ${c.id}`)
	const currentPost = new Map<string, MissionV2['postReports'][number]>()
	for (const e of s.postReports) if (e.designDigest === intentDigest(s.manifest)) currentPost.set(canonical([e.baseline, e.policyDigest, [...e.unitIds].sort()]), e)
	for (const u of unitId ? [unitFor(s, unitId)] : s.units) {
		for (const e of currentPost.values()) if (e.unitIds.includes(u.id)) {
			for (const r of e.results) if (r.outcome !== 'passed') out.push(`${u.id}/${r.criterionId}: current post-evidence ${r.outcome}`)
		}
		const p = u.postDelivery.at(-1)
		if (p && newerPostEvidence(s, p)) out.push(`${u.id}: post-delivery package stale`)
		for (const f of allFindings(s).filter(f => f.unitIds.includes(u.id))) {
			const d = s.dispositions.findLast(d => d.findingId === f.finding.id)
			out.push(`${u.id}/${f.finding.id}: ${d ? d.outcome + ' reported; qualified resolution required' : 'unresolved finding'}`)
		}
		for (const r of u.postDelivery.at(-1)?.results ?? []) if (r.outcome !== 'passed') out.push(`${u.id}/${r.criterionId}: post-delivery report ${r.outcome}`)
		const a = u.attempts.at(-1)
		if (!a || a.stale) { out.push(`${u.id}: current candidate required`); continue }
		if (a.candidate.risk === 'unknown') out.push(`${u.id}: risk is unknown`)
		if (a.designDigest !== intentDigest(s.manifest)) out.push(`${u.id}: historical design; current acceptance requires corrective units`)
		for (const id of attemptCriteria(s, u.id, a)) {
			out.push(`${u.id}/${id}: qualified acceptance evidence required`)
			if (a.reports.some(r => r.criterionIds.includes(id) && r.outcome !== 'passed')) out.push(`${u.id}/${id}: reported failure or blocker`)
		}
		const ed = evidenceDigestV2(s, u.id, a.id)
		for (const gate of [1, 2]) if (!a.reviews.some(r => r.gate === gate && r.passed && r.evidenceDigest === ed)) out.push(`${u.id}: Review ${gate} required for current evidence`)
		if (!a.integration) out.push(`${u.id}: integration not observed`)
		else out.push(`${u.id}: qualified post-delivery evidence required`)
	}
	const closure = s.closureReports.at(-1)
	if (closure && newerPostEvidence(s, closure)) out.push('Assembled-baseline package stale')
	for (const r of s.closureReports.at(-1)?.results ?? []) if (r.outcome !== 'passed') out.push(`${r.criterionId}: assembled-baseline report ${r.outcome}`)
	out.push('Qualified assembled-baseline closure required')
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
		review: ['unitId', 'attemptId', 'gate', 'fingerprint', 'evidenceDigest', 'reviewer', 'passed', 'record', 'findingIds'],
		finding: ['unitId', 'attemptId', 'fingerprint', 'finding'], pause: ['reason'], resume: [],
		'post-delivery': ['unitId', 'package'], 'closure-report': ['package'], 'post-report': ['evidence'], disposition: ['disposition'],
		'import-v1': ['record'],
	}
	if (!action || !Object.hasOwn(fields, action.type)) throw new Error('Unsupported v2 action')
	object(action, ['type', ...fields[action.type]])
	if (s.paused && !['pause', 'resume', 'observe-integration'].includes(action.type)) throw new Error('Mission paused; resume explicitly')
	switch (action.type) {
		case 'design': {
			const m = parseManifest(action.manifest)
			if (s.manifest && (m.missionId !== s.manifest.missionId || m.repository !== s.manifest.repository)) throw new Error('Cannot change mission identity')
			if (s.units.some(u => !m.deliveries.some(d => d.id === u.id))) throw new Error('Preserve unit allocation history; use a corrective unit')
			const history = s.snapshots.flatMap(snapshot => snapshot.manifest.criteria)
			if (m.dispositions?.some(d => !history.some(c => c.id === d.criterionId))) throw new Error('Unknown historical criterion disposition')
			if (history.some(c => !m.criteria.some(n => n.id === c.id) && !m.dispositions?.some(d => d.criterionId === c.id))) throw new Error('Removed criterion requires a disposition')
			for (const c of m.criteria) {
				const old = s.manifest?.criteria.find(prior => prior.id === c.id)
				if (!old || intentDigest(old) !== intentDigest(c)) {
					const allocation = m.allocations.find(a => a.criterionId === c.id)!
					if (s.units.find(u => u.id === allocation.finalUnitId)?.attempts.at(-1)?.integration) throw new Error('Changed criterion requires an unintegrated corrective final unit')
				}
			}
			for (const u of s.units) if (!u.attempts.at(-1)?.integration) {
				u.attempts.forEach(a => { a.stale = true }); u.status = 'planned'
			}
			for (const d of m.deliveries) if (!s.units.some(u => u.id === d.id)) s.units.push({ id: d.id, status: 'planned', riskFloor: 'unknown', attempts: [], postDelivery: [] })
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
			if (c.risk === 'high' || u.riskFloor !== 'high') u.riskFloor = c.risk
			const risk = u.riskFloor === 'high' && c.risk !== 'unknown' ? 'high' : c.risk
			u.pr = c.pr; u.attempts.forEach(a => { a.stale = true })
			u.attempts.push({ id: action.attemptId, candidate: { ...c, risk }, designDigest: s.approvedDesign, stale: false, reports: [], reviews: [], findings: [] })
			u.status = 'reviewing'; break
		}
		case 'report': {
			const a = attemptFor(s, action.unitId, action.attemptId)
			if (action.fingerprint !== fingerprintV2(s, action.unitId, action.attemptId)) throw new Error('Missing or stale fingerprint')
			const r = action.evidence
			object(r, ['id', 'criterionIds', 'outcome', 'record']); identity(r.id); prose(r.record); strings(r.criterionIds)
			if (!['passed', 'failed', 'blocked'].includes(r.outcome)) throw new Error('Invalid report outcome')
			const ids = attemptCriteria(s, action.unitId, a)
			if (r.criterionIds.some(id => !ids.includes(id)) || evidenceExists(s, r.id)) throw new Error('Unresolved criterion or duplicate evidence')
			a.reports.push({ ...structuredClone(r), producer: 'reported' }); break
		}
		case 'review': {
			const a = attemptFor(s, action.unitId, action.attemptId)
			if (action.fingerprint !== fingerprintV2(s, action.unitId, action.attemptId)) throw new Error('Missing or stale fingerprint')
			if (action.evidenceDigest !== evidenceDigestV2(s, action.unitId, action.attemptId)) throw new Error('Review evidence changed')
			prose(action.reviewer); prose(action.record); strings(action.findingIds, true)
			if (![1, 2].includes(action.gate) || typeof action.passed !== 'boolean') throw new Error('Invalid review')
			if (a.candidate.risk === 'high' && action.reviewer === s.thread) throw new Error('High risk requires independent review')
			if (action.findingIds.some(id => !unitFor(s, action.unitId).attempts.some(old => old.findings.some(f => f.id === id)))) throw new Error('Unknown review finding')
			if (action.gate === 2 && !a.reviews.some(r => r.gate === 1 && r.passed && r.evidenceDigest === action.evidenceDigest)) throw new Error('Passing first review required')
			if (a.reviews.some(r => !r.passed)) throw new Error('Repair requires a new attempt')
			if (a.reviews.some(r => r.gate === action.gate && r.evidenceDigest === action.evidenceDigest)) throw new Error('Review already recorded')
			const { gate, fingerprint, evidenceDigest, reviewer, passed, record, findingIds } = action
			a.reviews.push({ gate, fingerprint, evidenceDigest, reviewer, passed, record, findingIds }); break
		}
		case 'finding': {
			const a = attemptFor(s, action.unitId, action.attemptId)
			if (action.fingerprint !== fingerprintV2(s, action.unitId, action.attemptId)) throw new Error('Missing or stale fingerprint')
			finding(action.finding, attemptCriteria(s, action.unitId, a))
			if (allFindings(s).some(f => f.finding.id === action.finding.id)) throw new Error('Finding identity already used')
			a.findings.push(structuredClone(action.finding)); break
		}
		case 'post-report': {
			const e = action.evidence
			object(e, ['id', 'baseline', 'designDigest', 'policyDigest', 'unitIds', 'results', 'record']); identity(e.id)
			if (evidenceExists(s, e.id)) throw new Error('Duplicate evidence identity')
			postScope(s, e)
			s.postReports.push({ ...structuredClone(e), producer: 'reported', integrationDigest: integrationDigest(s, e.unitIds), sequence: s.events.length + 1, baselineInclusion: 'unverified' }); break
		}
		case 'disposition': {
			const d = action.disposition
			object(d, ['findingId', 'outcome', 'evidenceIds', 'owner', 'reviewer', 'record'], ['correctiveUnitId'])
			prose(d.owner); prose(d.reviewer); prose(d.record); strings(d.evidenceIds, d.outcome === 'deferred')
			const f = allFindings(s).find(f => f.finding.id === d.findingId)
			if (!f || !['fixed', 'rejected', 'deferred'].includes(d.outcome)) throw new Error('Invalid finding disposition')
			if (d.correctiveUnitId) unitFor(s, d.correctiveUnitId)
			if (d.outcome === 'deferred' && !d.correctiveUnitId) throw new Error('Deferred finding requires a corrective unit')
			if (['high', 'critical'].includes(f.finding.severity) && (d.reviewer === s.thread || d.reviewer === f.finding.owner)) throw new Error('Consequential disposition requires independent review')
			for (const id of d.evidenceIds) {
				const post = s.postReports.find(e => e.id === id)
				const units = d.correctiveUnitId ? [...f.unitIds, d.correctiveUnitId] : f.unitIds
				const attempt = s.units.filter(u => units.includes(u.id)).map(u => ({ u, a: u.attempts.at(-1) })).find(({ a }) => a && !a.stale && a.reports.some(r => r.id === id))
				const event = s.events.find(e => e.action.type === 'report' && e.action.evidence.id === id)
				const report = attempt?.a?.reports.find(r => r.id === id)
				const postValid = post && post.sequence > f.sequence && post.designDigest === intentDigest(s.manifest) && post.integrationDigest === integrationDigest(s, post.unitIds) && units.some(u => post.unitIds.includes(u)) && f.finding.criterionIds.every(c => post.results.some(r => r.criterionId === c && r.outcome === 'passed'))
				const reportValid = report && event && event.sequence > f.sequence && attempt!.a!.designDigest === intentDigest(s.manifest) && report.outcome === 'passed' && f.finding.criterionIds.every(c => report.criterionIds.includes(c))
				if (!postValid && !reportValid) throw new Error('Missing, stale or unrelated repair evidence')
			}
			s.dispositions.push({ ...structuredClone(d), producer: 'reported', sequence: s.events.length + 1 }); break
		}
		case 'pause': prose(action.reason); s.paused = action.reason; break
		case 'resume': delete s.paused; break
		case 'import-v1': {
			const old = parseMission(action.record, s.thread)
			if (s.events.length !== 1 || s.legacy || intentDigest(legacyManifest(old, s.manifest.repository)) !== intentDigest(s.manifest)) throw new Error('Invalid v1 import mapping')
			s.legacy = structuredClone(old)
			if (old.paused) s.paused = old.paused
			s.units[0].riskFloor = old.riskFloor
			if (old.candidate) {
				const u = s.units[0]
				u.pr = old.candidate.pr
				const a: Attempt = { id: 'A-imported', candidate: structuredClone(old.candidate), designDigest: intentDigest(s.manifest), stale: old.phase !== 'merged', reports: [], reviews: [], findings: [] }
				if (old.phase === 'merged') { sha(old.mergeCommit); a.integration = { commit: old.mergeCommit, origin: 'legacy-reported' }; u.status = 'integrated' }
				u.attempts.push(a)
			}
			break
		}
		case 'post-delivery':
			postPackage(s, action.package, action.unitId)
			unitFor(s, action.unitId).postDelivery.push(structuredClone(action.package))
			unitFor(s, action.unitId).status = 'adversarial-review'; break
		case 'closure-report':
			postPackage(s, action.package)
			s.closureReports.push(structuredClone(action.package))
			// Share the identical package, never manufacture qualified closure.
			for (const u of s.units) { u.postDelivery.push(structuredClone(action.package)); u.status = 'adversarial-review' }
			break
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
	object(value, ['schemaVersion', 'thread', 'manifest', 'intentAuthority', 'status', 'snapshots', 'units', 'events', 'closureReports', 'postReports', 'dispositions'], ['approvedDesign', 'defense', 'paused', 'legacy'])
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
