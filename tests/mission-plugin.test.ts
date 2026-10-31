import { expect, test } from 'bun:test'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import register from '../plugins/mission-control'
import { GitHub } from '../plugins/mission-control/lib/github'
import { createMission } from '../plugins/mission-control/lib/mission'
import { previewMigration } from '../plugins/mission-control/lib/migration'
import { intentDigest } from '../plugins/mission-control/lib/contracts'

function harness(root = mkdtempSync(join(tmpdir(), 'mission-plugin-')), github?: any) {
	execFileSync('git', ['init', '-q', root])
	const tools: Record<string, any> = {}, hooks: Record<string, any> = {}, dialogs: any[] = [], notifications: string[] = []
	let answer: any = { acknowledgment: 'ACKNOWLEDGE' }
	const ctx = { thread: { id: 'T-test' }, signal: new AbortController().signal, ui: {
		confirm: async (dialog: any) => { dialogs.push(dialog); return answer },
		notify: async (message: string) => { notifications.push(message) },
	} }
	const amp = { system: { workspaceRoot: root }, helpers: { filePathFromURI: (p: string) => p }, configuration: { get: async () => ({}) },
		registerTool: (tool: any) => { tools[tool.name] = tool.execute }, on: (event: string, handler: any) => { hooks[event] = handler },
	}
	register(amp as any, github)
	return { root, tools, hooks, dialogs, notifications, ctx, answer: (value: any) => { answer = value }, call: (name: string, input = {}) => tools[name](input, ctx) }
}
const bundle = { spec: 'Export rows exactly', plan: 'Test, fix, review', technical: 'Offsets', ux: 'Actionable CLI errors' }
const shadowManifest = previewMigration(createMission('T-fixture', 'Resume exports'), 'acme/app').manifest
test('v2 opt-in uses native approvals but never invokes remote writes or continuation loops', async () => {
	const h = harness(undefined, { preflight: async () => { throw new Error('unexpected remote mutation') }, request: async () => { throw new Error('unexpected remote mutation') } })
	try {
		const start = JSON.parse(await h.call('mission_start', { schemaVersion: 2, manifest: shadowManifest }))
		expect(start.schemaVersion).toBe(2)
		expect(start.blockers).toContain('remote-verification-unqualified')
		h.answer(undefined)
		await expect(h.call('mission_approve', { stage: 'design' })).rejects.toThrow('acknowledgment')
		for (const type of ['approve-design', 'import-v1', 'observe-integration', 'merge-requested']) await expect(h.call('mission_update', { action: { type } })).rejects.toThrow('Internal')
		h.answer({ acknowledgment: 'ACKNOWLEDGE' })
		await h.call('mission_approve', { stage: 'design' })
		await h.call('mission_update', { action: { type: 'defense', digest: intentDigest(shadowManifest), record: 'Recovery inputs and failure boundaries explained.' } })
		await h.call('mission_update', { action: { type: 'build', unitId: 'U-1' } })
		const again = harness(h.root)
		expect(JSON.parse(await again.call('mission_status')).units[0].status).toBe('building')
		for (const name of ['mission_merge', 'mission_recover']) await expect(h.call(name)).rejects.toThrow('remote-verification-unqualified')
		await expect(h.call('mission_approve', { stage: 'merge' })).rejects.toThrow('remote-verification-unqualified')
		expect(await h.hooks['agent.end']({ thread: { id: 'T-test' }, status: 'done' })).toBeUndefined()
		expect(h.dialogs[0].message).toContain('local-reported')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})
test('v2 stale native responses do not approve an amended manifest', async () => {
	const h = harness()
	try {
		await h.call('mission_start', { schemaVersion: 2, manifest: shadowManifest })
		h.ctx.ui.confirm = async () => {
			const changed = structuredClone(shadowManifest)
			changed.criteria[0].outcome = 'Resume after clean shutdown only'
			await h.call('mission_update', { action: { type: 'design', manifest: changed } })
			return { acknowledgment: 'ACKNOWLEDGE' }
		}
		await expect(h.call('mission_approve', { stage: 'design' })).rejects.toThrow('stale')
		expect(JSON.parse(await h.call('mission_status')).approvedDesign).toBeUndefined()
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})
test('v2 reconciliation observes only exact integration and leaves missing local gates visible', async () => {
	let remoteHead = 'e'.repeat(40)
	const h = harness(undefined, { pull: async () => ({ merged: true, head: { sha: remoteHead }, base: { ref: 'dev', repo: { full_name: 'acme/app' } }, merge_commit_sha: 'c'.repeat(40) }) })
	try {
		await h.call('mission_start', { schemaVersion: 2, manifest: shadowManifest })
		await h.call('mission_approve', { stage: 'design' })
		await h.call('mission_update', { action: { type: 'defense', digest: intentDigest(shadowManifest), record: 'Observe only, never send remote effects.' } })
		await h.call('mission_update', { action: { type: 'build', unitId: 'U-1' } })
		await h.call('mission_update', { action: { type: 'candidate', unitId: 'U-1', attemptId: 'A-1', manifest: shadowManifest, candidate: { repo: 'acme/app', pr: 7, head: 'a'.repeat(40), base: 'b'.repeat(40), risk: 'low' } } })
		await expect(h.call('mission_reconcile')).rejects.toThrow('Explicit')
		await h.call('mission_reconcile', { unitId: 'U-1', attemptId: 'A-1' })
		expect(JSON.parse(await h.call('mission_status')).units[0].status).toBe('reviewing')
		remoteHead = 'a'.repeat(40)
		const observed = JSON.parse(await h.call('mission_reconcile', { unitId: 'U-1', attemptId: 'A-1' }))
		expect(observed.units[0].status).toBe('integrated')
		expect(observed.blockers).toContain('U-1: Review 1 required for current evidence')
		await h.call('mission_update', { action: { type: 'post-report', evidence: { id: 'E-post', baseline: 'c'.repeat(40), designDigest: observed.designDigest, policyDigest: 'unqualified', unitIds: ['U-1'], results: [{ criterionId: 'C-1', outcome: 'passed', record: 'Synthetic journey report only.' }], record: 'Fresh post-integration report.' } } })
		expect(JSON.parse(await h.call('mission_status')).postReports[0].producer).toBe('reported')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})
test('native migration previews without writing, requires acknowledgment and preserves v1 on decline', async () => {
	const h = harness()
	try {
		await h.call('mission_start', { requirements: 'Resume exports' })
		const before = await h.call('mission_status')
		const preview = JSON.parse(await h.call('mission_migrate', { adopt: false, repository: 'acme/app' }))
		expect(preview.schemaVersion).toBe(2)
		expect(await h.call('mission_status')).toBe(before)
		h.answer(undefined)
		await expect(h.call('mission_migrate', { adopt: true, repository: 'acme/app', expectedDigest: preview.sourceDigest })).rejects.toThrow('acknowledgment')
		expect(await h.call('mission_status')).toBe(before)
		h.answer({ acknowledgment: 'ACKNOWLEDGE' })
		const adopted = JSON.parse(await h.call('mission_migrate', { adopt: true, repository: 'acme/app', expectedDigest: preview.sourceDigest }))
		expect(adopted.schemaVersion).toBe(2)
		expect(adopted.approvedDesign).toBeUndefined()
		expect(adopted.blockers).toContain('remote-verification-unqualified')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})
async function build(h: ReturnType<typeof harness>) {
	await h.call('mission_start', { requirements: 'Resume exports' })
	await h.call('mission_update', { action: { type: 'design', bundle, criteria: ['Exact rows'] } })
	await h.call('mission_approve', { stage: 'design' })
	const s = JSON.parse(await h.call('mission_status'))
	await h.call('mission_update', { action: { type: 'defense', digest: s.design.digest, record: 'Crash after flush must roll back tail.' } })
	await h.call('mission_update', { action: { type: 'build' } })
}
test('registered tools persist an owner-approved mission across reload, without auto-merge prompts', async () => {
	const h = harness()
	try {
		await build(h)
		expect(h.dialogs).toHaveLength(1)
		expect(h.dialogs[0].fields[0]).toMatchObject({ secret: true, value: '' })
		expect(h.dialogs[0].message).toContain(bundle.technical)
		expect(h.notifications.join('\n')).toContain('ask-before-merge')
		const again = harness(h.root)
		const state = JSON.parse(await again.call('mission_status'))
		expect(state.phase).toBe('building')
		expect(state.mode).toBe('auto')
		expect(state.requirements).toBe('Resume exports')
		const exclude = execFileSync('git', ['rev-parse', '--git-path', 'info/exclude'], { cwd: h.root, encoding: 'utf8' }).trim()
		expect(readFileSync(join(h.root, exclude), 'utf8')).toContain('/.amp/in/')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})
test('forged, dismissed and stale approval cannot advance the build', async () => {
	const h = harness()
	try {
		await h.call('mission_start', { requirements: 'Resume exports' })
		await h.call('mission_update', { action: { type: 'design', bundle, criteria: ['Exact rows'] } })
		await expect(h.call('mission_update', { action: { type: 'approve-design', digest: 'forged' } })).rejects.toThrow()
		h.answer(undefined)
		await expect(h.call('mission_approve', { stage: 'design' })).rejects.toThrow('acknowledgment')
		await expect(h.call('mission_update', { action: { type: 'build' } })).rejects.toThrow()
		h.ctx.ui.confirm = async () => {
			await h.call('mission_update', { action: { type: 'design', bundle: { ...bundle, ux: 'Changed interface' }, criteria: ['Exact rows'] } })
			return { acknowledgment: 'ACKNOWLEDGE' }
		}
		await expect(h.call('mission_approve', { stage: 'design' })).rejects.toThrow('stale')
		expect(JSON.parse(await h.call('mission_status')).approvedDesign).toBeUndefined()
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})
test.each([['low', 'auto'], ['medium', 'auto'], ['high', 'auto'], ['low', 'ask'], ['unknown', 'auto']])('risk %s mode %s uses local gates and GitHub without custom configuration', async (risk, mode) => {
	const effects: string[][] = []
	const github = new GitHub(async args => {
		effects.push(args)
		if (args[0] === 'pr') return ''
		if (args[1] === 'graphql') return JSON.stringify({ data: { repository: { pullRequest: { isMergeQueueEnabled: false, isInMergeQueue: false, mergeQueueEntry: null } } } })
		if (args[1].includes('/protection')) return JSON.stringify({ enforce_admins: { enabled: true }, required_pull_request_reviews: {}, required_status_checks: { strict: true, contexts: ['test'], checks: [{ context: 'test', app_id: 15368 }] } })
		if (args[1].includes('/check-runs')) return JSON.stringify({ total_count: 1, check_runs: [{ name: 'test', app: { id: 15368 }, head_sha: 'a'.repeat(40), status: 'completed', conclusion: 'success' }] })
		return JSON.stringify({ state: 'open', merged: false, head: { sha: 'a'.repeat(40) }, base: { sha: 'b'.repeat(40), ref: 'dev', repo: { full_name: 'acme/app' } } })
	})
	const h = harness(undefined, github)
	try {
		await build(h)
		if (mode === 'ask') await h.call('mission_merge_mode', { mode })
		await h.call('mission_update', { action: { type: 'candidate', candidate: { repo: 'acme/app', pr: 7, head: 'a'.repeat(40), base: 'b'.repeat(40), risk } } })
		const s = JSON.parse(await h.call('mission_status'))
		for (const gate of [1, 2]) await h.call('mission_update', { action: { type: 'review', gate, fingerprint: s.fingerprint, passed: true, reviewer: 'T-review', record: 'Inspected recovery paths; no findings.' } })
		await h.call('mission_update', { action: { type: 'evidence', fingerprint: s.fingerprint, results: ['src/export.ts: exact parsed rows verified via CLI'], tryIt: 'Run export --resume', value: 'No duplicate row cleanup' } })
		await expect(h.call('mission_merge')).rejects.toThrow('not been presented')
		await h.call('mission_present')
		expect(h.notifications.at(-1)).toContain('src/export.ts')
		expect(h.notifications.at(-1)).toContain('Run export --resume')
		if (risk === 'unknown') {
			await expect(h.call('mission_merge')).rejects.toThrow('Risk is unknown')
			expect(effects).toEqual([])
			return
		}
		if (risk === 'high' || mode === 'ask') {
			await expect(h.call('mission_merge')).rejects.toThrow('Owner merge acknowledgment required')
			expect(effects).toEqual([])
			h.answer(undefined)
			await expect(h.call('mission_approve', { stage: 'merge' })).rejects.toThrow('acknowledgment')
			await expect(h.call('mission_merge')).rejects.toThrow('Owner merge acknowledgment required')
			h.answer({ acknowledgment: 'ACKNOWLEDGE' })
			await h.call('mission_approve', { stage: 'merge' })
		} else expect(h.dialogs).toHaveLength(1)
		await h.call('mission_merge')
		expect(effects.at(-1)).toEqual(['pr', 'merge', '7', '--repo', 'acme/app', '--squash', '--match-head-commit', 'a'.repeat(40)])
		expect(JSON.parse(await h.call('mission_status')).phase).toBe('merge-pending')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('lost merge response survives reload without a duplicate mutation or false completion', async () => {
	let requests = 0
	let remote: any = { state: 'open', merged: false }
	const transport = { preflight: async () => {}, request: async () => { requests++; throw new Error('Response lost') }, pull: async () => remote }
	const h = harness(undefined, transport)
	try {
		await build(h)
		await h.call('mission_update', { action: { type: 'candidate', candidate: { repo: 'acme/app', pr: 7, head: 'a'.repeat(40), base: 'b'.repeat(40), risk: 'low' } } })
		const s = JSON.parse(await h.call('mission_status'))
		for (const gate of [1, 2]) await h.call('mission_update', { action: { type: 'review', gate, fingerprint: s.fingerprint, passed: true, reviewer: 'T-review', record: 'Inspected CLI outcome' } })
		await h.call('mission_update', { action: { type: 'evidence', fingerprint: s.fingerprint, results: ['Exact rows verified'], tryIt: 'Run export', value: 'No lost work' } })
		await h.call('mission_present')
		await expect(h.call('mission_merge')).rejects.toThrow('Response lost')
		const reloaded = harness(h.root, transport)
		expect(JSON.parse(await reloaded.call('mission_status')).phase).toBe('merge-pending')
		await expect(reloaded.call('mission_merge')).rejects.toThrow('Reconcile')
		expect(await reloaded.call('mission_reconcile')).toContain('Not confirmed integrated')
		remote = { merged: true, head: { sha: 'c'.repeat(40) }, base: { ref: 'dev', repo: { full_name: 'acme/app' } }, merge_commit_sha: 'd'.repeat(40) }
		expect(await reloaded.call('mission_reconcile')).toContain('Not confirmed integrated')
		remote.head.sha = 'a'.repeat(40)
		expect(JSON.parse(await reloaded.call('mission_reconcile')).phase).toBe('merged')
		expect(requests).toBe(1)
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('recovery requires owner acknowledgment and stable unqueued remote state', async () => {
	const transport = { preflight: async () => {}, request: async () => { throw new Error('Not delivered') }, pull: async () => remote }
	let remote: any = { state: 'open', merged: false, auto_merge: {}, isMergeQueueEnabled: false, isInMergeQueue: false, mergeQueueEntry: null, head: { sha: 'a'.repeat(40) }, base: { sha: 'b'.repeat(40), ref: 'dev', repo: { full_name: 'acme/app' } } }
	const h = harness(undefined, transport)
	try {
		await build(h)
		await h.call('mission_update', { action: { type: 'candidate', candidate: { repo: 'acme/app', pr: 7, head: 'a'.repeat(40), base: 'b'.repeat(40), risk: 'low' } } })
		const s = JSON.parse(await h.call('mission_status'))
		for (const gate of [1, 2]) await h.call('mission_update', { action: { type: 'review', gate, fingerprint: s.fingerprint, passed: true, reviewer: 'T-review', record: 'Reviewed actual outcome' } })
		await h.call('mission_update', { action: { type: 'evidence', fingerprint: s.fingerprint, results: ['Exact rows verified'], tryIt: 'Run export', value: 'No lost work' } })
		await h.call('mission_present')
		await expect(h.call('mission_merge')).rejects.toThrow('Not delivered')
		await expect(h.call('mission_recover')).rejects.toThrow('unqueued')
		remote.auto_merge = null
		remote.isInMergeQueue = true
		await expect(h.call('mission_recover')).rejects.toThrow('unqueued')
		remote.isInMergeQueue = false
		h.answer(undefined)
		await expect(h.call('mission_recover')).rejects.toThrow('acknowledgment')
		h.answer({ acknowledgment: 'ACKNOWLEDGE' })
		const recovered = JSON.parse(await h.call('mission_recover'))
		expect(recovered.phase).toBe('reviewing')
		expect(recovered.reviews).toEqual([])
		expect(recovered.generation).toBe(s.generation + 1)
		expect(recovered.fingerprint).not.toBe(s.fingerprint)
		await expect(h.call('mission_merge')).rejects.toThrow('Review 1')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})
