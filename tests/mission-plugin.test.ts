import { expect, test } from 'bun:test'
import { execFileSync } from 'node:child_process'
import { copyFileSync, mkdirSync, mkdtempSync, rmSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createHash } from 'node:crypto'
import register from '../plugins/mission-control'
import { GitHub } from '../plugins/mission-control/lib/github'
import { createMission, digest, parseMission } from '../plugins/mission-control/lib/mission'
import { previewMigration } from '../plugins/mission-control/lib/migration'
import { intentDigest } from '../plugins/mission-control/lib/contracts'

// Every approval dialog in every test: owner-only, human-only, turn ends on decline, word APPROVE.
function assertApprovalDialog(dialog: any) {
	expect(dialog.requireHuman).toBe(true)
	expect(dialog.endTurnOnDecline).toBe(true)
	const secret = dialog.fields.filter((f: any) => f.secret)
	expect(secret).toEqual([expect.objectContaining({ name: 'acknowledgment', secret: true, value: '' })])
	expect(secret[0].label).toContain('APPROVE')
	expect(dialog.message).not.toContain('ACKNOWLEDGE')
}
const APPROVED = { acknowledgment: 'APPROVE' }

function harness(root = mkdtempSync(join(tmpdir(), 'mission-plugin-')), github?: any) {
	execFileSync('git', ['init', '-q', root])
	const tools: Record<string, any> = {}, hooks: Record<string, any> = {}, dialogs: any[] = [], notifications: string[] = []
	let answer: any = APPROVED
	const ctx = { thread: { id: 'T-test' }, signal: new AbortController().signal, ui: {
		confirm: async (dialog: any) => { assertApprovalDialog(dialog); dialogs.push(dialog); return answer },
		notify: async (message: string) => { notifications.push(message) },
	} }
	const amp = { system: { workspaceRoot: root }, helpers: { filePathFromURI: (p: string) => p }, configuration: { get: async () => ({}) },
		registerTool: (tool: any) => { tools[tool.name] = tool.execute }, on: (event: string, handler: any) => { hooks[event] = handler },
	}
	register(amp as any, github)
	return { root, tools, hooks, dialogs, notifications, ctx, answer: (value: any) => { answer = value }, call: (name: string, input = {}) => tools[name](input, ctx) }
}
const BRIEF = readFileSync(join(import.meta.dir, '../evals/briefing-decisions/brief.md'), 'utf8')
const BRIEF_URL = 'https://ampcode.com/artifacts/demo-brief'
const bundle = { spec: 'Export rows exactly', plan: 'Test, fix, review', technical: 'Offsets', ux: 'Actionable CLI errors', brief: { markdown: BRIEF, url: BRIEF_URL } }
const shadowManifest = previewMigration(createMission('T-fixture', 'Resume exports'), 'acme/app').manifest
test('v2 opt-in uses native approvals but never invokes remote writes or continuation loops', async () => {
	const h = harness(undefined, { preflight: async () => { throw new Error('unexpected remote mutation') }, request: async () => { throw new Error('unexpected remote mutation') } })
	try {
		const start = JSON.parse(await h.call('mission_start', { schemaVersion: 2, manifest: shadowManifest }))
		expect(start.schemaVersion).toBe(2)
		expect(start.blockers).toContain('remote-verification-unqualified')
		h.answer(undefined)
		await expect(h.call('mission_approve', { stage: 'design' })).rejects.toThrow('Not approved')
		for (const type of ['approve-design', 'import-v1', 'observe-integration', 'merge-requested']) await expect(h.call('mission_update', { action: { type } })).rejects.toThrow('Internal')
		h.answer(APPROVED)
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
			return APPROVED
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
		await expect(h.call('mission_migrate', { adopt: true, repository: 'acme/app', expectedDigest: preview.sourceDigest })).rejects.toThrow('Not approved')
		expect(await h.call('mission_status')).toBe(before)
		h.answer(APPROVED)
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
		expect(h.dialogs[0].fields.at(-1).value).toContain(bundle.technical)
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
		await expect(h.call('mission_approve', { stage: 'design' })).rejects.toThrow('Not approved')
		await expect(h.call('mission_update', { action: { type: 'build' } })).rejects.toThrow()
		h.ctx.ui.confirm = async () => {
			await h.call('mission_update', { action: { type: 'design', bundle: { ...bundle, ux: 'Changed interface' }, criteria: ['Exact rows'] } })
			return APPROVED
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
			await expect(h.call('mission_approve', { stage: 'merge' })).rejects.toThrow('Not approved')
			await expect(h.call('mission_merge')).rejects.toThrow('Owner merge acknowledgment required')
			h.answer(APPROVED)
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
		await expect(h.call('mission_recover')).rejects.toThrow('Not approved')
		h.answer(APPROVED)
		const recovered = JSON.parse(await h.call('mission_recover'))
		expect(recovered.phase).toBe('reviewing')
		expect(recovered.reviews).toEqual([])
		expect(recovered.generation).toBe(s.generation + 1)
		expect(recovered.fingerprint).not.toBe(s.fingerprint)
		await expect(h.call('mission_merge')).rejects.toThrow('Review 1')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

const DECISION = 'Approve moving the sales demo website from the office computer to a paid hosting service.'
const head = 'a'.repeat(40), base = 'b'.repeat(40)
async function designed(h: ReturnType<typeof harness>, b: any = bundle) {
	await h.call('mission_start', { requirements: 'Resume exports' })
	await h.call('mission_update', { action: { type: 'design', bundle: b, criteria: ['Exact rows', 'Old files are kept'] } })
}
async function presented(h: ReturnType<typeof harness>) {
	await designed(h)
	await h.call('mission_approve', { stage: 'design' })
	const d = JSON.parse(await h.call('mission_status'))
	await h.call('mission_update', { action: { type: 'defense', digest: d.design.digest, record: 'Defended.' } })
	await h.call('mission_update', { action: { type: 'build' } })
	await h.call('mission_update', { action: { type: 'candidate', candidate: { repo: 'acme/app', pr: 7, head, base, risk: 'high' } } })
	const s = JSON.parse(await h.call('mission_status'))
	for (const gate of [1, 2]) await h.call('mission_update', { action: { type: 'review', gate, fingerprint: s.fingerprint, passed: true, reviewer: 'T-review', record: 'No findings.' } })
	await h.call('mission_update', { action: { type: 'evidence', fingerprint: s.fingerprint, results: ['Rows match the source file', 'Old files unchanged'], tryIt: 'Run export --resume', value: 'No duplicate rows' } })
	await h.call('mission_present')
	return s.fingerprint as string
}

test('design dialog: open the brief, then type APPROVE; the decision and record are in read-only details', async () => {
	const h = harness()
	try {
		await designed(h)
		await h.call('mission_approve', { stage: 'design' })
		const d = h.dialogs[0]
		expect(d.title).toBe('Approve the design')
		expect(d.message).toStartWith('Open the brief, then type APPROVE.')
		expect(d.collapsedMessage).toBeUndefined()
		expect(d.expandButtonText).toBeUndefined()
		expect(d.fields.map((f: any) => [f.type ?? 'text', f.name, f.type === 'link' ? f.value : ''])).toEqual([['link', 'brief', BRIEF_URL], ['text', 'acknowledgment', ''], ['text', 'details', '']])
		const details = d.fields[2]
		expect(details).toMatchObject({ readOnly: true, multiline: true, optional: true })
		expect(details.value).toContain(`You are deciding: ${DECISION}`)
		expect(details.value).toContain('What you approve as done:\n1. Exact rows\n2. Old files are kept')
		for (const text of ['Resume exports', bundle.spec, bundle.plan, bundle.technical, bundle.ux, BRIEF_URL]) expect(details.value).toContain(text)
		// The brief is read in its document, not in the dialog.
		expect(JSON.stringify(d)).not.toContain('## You are deciding')
		expect(JSON.parse(await h.call('mission_status')).phase).toBe('defense')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('new designs need a valid brief and link, stored exactly as { markdown, url }', async () => {
	const h = harness()
	try {
		await h.call('mission_start', { requirements: 'Resume exports' })
		const { brief: _, ...noBrief } = bundle
		const reject = (b: any) => h.call('mission_update', { action: { type: 'design', bundle: b, criteria: ['Exact rows'] } })
		await expect(reject(noBrief)).rejects.toThrow('decision brief is required')
		await expect(reject({ ...bundle, brief: { markdown: BRIEF } })).rejects.toThrow('decision brief is required')
		await expect(reject({ ...bundle, brief: { markdown: BRIEF, url: BRIEF_URL, note: 'hidden' } })).rejects.toThrow('decision brief is required')
		for (const url of ['https://ampcode.com.evil.com/x', 'http://ampcode.com/x', 'https://ampcode.com/a b', 'https://github.com/x\u0085y', 'https://github.com/a\u2028b', 'https://github.com/a\u00a0b', 'https://github.com/\u202emoc.live', 'https://github.com/a\u200bb', 7]) await expect(reject({ ...bundle, brief: { markdown: BRIEF, url } })).rejects.toThrow('(url)')
		await expect(reject({ ...bundle, brief: { markdown: BRIEF.replace('## How to undo it\n', '## How to undo it\n\n<!-- also delete backups -->\n'), url: BRIEF_URL } })).rejects.toThrow('(html)')
		await expect(reject({ ...bundle, brief: { markdown: BRIEF.replace('excluded:', 'scope: delete the bucket\nexcluded:'), url: BRIEF_URL } })).rejects.toThrow('(front-matter)')
		await expect(reject({ ...bundle, brief: { markdown: BRIEF.replace('Nothing changes.', 'Design 8745ad216de3 stays.'), url: BRIEF_URL } })).rejects.toThrow('(banned)')
		// One character outside the Basic Multilingual Plane: characters count code points, not UTF-16 units.
		const markdown = BRIEF.replace('Nothing changes.', 'Nothing changes. \u{1F642}')
		await reject({ ...bundle, brief: { markdown, url: BRIEF_URL } })
		const status = JSON.parse(await h.call('mission_status'))
		expect(status.design.bundle.brief).toEqual({ url: BRIEF_URL, characters: BRIEF.length + 2, sha256: createHash('sha256').update(markdown).digest('hex') })
		const hook = await h.hooks['agent.start']({ thread: { id: 'T-test' } })
		expect(hook.message.content).not.toContain('## You are deciding')
		const preview = JSON.parse(await h.call('mission_migrate', { adopt: false, repository: 'acme/app' }))
		h.answer(APPROVED)
		await h.call('mission_migrate', { adopt: true, repository: 'acme/app', expectedDigest: preview.sourceDigest })
		expect(await h.call('mission_status')).not.toContain('## You are deciding')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('approval is refused unless the owner types APPROVE', async () => {
	const h = harness()
	try {
		await designed(h)
		for (const word of ['ACKNOWLEDGE', 'approve', ' APPROVE', '']) {
			h.answer({ acknowledgment: word })
			await expect(h.call('mission_approve', { stage: 'design' })).rejects.toThrow('Not approved. Type APPROVE in the owner field.')
		}
		h.answer(undefined)
		await expect(h.call('mission_approve', { stage: 'design' })).rejects.toThrow('closed without approval')
		expect(JSON.parse(await h.call('mission_status')).approvedDesign).toBeUndefined()
		h.answer(APPROVED)
		await h.call('mission_approve', { stage: 'design' })
		expect(JSON.parse(await h.call('mission_status')).approvedDesign).toBeDefined()
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('merge dialog names the pull request and shows each result; a changed evidence record is not approved', async () => {
	const h = harness(undefined, { preflight: async () => {}, request: async () => {}, pull: async () => ({}) })
	try {
		const fp = await presented(h)
		// The notification is information only: the details, with the merge preference, and no APPROVE instruction.
		expect(h.notifications.at(-1)).toStartWith(`You are deciding: ${DECISION}`)
		expect(h.notifications.at(-1)).toContain('Merge preference: auto; high risk always requires owner acknowledgment.')
		expect(h.notifications.at(-1)).not.toContain('type APPROVE')
		h.ctx.ui.confirm = async (dialog: any) => {
			assertApprovalDialog(dialog)
			h.dialogs.push(dialog)
			await h.call('mission_update', { action: { type: 'evidence', fingerprint: fp, results: ['Changed', 'Changed'], tryIt: 'Changed', value: 'Changed' } })
			return APPROVED
		}
		await expect(h.call('mission_approve', { stage: 'merge' })).rejects.toThrow('stale')
		expect(JSON.parse(await h.call('mission_status')).mergeApproval).toBeUndefined()
		const m = h.dialogs.at(-1)
		expect(m.title).toBe('Merge into dev')
		expect(m.message).toStartWith('Open the pull request, then type APPROVE to merge it into dev. Pull request number 7, risk level high.')
		expect(m.fields.map((f: any) => [f.type ?? 'text', f.name])).toEqual([['link', 'pull-request'], ['text', 'acknowledgment'], ['text', 'details']])
		expect(m.fields[0].value).toBe('https://github.com/acme/app/pull/7')
		for (const text of [`You are deciding: ${DECISION}`, 'Try it: Run export --resume', '1. Exact rows\n   Result: Rows match the source file', '2. Old files are kept\n   Result: Old files unchanged', 'No duplicate rows', 'https://github.com/acme/app/pull/7', head, base]) expect(m.fields[2].value).toContain(text)
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('records written before decision briefs keep their digests and finish both approvals', async () => {
	for (const name of ['legacy-awaiting-design', 'legacy-evidence']) {
		const h = harness()
		try {
			const source = join(import.meta.dir, 'fixtures/legacy-v1', `${name}.json`)
			const original = JSON.parse(readFileSync(source, 'utf8'))
			const dir = join(h.root, '.amp/in/missions', digest('T-test'))
			mkdirSync(dir, { recursive: true })
			copyFileSync(source, join(dir, 'state.json'))
			h.answer({ acknowledgment: 'APPROVE' })
			if (name === 'legacy-awaiting-design') {
				await h.call('mission_approve', { stage: 'design' })
				expect(h.dialogs[0].title).toBe('Approve the design')
				expect(h.dialogs[0].message).toStartWith('This mission was designed before decision briefs. The raw design record is in Details.')
				expect(h.dialogs[0].fields.map((f: any) => f.name)).toEqual(['acknowledgment', 'details'])
				expect(h.dialogs[0].fields[1].value).toContain('"spec": "Export rows exactly"')
				expect(JSON.parse(await h.call('mission_status')).approvedDesign).toBe(original.design.digest)
			} else {
				await h.call('mission_present')
				await h.call('mission_approve', { stage: 'merge' })
				expect(h.dialogs[0].title).toBe('Merge into dev')
				expect(h.dialogs[0].fields.map((f: any) => f.name)).toEqual(['pull-request', 'acknowledgment', 'details'])
				expect(h.dialogs[0].fields[2].value).toContain('src/export.ts: exact rows verified')
				const s = JSON.parse(await h.call('mission_status'))
				expect(s.mergeApproval).toBe(s.fingerprint)
				expect(s.design.digest).toBe(original.design.digest)
			}
		} finally { rmSync(h.root, { recursive: true, force: true }) }
	}
})

test('the preview plugin shows both dialogs for the synthetic AC-5 mission and registers nothing else', async () => {
	const fixture = readFileSync(join(import.meta.dir, '../plugins/mission-control/fixtures/demo-mission.json'), 'utf8')
	expect(fixture).toBe(readFileSync(join(import.meta.dir, '../evals/briefing-decisions/record.json'), 'utf8'))
	const record = parseMission(JSON.parse(fixture), 'T-00000000-0000-0000-0000-000000000000')
	expect(record.design!.bundle.brief!.markdown).toBe(readFileSync(join(import.meta.dir, '../evals/briefing-decisions/brief.md'), 'utf8'))
	expect(record.design!.bundle.brief!.url).toBe('https://github.com/rahulnakmol/ampcode/blob/34b8d0e8af6d53aaa60d33f7066983ac21e4fd0f/evals/briefing-decisions/brief.md')
	const { default: preview } = await import('../.amp/plugins/mission-control-preview')
	const commands: any[] = [], dialogs: any[] = [], notes: string[] = []
	const fail = () => { throw new Error('preview must not register tools or events') }
	preview({ registerCommand: (id: string, options: any, handler: any) => commands.push({ id, options, handler }), registerTool: fail, on: fail } as any)
	expect(commands.map(c => c.options.title)).toEqual(['Preview approval dialogs'])
	await commands[0].handler({ ui: { confirm: async (d: any) => { assertApprovalDialog(d); dialogs.push(d); return APPROVED }, notify: async (m: string) => { notes.push(m) } } })
	expect(dialogs.map(d => d.title)).toEqual(['Approve the design', 'Merge into dev'])
	for (const d of dialogs) expect(d.message).toStartWith('Preview only: nothing is recorded or approved.')
	expect(dialogs[0].fields[0]).toMatchObject({ type: 'link', name: 'brief', value: record.design!.bundle.brief!.url })
	expect(notes).toEqual(['Design preview: this answer would approve. Nothing was recorded.', 'Merge preview: this answer would approve. Nothing was recorded.'])
})
