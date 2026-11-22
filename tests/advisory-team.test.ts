import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import type { CreateAgentConfig, PluginAPI, PluginAgentModeDefinition, PluginToolDefinition } from '@ampcode/plugin'
import register from '../plugins/advisory-team/index'

function setup(fail = false) {
	const agents: CreateAgentConfig[] = []
	const modes: PluginAgentModeDefinition[] = []
	const tools: PluginToolDefinition[] = []
	const calls: unknown[] = []
	register({
		createAgent(config: CreateAgentConfig) {
			agents.push(config)
			return {
				definition: config,
				async run(request: string, options: unknown) {
					calls.push({ name: config.name, request, options })
					if (fail) throw new Error('Unavailable model')
					return { text: `${config.name}: advice only` }
				},
			}
		},
		registerAgentMode(mode: PluginAgentModeDefinition) { modes.push(mode) },
		registerTool(tool: PluginToolDefinition) { tools.push(tool) },
	} as unknown as PluginAPI)
	return { agents, modes, tools, calls }
}

const ctx = { thread: { id: 'T-00000000-0000-0000-0000-000000000001' } } as Parameters<PluginToolDefinition['execute']>[1]

describe('advisory team', () => {
	test('registers the three distinct models, prompts, modes and consultation tools', () => {
		const { agents, modes, tools } = setup()
		expect(modes.map(m => [m.key, m.label])).toEqual([
			['archi', 'Archi'], ['darci', 'Darci'], ['opsci', 'Opsci'],
		])
		expect(agents.map(a => a.model)).toEqual([
			'anthropic/claude-fable-5-1', 'anthropic/claude-fable-5-1', 'openai/gpt-6-astra',
		])
		const roleMarkers = ['# Archi', '# Darci', '# Opsci']
		for (const [i, agent] of agents.entries()) {
			expect(agent.instructions).toContain('Never modify source')
			expect(agent.instructions).toContain(roleMarkers[i])
			expect(agent.reasoningEffort).toBe('high')
			expect(agent.features).toEqual([])
			expect(agent.subagents).toBeUndefined()
			expect(agent.oracle).toBeUndefined()
			expect(modes[i].agent).toBe(agent)
		}
		expect(tools.map(t => t.name)).toEqual(['consult_archi', 'consult_darci', 'consult_opsci'])
		const source = readFileSync(new URL('../plugins/advisory-team/index.ts', import.meta.url), 'utf8')
		const directives = [...source.matchAll(/^\/\/ @amp-agent-mode (.+)$/gm)].map(m => JSON.parse(m[1]))
		expect(directives).toEqual(modes.map(({ key, label, description }) => ({ key, label, description })))
		for (const directive of directives) {
			expect(typeof directive.description).toBe('string')
			expect(directive.description.length).toBeGreaterThan(20)
		}
	})

	test('uses an exact direct-tool allowlist without mutation or delegation escape tools', () => {
		for (const agent of setup().agents) {
			expect(agent.tools).toEqual([
				'Read', 'finder', 'librarian', 'oracle', 'read_thread',
				'web_search', 'read_web_page', 'view_media', 'skill',
			])
		}
	})

	test('each consultation preserves the request, parent and executor and returns its own agent response', async () => {
		const { tools, calls } = setup()
		for (const [i, tool] of tools.entries()) {
			const name = ['Archi', 'Darci', 'Opsci'][i]
			const request = `Scope ${i}: inspect /project/service.ts; do not edit.`
			expect(await tool.execute({ request }, ctx)).toBe(`${name}: advice only`)
			expect(calls[i]).toEqual({ name, request, options: {
				parentThreadID: ctx.thread.id, executor: 'local', timeoutMs: 600000,
			} })
		}
	})

	test('invalid input never launches an agent; execution failure is not a clean result', async () => {
		const { tools, calls } = setup(true)
		for (const request of [undefined, '', '  ', 7]) {
			await expect(tools[0].execute({ request }, ctx)).rejects.toThrow('non-empty')
		}
		expect(calls).toEqual([])
		await expect(tools[2].execute({ request: 'Investigate this incident' }, ctx)).rejects.toThrow('Unavailable model')
		expect(calls).toHaveLength(1)
	})
})

const read = (path: string) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8')
const roles = {
	archi: read('plugins/advisory-team/archi.md'),
	darci: read('plugins/advisory-team/darci.md'),
}
const skill = read('skills/architecting/SKILL.md')
const dataAndAi = read('skills/architecting/reference/data-and-ai.md')

describe('Archi and Darci load the architecting skill (W2)', () => {
	test('W2.1 Archi names architecting; Darci names architecting and data-and-ai; both stay advisory', () => {
		expect(roles.archi).toContain('Load the `architecting` skill and follow it')
		expect(roles.darci).toContain('Load the `architecting` skill')
		expect(roles.darci).toContain('`reference/data-and-ai.md`')
		for (const text of Object.values(roles)) {
			expect(text).toMatch(/never write files/i)
		}
	})

	test('W2.2 each role file has at most 20 lines and keeps its role-specific limits', () => {
		for (const text of Object.values(roles)) {
			expect(text.replace(/\n$/, '').split('\n').length).toBeLessThanOrEqual(20)
		}
		expect(roles.darci).toContain('Do not request connection strings in chat')
		expect(roles.darci).toContain('Live connectors are not installed')
		expect(roles.darci).toContain('Do not run migrations, expensive exploratory queries, or extract customer records by default.')
		expect(roles.darci).toContain('Do not launch implementation work.')
		for (const text of Object.values(roles)) expect(text).toContain('Never write files')
		expect(roles.archi).toMatch(/one-shot consultation/i)
		expect(roles.archi).toMatch(/return the interview questions to the caller/i)
		expect(roles.archi).toMatch(/do not invent the user's answers/i)
	})

	test('W2.3 the moved method lines are in the skill, not in the role files', () => {
		expect(skill).toContain('Domain-driven design: ubiquitous language')
		expect(dataAndAi).toContain('Compare SQL Server/PostgreSQL reporting')
		expect(roles.archi).not.toContain('Domain-driven design: ubiquitous language')
		expect(roles.darci).not.toContain('Compare SQL Server/PostgreSQL reporting')
	})

	test('W2.4 the tool allowlist and "Never modify source" are unchanged', () => {
		const shared = read('plugins/advisory-team/shared.md')
		expect(shared).toContain('Never modify source, configuration, databases, infrastructure, or remote state.')
		const { agents } = setup()
		for (const [i, key] of ['archi', 'darci'].entries()) {
			expect(agents[i].instructions).toBe(shared + '\n\n' + roles[key as keyof typeof roles])
			expect(agents[i].tools).toEqual([
				'Read', 'finder', 'librarian', 'oracle', 'read_thread',
				'web_search', 'read_web_page', 'view_media', 'skill',
			])
		}
	})

	test('W2.5 each role file says what to do when the skill cannot be loaded', () => {
		for (const text of Object.values(roles)) {
			expect(text).toContain('If the `architecting` skill cannot be loaded, say so in your answer. Then advise from the advisory contract above.')
		}
	})

	test('W2.6 architecting has a "Without a shell" rule: give the design_check.py command, label it "not run"', () => {
		const match = skill.match(/^#+ Without a shell\n([\s\S]*?)(?=^#+ )/m)
		expect(match).not.toBeNull()
		const section = match![1]
		expect(section).toContain('design_check.py')
		expect(section).toContain('not run')
		expect(section).toMatch(/give the\s+caller the exact command/i)
		expect(section).toMatch(/goldfishing/)
	})
})
