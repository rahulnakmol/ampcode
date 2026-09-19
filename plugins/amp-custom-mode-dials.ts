// @amp-agent-mode {"key":"swift","label":"Swift","features":["fast"]}
// @amp-agent-mode {"key":"weave","label":"Weave"}
// @amp-agent-mode {"key":"prime","label":"Prime"}

import type { PluginAPI } from '@ampcode/plugin'

export const description =
	'Adds the Amp Custom Mode Dials: Swift, Weave, and Prime, with Claude Fable 5.1 as Oracle.'

export default function (amp: PluginAPI) {
	const swift = amp.createAgent({
		extends: 'medium',
		model: 'xai/grok-4.6',
		reasoningEffort: 'medium',
		features: ['fast'],
		instructions:
			'Prefer direct execution. Delegate only independent work, and consult Oracle only when uncertainty materially risks correctness.',
		oracle: {
			model: 'anthropic/claude-fable-5-1',
			effort: 'medium',
		},
		display: {
			label: 'Swift',
			color: '#0ea5e9',
		},
	})

	const weave = amp.createAgent({
		extends: 'medium',
		model: 'anthropic/claude-opus-5',
		reasoningEffort: 'medium',
		instructions:
			'Keep implementation focused and evidence-driven. Consult Oracle only for unresolved, high-impact decisions.',
		oracle: {
			model: 'anthropic/claude-fable-5-1',
			effort: 'xhigh',
		},
		subagents: {
			model: 'anthropic/claude-sonnet-5',
			effort: 'medium',
		},
		display: {
			label: 'Weave',
			color: '#d97757',
		},
	})

	const deep = amp.createAgent({
		extends: 'high',
		model: 'anthropic/claude-opus-5',
		reasoningEffort: 'high',
		instructions:
			'Scale investigation to the risk. Stay below Ultra-style exhaustive exploration, delegate bounded research, and reserve Oracle for unresolved decisions where a miss would be expensive.',
		oracle: {
			model: 'anthropic/claude-fable-5-1',
			effort: 'max',
		},
		display: {
			label: 'Prime',
			color: '#b45309',
		},
	})

	amp.registerAgentMode({
		key: 'swift',
		description:
			'Runs medium-style work quickly on Grok 4.6 with Fast, specialist subagent routing, and a Fable 5.1 Oracle. Use between Low and Medium.',
		agent: swift.definition,
	})

	amp.registerAgentMode({
		key: 'weave',
		description:
			'Runs medium-style work on Claude Opus 5 with efficient Sonnet 5 subagents and a Fable 5.1 Oracle. Use between Medium and High.',
		agent: weave.definition,
	})

	amp.registerAgentMode({
		key: 'prime',
		description:
			'Runs risk-scaled high-style work on Claude Opus 5 with specialist subagent routing and a max-effort Fable 5.1 Oracle. Use between High and Ultra.',
		agent: deep.definition,
	})
}
