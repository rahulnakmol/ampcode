import { variant, type ContractRecord, type Pending } from './contract'

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
// Control and format characters (zero-width, bidirectional, tag characters) and the other default
// ignorable characters (variation selectors, fillers) are invisible or reorder text. Right-to-left
// letters, punctuation and digits (the blocks that hold every Bidi_Class R, AL and AN character)
// reorder the text around them, even text that looks like plain ASCII.
export const CONTROL = /[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029\u034f\u115f\u1160\u17b4\u17b5\u180b-\u180f\u2065\u3164\ufe00-\ufe0f\uffa0\ufff0-\ufff8\u{1bca0}-\u{1bca3}\u{1d173}-\u{1d17a}\u{e0000}-\u{e0fff}\u0590-\u08ff\ufb1d-\ufdff\ufe70-\ufeff\u{10800}-\u{10fff}\u{1e800}-\u{1efff}]|\p{Cf}/u
// Raw HTML (tags, comments, <!DOCTYPE, <![CDATA[, <?...?>), HTML character references and Markdown
// link reference definitions all render as hidden text; GitHub decodes a reference before math, so it
// can also become an invisible character or a math command.
// A reference definition hides text even inside a list item or block quote, with an escaped ],
// or with a label that continues on the next line after a backslash.
export const HIDDEN = /<(?:[!?]|[A-Za-z/])|&(?:#[0-9]+|#[xX][0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);|^[ \t>*+\-0-9.)]*\[(?:\\[\s\S]|[^\\\]])*\]:/m
// Markdown that renders some of its text invisibly. Links and fences are allowlisted: a link is
// [text](destination) with text and a plain destination (no spaces, parentheses, backslashes or
// quotes) closed at once, so it has no title; a fence line holds only the fence. Images, empty link
// text, GitHub math holding a TeX special character (a command, a % comment or an error) and table
// rows wider than their header are rejected.
const IMAGE = /!\[/
const INLINE_LINK = /\]\((?!<?[^\s()<>\\"']+>?\))/
const EMPTY_LINK = /\[[ \t*_~]*\]\(/
const FENCE_LABEL = /^[ \t>*+\-0-9.)]*(?:`{3,}(?!`)|~{3,}(?!~))[ \t]*[^ \t\n]/m
// GitHub inline math is $...$ within one paragraph, with no space after the opening $ or before the
// closing $, and no digit after it. $$ (display math) and $` (backtick math) are rejected outright.
const MATH = /\$(?![ \t\n])(?:[^$\n]|\n(?![ \t>]*\n))*[\\%&#{}^_~](?:[^$\n]|\n(?![ \t>]*\n))*(?<![ \t\n])\$(?![0-9])|\$\$|\$`/
const TABLE_DELIMITER = /^\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$/
const CONTAINER = /^[ \t>]*/
// Quote and list markers before a table line, repeated for nested lists and quotes.
const PREFIX = /^(?:[ \t>]*(?:[-*+]|[0-9]+[.)])[ \t]+)*[ \t>]*/
// YAML would read these in a front-matter value as a comment, anchor, alias, tag or block, and
// GitHub's front-matter table would hide words. A backslash can be a double-quoted escape for an
// invisible character.
const YAML_SPECIAL = /^[&*!|>{[%@`]|[ \t]#|\\/
const LIST_ITEM = /^[ \t]*(?:[-*+]|[0-9]+\.)[ \t]+(.*)$/
const HEADING = /^## (.+?)[ \t]*$/
const WORD = /[A-Za-z][A-Za-z'-]*|[0-9][0-9,.%]*/g

export type BriefData = { decision: string; yes: string; no: string; risks: string[]; excluded: string[]; picture?: string }

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
	let s = trim(line.replace(PREFIX, ''))
	if (s.startsWith('|')) s = s.slice(1)
	if (s.endsWith('|') && !s.endsWith('\\|')) s = s.slice(0, -1)
	return s.split(/(?<!\\)\|/).length
}
/** The first Markdown construct that hides words, or undefined. Keep in step with brief_check.py. */
export function hiddenMarkdown(text: string) {
	if (IMAGE.test(text)) return 'an image'
	if (EMPTY_LINK.test(text)) return 'a link with no text'
	if (INLINE_LINK.test(text)) return 'a link with a title or an unusual destination'
	if (FENCE_LABEL.test(text)) return 'a code fence with a label'
	if (MATH.test(text)) return 'math with a TeX special character'
	const lines = text.split('\n')
	for (let i = 1; i < lines.length; i++) {
		const header = lines[i - 1].replace(PREFIX, ''), delimiter = lines[i].replace(CONTAINER, '')
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
			if (YAML_SPECIAL.test(trim(item[1]))) throw new BriefError('front-matter', `a '${key}' item starts with a YAML symbol or has ' #' or a backslash; write plain text`)
			;(data[key] as string[]).push(unquote(item[1]))
			continue
		}
		const pair = /^([a-z]+):(.*)$/.exec(line)
		if (!pair) throw new BriefError('front-matter', `cannot read this line: ${trim(line)}`)
		key = pair[1]
		const value = trim(pair[2])
		if (YAML_SPECIAL.test(value)) throw new BriefError('front-matter', `'${pair[1]}' starts with a YAML symbol or has ' #' or a backslash; write plain text`)
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
	if (CONTROL.test(markdown)) throw new BriefError('characters', 'use plain newlines and left-to-right text (no carriage returns, line separators, control characters, invisible characters such as zero-width marks or emoji variation selectors, or right-to-left letters)')
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
	if (HIDDEN.test(front + prose + record)) throw new BriefError('html', 'raw HTML, HTML comments, character references such as &amp; and link reference definitions are not allowed, except the technical record block itself')
	const hiding = hiddenMarkdown(front + prose + record)
	if (hiding) throw new BriefError('markdown', `${hiding} can hide words; use plain links with text, unlabelled code fences, no images, no $$, no $\` and no $ math with \\ % & # { } ^ _ ~, and no table rows wider than their header`)
	for (const [part, where] of [[front, 'front matter'], [prose, 'prose']]) {
		const names = banned(part)
		if (names.length) throw new BriefError('banned', `${names[0]} pattern in the ${where}; move codes to the technical record`)
	}
	const long = sentences(prose).filter(s => (s.match(WORD) ?? []).length > 25)
	if (long.length) throw new BriefError('sentence-length', `${long.length} sentence(s) over 25 words, first: ${long[0].slice(0, 80)}`)
	return data
}

// Schema 3 contract dialogs. The owner ticks a box for each default and pre-authorized effect,
// or writes Changes; there is no typed word and no secret field. Who answered comes from the
// dialog's onAnswered responder, which the tool passes to readAnswer as data.
export const NOT_APPROVED = 'Not approved: tick every box, or write what to change.'
export const UNCONFIRMED = 'This client could not confirm who answered; open the approval in the Amp web app'
const OWNER_NOTE = "Only the thread owner's answer counts; Amp reports who answered."
const CHANGES = 'changes'
export type ContractField =
	| { type: 'link'; name: string; label: string; value: string }
	| { type: 'checkbox'; name: string; label: string; value: 'false' }
	| { name: typeof CHANGES; label: string; value: ''; placeholder: string; multiline: true; optional: true }
export type ContractDialog = {
	title: string; message: string; confirmButtonText: 'Submit'; requireHuman: true; endTurnOnDecline: true; fields: ContractField[]
}
const sentence = (text: string) => /[.!?]$/.test(text.trim()) ? text.trim() : `${text.trim()}.`
function contractDialog(record: ContractRecord, title: string, message: string, boxes: { name: string; label: string }[]): ContractDialog {
	return {
		// Checkbox labels hold record text, collapsed to one line; title and message hold fixed text.
		title, message: `${message}\n\n${OWNER_NOTE}`, confirmButtonText: 'Submit', requireHuman: true, endTurnOnDecline: true,
		fields: [
			{ type: 'link', name: 'brief', label: 'Open the contract brief', value: record.contract.brief.url },
			...boxes.map(b => ({ type: 'checkbox' as const, name: b.name, label: collapse(b.label), value: 'false' as const })),
			{ name: CHANGES, label: 'Changes (optional)', value: '', placeholder: 'What to change, in your words', multiline: true, optional: true },
		],
	}
}

/** The kickoff dialog: one unticked box per open-question default and per pre-authorized effect.
 * Effects that are not pre-authorized get their own effect dialog when the mission needs them. */
export function kickoffDialog(record: ContractRecord): ContractDialog {
	const c = record.contract
	return contractDialog(record, 'Approve the mission contract',
		`One approval starts the whole mission. ${variant(record) === 'ship' ? 'Each milestone merges into dev once its gates pass.' : 'No milestone merges: each pull request stays open for you, and the next milestone builds on it.'} Open the contract brief, tick each default you accept, and submit. To change something, untick it or write it in Changes; nothing is approved then.`,
		[
			...c.openQuestions.map(q => ({ name: `default-${q.id}`, label: `${q.id}. ${q.question} Default: ${q.default}` })),
			...c.effects.filter(e => e.preAuthorized).map(e => ({ name: `effect-${e.id}`, label: `${e.id}. ${sentence(e.effect)} Pre-authorized: ${e.source}` })),
		])
}

/** The effect dialog for a pending effect approval: the same pattern with one box. */
export function effectDialog(record: ContractRecord, pending: Pending): ContractDialog {
	if (pending.kind !== 'effect') throw new Error('An effect dialog needs a pending effect approval')
	let box: { name: string; label: string }
	if (pending.effectId !== undefined) {
		const e = record.contract.effects.find(e => e.id === pending.effectId)
		if (!e) throw new Error(`Refused (effectId): unknown effect ${pending.effectId}`)
		if (e.preAuthorized) throw new Error(`Refused (effectId): ${e.id} is pre-authorized and needs no dialog`)
		box = { name: `effect-${e.id}`, label: `Approve once: ${e.id}. ${sentence(e.effect)} Contract note: ${e.source}` }
	} else box = { name: 'effect', label: `Approve once: ${sentence(pending.effect ?? '')} Why: ${pending.why}` }
	return contractDialog(record, 'Approve an outside effect',
		'This mission wants to do something its contract did not pre-authorize. Open the contract brief, then tick to approve it once. To change it, leave the box unticked or write it in Changes; nothing is approved then.',
		[box])
}

/** What the dialog promise and onAnswered gave: `failed` when the dialog threw, `values` undefined
 * when it was dismissed, and the responder onAnswered reported, if any. */
export type DialogAnswer = { failed?: boolean; values?: Record<string, string>; responder?: { userID: string } }
/** What the agent gets. `reopen` is true exactly in cases 1 to 3 of the order rule. */
export type AnswerReading =
	| { outcome: 'approved'; responder: string; reopen: false }
	| { outcome: 'changes'; message: string; reopen: false }
	| { outcome: 'unticked'; message: typeof NOT_APPROVED; reopen: false }
	| { outcome: 'unconfirmed'; message: typeof UNCONFIRMED; reopen: true }
	| { outcome: 'nothing'; reopen: true }

/** Read a kickoff or effect answer in the contract's order rule; the first case that applies decides.
 * The caller still checks that the contract digest is unchanged since the dialog opened. */
export function readAnswer(dialog: ContractDialog, answer: DialogAnswer, ownerID: string): AnswerReading {
	// 1. Dismissed or failed.
	if (answer.failed || !answer.values) return { outcome: 'nothing', reopen: true }
	// 2. No responder reported.
	if (!answer.responder) return { outcome: 'unconfirmed', message: UNCONFIRMED, reopen: true }
	// 3. The responder is not the owner.
	if (!ownerID || answer.responder.userID !== ownerID) return { outcome: 'nothing', reopen: true }
	// 4. Changes holds text: that text is the owner's answer.
	const changes = (answer.values[CHANGES] ?? '').trim()
	if (changes) return { outcome: 'changes', message: changes, reopen: false }
	// 5. A box is unticked. Only 'true' is a tick: a client that cannot show a box returns 'false'.
	const boxes = dialog.fields.filter(f => 'type' in f && f.type === 'checkbox')
	if (boxes.some(f => answer.values![f.name] !== 'true')) return { outcome: 'unticked', message: NOT_APPROVED, reopen: false }
	return { outcome: 'approved', responder: answer.responder.userID, reopen: false }
}
