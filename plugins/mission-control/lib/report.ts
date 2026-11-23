import { banned, CONTROL, HIDDEN } from './brief'
import { STOP_REASONS, approvalDigest, type ContractRecord, type Item, type MilestoneState } from './contract'
import contractText from './contract-text.json'

// Checkpoint and close-out reports for a schema 3 contract mission. They ask nothing. Their
// sections come from contract-text.json, and outside the technical record they pass the
// briefing-decisions banned-pattern rules: record text that holds a code or a question mark is
// moved to the technical record, word for word, and the prose points to it.

export const REPORT_SECTIONS: { checkpoint: string[]; closeOut: string[] } = contractText.reportSections
const OPEN = '<details><summary>Technical record</summary>'
const CLOSE = '</details>'
const one = (text: string) => (text.match(/[^ \t\n]+/g) ?? []).join(' ')
// Technical record text keeps its words; < and & are escaped so it cannot close the block.
const sentence = (text: string) => /[.!?]$/.test(text) ? text : `${text}.`
const raw = (text: string) => one(text).replace(/&/g, '&amp;').replace(/</g, '&lt;')
// Prose must pass every briefing-decisions rule: no banned code, no question in any script, and
// no raw HTML, character reference or control or invisible character.
const QUESTION = /[?\uff1f\ufe56\u037e\u061f]/
const unsafe = (text: string) => banned(text)[0] ?? (QUESTION.test(text) ? 'a question' : HIDDEN.test(text) ? 'raw HTML or a character reference' : CONTROL.test(text) ? 'a control or invisible character' : undefined)

class Report {
	private prose: string[] = []
	private notes: string[] = []
	private record: string[] = []
	constructor(title: string) { this.prose.push(`## ${title}`, '', 'This report asks nothing.') }
	/** Record text for the prose, or a pointer to the note that holds it. */
	say(text: string) {
		const t = one(text)
		if (!unsafe(t)) return t
		this.notes.push(t)
		return `see note ${this.notes.length} in the technical record`
	}
	/** A table cell: plain text with its pipes escaped. */
	cell(text: string) { return this.say(text).replace(/\|/g, '\\|') }
	section(name: string, lines: string[]) { this.prose.push('', `### ${name}`, '', ...(lines.length ? lines : ['- None.'])) }
	technical(...lines: string[]) { this.record.push(...lines.map(l => `- ${raw(l)}`)) }
	done(): string {
		const prose = this.prose.join('\n')
		// Every fragment was checked; this guards the joins between them.
		const found = unsafe(prose)
		if (found) throw new Error(`Report rejected: ${found} outside the technical record`)
		const notes = this.notes.map((n, i) => `- Note ${i + 1}: ${raw(n)}`)
		return [prose, '', OPEN, '', ...this.record, ...notes, '', CLOSE, ''].join('\n')
	}
}

const itemsIn = (r: ContractRecord, milestoneId: string): Item[] => [...r.contract.items, ...r.filed].filter(i => i.milestone === milestoneId)
const titleOf = (r: ContractRecord, m: MilestoneState) => r.contract.milestones.find(x => x.id === m.id)!.title
const criteriaOf = (r: ContractRecord, m: MilestoneState) => [...itemsIn(r, m.id).flatMap(i => i.done), ...r.contract.milestones.find(x => x.id === m.id)!.exit]
const pullURL = (m: MilestoneState) => `https://github.com/${m.candidate!.repo}/pull/${m.candidate!.pr}`
const mergedAt = (r: ContractRecord, milestoneId: string | undefined) =>
	milestoneId === undefined ? -1 : r.events.findIndex(e => e.action.type === 'merged' && e.action.milestoneId === milestoneId)

function assumptions(out: Report, list: ContractRecord['assumptions']) {
	return list.map(a => `- ${sentence(out.say(a.assumption))} Why: ${out.say(a.why)}`)
}
function humanTests(out: Report, r: ContractRecord, m: MilestoneState) {
	return itemsIn(r, m.id).map(i => `- ${out.say(i.id)}, ${out.say(i.title)}: ${out.say(i.humanTest)}`)
}
function milestoneRecord(r: ContractRecord, m: MilestoneState): string[] {
	const c = m.candidate!, fp = m.evidence!.fingerprint
	return [
		`Milestone ${m.id}: pull request ${pullURL(m)}, head ${c.head}, base ${c.base}, merge commit ${m.mergeCommit} on dev, fingerprint ${fp}, generation ${m.generation}.`,
		...m.reviews.filter(x => x.fingerprint === fp).map(x => `Milestone ${m.id} gate ${x.gate} review ${x.passed ? 'passed' : 'failed'}, by ${x.reviewer}: ${x.record}`),
		`Milestone ${m.id} failed rounds: gate 1 ${m.failed[0]}, gate 2 ${m.failed[1]}. Dispositions: ${m.dispositions.map(d => `gate ${d.gate} ${d.outcome} (${d.record})`).join('; ') || 'none'}.`,
		`Milestone ${m.id} human test as run: ${m.evidence!.humanTest}`,
		...itemsIn(r, m.id).map(i => {
			const s = r.items.find(x => x.id === i.id)!
			return `Item ${i.id}: ${s.origin === 'finding' ? 'filed from a finding, ' : ''}executor ${s.executor ? `${s.executor.kind} ${s.executor.id}` : 'none'}, review by ${s.review?.reviewer}: ${s.review?.record}`
		}),
	]
}

/** The checkpoint report for a merged milestone, by default the latest one. */
export function checkpointReport(record: ContractRecord, milestoneId?: string): string {
	const m = milestoneId === undefined ? record.milestones.filter(x => x.status === 'merged').at(-1) : record.milestones.find(x => x.id === milestoneId)
	if (!m || m.status !== 'merged') throw new Error(`Refused (milestoneId): a checkpoint report needs a merged milestone${milestoneId === undefined ? '' : `; ${milestoneId} is not merged`}`)
	const index = record.milestones.indexOf(m)
	const out = new Report(`Checkpoint: milestone ${m.id} merged into dev`)
	const [S1, S2, S3, S4, S5, S6] = REPORT_SECTIONS.checkpoint
	out.section(S1, [
		`- Milestone ${out.say(m.id)}, ${out.say(titleOf(record, m))}, merged into dev as pull request ${m.candidate!.pr}: ${out.say(pullURL(m))}`,
		'- Both milestone reviews passed on the same candidate, and every criterion has evidence on it.',
	])
	out.section(S2, itemsIn(record, m.id).flatMap(i => [
		`- ${out.say(i.id)}, ${out.say(i.title)}`,
		...(record.items.find(x => x.id === i.id)!.evidence ?? []).map(e => `  - ${out.say(e.criterion)}: ${out.say(e.result)}`),
	]))
	// Since the last report: taken after the previous milestone merged and before this one merged.
	// One taken later belongs to the next milestone's report.
	const from = mergedAt(record, record.milestones[index - 1]?.id), to = mergedAt(record, m.id)
	let k = 0
	const since = record.events.flatMap((e, i) => e.action.type === 'assume' ? [{ i, a: record.assumptions[k++] }] : []).filter(x => x.i > from && x.i < to).map(x => x.a)
	out.section(S3, assumptions(out, since))
	out.section(S4, [
		...record.filed.filter(i => record.milestones.find(x => x.id === i.milestone)!.status !== 'merged')
			.map(i => `- ${out.say(i.id)}, ${out.say(i.title)}, from a review finding outside the case list, planned for milestone ${out.say(i.milestone)}.`),
		...record.followUps.map(f => `- ${out.say(f.id)}, a follow-up for the close-out: ${out.say(f.text)}`),
	])
	out.section(S5, humanTests(out, record, m))
	const upcoming = record.milestones.slice(index + 1).find(x => x.status !== 'merged')
	out.section(S6, [upcoming
		? `- Milestone ${out.say(upcoming.id)}, ${out.say(titleOf(record, upcoming))}, with ${itemsIn(record, upcoming.id).map(i => out.say(i.id)).join(', ')}.`
		: '- Every milestone is merged; the close-out report comes next.'])
	out.technical(...milestoneRecord(record, m))
	return out.done()
}

/** The close-out report for a complete mission: every milestone merged. */
export function closeOutReport(record: ContractRecord): string {
	const open = record.milestones.filter(m => m.status !== 'merged')
	if (open.length) throw new Error(`Refused (close-out): every milestone must be merged first; open: ${open.map(m => m.id).join(', ')}`)
	const out = new Report('Close-out: every milestone merged into dev')
	const [S1, S2, S3, S4, S5, S6, S7] = REPORT_SECTIONS.closeOut
	const approved = record.approval?.digest === approvalDigest(record.contract)
	out.section(S1, [
		`- ${out.say(record.contract.outcome)}`,
		`- ${record.milestones.length} milestones merged into dev, ${record.items.length} items done (${record.filed.length} filed from findings), ${record.followUps.length} follow-ups, ${record.stops.length} stops, ${record.performed.length} effects performed.`,
	])
	out.section(S2, record.milestones.flatMap(m => [
		`- Milestone ${out.say(m.id)}, ${out.say(titleOf(record, m))}`,
		...criteriaOf(record, m).map(c => `  - ${out.say(c)}: ${out.say(m.evidence!.results.find(r => r.criterion === c)!.result)}`),
	]))
	out.section(S3, assumptions(out, record.assumptions))
	out.section(S4, [
		...record.filed.map(i => `- ${out.say(i.id)}, ${out.say(i.title)}, from a review finding outside the case list, done in milestone ${out.say(i.milestone)}.`),
		...record.followUps.map(f => `- ${out.say(f.id)}, a follow-up: ${out.say(f.text)}`),
	])
	const source = (e: ContractRecord['performed'][number]) => e.effectId ? record.contract.effects.find(x => x.id === e.effectId)?.source ?? '' : ''
	out.section(S5, record.performed.map(e => `- ${e.effectId ? `${out.say(e.effectId)}, ` : 'Not in the contract: '}${sentence(out.say(e.effect))}${e.why ? ` Why: ${sentence(out.say(e.why))}` : ''} ${e.preAuthorized ? `Pre-authorized: ${out.say(source(e))}` : 'Approved by the owner in the effect dialog.'}`))
	out.section(S6, [
		'| Gate | Kind | State | Decider | Source |',
		'| --- | --- | --- | --- | --- |',
		`| Readiness preflight | agent | ${record.preflight ? (record.preflight.passed ? 'passed' : 'failed') : 'not current'} | - | GitHub readiness checks |`,
		`| Kickoff | human | ${approved ? 'approved' : 'not current'} | ${approved ? 'the owner' : '-'} | kickoff dialog |`,
		...record.milestones.map(m => `| Milestone ${out.cell(m.id)} merge into dev | agent | merged | - | pull request ${m.candidate!.pr} |`),
		...record.performed.map(e => e.preAuthorized
			? `| Effect ${out.cell(e.effectId!)} | agent | performed | - | pre-authorized |`
			: `| ${e.effectId ? `Effect ${out.cell(e.effectId)}` : 'Effect not in the contract'} | human | approved | the owner | effect dialog |`),
		...record.stops.map(s => `| Stop ${out.cell(s.id)} | human | ${s.resolved ? 'answered' : 'open'} | ${s.resolved ? out.cell(s.resolved.source) : '-'} | stop reason ${STOP_REASONS.indexOf(s.reason) + 1} |`),
	])
	out.section(S7, record.milestones.flatMap(m => [...humanTests(out, record, m), `- Milestone ${out.say(m.id)}, as run: ${out.say(m.evidence!.humanTest)}`]))
	out.technical(
		`Approval: digest ${record.approval?.digest ?? 'none'}, responder ${record.approval?.responder ?? 'none'}, at ${record.approval?.at ?? '-'}; current digest ${approvalDigest(record.contract)}.`,
		`Preflight: digest ${record.preflight?.digest ?? 'none'}; ${(record.preflight?.results ?? []).map(x => `${x.check} ${x.passed ? 'passed' : 'failed'} (${x.detail})`).join('; ')}.`,
		...record.milestones.flatMap(m => milestoneRecord(record, m)),
		...record.performed.filter(e => e.responder).map(e => `Effect ${e.effectId ?? e.effect}: approved by ${e.responder} at ${e.at}.`),
		...record.stops.map(s => `Stop ${s.id}: ${s.reason} Blocks ${s.blocks.join(', ')}. Question: ${s.question} Answer: ${s.resolved?.answer ?? 'open'}`),
	)
	return out.done()
}
