import type { PluginAPI } from '@ampcode/plugin'
import { effectDialog, kickoffDialog, NOT_APPROVED, readAnswer, UNCONFIRMED, type AnswerReading, type DialogAnswer } from '../../plugins/mission-control/lib/brief'
import { approvalDigest, createRecord } from '../../plugins/mission-control/lib/contract'
import contract from '../../plugins/mission-control/fixtures/contract-mission.json'

export const description = 'Preview-only: shows the mission-control kickoff and effect approval dialogs for the contract fixture. It records nothing and approves nothing.'

const PREVIEW = 'Preview only: nothing is recorded or approved.'
// What the real tool would do with the answer. The preview never records it.
function outcome(reading: AnswerReading, kind: string) {
	if (reading.outcome === 'approved') return 'this answer would approve.'
	if (reading.outcome === 'changes') return "not approved; the owner's Changes text would go to the agent."
	if (reading.outcome === 'unticked') return NOT_APPROVED
	if (reading.outcome === 'unconfirmed') return `${UNCONFIRMED}.`
	return `no answer from the owner, so the quick action "Open ${kind} approval" would appear.`
}

// One command, no tools and no events, so it cannot clash with the installed mission-control plugin.
export default function (amp: PluginAPI) {
	amp.registerCommand('preview-approval-dialogs', { title: 'Preview approval dialogs', category: 'Mission control', description: 'Show the kickoff and effect dialogs for the contract fixture. Nothing is recorded.' }, async ctx => {
		// An in-memory record for the fixture; nothing is saved.
		const record = createRecord('T-00000000-0000-0000-0000-000000000000', contract)
		const effect = { kind: 'effect' as const, digest: approvalDigest(record.contract), effect: 'Promote dev to rolling', why: 'Shown by the preview; nothing is promoted' }
		for (const [stage, kind, dialog] of [['Kickoff', 'kickoff', kickoffDialog(record)], ['Effect', 'effect', effectDialog(record, effect)]] as const) {
			const answer: DialogAnswer = {}
			try {
				// Real titles and fields; the fixed preview note leads the message, so the dialog cannot be mistaken for a real approval.
				answer.values = await ctx.ui.confirm({ ...dialog, message: `${PREVIEW}\n\n${dialog.message}`, onAnswered: ({ responder }) => { if (responder) answer.responder = { userID: responder.userID } } } as any)
			} catch { answer.failed = true }
			await ctx.ui.notify(`${stage} preview: ${outcome(readAnswer(dialog, answer, amp.system?.user?.id ?? ''), kind)} Nothing was recorded.`)
		}
	})
}
