// @amp-agent-mode {"key":"archi","label":"Archi","description":"Interviews and guides users through enterprise SaaS architecture. Use for application design and architecture reviews."}
// @amp-agent-mode {"key":"darci","label":"Darci","description":"Interviews and guides users through data, analytics, and evidence-grounded AI architecture. Use for data platform and agentic system design."}
// @amp-agent-mode {"key":"revo","label":"Revo","description":"Investigates code changes for substantiated defects. Use for read-only PR and diff reviews."}
// @amp-agent-mode {"key":"opsci","label":"Opsci","description":"Correlates telemetry and deployed code to investigate failures. Use for guided, read-only incident analysis."}

import { readFileSync } from 'node:fs'
import type { PluginAPI, PluginAgentModel } from '@ampcode/plugin'

export const description =
	'Archi and Darci guide architecture decisions; Revo reviews code; Opsci investigates incidents. Advisory-only modes and consultation tools.'

// Keep model choices separate from role instructions. Verify replacements with
// `amp plugins show-agent-options --json` before changing these pins.
export const profiles = [
	{ key: 'archi', label: 'Archi', model: 'anthropic/claude-fable-5-1', description: 'Interviews and guides users through enterprise SaaS architecture. Use for application design and architecture reviews.' },
	{ key: 'darci', label: 'Darci', model: 'anthropic/claude-fable-5-1', description: 'Interviews and guides users through data, analytics, and evidence-grounded AI architecture. Use for data platform and agentic system design.' },
	{ key: 'revo', label: 'Revo', model: 'openai/gpt-6-astra', description: 'Investigates code changes for substantiated defects. Use for read-only PR and diff reviews.' },
	{ key: 'opsci', label: 'Opsci', model: 'openai/gpt-6-astra', description: 'Correlates telemetry and deployed code to investigate failures. Use for guided, read-only incident analysis.' },
] as const

// No shell, mutation tools, generic Task, thread creation, publishing, or MCP
// wildcards. Skills cannot grant tools omitted from this explicit allowlist.
export const advisoryTools = [
	'Read', 'finder', 'librarian', 'oracle', 'read_thread',
	'web_search', 'read_web_page', 'view_media', 'skill',
]

export default function (amp: PluginAPI) {
	const shared = readFileSync(new URL('./shared.md', import.meta.url), 'utf8')
	for (const profile of profiles) {
		const agent = amp.createAgent({
			name: profile.label,
			model: profile.model as PluginAgentModel,
			reasoningEffort: 'high',
			features: [],
			instructions: shared + '\n\n' + readFileSync(new URL(`./${profile.key}.md`, import.meta.url), 'utf8'),
			tools: [...advisoryTools],
		})
		amp.registerAgentMode({
			key: profile.key,
			label: profile.label,
			description: profile.description,
			agent: agent.definition,
		})
		amp.registerTool({
			name: `consult_${profile.key}`,
			description: `${profile.description} Returns advice, never implementation. Supply the question, repository/file paths, constraints, and relevant evidence. The caller must relay interview questions to the user.`,
			inputSchema: {
				type: 'object',
				properties: { request: { type: 'string', description: 'Self-contained advisory request with scope, context, evidence, and desired outcome.' } },
				required: ['request'],
			},
			async execute(input, ctx) {
				if (typeof input.request !== 'string' || !input.request.trim()) {
					throw new Error('A non-empty advisory request is required.')
				}
				const result = await agent.run(input.request, {
					parentThreadID: ctx.thread.id,
					executor: 'local',
					timeoutMs: 10 * 60 * 1000,
				})
				return result.text
			},
		})
	}
}
