import type { PluginAPI } from '@ampcode/plugin'
import { confirmOptions, designDialog, mergeDialog, refusal } from '../../plugins/mission-control/lib/brief'
import type { Mission } from '../../plugins/mission-control/lib/mission'
import record from '../../plugins/mission-control/fixtures/demo-mission.json'

export const description = 'Preview-only: shows the mission-control design and merge approval dialogs for a synthetic mission. It records nothing and approves nothing.'

// One command, no tools and no events, so it cannot clash with the installed mission-control plugin.
export default function (amp: PluginAPI) {
	amp.registerCommand('preview-approval-dialogs', { title: 'Preview approval dialogs', category: 'Mission control', description: 'Show the design and merge dialogs for a synthetic mission. Nothing is recorded.' }, async ctx => {
		const s = record as unknown as Mission
		for (const [stage, dialog] of [['Design', designDialog(s)], ['Merge', mergeDialog(s)]] as const) {
			const result = await ctx.ui.confirm(confirmOptions({ ...dialog, title: `Preview. ${dialog.title}` }))
			const refused = refusal(result, dialog.risks ?? [])
			await ctx.ui.notify(`${stage} preview: ${refused ?? 'this answer would approve.'} Nothing was recorded.`)
		}
	})
}
