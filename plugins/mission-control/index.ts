import type { PluginAPI, PluginThread, PluginToolContext, PluginUI, QuickAction } from '@ampcode/plugin'
import { execFileSync } from 'node:child_process'
import { appendFileSync, existsSync, readFileSync, realpathSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { digest } from './lib/mission'
import { canonical } from './lib/contracts'
import { GitHub } from './lib/github'
import { effectDialog, kickoffDialog, readAnswer, type AnswerReading, type ContractDialog, type DialogAnswer } from './lib/brief'
import { advance as advanceContract, approvalDigest, blocked, blockers as contractBlockers, createRecord, fingerprint as contractFingerprint, loadContractRecord, RetiredSchema, saveContractRecord, update as updateContract, type ContractRecord, type MilestoneState, type Pending } from './lib/contract'
import { checkpointReport, closeOutReport } from './lib/report'

export const description = 'Coordinates owner-approved software missions, revision-bound evidence and protected dev integration using existing GitHub credentials.'

const CONTRACT_ACTIONS = ['amend', 'replan', 'file', 'delegate', 'item-done', 'candidate', 'review', 'disposition', 'evidence', 'assume', 'stop', 'resume']
const NOTHING = 'No approval was recorded.'
const EFFECT_APPROVED = 'The owner approved this effect once, and it is recorded as performed.'
// The registered command behind the "Open kickoff approval" and "Open effect approval" quick actions.
const REOPEN = 'mission-reopen-approval'
// What the agent gets when a kickoff or effect dialog does not approve (the order rule in brief.ts).
function notApproved(reading: AnswerReading) {
	if (reading.outcome === 'changes') return `Not approved. The owner wrote in Changes:\n${reading.message}`
	if (reading.outcome === 'unticked' || reading.outcome === 'unconfirmed') return reading.message
	return NOTHING
}
const milestoneOf = (s: ContractRecord, milestoneId: unknown): MilestoneState => {
	const m = s.milestones.find(m => m.id === milestoneId)
	if (!m) throw new Error(`Refused (milestoneId): unknown milestone ${milestoneId}`)
	return m
}
function nextAction(s: ContractRecord) {
	const digest = approvalDigest(s.contract)
	if (s.preflight?.digest !== digest) return 'Run mission_preflight on the current contract'
	if (!s.preflight.passed) return 'Fix the failing readiness checks, then run mission_preflight again'
	if (s.approval?.digest !== digest) return 'Open the kickoff approval with mission_approve'
	const m = s.milestones.find(m => m.status !== 'merged')
	if (!m) return 'Every milestone is merged: write the close-out report with mission_report'
	if (m.status === 'merge-pending') return `Reconcile the merge of ${m.id} with mission_reconcile`
	const missing = contractBlockers(s, m.id)
	return missing.length ? `${m.id}: ${missing[0]}` : `Merge ${m.id} with mission_merge`
}
// The status the hooks show: approval, preflight, milestones with their items, open stops, a pending approval, and the next action.
function compactStatus(s: ContractRecord) {
	const digest = approvalDigest(s.contract)
	const defs = [...s.contract.items, ...s.filed]
	const preflight = s.preflight?.digest !== digest ? 'not run on the current contract' : s.preflight.passed ? 'passed' : 'failed'
	const stops = s.stops.filter(x => !x.resolved)
	return [
		`Contract mission ${s.contract.missionId} on ${s.contract.repository}.`,
		`Kickoff: ${s.approval?.digest === digest ? 'approved' : 'not approved'}; preflight: ${preflight}.`,
		...s.milestones.map(m => {
			const items = s.items.filter(i => defs.find(d => d.id === i.id)!.milestone === m.id).map(i => `${i.id} ${i.status}`)
			return `${m.id}: ${m.status}${m.status !== 'merged' && blocked(s, m.id) ? ', blocked by a stop' : ''}; items ${items.join(', ')}.`
		}),
		...(stops.length ? [`Open stops: ${stops.map(x => `${x.id} blocks ${x.blocks.join(', ')}`).join('; ')}.`] : []),
		...(s.pendingApproval ? [`Pending approval: ${s.pendingApproval.kind}.`] : []),
		`Next action: ${nextAction(s)}`,
	].join('\n')
}
// agent.end continues only when kickoff is approved, the mission is not complete, no item is
// delegated, and at least one unmerged milestone is not blocked by a stop.
function workReady(s: ContractRecord) {
	return s.approval?.digest === approvalDigest(s.contract) && !s.items.some(i => i.status === 'delegated')
		&& s.milestones.some(m => m.status !== 'merged' && !blocked(s, m.id))
}
// The compact status: approval, preflight, items, milestones with their fingerprints and blockers, and the next action.
function contractStatus(s: ContractRecord) {
	const digest = approvalDigest(s.contract)
	const milestones = s.milestones.map(m => {
		const fp = m.candidate ? contractFingerprint(s, m.id) : null
		return {
			id: m.id, status: m.status, candidate: m.candidate ?? null, generation: m.generation, fingerprint: fp, failedRounds: m.failed,
			reviews: m.reviews.filter(r => r.fingerprint === fp).map(({ gate, passed, reviewer }) => ({ gate, passed, reviewer })),
			evidence: m.evidence ? { current: m.evidence.fingerprint === fp } : null, mergeCommit: m.mergeCommit ?? null,
			blockers: m.status === 'merged' ? [] : contractBlockers(s, m.id),
		}
	})
	const defs = [...s.contract.items, ...s.filed]
	const next = nextAction(s)
	return JSON.stringify({
		schemaVersion: 3, missionId: s.contract.missionId, repository: s.contract.repository, digest,
		approval: s.approval ? { ...s.approval, current: s.approval.digest === digest } : null,
		preflight: s.preflight ? { current: s.preflight.digest === digest, passed: s.preflight.passed, failed: s.preflight.results.filter(r => !r.passed).map(r => `${r.check}: ${r.detail}`) } : null,
		pendingApproval: s.pendingApproval ?? null,
		items: s.items.map(i => ({ id: i.id, milestone: defs.find(d => d.id === i.id)!.milestone, origin: i.origin, status: i.status, executor: i.executor ?? null })),
		milestones, stops: s.stops.filter(x => !x.resolved), assumptions: s.assumptions.length,
		filed: s.filed.map(i => i.id), followUps: s.followUps.map(f => f.id), performed: s.performed, next,
	}, null, 2)
}
// Recovery reads: an open, unmerged, unqueued PR into dev with full SHAs.
const unqueued = (p: any, repo: string) => p.state === 'open' && p.merged === false && p.auto_merge === null && p.isMergeQueueEnabled === false && p.isInMergeQueue === false && p.mergeQueueEntry === null && p.base?.ref === 'dev' && p.base?.repo?.full_name === repo && /^[a-f0-9]{40}$/.test(p.head?.sha) && /^[a-f0-9]{40}$/.test(p.base?.sha)

export default function (amp: PluginAPI, github = new GitHub()) {
	const inFlight = new Set<string>()
	const root = () => {
		if (!amp.system.workspaceRoot) throw new Error('A local Git workspace is required')
		const path = amp.helpers.filePathFromURI(amp.system.workspaceRoot)
		if (!path) throw new Error('A local Git workspace is required')
		return path
	}
	const pathFor = (thread: string) => join(root(), '.amp/in/missions', digest(thread), 'state.json')
	// A v1 or v2 record throws RetiredSchema here, so every tool reports it and none writes it.
	const read = (thread: string): ContractRecord | undefined => amp.system.workspaceRoot ? loadContractRecord(pathFor(thread), thread) : undefined
	const contract = (thread: string) => {
		const s = read(thread)
		if (!s) throw new Error('Start a contract mission with mission_start { contract }')
		return s
	}
	// The hooks report a retired record instead of failing the turn.
	const current = (thread: string): ContractRecord | RetiredSchema | undefined => {
		try { return read(thread) } catch (error) { if (error instanceof RetiredSchema) return error; throw error }
	}
	const saveContract = (s: ContractRecord) => { saveContractRecord(pathFor(s.thread), s); return s }
	// A kickoff or effect dialog. Who answered comes from onAnswered and is compared with the signed-in user.
	const ask = async (ui: PluginUI, dialog: ContractDialog) => {
		const answer: DialogAnswer = {}
		try {
			answer.values = await ui.confirm({ ...dialog, onAnswered: ({ responder }) => { if (responder) answer.responder = { userID: responder.userID } } } as any)
		} catch { answer.failed = true }
		return readAnswer(dialog, answer, amp.system.user?.id ?? '')
	}
	// Reopen: after cases 1 to 3 of the order rule, the thread shows a quick action that runs
	// REOPEN for the pending entry. It lives in this plugin process, as quick actions do.
	const reopens = new Map<string, { pending: Pending; action?: QuickAction }>()
	const dropReopen = (thread: string) => { reopens.get(thread)?.action?.unsubscribe(); reopens.delete(thread) }
	const offerReopen = (thread: PluginThread, pending: Pending) => {
		dropReopen(thread.id)
		const action = thread.createQuickAction?.({ text: `Open ${pending.kind} approval`, icon: 'check', action: 'run-command', args: { command: REOPEN } })
		reopens.set(thread.id, { pending, action })
	}
	// The reopen entry while the record still holds its pending approval on the current contract.
	const reopenFor = (s: ContractRecord) => {
		const r = reopens.get(s.thread), p = s.pendingApproval
		if (r && p && p.digest === approvalDigest(s.contract) && canonical(p) === canonical(r.pending)) return r
		if (r) dropReopen(s.thread)
		return undefined
	}
	// What the agent learns on its next turn about an approval given through REOPEN.
	const reopened = new Map<string, string>()
	// Records the pending entry, opens the kickoff or effect dialog, and records an approval.
	// The quick action is offered exactly when the answer reads as case 1, 2 or 3.
	const approval = async (thread: PluginThread, ui: PluginUI, s: ContractRecord, target: Omit<Pending, 'digest'>, signal?: AbortSignal) => {
		const digest = approvalDigest(s.contract)
		dropReopen(s.thread)
		const opened = saveContract(advanceContract(s, { type: 'approval-pending', digest, ...target }))
		const reading = await ask(ui, target.kind === 'kickoff' ? kickoffDialog(opened) : effectDialog(opened, opened.pendingApproval!))
		// An amend while the dialog was open voids its pending entry: no quick action and no posted answer for it.
		const latest = read(s.thread)
		const stale = !latest || !latest.pendingApproval || canonical(latest.pendingApproval) !== canonical(opened.pendingApproval)
		if (reading.reopen && !stale) offerReopen(thread, opened.pendingApproval!)
		// A stopped turn still leaves the quick action; a command has no abort signal.
		signal?.throwIfAborted()
		if (reading.outcome !== 'approved') return { reading, stale }
		const now = unchanged(s.thread, digest, target.kind, opened.events.length)
		const { kind: _kind, ...effect } = target
		return { reading, record: saveContract(advanceContract(now, target.kind === 'kickoff' ? { type: 'approve', digest, responder: reading.responder } : { type: 'effect', ...effect, responder: reading.responder })) }
	}
	// After an approving answer: the record is read again. The contract must be the one the dialog showed,
	// and no amend since this dialog opened (event `from` on) changed it, even one that was changed back.
	const unchanged = (thread: string, digest: string, what: string, from: number) => {
		const now = contract(thread)
		const amended = now.events.slice(from).some(e => e.action.type === 'amend' && approvalDigest(e.action.contract) !== digest)
		if (approvalDigest(now.contract) !== digest || amended) throw new Error(`Stale: the contract changed while the ${what} dialog was open; nothing was recorded. Open it again.`)
		return now
	}
	function tool(name: string, description: string, properties: Record<string, any>, execute: (input: any, ctx: PluginToolContext) => Promise<string>, required = Object.keys(properties)) {
		amp.registerTool({ name, description, inputSchema: { type: 'object', properties, required, additionalProperties: false }, execute })
	}
	tool('mission_start', 'Start a contract mission with { contract }: the schema 3 contract (16 fields; see the delivering skill) that gets one kickoff approval, then merges milestone by milestone. Uses native Amp specialists, not a separate runtime.', { contract: { type: 'object', additionalProperties: true } }, async (input, ctx) => {
		ctx.signal.throwIfAborted()
		if (read(ctx.thread.id)) throw new Error('Mission already exists; use mission_status')
		if (input?.contract === undefined || Object.keys(input).some(k => k !== 'contract')) throw new Error('Refused (contract): mission_start takes only { contract }, a schema 3 contract; the v1 and v2 mission schemas are retired')
		const s = createRecord(ctx.thread.id, input.contract)
		const cwd = root()
		const gitRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd, encoding: 'utf8' }).trim()
		if (realpathSync(cwd) !== realpathSync(gitRoot)) throw new Error('Open the dedicated worktree root before starting a mission')
		const exclude = resolve(cwd, execFileSync('git', ['rev-parse', '--git-path', 'info/exclude'], { cwd, encoding: 'utf8' }).trim())
		const rules = existsSync(exclude) ? readFileSync(exclude, 'utf8') : ''
		if (!rules.split('\n').includes('/.amp/in/')) appendFileSync(exclude, '\n/.amp/in/\n')
		return contractStatus(saveContract(s))
	})
	tool('mission_status', 'Reload mission checkpoints and blockers. A merge request is not a completed mission.', {}, async (_input, ctx) => contractStatus(contract(ctx.thread.id)))
	tool('mission_update', 'Contract missions (schema 3): amend {contract,reason}; replan {itemId,into[]}; file {item} or {followUp:{id,text}}; delegate {itemId,executor:{kind:thread|subagent,id}}; item-done {itemId,evidence[{criterion,result}],review:{reviewer,record}}; candidate {milestoneId,pr,head,base}; review {milestoneId,gate:1|2,fingerprint,passed,reviewer,record}; disposition {milestoneId,gate,outcome:fixed|replanned|filed,record,itemIds?}; evidence {milestoneId,fingerprint,results[{criterion,result}],humanTest}; assume {question,assumption,why}; stop {reason:1-5,question,options[],recommendation,blocks[]}; resume {stopId,answer,source}. Read fingerprints from mission_status. The internal approval, preflight, effect and merge actions cannot be supplied.', { action: { type: 'object', properties: { type: { type: 'string', enum: CONTRACT_ACTIONS } }, required: ['type'], additionalProperties: true } }, async (input, ctx) => {
		ctx.signal.throwIfAborted()
		const s = contract(ctx.thread.id)
		// The public dispatch refuses the internal actions (P1).
		return contractStatus(saveContract(updateContract(s, input.action)))
	})
	tool('mission_approve', 'Contract missions: open the kickoff dialog, the one owner approval, after a passing mission_preflight on the current contract. Milestones merge without an owner dialog. Never accepts an agent-supplied approval.', {}, async (_input, ctx) => {
		const s = contract(ctx.thread.id)
		// The pending entry is recorded first, so a dismissed dialog can be reopened; refused before a passing preflight (P15).
		const { reading, record } = await approval(ctx.thread, ctx.ui, s, { kind: 'kickoff' }, ctx.signal)
		if (!record) return notApproved(reading)
		return `Kickoff approved by the owner.\n\n${contractStatus(record)}`
	})
	tool('mission_merge', 'Request an immediate exact-head squash merge of the milestone (milestoneId) into dev with existing GitHub credentials only after its merge blockers, required pinned CI and branch protection pass. Opens no dialog. Never queues authorization for a future head or authorizes release/deployment.', { milestoneId: { type: 'string' } }, async (input, ctx) => {
		const s = contract(ctx.thread.id)
		const missing = contractBlockers(s, input.milestoneId)
		if (missing.length) throw new Error(`Refused: ${missing.join('; ')}`)
		const m = milestoneOf(s, input.milestoneId)
		await github.preflight(m.candidate!)
		ctx.signal.throwIfAborted()
		// Saved before the request: an unknown outcome is reconciled, never repeated.
		const pending = saveContract(advanceContract(s, { type: 'merge-requested', milestoneId: m.id, fingerprint: contractFingerprint(s, m.id) }))
		const key = `${s.thread} ${m.id}`
		inFlight.add(key)
		try { await github.request(m.candidate!) } finally { inFlight.delete(key) }
		return contractStatus(pending) + `\nRequest issued for ${m.id}, not confirmed merged. Use mission_reconcile.`
	})
	tool('mission_reconcile', "Read GitHub after restart or an uncertain merge outcome of the milestone (milestoneId). Never repeats a merge.", { milestoneId: { type: 'string' } }, async (input, ctx) => {
		const s = contract(ctx.thread.id)
		const m = milestoneOf(s, input.milestoneId)
		if (m.status !== 'merge-pending') return contractStatus(s)
		const c = m.candidate!
		const pr = await github.pull(c)
		ctx.signal.throwIfAborted()
		if (pr.merged === true && pr.head?.sha === c.head && pr.base?.ref === 'dev' && pr.base?.repo?.full_name === c.repo) {
			return contractStatus(saveContract(advanceContract(s, { type: 'merged', milestoneId: m.id, fingerprint: contractFingerprint(s, m.id), commit: pr.merge_commit_sha })))
		}
		return contractStatus(s) + `\n${m.id} is not confirmed merged. Inspect the PR, CI and any uncertain request; do not repeat the merge.`
	})
	tool('mission_recover', "Recovery after investigating a settled, unqueued merge attempt of the milestone (milestoneId). Reads GitHub twice, advances the recovery generation, invalidates the milestone's reviews and evidence, and returns to review without issuing another merge. Opens no dialog. Never use while a request may still be in flight.", { milestoneId: { type: 'string' } }, async (input, ctx) => {
		const s = contract(ctx.thread.id)
		const m = milestoneOf(s, input.milestoneId)
		const key = `${s.thread} ${m.id}`
		if (m.status !== 'merge-pending' || inFlight.has(key)) throw new Error('Recovery requires a settled pending request')
		const c = m.candidate!
		const pr = await github.pull(c)
		if (!unqueued(pr, c.repo)) throw new Error('Recovery requires an open, unmerged, unqueued dev PR; investigate remote state first')
		const live = await github.pull(c)
		ctx.signal.throwIfAborted()
		if (!unqueued(live, c.repo) || live.head.sha !== pr.head.sha || live.base.sha !== pr.base.sha || inFlight.has(key)) throw new Error('Remote changed during recovery; reconcile again')
		return contractStatus(saveContract(advanceContract(s, { type: 'recover', milestoneId: m.id, fingerprint: contractFingerprint(s, m.id) }))) + `\nRecovered ${m.id}: its reviews and evidence are void, and the merge was not retried.`
	})
	tool('mission_preflight', "Contract missions: run the GitHub readiness checks (repository and push permission, dev, readable and enforced protection, required checks pinned to apps, green CI on dev) and bind the result to the current contract digest. Kickoff needs a passing preflight on the current contract. Also lists the contract's agent-reported readiness entries.", {}, async (_input, ctx) => {
		const s = contract(ctx.thread.id)
		const checks = await github.readiness(s.contract.repository)
		ctx.signal.throwIfAborted()
		const next = saveContract(advanceContract(s, { type: 'preflight', digest: approvalDigest(s.contract), results: checks.map(r => ({ check: r.name, passed: r.pass, detail: r.reason })) }))
		return [
			`Readiness preflight ${next.preflight!.passed ? 'passed' : 'failed'} on the current contract:`,
			...checks.map(r => `${r.pass ? 'PASS' : 'FAIL'} ${r.id}. ${r.name}: ${r.reason}`),
			'Agent-reported readiness (from the contract, not checked by the plugin):',
			...(s.contract.readiness.length ? s.contract.readiness.map(r => `- ${r.id}. ${r.check}: ${r.evidence}`) : ['- None.']),
			'', contractStatus(next),
		].join('\n')
	})
	tool('mission_effect', 'Contract missions: call right before an outside effect. Name a contract effect {effectId}, or describe one that is not in the contract {effect, why}. A pre-authorized effect is recorded with no dialog. Any other effect opens the owner effect dialog and is recorded only when the owner approves it once. Records the performed effect; never changes the contract.', { effectId: { type: 'string' }, effect: { type: 'string' }, why: { type: 'string' } }, async (input, ctx) => {
		const s = contract(ctx.thread.id)
		const target = Object.fromEntries(['effectId', 'effect', 'why'].filter(k => Object.hasOwn(input, k)).map(k => [k, input[k]]))
		const listed = s.contract.effects.find(e => e.id === target.effectId)
		if (listed?.preAuthorized) return `Recorded ${listed.id} as performed. It is pre-authorized, so no dialog opened.\n\n${contractStatus(saveContract(advanceContract(s, { type: 'effect', ...target })))}`
		const { reading, record } = await approval(ctx.thread, ctx.ui, s, { kind: 'effect', ...target }, ctx.signal)
		if (!record) return notApproved(reading)
		return `${EFFECT_APPROVED} Perform it now, exactly as described.\n\n${contractStatus(record)}`
	}, [])
	tool('mission_report', 'Contract missions: write the checkpoint report for a merged milestone (kind checkpoint; milestoneId defaults to the latest merged) or the close-out report once every milestone is merged (kind close-out). Reports ask nothing; post them where the contract says.', { kind: { type: 'string', enum: ['checkpoint', 'close-out'] }, milestoneId: { type: 'string' } }, async (input, ctx) => {
		const s = contract(ctx.thread.id)
		if (input.kind === 'checkpoint') return checkpointReport(s, input.milestoneId)
		if (input.kind !== 'close-out') throw new Error('Refused (kind): checkpoint or close-out is required')
		if (input.milestoneId !== undefined) throw new Error('Refused (milestoneId): the close-out covers every milestone')
		return closeOutReport(s)
	}, ['kind'])
	// Reopens the dialog for the pending entry and records the answer. The owner's Changes text is
	// posted to the thread as their dialog answer; cases 1 to 3 keep the quick action.
	amp.registerCommand(REOPEN, { title: 'Reopen mission approval', category: 'Mission control', description: "Reopen the mission's pending kickoff or effect approval dialog and record the owner's answer." }, async ctx => {
		const thread = ctx.thread
		try {
			const s = thread && read(thread.id)
			const p = s ? s.pendingApproval : undefined
			if (!thread || !s || !p || p.digest !== approvalDigest(s.contract)) {
				if (thread) dropReopen(thread.id)
				return await ctx.ui.notify('No mission approval is pending in this thread.')
			}
			const { digest: _digest, ...target } = p
			const { reading, record, stale } = await approval(thread, ctx.ui, s, target)
			if (record) {
				const effect = p.effectId ?? p.effect
				reopened.set(thread.id, p.kind === 'kickoff' ? 'The owner approved the kickoff in the reopened approval dialog.' : `${EFFECT_APPROVED} It was approved in the reopened approval dialog: ${effect}. Perform it now, exactly as described.`)
				return await ctx.ui.notify(p.kind === 'kickoff' ? 'Kickoff approved by the owner and recorded. Send a message to continue the mission.' : `${EFFECT_APPROVED} Send a message so the agent performs it.`)
			}
			if (stale) return await ctx.ui.notify('Stale: the contract changed while the approval dialog was open; nothing was recorded or posted.')
			if (reading.outcome === 'changes') return await thread.appendUserMessage({ type: 'user-message', content: `The mission owner answered the ${p.kind} approval dialog: not approved. The owner wrote in Changes:\n${reading.message}` })
			await ctx.ui.notify(notApproved(reading))
		} catch (error) { await ctx.ui.notify((error as Error).message) }
	})
	amp.on('session.start', async (event, ctx) => {
		const s = current(event.thread.id)
		if (s) await ctx.ui.notify(s instanceof RetiredSchema ? s.message : compactStatus(s))
	})
	amp.on('agent.start', async event => {
		const s = current(event.thread.id)
		if (s instanceof RetiredSchema) return { message: { content: s.message } }
		if (!s) return
		const r = reopenFor(s), note = reopened.get(s.thread)
		reopened.delete(s.thread)
		const tool = r?.pending.kind === 'kickoff' ? 'mission_approve' : 'mission_effect'
		return { message: { content: [
			'Active contract mission. Follow delivering; mission_status has the fingerprints and details. Local records do not override required CI or branch protection.',
			compactStatus(s),
			...(r ? [`An owner approval is pending: the ${r.pending.kind} approval dialog ended without the owner's answer. The owner reopens it with the quick action "Open ${r.pending.kind} approval" above the composer in the Amp web app. Tell the owner it is waiting; open it again with ${tool} only when the owner asks.`] : []),
			...(note ? [note] : []),
		].join('\n') } }
	})
	amp.on('agent.end', async event => {
		if (event.status !== 'done') return
		const s = current(event.thread.id)
		if (!s || s instanceof RetiredSchema || !workReady(s)) return
		return { action: 'continue', maxContinuations: 3, userMessage: `The contract mission has work ready. Next action: ${nextAction(s)}\nContinue the contract loop in delivering. Record a stop with mission_update only for one of the five stop reasons. Do not bypass a merge blocker, required CI or branch protection.` }
	})
}
