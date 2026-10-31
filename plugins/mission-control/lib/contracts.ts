import { createHash } from 'node:crypto'

export type ManifestV2 = {
	schemaVersion: 2; missionId: string; repository: string
	requirements: { id: string; need: string; scope: string; nonGoals: string }[]
	criteria: { id: string; requirementIds: string[]; outcome: string; authority: 'mission' | 'policy'; policyRef?: string; method: 'automated' | 'journey' | 'judgment'; checks: string[]; threshold: string }[]
	decisions: { id: string; requirementIds: string[]; rationale: string; alternatives: string; revisit: string }[]
	slices: { id: string; criterionIds: string[]; paths: string[] }[]
	deliveries: { id: string; sliceIds: string[]; criterionIds: string[] }[]
	allocations: { criterionId: string; contributors: string[]; finalUnitId: string }[]
	dispositions?: { criterionId: string; reason: string; owner: string; replacementIds: string[] }[]
}

export function object(value: unknown, required: string[], optional: string[] = []): asserts value is Record<string, any> {
	if (!value || typeof value !== 'object' || Array.isArray(value) || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) throw new Error('Object required')
	if (required.some(k => !Object.hasOwn(value, k)) || Object.keys(value).some(k => !required.includes(k) && !optional.includes(k))) throw new Error('Missing or unknown fields')
}
export function prose(value: unknown): asserts value is string {
	if (typeof value !== 'string' || !value.trim() || Buffer.byteLength(value) > 16 * 1024) throw new Error('Non-empty text up to 16 KiB required')
}
export function identity(value: unknown): asserts value is string {
	if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(value)) throw new Error('Invalid identity')
}
export function list(value: unknown, empty = false): asserts value is any[] {
	if (!Array.isArray(value) || (!empty && !value.length) || value.length > 1000) throw new Error('Bounded list required')
}
export function strings(value: unknown, empty = false): asserts value is string[] {
	list(value, empty); value.forEach(prose)
	if (new Set(value).size !== value.length) throw new Error('Duplicate values')
}
function refs(value: unknown, ids: Set<string>) {
	strings(value)
	if (value.some(id => !ids.has(id))) throw new Error('Unresolved reference')
}
export function canonical(value: unknown, depth = 0): string {
	if (depth > 32) throw new Error('JSON nesting exceeds limit')
	if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value)
	if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value)
	if (Array.isArray(value)) return '[' + Array.from(value, item => canonical(item, depth + 1)).join(',') + ']'
	if (value && typeof value === 'object' && [Object.prototype, null].includes(Object.getPrototypeOf(value))) {
		return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical((value as any)[key], depth + 1)).join(',') + '}'
	}
	throw new Error('Only finite JSON values are supported')
}
export function intentDigest(value: unknown) { return createHash('sha256').update(canonical(value)).digest('hex') }

export function parseManifest(value: unknown): ManifestV2 {
	if (Buffer.byteLength(canonical(value)) > 1024 * 1024) throw new Error('Manifest exceeds 1 MiB')
	object(value, ['schemaVersion', 'missionId', 'repository', 'requirements', 'criteria', 'decisions', 'slices', 'deliveries', 'allocations'], ['dispositions'])
	if (value.schemaVersion !== 2) throw new Error('Unsupported manifest version')
	identity(value.missionId)
	if (typeof value.repository !== 'string' || !/^[\w.-]+\/[\w.-]+$/.test(value.repository)) throw new Error('Invalid repository')
	const all = new Set<string>()
	function records(items: unknown, required: string[], optional: string[] = [], empty = false) {
		list(items, empty)
		const ids = new Set<string>()
		for (const item of items) {
			object(item, ['id', ...required], optional); identity(item.id)
			if (all.has(item.id)) throw new Error('Duplicate identity')
			ids.add(item.id); all.add(item.id)
		}
		return ids
	}
	const requirements = records(value.requirements, ['need', 'scope', 'nonGoals'])
	for (const r of value.requirements) for (const key of ['need', 'scope', 'nonGoals']) prose(r[key])
	const criteria = records(value.criteria, ['requirementIds', 'outcome', 'authority', 'method', 'checks', 'threshold'], ['policyRef'])
	for (const c of value.criteria) {
		refs(c.requirementIds, requirements); prose(c.outcome); prose(c.threshold); strings(c.checks, c.method === 'judgment')
		if (!['mission', 'policy'].includes(c.authority) || !['automated', 'journey', 'judgment'].includes(c.method)) throw new Error('Unknown authority or method')
		if (c.authority === 'policy') prose(c.policyRef)
		else if (Object.hasOwn(c, 'policyRef')) throw new Error('Mission criterion cannot assert policy authority')
	}
	records(value.decisions, ['requirementIds', 'rationale', 'alternatives', 'revisit'], [], true)
	for (const d of value.decisions) {
		refs(d.requirementIds, requirements)
		for (const key of ['rationale', 'alternatives', 'revisit']) prose(d[key])
	}
	const slices = records(value.slices, ['criterionIds', 'paths'])
	for (const s of value.slices) {
		refs(s.criterionIds, criteria); strings(s.paths)
		if (s.paths.some((p: string) => p.startsWith('/') || p.includes('\\') || p.includes(':') || p.includes('\0') || p.split('/').some(v => ['', '.', '..'].includes(v)))) throw new Error('Unsafe relative path')
	}
	const units = records(value.deliveries, ['sliceIds', 'criterionIds'])
	for (const u of value.deliveries) {
		refs(u.sliceIds, slices); refs(u.criterionIds, criteria)
		const covered = new Set<string>(value.slices.filter((s: any) => u.sliceIds.includes(s.id)).flatMap((s: any) => s.criterionIds))
		if (u.criterionIds.some((id: string) => !covered.has(id)) || [...covered].some(id => !u.criterionIds.includes(id))) throw new Error('Delivery criteria differ from slice coverage')
	}
	list(value.allocations)
	const allocated = new Set<string>()
	for (const a of value.allocations) {
		object(a, ['criterionId', 'contributors', 'finalUnitId'])
		if (!criteria.has(a.criterionId) || allocated.has(a.criterionId)) throw new Error('Invalid criterion allocation')
		allocated.add(a.criterionId); refs(a.contributors, units)
		if (!a.contributors.includes(a.finalUnitId)) throw new Error('Final unit must contribute')
		for (const id of a.contributors) if (!value.deliveries.find((u: any) => u.id === id).criterionIds.includes(a.criterionId)) throw new Error('Unit does not cover criterion')
	}
	if (allocated.size !== criteria.size) throw new Error('Every criterion requires an allocation')
	if (value.dispositions !== undefined) {
		list(value.dispositions, true)
		const disposed = new Set<string>()
		for (const d of value.dispositions) {
			object(d, ['criterionId', 'reason', 'owner', 'replacementIds']); identity(d.criterionId); prose(d.reason); prose(d.owner); strings(d.replacementIds, true)
			if (disposed.has(d.criterionId) || criteria.has(d.criterionId) || d.replacementIds.some((id: string) => !criteria.has(id))) throw new Error('Invalid criterion disposition')
			disposed.add(d.criterionId)
		}
	}
	return structuredClone(value) as ManifestV2
}
