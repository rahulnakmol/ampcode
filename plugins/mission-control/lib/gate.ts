// This is a decision function for an EXTERNALLY trusted controller, not an
// authorizer for agent-supplied JSON. See docs/mission-control.md for provenance.
export interface GateSnapshot {
	repo: string; pr: number; owner: string; implementer: string; mode: string; risk: string
	design: string; head: string; base: string; generation: number; paths: string[]; criteria: string[]
	live: { repo: string; pr: number; head: string; base: string; target: string; state: string }
	approval: { actor: string; design: string; sequence: number }
	defense: { design: string; sequence: number }; buildSequence: number
	evidence: { head: string; base: string; design: string; generation: number; passed: string[]; published: boolean }
	reviews: { gate: number; reviewer: string; head: string; base: string; generation: number; passed: boolean; sequence: number }[]
	requiredChecks: string[]; checks: { name: string; head: string; conclusion: string }[]
	mergeApproval?: { actor: string; head: string; base: string; design: string; mode: string; generation: number }
}

// Conservative floor, not a complete semantic security classifier. A trusted
// reviewer must still classify changes outside these path patterns.
export function riskFloor(paths: string[]) {
	return paths.some(p => /(^|\/)(auth[^/]*|permission[^/]*|security|migrations?|payments?|billing|\.github)(\/|\.|$)/i.test(p)) ? 'high' : 'low'
}
export function evaluateGate(s: GateSnapshot): string[] {
	const blocked: string[] = []
	try {
		if (![s.paths, s.criteria, s.requiredChecks, s.evidence.passed].every(values => Array.isArray(values) && values.every(v => typeof v === 'string' && v.trim())) || !Array.isArray(s.reviews) || !Array.isArray(s.checks)) return ['Malformed trusted controller collections']
		if (!Number.isSafeInteger(s.generation) || s.generation < 0) blocked.push('Invalid recovery generation')
		if (!s.owner || !s.implementer || !/^[\w.-]+\/[\w.-]+$/.test(s.repo) || !Number.isSafeInteger(s.pr) || s.pr <= 0 || !/^[a-f0-9]{64}$/.test(s.design) || ![s.head, s.base].every(v => /^[a-f0-9]{40}$/.test(v))) blocked.push('Invalid trusted mission identity')
		if (s.live.repo !== s.repo || s.live.pr !== s.pr || s.live.head !== s.head || s.live.base !== s.base || s.live.target !== 'dev' || s.live.state !== 'open') blocked.push('Live PR does not match the registered dev candidate')
		if (!['auto', 'ask'].includes(s.mode) || !['low', 'medium', 'high'].includes(s.risk)) blocked.push('Unknown merge mode or risk')
		if (s.approval.actor !== s.owner || s.approval.design !== s.design || s.defense.design !== s.design || ![s.approval.sequence, s.defense.sequence, s.buildSequence].every(v => Number.isSafeInteger(v) && v > 0) || !(s.approval.sequence < s.defense.sequence && s.defense.sequence < s.buildSequence)) blocked.push('Owner approval, defense and build order not established')
		const high = s.risk === 'high' || riskFloor(s.paths) === 'high'
		const reviews = [1, 2].map(gate => s.reviews.filter(r => r.gate === gate))
		if (reviews.some(rs => rs.length !== 1) || reviews.some(rs => rs.some(r => r.head !== s.head || r.base !== s.base || r.generation !== s.generation || r.passed !== true || !r.reviewer || (high && r.reviewer === s.implementer)))) blocked.push('Two passing revision-bound reviews required')
		if (reviews.some(rs => rs.some(r => !Number.isSafeInteger(r.sequence) || r.sequence <= 0)) || !reviews[0][0] || !reviews[1][0] || !(s.buildSequence < reviews[0][0].sequence && reviews[0][0].sequence < reviews[1][0].sequence)) blocked.push('Review order not established')
		if (!s.criteria.length || new Set(s.criteria).size !== s.criteria.length || s.criteria.some(id => !s.evidence.passed.includes(id)) || s.evidence.head !== s.head || s.evidence.base !== s.base || s.evidence.design !== s.design || s.evidence.generation !== s.generation || s.evidence.published !== true) blocked.push('Published acceptance evidence required')
		if (!s.requiredChecks.length || s.requiredChecks.some(name => !name.trim() || s.checks.filter(c => c.name === name).length !== 1 || !s.checks.some(c => c.name === name && c.head === s.head && c.conclusion === 'success'))) blocked.push('Successful required checks for exact head required')
		const a = s.mergeApproval
		if ((high || s.mode === 'ask') && (!a || a.actor !== s.owner || a.head !== s.head || a.base !== s.base || a.design !== s.design || a.mode !== s.mode || a.generation !== s.generation)) blocked.push('Owner candidate acknowledgment required')
	} catch { blocked.push('Malformed trusted controller snapshot') }
	return blocked
}
