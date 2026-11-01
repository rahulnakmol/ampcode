import { expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import type { CreateAgentConfig, PluginAPI, PluginAgentModeDefinition } from '@ampcode/plugin'
import register from '../plugins/amp-custom-mode-dials'

test('selected routing keeps Fast variants on the same model, effort and workflow', () => {
	const modes: PluginAgentModeDefinition[] = []
	register({
		createAgent(config: CreateAgentConfig) { return { definition: config } },
		registerAgentMode(mode: PluginAgentModeDefinition) { modes.push(mode) },
	} as unknown as PluginAPI)
	expect(modes.map(m => m.key)).toEqual(['swift', 'weave', 'prime', 'weave-fast', 'prime-fast'])
	const byKey = new Map(modes.map(m => [m.key, m.agent as CreateAgentConfig]))
	for (const [key, model, effort] of [
		['swift', 'anthropic/claude-sonnet-5-5', 'medium'],
		['weave', 'openai/gpt-6.1-sol', 'high'],
		['prime', 'anthropic/claude-fable-5-1', 'medium'],
	]) {
		const base = byKey.get(key)!
		expect(base.model).toBe(model)
		expect(base.reasoningEffort).toBe(effort)
		expect(base.features).toEqual([])
		expect('subagents' in base).toBe(false)
		expect('oracle' in base).toBe(false)
		if (key !== 'swift') {
			const fast = byKey.get(`${key}-fast`)!
			expect(fast).toEqual({
				...base,
				features: ['fast'],
				display: { ...base.display!, label: `${base.display!.label} Fast` },
			})
		}
	}
	const source = readFileSync(new URL('../plugins/amp-custom-mode-dials.ts', import.meta.url), 'utf8')
	const metadata = [...source.matchAll(/^\/\/ @amp-agent-mode (.+)$/gm)].map(m => JSON.parse(m[1]))
	expect(metadata).toEqual(modes.map(m => ({ key: m.key, label: (m.agent as CreateAgentConfig).display!.label })))
})
