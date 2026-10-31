import type { PluginAPI, PluginToolContext } from '@ampcode/plugin'
import { execFileSync } from 'node:child_process'
import { appendFileSync, existsSync, readFileSync, realpathSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { advance, blockers, createMission, digest, fingerprint, loadRecord, saveRecord, readRecordBytes, parseMission, type Action, type Mission } from './lib/mission'
import { advanceV2, blockersV2, createMissionV2, fingerprintV2, evidenceDigestV2, type ActionV2, type MissionV2 } from './lib/mission-v2'
import { intentDigest } from './lib/contracts'
import { migrateMission, previewMigration, sourceDigest } from './lib/migration'
import { GitHub } from './lib/github'

export const description = 'Coordinates owner-approved software missions, revision-bound evidence and protected dev integration using existing GitHub credentials.'

type RecordState = Mission | MissionV2
function isV2(s: RecordState): s is MissionV2 { return 'schemaVersion' in s }
function packet(s: RecordState) {
	if (isV2(s)) return [
		'V2 shadow mission. Intent authority: local-reported. Remote verification is unqualified; merges are disabled.',
		`Current intent digest: ${intentDigest(s.manifest)}`, JSON.stringify(s.manifest, null, 2),
		'Previous intent (review amendments and dispositions):', JSON.stringify(s.snapshots.at(-2)?.manifest ?? null, null, 2),
		`Affected units: ${s.units.map(u => u.id + ': ' + u.status).join(', ')}`,
		'All submitted review/results remain reported, not authenticated execution. A design acknowledgment approves this exact local manifest, not remote authority or release.',
	].join('\n\n')
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
	const read = (thread: string) => amp.system.workspaceRoot ? loadRecord(pathFor(thread), thread) : undefined
	const required = (thread: string) => {
		const s = read(thread)
		if (!s) throw new Error('Start a mission explicitly with mission_start')
		return s
	}
	function write(s: Mission, action: Action): Mission
	function write(s: MissionV2, action: ActionV2): MissionV2
	function write(s: RecordState, action: Action | ActionV2): RecordState
	function write(s: RecordState, action: Action | ActionV2): RecordState {
		const next = isV2(s) ? advanceV2(s, action as ActionV2) : advance(s, action as Action)
		saveRecord(pathFor(s.thread), next)
		return next
	}
	const status = (s: RecordState) => JSON.stringify(isV2(s) ? {
		...s, designDigest: intentDigest(s.manifest), evidenceClass: 'reported', blockers: blockersV2(s),
		current: s.units.map(u => {
			const a = u.attempts.at(-1)
			return { unitId: u.id, attemptId: a?.id, fingerprint: a && !a.stale ? fingerprintV2(s, u.id, a.id) : null, evidenceDigest: a && !a.stale ? evidenceDigestV2(s, u.id, a.id) : null }
		}),
	} : { ...s, fingerprint: fingerprint(s), blockers: blockers(s) }, null, 2)
	const acknowledge = async (ctx: PluginToolContext, message: string) => {
		const result = await ctx.ui.confirm({
			title: 'Mission owner acknowledgment', message: message + '\n\nOnly the thread owner may approve/adopt this mission. Type ACKNOWLEDGE. This is not a password or credential; the masked field restricts the dialog to the owner.',
			requireHuman: true, endTurnOnDecline: true,
			fields: [{ name: 'acknowledgment', label: 'Type ACKNOWLEDGE (not a secret)', value: '', secret: true }],
		})
		ctx.signal.throwIfAborted()
		if (result?.acknowledgment !== 'ACKNOWLEDGE') throw new Error('Owner acknowledgment absent; mission remains blocked')
	}
	function tool(name: string, description: string, properties: Record<string, any>, execute: (input: any, ctx: PluginToolContext) => Promise<string>, required = Object.keys(properties)) {
		amp.registerTool({ name, description, inputSchema: { type: 'object', properties, required, additionalProperties: false }, execute })
	}
	tool('mission_start', 'Start v1 from requirements (default), or explicitly opt into v2 shadow traceability with schemaVersion:2 and a complete manifest. V2 never sends merges. Load grilling/delivering; obtain native owner design acknowledgment before defense/build. Uses native Amp specialists, not a separate runtime.', { requirements: { type: 'string' }, schemaVersion: { type: 'integer', enum: [1, 2] }, manifest: { type: 'object', additionalProperties: true } }, async (input, ctx) => {
		ctx.signal.throwIfAborted()
		if (read(ctx.thread.id)) throw new Error('Mission already exists; use mission_status')
		if (input.schemaVersion !== undefined && ![1, 2].includes(input.schemaVersion)) throw new Error('Unsupported mission schema')
		if (input.schemaVersion !== 2 && input.manifest !== undefined) throw new Error('Manifest requires explicit schemaVersion:2')
		if (input.schemaVersion === 2 && input.requirements !== undefined) throw new Error('V2 requirements belong in the manifest')
		const s = input.schemaVersion === 2 ? createMissionV2(ctx.thread.id, input.manifest) : createMission(ctx.thread.id, input.requirements)
		const cwd = root()
		const gitRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd, encoding: 'utf8' }).trim()
		if (realpathSync(cwd) !== realpathSync(gitRoot)) throw new Error('Open the dedicated worktree root before starting a mission')
		const exclude = resolve(cwd, execFileSync('git', ['rev-parse', '--git-path', 'info/exclude'], { cwd, encoding: 'utf8' }).trim())
		const rules = existsSync(exclude) ? readFileSync(exclude, 'utf8') : ''
		if (!rules.split('\n').includes('/.amp/in/')) appendFileSync(exclude, '\n/.amp/in/\n')
		saveRecord(pathFor(ctx.thread.id), s)
		return status(s)
	}, [])
	tool('mission_status', 'Reload mission checkpoints and blockers. A merge request is not a completed mission.', {}, async (_input, ctx) => status(required(ctx.thread.id)))
	const publicActions = ['design', 'defense', 'build', 'candidate', 'review', 'evidence', 'report', 'finding', 'post-report', 'disposition', 'post-delivery', 'closure-report', 'pause', 'resume']
	tool('mission_update', 'V1: design {bundle:{spec,plan,technical,ux},criteria}; defense {digest,record}; build; candidate {candidate}; review {gate,fingerprint,passed,reviewer,record}; evidence {fingerprint,results,tryIt,value}; pause {reason}; resume. V2: design {manifest}; build {unitId}; candidate {unitId,attemptId,candidate,manifest}; report {unitId,attemptId,fingerprint,evidence:{id,criterionIds,outcome,record}}; review adds unitId,attemptId,evidenceDigest,findingIds. finding {unitId,attemptId,fingerprint,finding:{id,criterionIds,severity,confidence,location,record,owner}}. post-report {evidence:{id,baseline,designDigest,policyDigest,unitIds,results:[{criterionId,outcome,record}],record}}. post-delivery {unitId,package} / closure-report {package}: package replaces post-report id with evidenceIds and findings. disposition {disposition:{findingId,outcome:fixed|rejected|deferred,evidenceIds,owner,reviewer,record,correctiveUnitId?}}. V2 results/dispositions are reported only; references must resolve. No internal approval/import/execution/integration actions.', { action: { type: 'object', properties: { type: { type: 'string', enum: publicActions } }, required: ['type'], additionalProperties: true } }, async (input, ctx) => {
		ctx.signal.throwIfAborted()
		if (!publicActions.includes(input.action?.type)) throw new Error('Internal approval and integration actions cannot be supplied by agents')
		const s = required(ctx.thread.id)
		if (!isV2(s) && input.action.type === 'build') {
			await ctx.ui.notify('Build entry: low/medium risk defaults to automatic merge into dev after evidence and all gates. No response is needed. For ask-before-merge, use mission_merge_mode with mode ask; high risk always requires owner acknowledgment.')
			ctx.signal.throwIfAborted()
		}
		return status(write(s, input.action))
	})
	tool('mission_approve', 'Request an owner-restricted acknowledgment of the exact design bundle or presented merge candidate. Never accepts an agent-supplied approval.', { stage: { type: 'string', enum: ['design', 'merge'] } }, async (input, ctx) => {
		const s = required(ctx.thread.id)
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
		await acknowledge(ctx, `Acknowledge ${input.stage} before proceeding.\n\n${packet(s)}`)
		return status(write(s, input.stage === 'design' ? { type: 'approve-design', digest: s.design!.digest } : { type: 'approve-merge', fingerprint: fingerprint(s) }))
	})
	tool('mission_merge_mode', 'Owner-controlled override of default automatic low/medium integration. Changing mode invalidates presented evidence and merge acknowledgment, not code reviews. High risk still requires acknowledgment.', { mode: { type: 'string', enum: ['auto', 'ask'] } }, async (input, ctx) => {
		if (!['auto', 'ask'].includes(input.mode)) throw new Error('Invalid merge mode')
		const s = required(ctx.thread.id)
		if (isV2(s)) throw new Error('remote-verification-unqualified: v2 merge mode is disabled')
		await acknowledge(ctx, `Set this mission's merge preference to ${input.mode}. High-risk acknowledgment remains mandatory.`)
		return status(write(s, { type: 'mode', mode: input.mode }))
	})
	tool('mission_present', 'Show the owner implementation locations, criterion evidence, design, candidate and try-it instructions before any merge request. Also publish the packet on the PR for reviewers; this tool shows it in Amp only.', {}, async (_input, ctx) => {
		const s = required(ctx.thread.id)
		if (isV2(s)) { await ctx.ui.notify(packet(s) + '\n\n' + status(s)); return status(s) }
		if (!s.evidence) throw new Error('Acceptance evidence required')
		await ctx.ui.notify(packet(s))
		ctx.signal.throwIfAborted()
		return status(write(s, { type: 'presented', fingerprint: fingerprint(s) }))
	})
	tool('mission_merge', 'Request an immediate exact-head squash merge into dev with existing GitHub credentials only after local gates, required pinned CI and branch protection pass. Never queues authorization for a future head or authorizes release/deployment.', {}, async (_input, ctx) => {
		const s = required(ctx.thread.id)
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
	})
	tool('mission_reconcile', 'Read GitHub after restart or uncertain merge outcome. Never repeats a merge. V2 requires unitId/attemptId and records only exact-head dev integration; prior missing gates remain missing.', { unitId: { type: 'string' }, attemptId: { type: 'string' } }, async (input, ctx) => {
		const s = required(ctx.thread.id)
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
	tool('mission_recover', 'Owner-only recovery after investigating a settled, unqueued merge attempt. Reads GitHub twice, advances the recovery generation, invalidates all candidate evidence and approval, and returns to review without issuing another merge. Never use while a request may still be in flight.', {}, async (_input, ctx) => {
		const s = required(ctx.thread.id)
		if (isV2(s)) throw new Error('remote-verification-unqualified: v2 creates no pending remote effects to recover')
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
	tool('mission_migrate', 'Preview a v1-to-v2 shadow migration without writes. adopt:true requires expectedDigest from preview and an owner dialog, then backs up exact original bytes under a lock. Pending effects must reconcile under v1 first. Migration is not v2 design approval. For unbound v1 missions supply repository owner/name.', { adopt: { type: 'boolean' }, expectedDigest: { type: 'string' }, repository: { type: 'string' } }, async (input, ctx) => {
		ctx.signal.throwIfAborted()
		const s = required(ctx.thread.id)
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
	amp.on('session.start', async (event, ctx) => {
		const s = read(event.thread.id)
		if (s) await ctx.ui.notify(isV2(s) ? `V2 shadow mission resumed at ${s.status}. Use mission_status. Remote verification remains unqualified; do not retry merges.` : `Mission resumed at ${s.phase}. Use mission_status${s.phase === 'merge-pending' ? ' and mission_reconcile' : ''}.`)
	})
	amp.on('agent.start', async event => {
		const s = read(event.thread.id)
		if (s) return { message: { content: `Active software mission: ${status(s)}\nFollow delivering. Preserve owner-approved requirements, plan, technical/UX design; whiteboard before build. Local workflow records do not override required CI or branch protection.` } }
	})
	amp.on('agent.end', async event => {
		if (event.status !== 'done') return
		const s = read(event.thread.id)
		if (!s || isV2(s) || s.paused || !['building', 'reviewing', 'evidence'].includes(s.phase) || (s.presented && blockers(s).includes('Owner merge acknowledgment required'))) return
		return { action: 'continue', maxContinuations: 3, userMessage: 'The active mission is not integrated. Continue its approved build/review/evidence loop, or record a concrete blocker with mission_update pause. Do not bypass approval, required CI, branch protection or unavailable-platform gates. Never claim a requested merge is completion.' }
	})
}
