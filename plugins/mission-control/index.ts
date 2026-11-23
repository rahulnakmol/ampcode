import type { PluginAPI, PluginThread, PluginToolContext, PluginUI, QuickAction } from '@ampcode/plugin'
import { execFileSync } from 'node:child_process'
import { appendFileSync, existsSync, readFileSync, realpathSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { advance, blockers, createMission, digest, fingerprint, loadRecord, saveRecord, readRecordBytes, parseMission, type Action, type Mission } from './lib/mission'
import { advanceV2, blockersV2, createMissionV2, fingerprintV2, evidenceDigestV2, type ActionV2, type MissionV2 } from './lib/mission-v2'
import { canonical, intentDigest } from './lib/contracts'
import { migrateMission, previewMigration, sourceDigest } from './lib/migration'
import { GitHub } from './lib/github'
import { confirmOptions, designDialog, effectDialog, kickoffDialog, mergeDialog, rawDetails, readAnswer, refusal, type AnswerReading, type ContractDialog, type Dialog, type DialogAnswer } from './lib/brief'
import { advance as advanceContract, approvalDigest, blocked, blockers as contractBlockers, createRecord, fingerprint as contractFingerprint, loadContractRecord, saveContractRecord, update as updateContract, type ContractRecord, type MilestoneState, type Pending } from './lib/contract'
import { checkpointReport, closeOutReport } from './lib/report'
import { createHash } from 'node:crypto'

export const description = 'Coordinates owner-approved software missions, revision-bound evidence and protected dev integration using existing GitHub credentials.'

// Until W6 retires v1 and v2, the record's schema picks the handlers: schema 3 records and
// mission_start { contract } use the contract handlers, v1 and v2 keep theirs.
type RecordState = Mission | MissionV2 | ContractRecord
function isV2(s: RecordState): s is MissionV2 { return (s as any).schemaVersion === 2 }
function isContract(s: RecordState): s is ContractRecord { return (s as any).schemaVersion === 3 }
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
function packet(s: RecordState) {
	if (isV2(s)) return [
		'V2 shadow mission. Intent authority: local-reported. Remote verification is unqualified; merges are disabled.',
		`Current intent digest: ${intentDigest(s.manifest)}`, JSON.stringify(s.manifest, null, 2),
		'Previous intent (review amendments and dispositions):', JSON.stringify(s.snapshots.at(-2)?.manifest ?? null, null, 2),
		`Affected units: ${s.units.map(u => u.id + ': ' + u.status).join(', ')}`,
		'All submitted review/results remain reported, not authenticated execution. A design acknowledgment approves this exact local manifest, not remote authority or release.',
	].join('\n\n')
	return rawDetails(s)
}
// The full brief is in the record; status (sent on every agent turn) carries only its link, size and hash.
function compact(s: Mission) {
	const brief = s.design?.bundle.brief
	if (!brief) return s
	return { ...s, design: { ...s.design!, bundle: { ...s.design!.bundle, brief: { url: brief.url, characters: [...brief.markdown].length, sha256: createHash('sha256').update(brief.markdown).digest('hex') } } } }
}

export default function (amp: PluginAPI, github = new GitHub()) {
	const inFlight = new Set<string>()
	const root = () => {
		if (!amp.system.workspaceRoot) throw new Error('A local Git workspace is required')
		const path = amp.helpers.filePathFromURI(amp.system.workspaceRoot)
		if (!path) throw new Error('A local Git workspace is required')
		return path
	}
	const pathFor = (thread: string) => join(root(), '.amp/in/missions', digest(thread), 'state.json')
	const read = (thread: string): RecordState | undefined => {
		if (!amp.system.workspaceRoot) return undefined
		const path = pathFor(thread), raw = readRecordBytes(path)
		if (raw === undefined) return undefined
		return JSON.parse(raw)?.schemaVersion === 3 ? loadContractRecord(path, thread) : loadRecord(path, thread)
	}
	const required = (thread: string) => {
		const s = read(thread)
		if (!s) throw new Error('Start a mission explicitly with mission_start')
		return s
	}
	const legacy = (thread: string) => {
		const s = required(thread)
		if (isContract(s)) throw new Error('This tool is not part of contract missions; mission_status shows the next action')
		return s
	}
	const contract = (thread: string) => {
		const s = required(thread)
		if (!isContract(s)) throw new Error('This tool needs a contract mission, started with mission_start { contract }')
		return s
	}
	const saveContract = (s: ContractRecord) => { saveContractRecord(pathFor(s.thread), s); return s }
	// A kickoff or effect dialog. Who answered comes from onAnswered and is compared with the signed-in user.
	// A command has no abort signal.
	const ask = async (ui: PluginUI, dialog: ContractDialog, signal?: AbortSignal) => {
		const answer: DialogAnswer = {}
		try {
			answer.values = await ui.confirm({ ...dialog, onAnswered: ({ responder }) => { if (responder) answer.responder = { userID: responder.userID } } } as any)
		} catch { answer.failed = true }
		signal?.throwIfAborted()
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
		const reading = await ask(ui, target.kind === 'kickoff' ? kickoffDialog(opened) : effectDialog(opened, opened.pendingApproval!), signal)
		if (reading.reopen) offerReopen(thread, opened.pendingApproval!)
		if (reading.outcome !== 'approved') return { reading }
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
	function write(s: Mission, action: Action): Mission
	function write(s: MissionV2, action: ActionV2): MissionV2
	function write(s: RecordState, action: Action | ActionV2): RecordState
	function write(s: RecordState, action: Action | ActionV2): RecordState {
		const next = isV2(s) ? advanceV2(s, action as ActionV2) : advance(s, action as Action)
		saveRecord(pathFor(s.thread), next)
		return next
	}
	const status = (s: RecordState) => isContract(s) ? contractStatus(s) : JSON.stringify(isV2(s) ? {
		...s, ...(s.legacy ? { legacy: compact(s.legacy) } : {}),
		events: s.events.map(e => e.action.type === 'import-v1' ? { ...e, action: { ...e.action, record: compact(e.action.record) } } : e),
		designDigest: intentDigest(s.manifest), evidenceClass: 'reported', blockers: blockersV2(s),
		current: s.units.map(u => {
			const a = u.attempts.at(-1)
			return { unitId: u.id, attemptId: a?.id, fingerprint: a && !a.stale ? fingerprintV2(s, u.id, a.id) : null, evidenceDigest: a && !a.stale ? evidenceDigestV2(s, u.id, a.id) : null }
		}),
	} : { ...compact(s), fingerprint: fingerprint(s), blockers: blockers(s) }, null, 2)
	const acknowledge = async (ctx: PluginToolContext, dialog: Dialog | string) => {
		const d = typeof dialog === 'string' ? { title: 'Mission owner acknowledgment', message: dialog } : dialog
		const result = await ctx.ui.confirm(confirmOptions(d))
		ctx.signal.throwIfAborted()
		const refused = refusal(result)
		if (refused) throw new Error(refused)
	}
	function tool(name: string, description: string, properties: Record<string, any>, execute: (input: any, ctx: PluginToolContext) => Promise<string>, required = Object.keys(properties)) {
		amp.registerTool({ name, description, inputSchema: { type: 'object', properties, required, additionalProperties: false }, execute })
	}
	tool('mission_start', 'Start a contract mission with { contract }: the schema 3 contract (16 fields; see the delivering skill) that gets one kickoff approval, then merges milestone by milestone. Until they are retired: v1 from requirements, or v2 shadow traceability with schemaVersion:2 and a complete manifest; v2 never sends merges. Uses native Amp specialists, not a separate runtime.', { contract: { type: 'object', additionalProperties: true }, requirements: { type: 'string' }, schemaVersion: { type: 'integer', enum: [1, 2] }, manifest: { type: 'object', additionalProperties: true } }, async (input, ctx) => {
		ctx.signal.throwIfAborted()
		if (read(ctx.thread.id)) throw new Error('Mission already exists; use mission_status')
		if (input.contract !== undefined && ['requirements', 'schemaVersion', 'manifest'].some(k => input[k] !== undefined)) throw new Error('A contract mission takes only { contract }')
		if (input.schemaVersion !== undefined && ![1, 2].includes(input.schemaVersion)) throw new Error('Unsupported mission schema')
		if (input.schemaVersion !== 2 && input.manifest !== undefined) throw new Error('Manifest requires explicit schemaVersion:2')
		if (input.schemaVersion === 2 && input.requirements !== undefined) throw new Error('V2 requirements belong in the manifest')
		const s = input.contract !== undefined ? createRecord(ctx.thread.id, input.contract) : input.schemaVersion === 2 ? createMissionV2(ctx.thread.id, input.manifest) : createMission(ctx.thread.id, input.requirements)
		const cwd = root()
		const gitRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd, encoding: 'utf8' }).trim()
		if (realpathSync(cwd) !== realpathSync(gitRoot)) throw new Error('Open the dedicated worktree root before starting a mission')
		const exclude = resolve(cwd, execFileSync('git', ['rev-parse', '--git-path', 'info/exclude'], { cwd, encoding: 'utf8' }).trim())
		const rules = existsSync(exclude) ? readFileSync(exclude, 'utf8') : ''
		if (!rules.split('\n').includes('/.amp/in/')) appendFileSync(exclude, '\n/.amp/in/\n')
		if (isContract(s)) saveContract(s)
		else saveRecord(pathFor(ctx.thread.id), s)
		return status(s)
	}, [])
	tool('mission_status', 'Reload mission checkpoints and blockers. A merge request is not a completed mission.', {}, async (_input, ctx) => status(required(ctx.thread.id)))
	const publicActions = ['design', 'defense', 'build', 'candidate', 'review', 'evidence', 'report', 'finding', 'post-report', 'disposition', 'post-delivery', 'closure-report', 'pause', 'resume']
	tool('mission_update', 'Contract missions (schema 3): amend {contract,reason}; replan {itemId,into[]}; file {item} or {followUp:{id,text}}; delegate {itemId,executor:{kind:thread|subagent,id}}; item-done {itemId,evidence[{criterion,result}],review:{reviewer,record}}; candidate {milestoneId,pr,head,base}; review {milestoneId,gate:1|2,fingerprint,passed,reviewer,record}; disposition {milestoneId,gate,outcome:fixed|replanned|filed,record,itemIds?}; evidence {milestoneId,fingerprint,results[{criterion,result}],humanTest}; assume {question,assumption,why}; stop {reason:1-5,question,options[],recommendation,blocks[]}; resume {stopId,answer,source}. Read fingerprints from mission_status. V1: design {bundle:{spec,plan,technical,ux,brief:{markdown,url}},criteria}, where markdown is the decision brief written with briefing-decisions and checked by brief_check.py, and url is the https ampcode.com or github.com document where the owner reads it, published from that text; defense {digest,record}; build; candidate {candidate}; review {gate,fingerprint,passed,reviewer,record}; evidence {fingerprint,results,tryIt,value}; pause {reason}; resume. V2: design {manifest}; build {unitId}; candidate {unitId,attemptId,candidate,manifest}; report {unitId,attemptId,fingerprint,evidence:{id,criterionIds,outcome,record}}; review adds unitId,attemptId,evidenceDigest,findingIds. finding {unitId,attemptId,fingerprint,finding:{id,criterionIds,severity,confidence,location,record,owner}}. post-report {evidence:{id,baseline,designDigest,policyDigest,unitIds,results:[{criterionId,outcome,record}],record}}. post-delivery {unitId,package} / closure-report {package}: package replaces post-report id with evidenceIds and findings. disposition {disposition:{findingId,outcome:fixed|rejected|deferred,evidenceIds,owner,reviewer,record,correctiveUnitId?}}. V2 results/dispositions are reported only; references must resolve. No internal approval/import/execution/integration actions.', { action: { type: 'object', properties: { type: { type: 'string', enum: [...new Set([...CONTRACT_ACTIONS, ...publicActions])] } }, required: ['type'], additionalProperties: true } }, async (input, ctx) => {
		ctx.signal.throwIfAborted()
		const s = required(ctx.thread.id)
		// The public dispatch refuses the internal actions (P1).
		if (isContract(s)) return status(saveContract(updateContract(s, input.action)))
		if (!publicActions.includes(input.action?.type)) throw new Error('Internal approval and integration actions cannot be supplied by agents')
		if (!isV2(s) && input.action.type === 'build') {
			await ctx.ui.notify('Build entry: low/medium risk defaults to automatic merge into dev after evidence and all gates. No response is needed. For ask-before-merge, use mission_merge_mode with mode ask; high risk always requires owner acknowledgment.')
			ctx.signal.throwIfAborted()
		}
		return status(write(s, input.action))
	})
	tool('mission_approve', 'Contract missions: open the kickoff dialog, the one owner approval, after a passing mission_preflight on the current contract; no stage. V1 and v2: request an owner-restricted acknowledgment of the exact design bundle or presented merge candidate (stage design or merge). Never accepts an agent-supplied approval.', { stage: { type: 'string', enum: ['design', 'merge'] } }, async (input, ctx) => {
		const s = required(ctx.thread.id)
		if (isContract(s)) {
			if (input.stage !== undefined) throw new Error('A contract mission has one approval, at kickoff, and no stage; milestones merge without an owner dialog')
			// The pending entry is recorded first, so a dismissed dialog can be reopened; refused before a passing preflight (P15).
			const { reading, record } = await approval(ctx.thread, ctx.ui, s, { kind: 'kickoff' }, ctx.signal)
			if (!record) return notApproved(reading)
			return `Kickoff approved by the owner.\n\n${status(record)}`
		}
		if (input.stage !== 'design' && input.stage !== 'merge') throw new Error('Invalid approval stage')
		if (isV2(s)) {
			if (input.stage === 'merge') throw new Error('remote-verification-unqualified: v2 cannot authorize merges')
			if (s.status !== 'framing') throw new Error('Design acknowledgment is not pending')
			await acknowledge(ctx, packet(s))
			if (intentDigest(required(s.thread)) !== intentDigest(s)) throw new Error('Mission changed during dialog; stale acknowledgment')
			return status(write(s, { type: 'approve-design', digest: intentDigest(s.manifest) }))
		}
		if (input.stage === 'design' && !s.design) throw new Error('Design bundle required')
		if (input.stage === 'merge' && s.presented !== fingerprint(s)) throw new Error('Present candidate evidence first')
		await acknowledge(ctx, input.stage === 'design' ? designDialog(s) : mergeDialog(s))
		return status(write(s, input.stage === 'design' ? { type: 'approve-design', digest: s.design!.digest } : { type: 'approve-merge', fingerprint: fingerprint(s) }))
	})
	tool('mission_merge_mode', 'Owner-controlled override of default automatic low/medium integration. Changing mode invalidates presented evidence and merge acknowledgment, not code reviews. High risk still requires acknowledgment.', { mode: { type: 'string', enum: ['auto', 'ask'] } }, async (input, ctx) => {
		if (!['auto', 'ask'].includes(input.mode)) throw new Error('Invalid merge mode')
		const s = legacy(ctx.thread.id)
		if (isV2(s)) throw new Error('remote-verification-unqualified: v2 merge mode is disabled')
		await acknowledge(ctx, `Set this mission's merge preference to ${input.mode}. High-risk acknowledgment remains mandatory.`)
		return status(write(s, { type: 'mode', mode: input.mode }))
	})
	tool('mission_present', 'Show the owner implementation locations, criterion evidence, design, candidate and try-it instructions before any merge request. Also publish the packet on the PR for reviewers; this tool shows it in Amp only.', {}, async (_input, ctx) => {
		const s = legacy(ctx.thread.id)
		if (isV2(s)) { await ctx.ui.notify(packet(s) + '\n\n' + status(s)); return status(s) }
		if (!s.evidence) throw new Error('Acceptance evidence required')
		const merge = mergeDialog(s)
		// Information only; the merge dialog is the approval view.
		await ctx.ui.notify(merge.details!)
		ctx.signal.throwIfAborted()
		return status(write(s, { type: 'presented', fingerprint: fingerprint(s) }))
	})
	tool('mission_merge', 'Request an immediate exact-head squash merge into dev with existing GitHub credentials only after local gates, required pinned CI and branch protection pass; contract missions name the milestoneId and open no dialog. Never queues authorization for a future head or authorizes release/deployment.', { milestoneId: { type: 'string' } }, async (input, ctx) => {
		const s = required(ctx.thread.id)
		if (isContract(s)) {
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
			return status(pending) + `\nRequest issued for ${m.id}, not confirmed merged. Use mission_reconcile.`
		}
		if (isV2(s)) throw new Error('remote-verification-unqualified: v2 remote effects are disabled')
		const missing = blockers(s)
		if (missing.length) throw new Error(missing.join('; '))
		if (s.phase === 'merge-pending' || s.phase === 'merged') throw new Error('Reconcile existing request; do not repeat merge effects')
		await github.preflight(s)
		ctx.signal.throwIfAborted()
		// Persist BEFORE effects. A crash or unknown network outcome must never
		// turn into an automatically repeated merge command.
		const pending = write(s, { type: 'merge-requested', fingerprint: fingerprint(s) })
		inFlight.add(s.thread)
		try { await github.request(pending) } finally { inFlight.delete(s.thread) }
		return status(pending) + '\nRequest issued, not confirmed merged. Use mission_reconcile.'
	}, [])
	tool('mission_reconcile', 'Read GitHub after restart or uncertain merge outcome. Never repeats a merge. Contract missions name the milestoneId. V2 requires unitId/attemptId and records only exact-head dev integration; prior missing gates remain missing.', { milestoneId: { type: 'string' }, unitId: { type: 'string' }, attemptId: { type: 'string' } }, async (input, ctx) => {
		const s = required(ctx.thread.id)
		if (isContract(s)) {
			const m = milestoneOf(s, input.milestoneId)
			if (m.status !== 'merge-pending') return status(s)
			const c = m.candidate!
			const pr = await github.pull(c)
			ctx.signal.throwIfAborted()
			if (pr.merged === true && pr.head?.sha === c.head && pr.base?.ref === 'dev' && pr.base?.repo?.full_name === c.repo) {
				return status(saveContract(advanceContract(s, { type: 'merged', milestoneId: m.id, fingerprint: contractFingerprint(s, m.id), commit: pr.merge_commit_sha })))
			}
			return status(s) + `\n${m.id} is not confirmed merged. Inspect the PR, CI and any uncertain request; do not repeat the merge.`
		}
		if (isV2(s)) {
			const unit = s.units.find(u => u.id === input.unitId)
			const a = unit?.attempts.at(-1)
			if (!unit || !a || a.id !== input.attemptId || a.stale) throw new Error('Explicit current unitId and attemptId required')
			if (a.integration) return status(s)
			const pr = await github.pull({ candidate: a.candidate } as Mission)
			ctx.signal.throwIfAborted()
			if (pr.merged === true && pr.head?.sha === a.candidate.head && pr.base?.ref === 'dev' && pr.base?.repo?.full_name === a.candidate.repo) {
				return status(write(s, { type: 'observe-integration', unitId: unit.id, attemptId: a.id, commit: pr.merge_commit_sha, remoteHead: pr.head.sha, targetRef: pr.base.ref, repository: pr.base.repo.full_name }))
			}
			return status(s) + '\nExact integration not observed; do not infer completion.'
		}
		if (s.phase !== 'merge-pending') return status(s)
		const pr = await github.pull(s)
		ctx.signal.throwIfAborted()
		if (pr.merged === true && pr.head?.sha === s.candidate!.head && pr.base?.ref === 'dev' && pr.base?.repo?.full_name === s.candidate!.repo) {
			return status(write(s, { type: 'merged', fingerprint: fingerprint(s), commit: pr.merge_commit_sha }))
		}
		return status(s) + '\nNot confirmed integrated. Inspect current PR/CI and any uncertain request; do not repeat blindly.'
	}, [])
	tool('mission_recover', 'Recovery after investigating a settled, unqueued merge attempt. Reads GitHub twice, advances the recovery generation, invalidates candidate reviews and evidence, and returns to review without issuing another merge. Contract missions name the milestoneId and open no dialog; v1 asks the owner. Never use while a request may still be in flight.', { milestoneId: { type: 'string' } }, async (input, ctx) => {
		const s = required(ctx.thread.id)
		if (isContract(s)) {
			const m = milestoneOf(s, input.milestoneId)
			const key = `${s.thread} ${m.id}`
			if (m.status !== 'merge-pending' || inFlight.has(key)) throw new Error('Recovery requires a settled pending request')
			const c = m.candidate!
			const pr = await github.pull(c)
			if (!unqueued(pr, c.repo)) throw new Error('Recovery requires an open, unmerged, unqueued dev PR; investigate remote state first')
			const live = await github.pull(c)
			ctx.signal.throwIfAborted()
			if (!unqueued(live, c.repo) || live.head.sha !== pr.head.sha || live.base.sha !== pr.base.sha || inFlight.has(key)) throw new Error('Remote changed during recovery; reconcile again')
			return status(saveContract(advanceContract(s, { type: 'recover', milestoneId: m.id, fingerprint: contractFingerprint(s, m.id) }))) + `\nRecovered ${m.id}: its reviews and evidence are void, and the merge was not retried.`
		}
		if (isV2(s)) throw new Error('remote-verification-unqualified: v2 creates no pending remote effects to recover')
		if (s.phase !== 'merge-pending' || inFlight.has(s.thread)) throw new Error('Recovery requires a settled pending request')
		const pr = await github.pull(s)
		if (!unqueued(pr, s.candidate!.repo)) throw new Error('Recovery requires an open, unmerged, unqueued dev PR; investigate remote state first')
		await acknowledge(ctx, `Recover https://github.com/${s.candidate!.repo}/pull/${s.candidate!.pr} at remote head ${pr.head.sha}, base ${pr.base.sha}. Confirm the previous request has settled and no executor is still sending it. This invalidates reviews/evidence and merge acknowledgment; it does NOT retry the merge.`)
		const live = await github.pull(s)
		ctx.signal.throwIfAborted()
		if (!unqueued(live, s.candidate!.repo) || live.head.sha !== pr.head.sha || live.base.sha !== pr.base.sha || inFlight.has(s.thread)) throw new Error('Remote changed during recovery; reconcile again')
		return status(write(s, { type: 'recover', fingerprint: fingerprint(s) }))
	}, [])
	tool('mission_migrate', 'Preview a v1-to-v2 shadow migration without writes. adopt:true requires expectedDigest from preview and an owner dialog, then backs up exact original bytes under a lock. Pending effects must reconcile under v1 first. Migration is not v2 design approval. For unbound v1 missions supply repository owner/name.', { adopt: { type: 'boolean' }, expectedDigest: { type: 'string' }, repository: { type: 'string' } }, async (input, ctx) => {
		ctx.signal.throwIfAborted()
		const s = legacy(ctx.thread.id)
		if (isV2(s)) throw new Error('Mission is already v2')
		if (typeof input.adopt !== 'boolean') throw new Error('Explicit adopt boolean required')
		const raw = readRecordBytes(pathFor(s.thread))!
		const hash = sourceDigest(raw)
		const preview = previewMigration(parseMission(JSON.parse(raw), s.thread), input.repository)
		if (!input.adopt) return JSON.stringify({ ...preview, sourceDigest: hash, blockers: blockersV2(preview) }, null, 2)
		if (input.expectedDigest !== hash) throw new Error('Migration source changed; preview again')
		await acknowledge(ctx, 'Adopt v2 shadow storage. Preserve a read-only byte backup; new v2 design needs separate acknowledgment. V1 merges will no longer be available for this record.\n\n' + packet(preview))
		return status(migrateMission(pathFor(s.thread), s.thread, hash, input.repository))
	}, ['adopt'])
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
			'', status(next),
		].join('\n')
	})
	tool('mission_effect', 'Contract missions: call right before an outside effect. Name a contract effect {effectId}, or describe one that is not in the contract {effect, why}. A pre-authorized effect is recorded with no dialog. Any other effect opens the owner effect dialog and is recorded only when the owner approves it once. Records the performed effect; never changes the contract.', { effectId: { type: 'string' }, effect: { type: 'string' }, why: { type: 'string' } }, async (input, ctx) => {
		const s = contract(ctx.thread.id)
		const target = Object.fromEntries(['effectId', 'effect', 'why'].filter(k => Object.hasOwn(input, k)).map(k => [k, input[k]]))
		const listed = s.contract.effects.find(e => e.id === target.effectId)
		if (listed?.preAuthorized) return `Recorded ${listed.id} as performed. It is pre-authorized, so no dialog opened.\n\n${status(saveContract(advanceContract(s, { type: 'effect', ...target })))}`
		const { reading, record } = await approval(ctx.thread, ctx.ui, s, { kind: 'effect', ...target }, ctx.signal)
		if (!record) return notApproved(reading)
		return `${EFFECT_APPROVED} Perform it now, exactly as described.\n\n${status(record)}`
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
			const p = s && isContract(s) ? s.pendingApproval : undefined
			if (!thread || !s || !isContract(s) || !p || p.digest !== approvalDigest(s.contract)) {
				if (thread) dropReopen(thread.id)
				return await ctx.ui.notify('No mission approval is pending in this thread.')
			}
			const { digest: _digest, ...target } = p
			const { reading, record } = await approval(thread, ctx.ui, s, target)
			if (record) {
				const effect = p.effectId ?? p.effect
				reopened.set(thread.id, p.kind === 'kickoff' ? 'The owner approved the kickoff in the reopened approval dialog.' : `${EFFECT_APPROVED} It was approved in the reopened approval dialog: ${effect}. Perform it now, exactly as described.`)
				return await ctx.ui.notify(p.kind === 'kickoff' ? 'Kickoff approved by the owner and recorded. Send a message to continue the mission.' : `${EFFECT_APPROVED} Send a message so the agent performs it.`)
			}
			if (reading.outcome === 'changes') return await thread.appendUserMessage({ type: 'user-message', content: `The mission owner answered the ${p.kind} approval dialog: not approved. The owner wrote in Changes:\n${reading.message}` })
			await ctx.ui.notify(notApproved(reading))
		} catch (error) { await ctx.ui.notify((error as Error).message) }
	})
	amp.on('session.start', async (event, ctx) => {
		const s = read(event.thread.id)
		if (s && isContract(s)) return await ctx.ui.notify(compactStatus(s))
		if (s) await ctx.ui.notify(isV2(s) ? `V2 shadow mission resumed at ${s.status}. Use mission_status. Remote verification remains unqualified; do not retry merges.` : `Mission resumed at ${s.phase}. Use mission_status${s.phase === 'merge-pending' ? ' and mission_reconcile' : ''}.`)
	})
	amp.on('agent.start', async event => {
		const s = read(event.thread.id)
		if (s && isContract(s)) {
			const r = reopenFor(s), note = reopened.get(s.thread)
			reopened.delete(s.thread)
			const tool = r?.pending.kind === 'kickoff' ? 'mission_approve' : 'mission_effect'
			return { message: { content: [
				'Active contract mission. Follow delivering; mission_status has the fingerprints and details. Local records do not override required CI or branch protection.',
				compactStatus(s),
				...(r ? [`An owner approval is pending: the ${r.pending.kind} approval dialog ended without the owner's answer. The owner reopens it with the quick action "Open ${r.pending.kind} approval" above the composer in the Amp web app. Tell the owner it is waiting; open it again with ${tool} only when the owner asks.`] : []),
				...(note ? [note] : []),
			].join('\n') } }
		}
		if (s) return { message: { content: `Active software mission: ${status(s)}\nFollow delivering. Preserve owner-approved requirements, plan, technical/UX design; whiteboard before build. Local workflow records do not override required CI or branch protection.` } }
	})
	amp.on('agent.end', async event => {
		if (event.status !== 'done') return
		const s = read(event.thread.id)
		if (s && isContract(s)) {
			if (!workReady(s)) return
			return { action: 'continue', maxContinuations: 3, userMessage: `The contract mission has work ready. Next action: ${nextAction(s)}\nContinue the contract loop in delivering. Record a stop with mission_update only for one of the five stop reasons. Do not bypass a merge blocker, required CI or branch protection.` }
		}
		if (!s || isV2(s) || s.paused || !['building', 'reviewing', 'evidence'].includes(s.phase) || (s.presented && blockers(s).includes('Owner merge acknowledgment required'))) return
		return { action: 'continue', maxContinuations: 3, userMessage: 'The active mission is not integrated. Continue its approved build/review/evidence loop, or record a concrete blocker with mission_update pause. Do not bypass approval, required CI, branch protection or unavailable-platform gates. Never claim a requested merge is completion.' }
	})
}
