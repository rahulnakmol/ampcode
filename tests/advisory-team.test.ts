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
	test('registers the four distinct models, prompts, modes and consultation tools', () => {
		const { agents, modes, tools } = setup()
		expect(modes.map(m => [m.key, m.label])).toEqual([
			['archi', 'Archi'], ['darci', 'Darci'], ['revo', 'Revo'], ['opsci', 'Opsci'],
		])
		expect(agents.map(a => a.model)).toEqual([
			'anthropic/claude-fable-5-1', 'anthropic/claude-fable-5-1', 'openai/gpt-6-astra', 'openai/gpt-6-astra',
		])
		const roleMarkers = ['# Archi', '# Darci', '# Revo', '# Opsci']
		for (const [i, agent] of agents.entries()) {
			expect(agent.instructions).toContain('Never modify source')
			expect(agent.instructions).toContain(roleMarkers[i])
			expect(agent.reasoningEffort).toBe('high')
			expect(agent.features).toEqual([])
			expect(agent.subagents).toBeUndefined()
			expect(agent.oracle).toBeUndefined()
			expect(modes[i].agent).toBe(agent)
		}
		expect(tools.map(t => t.name)).toEqual(['consult_archi', 'consult_darci', 'consult_revo', 'consult_opsci'])
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
			const name = ['Archi', 'Darci', 'Revo', 'Opsci'][i]
			const request = `Scope ${i}: inspect /project/service.ts; do not edit.`
			expect(await tool.execute({ request }, ctx)).toBe(`${name}: advice only`)
			expect(calls[i]).toEqual({ name, request, options: {
				parentThreadID: ctx.thread.id, executor: 'local', timeoutMs: 600000,
			} })
		}
	})

	test('invalid input never launches an agent; execution failure is not a clean review', async () => {
		const { tools, calls } = setup(true)
		for (const request of [undefined, '', '  ', 7]) {
			await expect(tools[0].execute({ request }, ctx)).rejects.toThrow('non-empty')
		}
		expect(calls).toEqual([])
		await expect(tools[2].execute({ request: 'Review this diff' }, ctx)).rejects.toThrow('Unavailable model')
		expect(calls).toHaveLength(1)
	})
})
