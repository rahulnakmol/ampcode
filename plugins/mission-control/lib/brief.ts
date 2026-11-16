import type { Mission } from './mission'

// The decision-brief rules from skills/briefing-decisions/scripts/brief_check.py, except reading
// ease and sentence length, which stay in the Python checker. Keep both in step: tests compare
// BANNED with banned.json and run both on tests/fixtures/brief-patterns.json.
export const HEADINGS = [
	'You are deciding', 'If you say yes', 'If you say no', 'What changes', 'What done looks like',
	'What we checked and what we did not', 'Risks you accept', 'Not included', 'How to undo it',
	'Words you may not know',
]
export const BANNED = [
	{ name: 'hex', pattern: '\\b(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,}\\b', ignoreCase: true },
	{ name: 'thread-id', pattern: '\\bT-[0-9a-f]{8}-', ignoreCase: true },
	{ name: 'task-id', pattern: '\\bTU-[A-Za-z0-9]{6,}', ignoreCase: true },
	{ name: 'json', pattern: '"[A-Za-z_][A-Za-z0-9_]*"\\s*:\\s*([\\[{"0-9]|true|false|null)', ignoreCase: true },
	{ name: 'model-slug', pattern: '\\b(anthropic|openai|google|google-vertex|xai|meta|moonshotai|alibaba|deepseek|minimax|nvidia|zhipuai)/[a-z0-9._-]+', ignoreCase: true },
	{ name: 'bare-code', pattern: '^[ \\t]*(?:(?:[-*+]|[0-9]+\\.)[ \\t]+)?(?:\\*\\*)?(?!(?:Q[1-4]|H[12]|FY[0-9]{2,4}|V[0-9])(?:\\*\\*)?:)[A-Z]{1,3}-?[0-9]{1,4}(?:\\*\\*)?:', ignoreCase: false },
]
const COMPILED = BANNED.map(p => ({ name: p.name, re: new RegExp(p.pattern, p.ignoreCase ? 'mi' : 'm') }))
const DETAILS_OPEN = '<details><summary>Technical record</summary>'
const KEYS = ['decision', 'yes', 'no', 'risks', 'excluded', 'picture']
const LIMITS: Record<string, number> = { decision: 30, yes: 40, no: 40 }
const LIST_LIMITS: Record<string, number> = { risks: 30, excluded: 20 }
const PICTURE_HOSTS = ['ampcode.com', 'github.com']
const LIST_ITEM = /^\s*(?:[-*+]|[0-9]+\.)\s+(.*)$/

export type BriefData = { decision: string; yes: string; no: string; risks: string[]; excluded: string[]; picture?: string }
export type Brief = { markdown: string }
export type Dialog = { title: string; message: string; collapsedMessage?: string; expandButtonText?: string; risks?: string[]; after?: any[] }

class BriefError extends Error {
	constructor(rule: string, detail: string) { super(`Decision brief rejected (${rule}): ${detail}. See the briefing-decisions skill.`) }
}
export const words = (text: string) => text.split(/\s+/).filter(Boolean).length
const collapse = (text: string) => text.split(/\s+/).filter(Boolean).join(' ')
const unquote = (value: string) => {
	const v = value.trim()
	return v.length >= 2 && v[0] === v.at(-1) && `"'`.includes(v[0]) ? v.slice(1, -1) : v
}
export function banned(text: string): string[] {
	return COMPILED.filter(p => p.re.test(text)).map(p => p.name)
}

function frontMatter(markdown: string) {
	const match = /^---\n([\s\S]*?)\n---\n/.exec(markdown)
	if (!match) throw new BriefError('front-matter', 'the brief must start with front matter between two --- lines')
	const data: Record<string, string | string[]> = {}
	let key: string | undefined
	for (const line of match[1].split('\n')) {
		if (!line.trim()) continue
		const item = /^\s+-\s+(.*)$/.exec(line)
		if (item) {
			if (!key || !Array.isArray(data[key])) throw new BriefError('front-matter', `list item outside a list: ${line.trim()}`)
			;(data[key] as string[]).push(unquote(item[1]))
			continue
		}
		const pair = /^([a-z]+):(.*)$/.exec(line)
		if (!pair) throw new BriefError('front-matter', `cannot read this line: ${line.trim()}`)
		key = pair[1]
		const value = pair[2].trim()
		if (!KEYS.includes(key)) throw new BriefError('front-matter', `unknown key '${key}'; allowed: ${KEYS.join(', ')}`)
		if (key in data) throw new BriefError('front-matter', `'${key}' appears twice`)
		data[key] = value ? unquote(value) : []
	}
	return { data, front: match[0], body: markdown.slice(match[0].length) }
}

function checkFrontMatter(data: Record<string, string | string[]>): BriefData {
	for (const [key, limit] of Object.entries(LIMITS)) {
		const value = data[key]
		if (typeof value !== 'string' || !value) throw new BriefError('front-matter', `'${key}' is required and must be one line of text`)
		if (words(value) > limit) throw new BriefError('front-matter', `'${key}' has ${words(value)} words; limit ${limit}`)
	}
	for (const [key, limit] of Object.entries(LIST_LIMITS)) {
		const items = data[key]
		if (!Array.isArray(items) || items.length < 1 || items.length > 6) throw new BriefError('front-matter', `'${key}' must list 1 to 6 items`)
		if (new Set(items.map(collapse)).size !== items.length) throw new BriefError('front-matter', `'${key}' items must be unique`)
		for (const i of items) if (!i || words(i) > limit) throw new BriefError('front-matter', `each '${key}' item needs 1 to ${limit} words: ${i}`)
	}
	if ('picture' in data) {
		let url: URL | undefined
		try { url = typeof data.picture === 'string' ? new URL(data.picture) : undefined } catch { url = undefined }
		if (!url || url.protocol !== 'https:' || !PICTURE_HOSTS.includes(url.hostname)) throw new BriefError('front-matter', "'picture' must be an https URL on ampcode.com or github.com")
	}
	return data as BriefData
}

/** The collapsed summary, as plain lines; brief_check.py counts the same words. */
export function summaryLines(d: BriefData) {
	return [`You are deciding: ${d.decision}`, `If you say yes: ${d.yes}`, `If you say no: ${d.no}`, 'Risks you accept:', ...d.risks.map((r, i) => `${i + 1}. ${r}`)]
}

/** Validate a decision brief and return its front matter. Throws a plain error naming the rule. */
export function validateBrief(markdown: unknown): BriefData {
	if (typeof markdown !== 'string' || !markdown.trim()) throw new BriefError('front-matter', 'bundle.brief.markdown must be the brief text')
	if ([...markdown].length > 20_000) throw new BriefError('length', `${[...markdown].length} characters; limit 20000`)
	const { data: raw, front, body } = frontMatter(markdown)
	const data = checkFrontMatter(raw)
	const count = words(summaryLines(data).join('\n'))
	if (count > 150) throw new BriefError('summary', `the collapsed summary has ${count} words; limit 150`)
	const start = body.indexOf(DETAILS_OPEN)
	if (start < 0) throw new BriefError('technical-record', `end the brief with a ${DETAILS_OPEN} block`)
	if (body.trimEnd().split('\n').at(-1)!.trim() !== '</details>' || body.split(DETAILS_OPEN).length !== 2) throw new BriefError('technical-record', 'the one technical record block must close with </details> and end the brief')
	const prose = body.slice(0, start)
	const found = [...prose.matchAll(/^## (.+?)[ \t]*$/gm)].map(m => m[1])
	if (found.join('\n') !== HEADINGS.join('\n')) {
		const missing = HEADINGS.find(h => !found.includes(h))
		throw new BriefError('headings', `${missing ? `missing '${missing}'` : 'wrong order or an extra ## heading'}; use exactly: ${HEADINGS.join(' / ')}`)
	}
	const sections: Record<string, string[]> = {}
	let current: string | undefined
	for (const line of prose.split('\n')) {
		const heading = /^## (.+?)[ \t]*$/.exec(line)
		if (heading) sections[current = heading[1]] = []
		else if (current) sections[current].push(line)
	}
	for (const [key, heading] of [['risks', 'Risks you accept'], ['excluded', 'Not included']] as const) {
		const listed = new Set(sections[heading].map(l => LIST_ITEM.exec(l)?.[1]).filter((v): v is string => v !== undefined).map(collapse))
		for (const item of data[key]) if (!listed.has(collapse(item))) throw new BriefError('consistency', `'${item}' from '${key}' must be a list item under '## ${heading}'`)
	}
	if (/<(?:!--|[A-Za-z/])/.test(prose)) throw new BriefError('html', 'raw HTML and HTML comments are not allowed before the technical record')
	for (const [part, where] of [[front, 'front matter'], [prose, 'prose']]) {
		const names = banned(part)
		if (names.length) throw new BriefError('banned', `${names[0]} pattern in the ${where}; move codes to the technical record`)
	}
	return data
}

const briefOf = (s: Mission) => s.design?.bundle.brief
const numbered = (items: string[]) => items.map((item, i) => `${i + 1}. ${item}`).join('\n')

/** Today's raw v1 details, kept for records designed before decision briefs. */
export function rawDetails(s: Mission) {
	const c = s.candidate
	return [
		`Mission requirements: ${s.requirements}`, `Design: ${s.design?.digest}`, JSON.stringify(s.design?.bundle, null, 2),
		c ? `Candidate: https://github.com/${c.repo}/pull/${c.pr}\nHead: ${c.head}\nBase: ${c.base}\nRisk: ${c.risk}` : '',
		...(s.design?.criteria ?? []).map((criterion, i) => `${i + 1}. ${criterion}\n${s.evidence?.results[i] ?? 'Not yet verified'}`),
		`Try it: ${s.evidence?.tryIt ?? 'Not yet supplied'}`, `Customer value: ${s.evidence?.value ?? 'Not yet established'}`,
		`Merge preference: ${s.mode}; high risk always requires owner acknowledgment.`,
		'Approvals and evidence are local workflow gates, not a hostile-shell security boundary. Required CI and protected dev must also permit integration.',
	].filter(Boolean).join('\n\n')
}
const LEGACY = 'This mission was designed before decision briefs. The details below are the raw design record.'

export function designDialog(s: Mission): Dialog {
	const brief = briefOf(s)
	if (!brief) return { title: 'Approve the design', message: `${LEGACY}\n\n${rawDetails(s)}`, risks: [], after: [] }
	// Stored briefs were validated when the design was recorded; they are not revalidated here.
	const parsed = frontMatter(brief.markdown)
	const data = parsed.data as BriefData, body = parsed.body
	const b = s.design!.bundle
	return {
		title: `Approve the design: ${data.decision}`,
		collapsedMessage: summaryMarkdown(data),
		expandButtonText: 'Read the brief',
		message: [
			body.trim(),
			`## What you approve as done\n\n${numbered(s.design!.criteria)}`,
			`## Technical record\n\n**Requirements:** ${s.requirements}\n\n**Spec:** ${b.spec}\n\n**Plan:** ${b.plan}\n\n**Technical design:** ${b.technical}\n\n**UX design:** ${b.ux}`,
		].join('\n\n'),
		risks: data.risks,
		after: data.picture ? [{ type: 'link', name: 'picture', label: 'Open the picture (illustration, not part of what you approve)', value: data.picture }] : [],
	}
}

export function summaryMarkdown(d: BriefData) {
	return [`**You are deciding:** ${d.decision}`, `**If you say yes:** ${d.yes}`, `**If you say no:** ${d.no}`, `**Risks you accept:**\n\n${numbered(d.risks)}`].join('\n\n')
}

export function mergeDialog(s: Mission): Dialog {
	const brief = briefOf(s)
	const c = s.candidate!
	const url = `https://github.com/${c.repo}/pull/${c.pr}`
	const link = [{ type: 'link', name: 'pull-request', label: 'Open the pull request', value: url }]
	if (!brief) return { title: 'Merge into dev', message: `${LEGACY}\n\n${rawDetails(s)}`, risks: [], after: link }
	const decision = frontMatter(brief.markdown).data.decision as string
	return {
		title: `Merge into dev: ${decision}`,
		collapsedMessage: `**Pull request:** number ${c.pr} in ${c.repo}\n\n**Risk level:** ${c.risk}\n\n**Try it:** ${s.evidence?.tryIt ?? 'Not supplied yet'}`,
		expandButtonText: 'Read the evidence',
		message: [
			'## What was approved as done, and the result',
			s.design!.criteria.map((criterion, i) => `${i + 1}. ${criterion}\n\n   Result: ${s.evidence?.results[i] ?? 'Not checked yet'}`).join('\n\n'),
			`**Customer value:** ${s.evidence?.value ?? 'Not established yet'}`,
			`**Pull request:** ${url}\n\n**Head:** ${c.head}\n\n**Base:** ${c.base}`,
			'Approvals are local workflow gates. Required checks and the protected dev branch must also allow the merge.',
		].join('\n\n'),
		risks: [],
		after: link,
	}
}

/** Every approval dialog: owner-only (the secret field), human-only, and the turn ends on decline. */
export function confirmOptions(d: Dialog) {
	return {
		title: d.title, message: d.message + '\n\nOnly the thread owner can approve. The masked field restricts this dialog to the owner; APPROVE is not a password.',
		...(d.expandButtonText ? { expandButtonText: d.expandButtonText, collapsedMessage: d.collapsedMessage } : {}),
		requireHuman: true, endTurnOnDecline: true,
		fields: [
			...(d.risks ?? []).map((risk, i) => ({ type: 'checkbox' as const, name: `risk-${i + 1}`, label: risk, value: 'false' })),
			{ name: 'acknowledgment', label: 'Type APPROVE to confirm you are the mission owner (owner-only check, not a password)', value: '', secret: true },
			...(d.after ?? []),
		],
	}
}

/** Why an answer does not approve, or undefined when it does. Only 'true' counts as a tick. */
export function refusal(result: Record<string, string> | undefined, risks: string[]): string | undefined {
	if (!result) return 'Not approved. The dialog was closed without approval; the mission remains blocked.'
	const unticked = risks.filter((_, i) => result[`risk-${i + 1}`] !== 'true')
	if (unticked.length) return `Not approved. These risks were not ticked: ${unticked.join('; ')}. If you ticked them, your Amp app may not show tick boxes; approve from the Amp web app.`
	if (result.acknowledgment !== 'APPROVE') return 'Not approved. Type APPROVE in the owner field.'
	return undefined
}
