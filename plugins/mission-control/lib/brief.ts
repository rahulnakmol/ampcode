import type { Mission } from './mission'

// The decision-brief rules from skills/briefing-decisions/scripts/brief_check.py, except reading
// ease, which stays in the Python checker. Keep both in step: tests compare BANNED with
// banned.json and run both on tests/fixtures/brief-patterns.json and brief-cases.json.
export const HEADINGS = [
	'You are deciding', 'If you say yes', 'If you say no', 'What changes', 'What done looks like',
	'What we checked and what we did not', 'Risks you accept', 'Not included', 'How to undo it',
	'Words you may not know',
]
export const BANNED = [
	{ name: 'hex', pattern: '\\b(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,}\\b', ignoreCase: true },
	{ name: 'thread-id', pattern: '\\bT-[0-9a-f]{8}-', ignoreCase: true },
	{ name: 'task-id', pattern: '\\bTU-[A-Za-z0-9]{6,}', ignoreCase: true },
	{ name: 'json', pattern: '"[A-Za-z_][A-Za-z0-9_]*"[ \\t\\n]*:[ \\t\\n]*([\\[{"0-9]|true|false|null)', ignoreCase: true },
	{ name: 'model-slug', pattern: '\\b(anthropic|openai|google|google-vertex|xai|meta|moonshotai|alibaba|deepseek|minimax|nvidia|zhipuai)/[a-z0-9._-]+', ignoreCase: true },
	{ name: 'bare-code', pattern: '^[ \\t]*(?:(?:[-*+]|[0-9]+\\.)[ \\t]+)?(?:\\*\\*)?(?!(?:Q[1-4]|H[12]|FY[0-9]{2,4}|V[0-9])(?:\\*\\*)?:)[A-Z]{1,3}-?[0-9]{1,4}(?:\\*\\*)?:', ignoreCase: false },
]
const COMPILED = BANNED.map(p => ({ name: p.name, re: new RegExp(p.pattern, p.ignoreCase ? 'mi' : 'm') }))
const DETAILS_OPEN = '<details><summary>Technical record</summary>'
const DETAILS_CLOSE = '</details>'
const KEYS = ['decision', 'yes', 'no', 'risks', 'excluded', 'picture']
const LIMITS: Record<string, number> = { decision: 30, yes: 40, no: 40 }
const LIST_LIMITS: Record<string, number> = { risks: 30, excluded: 20 }
export const LINK = /^https:\/\/(ampcode\.com|github\.com)(\/[\x21-\x7e]*)?$/
// Control and format characters (zero-width, bidirectional, tag characters) are invisible or reorder text.
const CONTROL = /[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029]|\p{Cf}/u
// Raw HTML (tags, comments, <!DOCTYPE, <![CDATA[, <?...?>) and Markdown link reference definitions
// all render as hidden text.
// A reference definition hides text even inside a list item or block quote, with an escaped ],
// or with a label that continues on the next line after a backslash.
const HIDDEN = /<(?:[!?]|[A-Za-z/])|^[ \t>*+\-0-9.)]*\[(?:\\[\s\S]|[^\\\]])*\]:/m
// Markdown that renders some of its text invisibly. Links and fences are allowlisted: a link is
// [text](destination) with text and a plain destination (no spaces, parentheses, backslashes or
// quotes) closed at once, so it has no title; a fence line holds only the fence. Images, empty link
// text, GitHub math commands and table rows wider than their header are rejected.
const IMAGE = /!\[/
const INLINE_LINK = /\]\((?!<?[^\s()<>\\"']+>?\))/
const EMPTY_LINK = /\[[ \t*_~]*\]\(/
const FENCE_LABEL = /^[ \t>*+\-0-9.)]*(?:`{3,}(?!`)|~{3,}(?!~))[ \t]*\S/m
const MATH = /\$[^$]*\\[A-Za-z]/
const TABLE_DELIMITER = /^\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$/
const CONTAINER = /^[ \t>]*/
const MARKER = /^(?:[-*+]|[0-9]+[.)])[ \t]+/
// YAML would read these in a front-matter value as a comment, anchor, alias, tag or block, and
// GitHub's front-matter table would hide words.
const YAML_SPECIAL = /^[&*!|>{[%@`]|[ \t]#/
const LIST_ITEM = /^[ \t]*(?:[-*+]|[0-9]+\.)[ \t]+(.*)$/
const HEADING = /^## (.+?)[ \t]*$/
const WORD = /[A-Za-z][A-Za-z'-]*|[0-9][0-9,.%]*/g

export type BriefData = { decision: string; yes: string; no: string; risks: string[]; excluded: string[]; picture?: string }
export type Brief = { markdown: string; url: string }
// title and message are Markdown in Amp, so they hold only fixed text. Agent and record text goes
// in details, a read-only field: "line breaks are kept and Markdown is not rendered".
export type Dialog = { title: string; message: string; link?: { name: string; label: string; value: string }; details?: string }

class BriefError extends Error {
	constructor(rule: string, detail: string) { super(`Decision brief rejected (${rule}): ${detail}. See the briefing-decisions skill.`) }
}
// Whitespace is space, tab and newline only, exactly as in brief_check.py.
const tokens = (text: string) => text.match(/[^ \t\n]+/g) ?? []
export const words = (text: string) => tokens(text).length
const collapse = (text: string) => tokens(text).join(' ')
const trim = (text: string) => text.replace(/^[ \t]+|[ \t]+$/g, '')
const unquote = (value: string) => {
	const v = trim(value)
	return v.length >= 2 && v[0] === v.at(-1) && `"'`.includes(v[0]) ? v.slice(1, -1) : v
}
function cells(line: string) {
	let s = trim(line.replace(CONTAINER, ''))
	if (s.startsWith('|')) s = s.slice(1)
	if (s.endsWith('|') && !s.endsWith('\\|')) s = s.slice(0, -1)
	return s.split(/(?<!\\)\|/).length
}
/** The first Markdown construct that hides words, or undefined. Keep in step with brief_check.py. */
function hiddenMarkdown(text: string) {
	if (IMAGE.test(text)) return 'an image'
	if (EMPTY_LINK.test(text)) return 'a link with no text'
	if (INLINE_LINK.test(text)) return 'a link with a title or an unusual destination'
	if (FENCE_LABEL.test(text)) return 'a code fence with a label'
	if (MATH.test(text)) return 'a math command'
	const lines = text.split('\n')
	for (let i = 1; i < lines.length; i++) {
		const header = lines[i - 1].replace(CONTAINER, '').replace(MARKER, ''), delimiter = lines[i].replace(CONTAINER, '')
		if (!(header.includes('|') || delimiter.includes('|')) || !TABLE_DELIMITER.test(delimiter) || !delimiter.includes('-')) continue
		const width = cells(header)
		for (const row of lines.slice(i + 1)) {
			if (!trim(row)) break
			if (cells(row) > width) return 'a table row wider than its header'
		}
	}
	return undefined
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
		if (!trim(line)) continue
		const item = /^[ \t]+-[ \t]+(.*)$/.exec(line)
		if (item) {
			if (!key || !Array.isArray(data[key])) throw new BriefError('front-matter', `list item outside a list: ${trim(line)}`)
			if (YAML_SPECIAL.test(trim(item[1]))) throw new BriefError('front-matter', `a '${key}' item starts with a YAML symbol or has ' #'; write plain text`)
			;(data[key] as string[]).push(unquote(item[1]))
			continue
		}
		const pair = /^([a-z]+):(.*)$/.exec(line)
		if (!pair) throw new BriefError('front-matter', `cannot read this line: ${trim(line)}`)
		key = pair[1]
		const value = trim(pair[2])
		if (YAML_SPECIAL.test(value)) throw new BriefError('front-matter', `'${pair[1]}' starts with a YAML symbol or has ' #'; write plain text`)
		if (!KEYS.includes(key)) throw new BriefError('front-matter', `unknown key '${key}'; allowed: ${KEYS.join(', ')}`)
		if (key in data) throw new BriefError('front-matter', `'${key}' appears twice`)
		data[key] = value ? unquote(value) : []
	}
	return { data, front: match[0], body: markdown.slice(match[0].length) }
}

function checkFrontMatter(data: Record<string, string | string[]>): BriefData {
	for (const [key, limit] of Object.entries(LIMITS)) {
		const value = data[key]
		if (typeof value !== 'string' || !words(value)) throw new BriefError('front-matter', `'${key}' is required and must be one line of text`)
		if (words(value) > limit) throw new BriefError('front-matter', `'${key}' has ${words(value)} words; limit ${limit}`)
	}
	for (const [key, limit] of Object.entries(LIST_LIMITS)) {
		const items = data[key]
		if (!Array.isArray(items) || items.length < 1 || items.length > 6) throw new BriefError('front-matter', `'${key}' must list 1 to 6 items`)
		if (new Set(items.map(collapse)).size !== items.length) throw new BriefError('front-matter', `'${key}' items must be unique`)
		for (const i of items) if (words(i) < 1 || words(i) > limit) throw new BriefError('front-matter', `each '${key}' item needs 1 to ${limit} words: ${i}`)
	}
	if ('picture' in data && !(typeof data.picture === 'string' && LINK.test(data.picture))) throw new BriefError('front-matter', "'picture' must be an https URL on ampcode.com or github.com")
	return data as BriefData
}

/** The labelled summary of the front matter; brief_check.py counts the same words. */
export function summaryLines(d: BriefData) {
	return [`You are deciding: ${d.decision}`, `If you say yes: ${d.yes}`, `If you say no: ${d.no}`, 'Risks you accept:', ...d.risks.map((r, i) => `${i + 1}. ${r}`)]
}

// Sentences as brief_check.py's readable_prose() and sentences() find them.
function sentences(prose: string) {
	const keep: string[] = []
	for (const line of prose.replace(/```[\s\S]*?```/g, ' ').split('\n')) {
		let s = trim(line)
		if (!s || s.startsWith('|') || s.startsWith('#') || s.startsWith('<')) continue
		s = s.replace(/`[^`]*`/g, 'X').replace(/\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/[*_>]+/g, '').replace(/^[-0-9. ]+/, '')
		keep.push(/[.!?:]$/.test(s) ? s : s + '.')
	}
	return keep.join(' ').split(/(?<=[.!?:])[ \t]+/).filter(s => /[A-Za-z]/.test(s))
}

/** Validate a decision brief and return its front matter. Throws a plain error naming the rule.
 * Same rules and order as brief_check.py, except reading ease, which stays in Python. */
export function validateBrief(markdown: unknown): BriefData {
	if (typeof markdown !== 'string') throw new BriefError('front-matter', 'bundle.brief.markdown must be the brief text')
	const length = [...markdown].length
	if (length > 20_000) throw new BriefError('length', `${length} characters; limit 20000`)
	if (CONTROL.test(markdown)) throw new BriefError('characters', 'use plain newlines (no carriage returns, line separators or control characters)')
	const { data: raw, front, body } = frontMatter(markdown)
	const data = checkFrontMatter(raw)
	const count = words(summaryLines(data).join('\n'))
	if (count > 150) throw new BriefError('summary', `the summary has ${count} words; limit 150`)
	const start = body.indexOf(DETAILS_OPEN)
	if (start < 0) throw new BriefError('technical-record', `end the brief with a ${DETAILS_OPEN} block`)
	const end = body.replace(/[ \t\n]+$/, '')
	if (trim(end.split('\n').at(-1)!) !== DETAILS_CLOSE || body.split(DETAILS_OPEN).length !== 2) throw new BriefError('technical-record', 'the one technical record block must close with </details> and end the brief')
	const prose = body.slice(0, start)
	const record = end.slice(start + DETAILS_OPEN.length, end.lastIndexOf(DETAILS_CLOSE))
	const found = prose.split('\n').map(l => HEADING.exec(l)?.[1]).filter((h): h is string => h !== undefined)
	if (found.join('\n') !== HEADINGS.join('\n')) {
		const missing = HEADINGS.find(h => !found.includes(h))
		throw new BriefError('headings', `${missing ? `missing '${missing}'` : 'wrong order or an extra ## heading'}; use exactly: ${HEADINGS.join(' / ')}`)
	}
	const sections: Record<string, string[]> = {}
	let current: string | undefined
	for (const line of prose.split('\n')) {
		const heading = HEADING.exec(line)
		if (heading) sections[current = heading[1]] = []
		else if (current) sections[current].push(line)
	}
	for (const [key, heading] of [['risks', 'Risks you accept'], ['excluded', 'Not included']] as const) {
		const listed = new Set(sections[heading].map(l => LIST_ITEM.exec(l)?.[1]).filter((v): v is string => v !== undefined).map(collapse))
		for (const item of data[key]) if (!listed.has(collapse(item))) throw new BriefError('consistency', `'${item}' from '${key}' must be a list item under '## ${heading}'`)
	}
	if (HIDDEN.test(front + prose + record)) throw new BriefError('html', 'raw HTML, HTML comments and link reference definitions are not allowed, except the technical record block itself')
	const hiding = hiddenMarkdown(front + prose + record)
	if (hiding) throw new BriefError('markdown', `${hiding} can hide words; use no images, link titles, labelled code fences or table rows wider than their header`)
	for (const [part, where] of [[front, 'front matter'], [prose, 'prose']]) {
		const names = banned(part)
		if (names.length) throw new BriefError('banned', `${names[0]} pattern in the ${where}; move codes to the technical record`)
	}
	const long = sentences(prose).filter(s => (s.match(WORD) ?? []).length > 25)
	if (long.length) throw new BriefError('sentence-length', `${long.length} sentence(s) over 25 words, first: ${long[0].slice(0, 80)}`)
	return data
}

const briefOf = (s: Mission) => s.design?.bundle.brief
const numbered = (items: string[]) => items.map((item, i) => `${i + 1}. ${item}`).join('\n')
const NOTE = 'Only the thread owner can approve. The owner field restricts this dialog to the owner; APPROVE is not a password.'

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
const LEGACY = 'This mission was designed before decision briefs. The raw design record is in Details.'

export function designDialog(s: Mission): Dialog {
	const brief = briefOf(s)
	if (!brief) return { title: 'Approve the design', message: LEGACY, details: rawDetails(s) }
	// Stored briefs were validated when the design was recorded; they are not revalidated here.
	const decision = frontMatter(brief.markdown).data.decision as string
	const b = s.design!.bundle
	return {
		title: 'Approve the design',
		message: 'Open the brief, then type APPROVE. You approve the brief as it reads now. If the stored brief text or its link changes, this approval no longer counts. Edits to the page after you approve do not cancel it.',
		link: { name: 'brief', label: 'Open the brief you are approving', value: brief.url },
		details: [
			`You are deciding: ${decision}`, `Brief: ${brief.url}`,
			`What you approve as done:\n${numbered(s.design!.criteria)}`,
			`Technical record\n\nRequirements: ${s.requirements}\n\nSpec: ${b.spec}\n\nPlan: ${b.plan}\n\nTechnical design: ${b.technical}\n\nUX design: ${b.ux}`,
		].join('\n\n'),
	}
}

export function mergeDialog(s: Mission): Dialog {
	const brief = briefOf(s)
	const c = s.candidate!
	const url = `https://github.com/${c.repo}/pull/${c.pr}`
	const link = { name: 'pull-request', label: 'Open the pull request', value: url }
	if (!brief) return { title: 'Merge into dev', message: LEGACY, link, details: rawDetails(s) }
	const decision = frontMatter(brief.markdown).data.decision as string
	return {
		title: 'Merge into dev',
		// The number and risk are validated values, not free text.
		message: `Open the pull request, then type APPROVE to merge it into dev. Pull request number ${c.pr}, risk level ${c.risk}.`,
		link,
		details: [
			`You are deciding: ${decision}`, `Try it: ${s.evidence?.tryIt ?? 'Not supplied yet'}`,
			`What was approved as done, and the result:\n${s.design!.criteria.map((criterion, i) => `${i + 1}. ${criterion}\n   Result: ${s.evidence?.results[i] ?? 'Not checked yet'}`).join('\n')}`,
			`Customer value: ${s.evidence?.value ?? 'Not established yet'}`,
			`Pull request: ${url}\nHead: ${c.head}\nBase: ${c.base}`,
			`Merge preference: ${s.mode}; high risk always requires owner acknowledgment.`,
			'Approvals are local workflow gates. Required checks and the protected dev branch must also allow the merge.',
		].join('\n\n'),
	}
}

/** Every approval dialog: owner-only (the secret field), human-only, and the turn ends on decline.
 * A link before the owner field shows as numbered steps; details come last and never block. */
export function confirmOptions(d: Dialog) {
	return {
		title: d.title, message: `${d.message}\n\n${NOTE}`,
		requireHuman: true, endTurnOnDecline: true,
		fields: [
			...(d.link ? [{ type: 'link' as const, ...d.link }] : []),
			{ name: 'acknowledgment', label: 'Type APPROVE to confirm you are the mission owner (owner-only check, not a password)', value: '', secret: true },
			...(d.details ? [{ name: 'details', label: 'Details', value: d.details, readOnly: true, multiline: true, optional: true }] : []),
		],
	}
}

/** Why an answer does not approve, or undefined when it does. */
export function refusal(result: Record<string, string> | undefined): string | undefined {
	if (!result) return 'Not approved. The dialog was closed without approval; the mission remains blocked.'
	if (result.acknowledgment !== 'APPROVE') return 'Not approved. Type APPROVE in the owner field.'
	return undefined
}
