import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { BANNED, banned, validateBrief } from '../plugins/mission-control/lib/brief'

// The decision-brief rules the contract's kickoff brief is checked with (validateBrief).
const brief = { markdown: readFileSync(join(import.meta.dir, '../evals/briefing-decisions/brief.md'), 'utf8') }

describe('decision briefs', () => {
	const read = (path: string) => readFileSync(join(import.meta.dir, '..', path), 'utf8')
	test('the plugin and brief_check.py share one banned list and agree on the shared lines', () => {
		expect(BANNED).toEqual(JSON.parse(read('skills/briefing-decisions/scripts/banned.json')).patterns)
		const lines = JSON.parse(read('tests/fixtures/brief-patterns.json'))
		for (const line of lines.pass) expect([line, banned(line)]).toEqual([line, []])
		for (const [line, rule] of lines.fail) expect(banned(line)).toContain(rule)
	})
	test('the plugin and brief_check.py reach the same verdict on every shared case', () => {
		const { cases } = JSON.parse(read('tests/fixtures/brief-cases.json'))
		const apply = (c: any) => {
			let text = brief.markdown
			for (const [old, next] of c.edits ?? []) {
				expect(text).toContain(old)
				text = text.replace(old, () => next)
			}
			if (c.cut) text = text.slice(0, text.indexOf(c.cut))
			if (c.pad) { const i = text.lastIndexOf('</details>'); text = text.slice(0, i) + 'x'.repeat(c.pad) + '\n\n' + text.slice(i) }
			return text + (c.append ?? '')
		}
		for (const c of cases) {
			const run = () => validateBrief(apply(c))
			if (c.rule === null || c.python_only) expect([c.why, run().decision.length > 0]).toEqual([c.why, true])
			else expect([c.why, (() => { try { run(); return 'accepted' } catch (e: any) { return e.message } })()]).toEqual([c.why, expect.stringContaining(`(${c.rule})`)])
		}
	})
	test('the synthetic briefs pass', () => {
		expect(validateBrief(brief.markdown).risks).toHaveLength(3)
		const example = /## Filled example[\s\S]*?````markdown\n([\s\S]*?)````/.exec(read('skills/briefing-decisions/reference/template.md'))![1]
		expect(validateBrief(example).decision).toContain('shared calendar')
	})
})
