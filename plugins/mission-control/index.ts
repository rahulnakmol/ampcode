import type { PluginAPI, PluginToolContext } from '@ampcode/plugin'
import { execFileSync } from 'node:child_process'
import { appendFileSync, existsSync, readFileSync, realpathSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { advance, blockers, createMission, digest, fingerprint, loadMission, saveMission, type Action, type Mission } from './lib/mission'
import { GitHub } from './lib/github'

export const description = 'Coordinates owner-approved software missions, revision-bound evidence and protected dev integration using existing GitHub credentials.'

function packet(s: Mission) {
	const c = s.candidate
	return [
		`Mission requirements: ${s.requirements}`, `Design: ${s.design?.digest}`, JSON.stringify(s.design?.bundle, null, 2),
		c ? `Candidate: https://github.com/${c.repo}/pull/${c.pr}\nHead: ${c.head}\nBase: ${c.base}\nRisk: ${c.risk}` : '',
		...(s.design?.criteria ?? []).map((criterion, i) => `${i + 1}. ${criterion}\n${s.evidence?.results[i] ?? 'Not yet verified'}`),
		`Try it: ${s.evidence?.tryIt ?? 'Not yet supplied'}`, `Customer value: ${s.evidence?.value ?? 'Not yet established'}`,
		`Merge preference: ${s.mode}; high risk always requires owner acknowledgment.`,
		'Approvals and evidence are local workflow gates, not a hostile-shell security boundary. Required CI and protected dev must also permit integration.',
	].filter(Boolean).join('\n\n')
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
	const read = (thread: string) => amp.system.workspaceRoot ? loadMission(pathFor(thread), thread) : undefined
	const required = (thread: string) => {
		const s = read(thread)
		if (!s) throw new Error('Start a mission explicitly with mission_start')
		return s
	}
	const write = (s: Mission, action: Action) => {
		const next = advance(s, action)
		saveMission(pathFor(s.thread), next)
		return next
	}
	const status = (s: Mission) => JSON.stringify({ ...s, fingerprint: fingerprint(s), blockers: blockers(s) }, null, 2)
	const acknowledge = async (ctx: PluginToolContext, message: string) => {
		const result = await ctx.ui.confirm({
			title: 'Mission owner acknowledgment', message: message + '\n\nOnly the thread owner may approve/adopt this mission. Type ACKNOWLEDGE. This is not a password or credential; the masked field restricts the dialog to the owner.',
			requireHuman: true, endTurnOnDecline: true,
			fields: [{ name: 'acknowledgment', label: 'Type ACKNOWLEDGE (not a secret)', value: '', secret: true }],
		})
		ctx.signal.throwIfAborted()
		if (result?.acknowledgment !== 'ACKNOWLEDGE') throw new Error('Owner acknowledgment absent; mission remains blocked')
	}
	function tool(name: string, description: string, properties: Record<string, any>, execute: (input: any, ctx: PluginToolContext) => Promise<string>) {
		amp.registerTool({ name, description, inputSchema: { type: 'object', properties, required: Object.keys(properties), additionalProperties: false }, execute })
	}
	tool('mission_start', 'Start a software mission from user requirements. Then load grilling; obtain an owner-approved spec, plan and technical/UX design before defense or build. Does not infer permission to deploy or publish.', { requirements: { type: 'string' } }, async (input, ctx) => {
		ctx.signal.throwIfAborted()
		if (read(ctx.thread.id)) throw new Error('Mission already exists; use mission_status')
		const s = createMission(ctx.thread.id, input.requirements)
		const cwd = root()
		const gitRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd, encoding: 'utf8' }).trim()
		if (realpathSync(cwd) !== realpathSync(gitRoot)) throw new Error('Open the dedicated worktree root before starting a mission')
		const exclude = resolve(cwd, execFileSync('git', ['rev-parse', '--git-path', 'info/exclude'], { cwd, encoding: 'utf8' }).trim())
		const rules = existsSync(exclude) ? readFileSync(exclude, 'utf8') : ''
		if (!rules.split('\n').includes('/.amp/in/')) appendFileSync(exclude, '\n/.amp/in/\n')
		saveMission(pathFor(ctx.thread.id), s)
		return status(s)
	})
	tool('mission_status', 'Reload mission checkpoints and blockers. A merge request is not a completed mission.', {}, async (_input, ctx) => status(required(ctx.thread.id)))
	tool('mission_update', 'Record workflow evidence. Actions: design {bundle:{spec,plan,technical,ux},criteria:string[]}; defense {digest,record}; build; candidate {candidate:{repo,pr,head,base,risk}}; review {gate:1|2,fingerprint,passed,reviewer,record}; evidence {fingerprint,results:string[] in criteria order,tryIt,value}; pause {reason}; resume. Include implementation locations, commands/results, limitations and failure/recovery evidence. Approval/merge receipts cannot be supplied here.', { action: { type: 'object', properties: { type: { type: 'string', enum: ['design', 'defense', 'build', 'candidate', 'review', 'evidence', 'pause', 'resume'] } }, required: ['type'], additionalProperties: true } }, async (input, ctx) => {
		ctx.signal.throwIfAborted()
		if (!['design', 'defense', 'build', 'candidate', 'review', 'evidence', 'pause', 'resume'].includes(input.action?.type)) throw new Error('Internal approval and integration actions cannot be supplied by agents')
		const s = required(ctx.thread.id)
		if (input.action.type === 'build') {
			await ctx.ui.notify('Build entry: low/medium risk defaults to automatic merge into dev after evidence and all gates. No response is needed. For ask-before-merge, use mission_merge_mode with mode ask; high risk always requires owner acknowledgment.')
			ctx.signal.throwIfAborted()
		}
		return status(write(s, input.action))
	})
	tool('mission_approve', 'Request an owner-restricted acknowledgment of the exact design bundle or presented merge candidate. Never accepts an agent-supplied approval.', { stage: { type: 'string', enum: ['design', 'merge'] } }, async (input, ctx) => {
		const s = required(ctx.thread.id)
		if (input.stage !== 'design' && input.stage !== 'merge') throw new Error('Invalid approval stage')
		if (input.stage === 'design' && !s.design) throw new Error('Design bundle required')
		if (input.stage === 'merge' && s.presented !== fingerprint(s)) throw new Error('Present candidate evidence first')
		await acknowledge(ctx, `Acknowledge ${input.stage} before proceeding.\n\n${packet(s)}`)
		return status(write(s, input.stage === 'design' ? { type: 'approve-design', digest: s.design!.digest } : { type: 'approve-merge', fingerprint: fingerprint(s) }))
	})
	tool('mission_merge_mode', 'Owner-controlled override of default automatic low/medium integration. Changing mode invalidates presented evidence and merge acknowledgment, not code reviews. High risk still requires acknowledgment.', { mode: { type: 'string', enum: ['auto', 'ask'] } }, async (input, ctx) => {
		if (!['auto', 'ask'].includes(input.mode)) throw new Error('Invalid merge mode')
		const s = required(ctx.thread.id)
		await acknowledge(ctx, `Set this mission's merge preference to ${input.mode}. High-risk acknowledgment remains mandatory.`)
		return status(write(s, { type: 'mode', mode: input.mode }))
	})
	tool('mission_present', 'Show the owner implementation locations, criterion evidence, design, candidate and try-it instructions before any merge request. Also publish the packet on the PR for reviewers; this tool shows it in Amp only.', {}, async (_input, ctx) => {
		const s = required(ctx.thread.id)
		if (!s.evidence) throw new Error('Acceptance evidence required')
		await ctx.ui.notify(packet(s))
		ctx.signal.throwIfAborted()
		return status(write(s, { type: 'presented', fingerprint: fingerprint(s) }))
	})
	tool('mission_merge', 'Request an immediate exact-head squash merge into dev with existing GitHub credentials only after local gates, required pinned CI and branch protection pass. Never queues authorization for a future head or authorizes release/deployment.', {}, async (_input, ctx) => {
		const s = required(ctx.thread.id)
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
	})
	tool('mission_reconcile', 'Read GitHub after restart or uncertain merge outcome. Never repeats a merge request. Report complete only for the recorded head merged into dev.', {}, async (_input, ctx) => {
		const s = required(ctx.thread.id)
		if (s.phase !== 'merge-pending') return status(s)
		const pr = await github.pull(s)
		ctx.signal.throwIfAborted()
		if (pr.merged === true && pr.head?.sha === s.candidate!.head && pr.base?.ref === 'dev' && pr.base?.repo?.full_name === s.candidate!.repo) {
			return status(write(s, { type: 'merged', fingerprint: fingerprint(s), commit: pr.merge_commit_sha }))
		}
		return status(s) + '\nNot confirmed integrated. Inspect current PR/CI and any uncertain request; do not repeat blindly.'
	})
	tool('mission_recover', 'Owner-only recovery after investigating a settled, unqueued merge attempt. Reads GitHub twice, advances the recovery generation, invalidates all candidate evidence and approval, and returns to review without issuing another merge. Never use while a request may still be in flight.', {}, async (_input, ctx) => {
		const s = required(ctx.thread.id)
		if (s.phase !== 'merge-pending' || inFlight.has(s.thread)) throw new Error('Recovery requires a settled pending request')
		const pr = await github.pull(s)
		const unqueued = (p: any) => p.state === 'open' && p.merged === false && p.auto_merge === null && p.isMergeQueueEnabled === false && p.isInMergeQueue === false && p.mergeQueueEntry === null && p.base?.ref === 'dev' && p.base?.repo?.full_name === s.candidate!.repo && /^[a-f0-9]{40}$/.test(p.head?.sha) && /^[a-f0-9]{40}$/.test(p.base?.sha)
		if (!unqueued(pr)) throw new Error('Recovery requires an open, unmerged, unqueued dev PR; investigate remote state first')
		await acknowledge(ctx, `Recover https://github.com/${s.candidate!.repo}/pull/${s.candidate!.pr} at remote head ${pr.head.sha}, base ${pr.base.sha}. Confirm the previous request has settled and no executor is still sending it. This invalidates reviews/evidence and merge acknowledgment; it does NOT retry the merge.`)
		const live = await github.pull(s)
		ctx.signal.throwIfAborted()
		if (!unqueued(live) || live.head.sha !== pr.head.sha || live.base.sha !== pr.base.sha || inFlight.has(s.thread)) throw new Error('Remote changed during recovery; reconcile again')
		return status(write(s, { type: 'recover', fingerprint: fingerprint(s) }))
	})
	amp.on('session.start', async (event, ctx) => {
		const s = read(event.thread.id)
		if (s) await ctx.ui.notify(`Mission resumed at ${s.phase}. Use mission_status${s.phase === 'merge-pending' ? ' and mission_reconcile' : ''}.`)
	})
	amp.on('agent.start', async event => {
		const s = read(event.thread.id)
		if (s) return { message: { content: `Active software mission: ${status(s)}\nFollow delivering. Preserve owner-approved requirements, plan, technical/UX design; whiteboard before build. Local workflow records do not override required CI or branch protection.` } }
	})
	amp.on('agent.end', async event => {
		if (event.status !== 'done') return
		const s = read(event.thread.id)
		if (!s || s.paused || !['building', 'reviewing', 'evidence'].includes(s.phase) || (s.presented && blockers(s).includes('Owner merge acknowledgment required'))) return
		return { action: 'continue', maxContinuations: 3, userMessage: 'The active mission is not integrated. Continue its approved build/review/evidence loop, or record a concrete blocker with mission_update pause. Do not bypass approval, required CI, branch protection or unavailable-platform gates. Never claim a requested merge is completion.' }
	})
}
