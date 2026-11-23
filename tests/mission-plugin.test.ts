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
import { NOT_APPROVED, UNCONFIRMED } from '../plugins/mission-control/lib/brief'
import contractText from '../plugins/mission-control/lib/contract-text.json'

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

// Schema 3 contract missions through the plugin's tools (W4). The fixture is this mission's own
// contract: 2 milestones (M2 with W1 and W3, M3 with W12), 6 open questions, 3 pre-authorized effects.
const OWNER = 'user-owner'
const CONTRACT = JSON.parse(readFileSync(join(import.meta.dir, '../plugins/mission-control/fixtures/contract-mission.json'), 'utf8'))
const REPO: string = CONTRACT.repository
const DEV = 'e'.repeat(40)
const HEAD = (pr: number) => pr.toString(16).padStart(40, 'f')
const MERGED = (pr: number) => pr.toString(16).padStart(40, 'c')
const CHILD = 'T-01a20729-43d7-73f7-be26-386150ddf086'
// The canonical stop text of the mission contract, section 8, copied exactly.
const FIVE = [
	'Change to the baseline: a criterion, scope item or design decision is wrong or conflicts, and no reading inside the contract works.',
	'Outside effect not in the contract: an irreversible or outside effect that the contract does not pre-authorize.',
	'A fact only a person holds, with no safe, reversible default.',
	'A red line: security, legal or safety.',
	'A milestone cannot meet its exit criteria after the work was re-planned and split.',
]
const NOTHING = 'No approval was recorded.'

// A fake gh for the real GitHub adapter: readiness reads, PR reads, the merge queue query and
// `pr merge`. Every merge request is recorded; loseNextMerge drops one response after sending it.
function fakeGitHub() {
	const state = {
		prs: new Map<number, { head: string; base: string; merged: boolean; queued: boolean }>(),
		merges: [] as string[][], ciPassing: true, push: true, loseNextMerge: false, during: undefined as undefined | (() => Promise<void>),
		// Rewrites each PR read, to show a different remote head or base.
		view: (pr: any) => pr,
	}
	const protection = { enforce_admins: { enabled: true }, required_pull_request_reviews: { required_approving_review_count: 0 }, required_status_checks: { strict: true, contexts: ['Extension checks'], checks: [{ context: 'Extension checks', app_id: 15368 }] } }
	const github = new GitHub(async args => {
		if (args[0] === 'pr') {
			state.merges.push(args)
			const pr = state.prs.get(Number(args[2]))!
			if (state.during) await state.during()
			if (state.loseNextMerge) { state.loseNextMerge = false; throw new Error('Response lost') }
			pr.merged = true
			return ''
		}
		const path = args[1]
		if (path === 'graphql') {
			const pr = state.prs.get(Number(args.at(-1)!.split('=')[1]))!
			return JSON.stringify({ data: { repository: { pullRequest: { isMergeQueueEnabled: false, isInMergeQueue: pr.queued, mergeQueueEntry: null } } } })
		}
		if (path === `repos/${REPO}`) return JSON.stringify({ permissions: { push: state.push } })
		if (path === `repos/${REPO}/branches/dev`) return JSON.stringify({ name: 'dev', protected: true, commit: { sha: DEV } })
		if (path === `repos/${REPO}/branches/dev/protection`) return JSON.stringify(protection)
		const runs = /^repos\/[^/]+\/[^/]+\/commits\/([a-f0-9]{40})\/check-runs/.exec(path)
		if (runs) return JSON.stringify({ total_count: 1, check_runs: [{ name: 'Extension checks', app: { id: 15368 }, head_sha: runs[1], status: 'completed', conclusion: state.ciPassing ? 'success' : 'failure' }] })
		const pull = /^repos\/[^/]+\/[^/]+\/pulls\/(\d+)$/.exec(path)
		if (pull) {
			const n = Number(pull[1]), pr = state.prs.get(n)!
			return JSON.stringify(state.view({ number: n, state: pr.merged ? 'closed' : 'open', merged: pr.merged, auto_merge: null, head: { sha: pr.head }, base: { sha: pr.base, ref: 'dev', repo: { full_name: REPO } }, merge_commit_sha: pr.merged ? MERGED(n) : null }))
		}
		throw new Error(`unexpected gh call: ${args.join(' ')}`)
	})
	return { github, state }
}

// What the fake client answers: the dialog's values (undefined when dismissed), who answered
// (null when the client cannot tell), or a failed dialog.
type Answer = { values?: Record<string, string>; responder?: string | null; failed?: boolean }
const ticked = (d: any, changes = '') => ({ ...Object.fromEntries(d.fields.filter((f: any) => f.type === 'checkbox').map((f: any) => [f.name, 'true'])), changes })
function contractHarness(github: any, root = mkdtempSync(join(tmpdir(), 'mission-contract-plugin-'))) {
	execFileSync('git', ['init', '-q', root])
	const tools: Record<string, any> = {}, hooks: Record<string, any> = {}, dialogs: any[] = []
	let answer: (dialog: any) => Answer | Promise<Answer> = d => ({ values: ticked(d) })
	const ctx = { thread: { id: 'T-test' }, signal: new AbortController().signal, ui: {
		confirm: async (dialog: any) => {
			dialogs.push(dialog)
			const a = await answer(dialog)
			if (a.failed) throw new Error('Dialog failed')
			await dialog.onAnswered?.({ responder: a.responder === null ? undefined : { userID: a.responder ?? OWNER } })
			return a.values
		},
		notify: async () => {},
	} }
	const amp = { system: { workspaceRoot: root, user: { id: OWNER, email: 'owner@example.com' } }, helpers: { filePathFromURI: (p: string) => p }, configuration: { get: async () => ({}) },
		registerTool: (tool: any) => { tools[tool.name] = tool.execute }, on: (event: string, handler: any) => { hooks[event] = handler },
	}
	register(amp as any, github)
	const call = (name: string, input: any = {}) => tools[name](input, ctx)
	return {
		root, dialogs, call, answer: (f: typeof answer) => { answer = f },
		act: (action: any) => call('mission_update', { action }),
		status: async () => JSON.parse(await call('mission_status')),
		file: () => JSON.parse(readFileSync(join(root, '.amp/in/missions', digest('T-test'), 'state.json'), 'utf8')),
	}
}
type ContractHarness = ReturnType<typeof contractHarness>
const itemsOf = (milestone: string) => CONTRACT.items.filter((i: any) => i.milestone === milestone)
const criteriaOf = (milestone: string) => [...itemsOf(milestone).flatMap((i: any) => i.done), ...CONTRACT.milestones.find((m: any) => m.id === milestone).exit]
const results = (criteria: string[]) => criteria.map(criterion => ({ criterion, result: `${criterion}: passed` }))
const fingerprintOf = async (h: ContractHarness, milestone: string) => (await h.status()).milestones.find((m: any) => m.id === milestone).fingerprint
async function kickoff(h: ContractHarness, contract = CONTRACT) {
	await h.call('mission_start', { contract })
	await h.call('mission_preflight')
	await h.call('mission_approve')
}
const STAGES = ['items', 'candidate', 'gate1', 'gate2', 'evidence'] as const
// Delegate and finish the milestone's items, then candidate, both reviews and evidence, stopping after `until`.
async function prepare(h: ContractHarness, gh: ReturnType<typeof fakeGitHub>, milestone: string, pr: number, until: typeof STAGES[number] = 'evidence') {
	for (const item of itemsOf(milestone)) {
		await h.act({ type: 'delegate', itemId: item.id, executor: { kind: 'thread', id: CHILD } })
		await h.act({ type: 'item-done', itemId: item.id, evidence: results(item.done), review: { reviewer: 'TU-item-review', record: 'No findings' } })
	}
	if (until === 'items') return
	gh.state.prs.set(pr, { head: HEAD(pr), base: DEV, merged: false, queued: false })
	await h.act({ type: 'candidate', milestoneId: milestone, pr, head: HEAD(pr), base: DEV })
	if (until === 'candidate') return
	const fp = await fingerprintOf(h, milestone)
	await h.act({ type: 'review', milestoneId: milestone, gate: 1, fingerprint: fp, passed: true, reviewer: 'TU-gate-1', record: 'No Blocker or Major inside section 6' })
	if (until === 'gate1') return
	await h.act({ type: 'review', milestoneId: milestone, gate: 2, fingerprint: fp, passed: true, reviewer: 'TU-gate-2', record: 'Second independent review; drift check clean' })
	if (until === 'gate2') return
	await h.act({ type: 'evidence', milestoneId: milestone, fingerprint: fp, results: results(criteriaOf(milestone)), humanTest: 'Ran the human tests by hand' })
}
const mergeArgs = (pr: number) => ['pr', 'merge', String(pr), '--repo', REPO, '--squash', '--match-head-commit', HEAD(pr)]

test('journey (SC1): start, preflight, approve, then 2 milestones delegated, reviewed, merged and reported: 1 dialog, 2 merges', async () => {
	const gh = fakeGitHub(), h = contractHarness(gh.github)
	try {
		await kickoff(h)
		const reports: string[] = []
		for (const [milestone, pr] of [['M2', 10], ['M3', 11]] as const) {
			await prepare(h, gh, milestone, pr)
			expect(await h.call('mission_merge', { milestoneId: milestone })).toContain('not confirmed merged')
			await h.call('mission_reconcile', { milestoneId: milestone })
			reports.push(await h.call('mission_report', { kind: 'checkpoint', milestoneId: milestone }))
		}
		expect(h.dialogs).toHaveLength(1)
		expect(h.dialogs[0].title).toBe('Approve the mission contract')
		expect(gh.state.merges).toEqual([mergeArgs(10), mergeArgs(11)])
		const s = await h.status()
		expect(s.milestones.map((m: any) => [m.id, m.status, m.mergeCommit])).toEqual([['M2', 'merged', MERGED(10)], ['M3', 'merged', MERGED(11)]])
		expect(s.approval).toMatchObject({ responder: OWNER, current: true })
		expect(reports[0]).toContain('## Checkpoint: milestone M2 merged into dev')
		expect(reports[1]).toContain('## Checkpoint: milestone M3 merged into dev')
		expect(await h.call('mission_report', { kind: 'close-out' })).toContain('## Close-out: every milestone merged into dev')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('P11: the 20 tool paths (12 mission_update actions and 8 tools) open 0 dialogs', async () => {
	const gh = fakeGitHub(), h = contractHarness(gh.github)
	const covered = new Set<string>()
	const quiet = async (path: string, name: string, input: any = {}) => {
		const before = h.dialogs.length
		const out = await h.call(name, input)
		expect(h.dialogs.length).toBe(before)
		covered.add(path)
		return out
	}
	const act = (action: any) => quiet(action.type, 'mission_update', { action })
	try {
		await quiet('mission_start', 'mission_start', { contract: CONTRACT })
		await quiet('mission_status', 'mission_status')
		await quiet('mission_preflight', 'mission_preflight')
		await h.call('mission_approve')
		expect(h.dialogs).toHaveLength(1)
		await quiet('mission_effect', 'mission_effect', { effectId: 'E3' })
		await act({ type: 'assume', question: 'Which branch name?', assumption: 'mission/m2-plugin', why: 'The contract names it' })
		const changed = structuredClone(CONTRACT)
		changed.items[2].humanTest = 'Read the guides in a browser'
		await act({ type: 'amend', contract: changed, reason: 'A clearer human test' })
		const W12 = changed.items[2]
		await act({ type: 'file', item: { ...W12, id: 'F1', title: 'Filed finding', done: ['The filed finding is fixed'], dependsOn: [] } })
		await act({ type: 'replan', itemId: 'W12', into: [{ ...W12, id: 'W12a', done: W12.done.slice(0, 2) }, { ...W12, id: 'W12b', done: W12.done.slice(2) }] })
		await act({ type: 'stop', reason: 3, question: 'Which guide comes first?', options: ['Mission control', 'Using skills'], recommendation: 'Mission control', blocks: ['M3'] })
		await act({ type: 'resume', stopId: 'S-1', answer: 'Mission control', source: 'Owner reply in the mission thread' })
		await act({ type: 'delegate', itemId: 'W1', executor: { kind: 'thread', id: CHILD } })
		for (const item of itemsOf('M2')) await act({ type: 'item-done', itemId: item.id, evidence: results(item.done), review: { reviewer: 'TU-item-review', record: 'No findings' } })
		gh.state.prs.set(10, { head: HEAD(10), base: DEV, merged: false, queued: false })
		await act({ type: 'candidate', milestoneId: 'M2', pr: 10, head: HEAD(10), base: DEV })
		const reviewed = async () => {
			const fp = await fingerprintOf(h, 'M2')
			await act({ type: 'review', milestoneId: 'M2', gate: 1, fingerprint: fp, passed: true, reviewer: 'TU-gate-1', record: 'No findings' })
			await act({ type: 'review', milestoneId: 'M2', gate: 2, fingerprint: fp, passed: true, reviewer: 'TU-gate-2', record: 'No findings' })
			await act({ type: 'evidence', milestoneId: 'M2', fingerprint: fp, results: results(criteriaOf('M2')), humanTest: 'Ran it by hand' })
		}
		await act({ type: 'review', milestoneId: 'M2', gate: 1, fingerprint: await fingerprintOf(h, 'M2'), passed: false, reviewer: 'TU-gate-1', record: 'Major inside section 6: P6' })
		await act({ type: 'disposition', milestoneId: 'M2', gate: 1, outcome: 'fixed', record: 'Fixed on the same head' })
		await reviewed()
		gh.state.loseNextMerge = true
		await expect(h.call('mission_merge', { milestoneId: 'M2' })).rejects.toThrow('Response lost')
		expect(h.dialogs).toHaveLength(1)
		covered.add('mission_merge')
		await quiet('mission_recover', 'mission_recover', { milestoneId: 'M2' })
		await reviewed()
		await quiet('mission_merge', 'mission_merge', { milestoneId: 'M2' })
		await quiet('mission_reconcile', 'mission_reconcile', { milestoneId: 'M2' })
		await quiet('mission_report', 'mission_report', { kind: 'checkpoint' })
		expect([...covered].sort()).toEqual([
			'amend', 'assume', 'candidate', 'delegate', 'disposition', 'evidence', 'file', 'item-done', 'replan', 'resume', 'review', 'stop',
			'mission_effect', 'mission_merge', 'mission_preflight', 'mission_reconcile', 'mission_recover', 'mission_report', 'mission_start', 'mission_status',
		].sort())
		expect(h.dialogs).toHaveLength(1)
		expect(gh.state.merges).toEqual([mergeArgs(10), mergeArgs(10)])
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('P1 through the tool: mission_update refuses each internal action', async () => {
	const h = contractHarness(fakeGitHub().github)
	try {
		await h.call('mission_start', { contract: CONTRACT })
		for (const type of ['approval-pending', 'approve', 'preflight', 'effect', 'merge-requested', 'merged', 'recover']) await expect(h.act({ type })).rejects.toThrow('internal action')
		expect(h.file().events).toHaveLength(1)
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('P2: a contract change while the kickoff dialog is open is stale, and nothing is recorded', async () => {
	const h = contractHarness(fakeGitHub().github)
	try {
		await h.call('mission_start', { contract: CONTRACT })
		await h.call('mission_preflight')
		h.answer(async d => {
			const changed = structuredClone(CONTRACT)
			changed.outcome = 'A different outcome.'
			await h.act({ type: 'amend', contract: changed, reason: 'The owner changed the outcome' })
			return { values: ticked(d) }
		})
		await expect(h.call('mission_approve')).rejects.toThrow('Stale')
		expect(h.dialogs).toHaveLength(1)
		const s = await h.status()
		expect(s.approval).toBeNull()
		expect(h.file().events.map((e: any) => e.action.type)).toEqual(['start', 'preflight', 'approval-pending', 'amend'])
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

// One case per merge blocker in section 3: each refusal names it, and no merge is requested.
const P6: [string, typeof STAGES[number], string, (h: ContractHarness, gh: ReturnType<typeof fakeGitHub>) => Promise<unknown>][] = [
	['kickoff approval on the current digest', 'evidence', 'Kickoff approval on the current contract required', h => h.act({ type: 'amend', contract: { ...CONTRACT, outcome: 'A different outcome.' }, reason: 'Changed outcome' })],
	['the milestone is not blocked', 'evidence', 'Blocked by stop S-1', h => h.act({ type: 'stop', reason: 4, question: 'Ship a secret?', options: ['No'], recommendation: 'No', blocks: ['W3'] })],
	['all its items are done', 'evidence', 'Items not done: W3', h => h.act({ type: 'disposition', milestoneId: 'M2', gate: 1, outcome: 'replanned', record: 'Reopened W3', itemIds: ['W3'] })],
	['earlier milestones are merged', 'evidence', 'Earlier milestones not merged: M2', async () => {}],
	['a current candidate', 'items', 'Candidate required', async () => {}],
	['gate 1 review on the fingerprint', 'candidate', 'Review 1 must pass on the current fingerprint', async () => {}],
	['gate 2 review on the fingerprint', 'gate1', 'Review 2 must pass on the current fingerprint', async () => {}],
	['evidence on the fingerprint', 'gate2', 'Evidence required on the current fingerprint', async () => {}],
	["GitHub's merge readiness", 'evidence', 'Required check not successful: Extension checks', async (_h, gh) => { gh.state.ciPassing = false }],
]
test.each(P6)('P6: a merge missing %s is refused, naming the blocker', async (name, until, blocker, perturb) => {
	const gh = fakeGitHub(), h = contractHarness(gh.github)
	try {
		await kickoff(h)
		await prepare(h, gh, 'M2', 10, until)
		await perturb(h, gh)
		const milestone = name === 'earlier milestones are merged' ? 'M3' : 'M2'
		await expect(h.call('mission_merge', { milestoneId: milestone })).rejects.toThrow(blocker)
		expect(gh.state.merges).toEqual([])
		expect((await h.status()).milestones.map((m: any) => m.status)).not.toContain('merge-pending')
		expect(h.dialogs).toHaveLength(1)
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('P8: a lost merge response is pending first, reconciled, never repeated, and recovered with no dialog only when settled and unqueued', async () => {
	const gh = fakeGitHub(), h = contractHarness(gh.github)
	try {
		await kickoff(h)
		await prepare(h, gh, 'M2', 10)
		const before = await fingerprintOf(h, 'M2')
		gh.state.during = async () => {
			// While the request is in flight, the pending state is already saved and recovery is refused.
			expect(h.file().milestones[0].status).toBe('merge-pending')
			await expect(h.call('mission_recover', { milestoneId: 'M2' })).rejects.toThrow('settled')
		}
		gh.state.loseNextMerge = true
		await expect(h.call('mission_merge', { milestoneId: 'M2' })).rejects.toThrow('Response lost')
		gh.state.during = undefined
		const again = contractHarness(gh.github, h.root)
		expect((await again.status()).milestones[0].status).toBe('merge-pending')
		await expect(again.call('mission_merge', { milestoneId: 'M2' })).rejects.toThrow('reconcile')
		expect(await again.call('mission_reconcile', { milestoneId: 'M2' })).toContain('not confirmed merged')
		// A merged PR at another head, or into another base, is not this candidate's merge.
		const pr10 = gh.state.prs.get(10)!
		pr10.merged = true
		for (const view of [(pr: any) => ({ ...pr, head: { sha: HEAD(99) } }), (pr: any) => ({ ...pr, base: { ...pr.base, ref: 'main' } }), (pr: any) => ({ ...pr, base: { ...pr.base, repo: { full_name: 'acme/fork' } } })]) {
			gh.state.view = view
			expect(await again.call('mission_reconcile', { milestoneId: 'M2' })).toContain('not confirmed merged')
		}
		gh.state.view = pr => pr
		pr10.merged = false
		expect((await again.status()).milestones[0].status).toBe('merge-pending')
		// The head moves between recovery's two reads.
		let reads = 0
		gh.state.view = pr => ++reads === 2 ? { ...pr, head: { sha: HEAD(99) } } : pr
		await expect(again.call('mission_recover', { milestoneId: 'M2' })).rejects.toThrow('Remote changed during recovery')
		gh.state.view = pr => pr
		gh.state.prs.get(10)!.queued = true
		await expect(again.call('mission_recover', { milestoneId: 'M2' })).rejects.toThrow('unqueued')
		gh.state.prs.get(10)!.queued = false
		expect(await again.call('mission_recover', { milestoneId: 'M2' })).toContain('the merge was not retried')
		const s = await again.status()
		expect(s.milestones[0]).toMatchObject({ status: 'candidate', generation: 1, reviews: [], evidence: null })
		expect(s.milestones[0].fingerprint).not.toBe(before)
		await expect(again.call('mission_merge', { milestoneId: 'M2' })).rejects.toThrow('Review 1')
		expect(gh.state.merges).toEqual([mergeArgs(10)])
		expect(h.dialogs.length + again.dialogs.length).toBe(1)
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('P9: a pre-authorized effect is recorded with no dialog; a listed one that is not pre-authorized and one not in the contract open the effect dialog', async () => {
	const gh = fakeGitHub(), h = contractHarness(gh.github)
	const contract = structuredClone(CONTRACT)
	contract.effects.push({ id: 'E4', effect: 'Promote dev to rolling', preAuthorized: false, source: 'Held by the owner until all waves are done' })
	try {
		await kickoff(h, contract)
		const digest = (await h.status()).digest
		expect(await h.call('mission_effect', { effectId: 'E1' })).toContain('no dialog')
		expect(h.dialogs).toHaveLength(1)
		h.answer(d => ({ values: { ...ticked(d), [d.fields.find((f: any) => f.type === 'checkbox').name]: 'false' } }))
		expect(await h.call('mission_effect', { effectId: 'E4' })).toBe(NOT_APPROVED)
		expect((await h.status()).performed).toHaveLength(1)
		h.answer(d => ({ values: ticked(d) }))
		await h.call('mission_effect', { effectId: 'E4' })
		await h.call('mission_effect', { effect: 'Post the release notes to the team channel', why: 'The owner asked for an announcement' })
		expect(h.dialogs.map(d => d.title)).toEqual(['Approve the mission contract', 'Approve an outside effect', 'Approve an outside effect', 'Approve an outside effect'])
		const s = await h.status()
		expect(s.performed.map((e: any) => [e.effectId ?? e.effect, e.preAuthorized, e.responder])).toEqual([
			['E1', true, undefined], ['E4', false, OWNER], ['Post the release notes to the team channel', false, OWNER],
		])
		expect(s.digest).toBe(digest)
		expect(h.file().contract).toEqual(contract)
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

const firstBox = (d: any) => d.fields.find((f: any) => f.type === 'checkbox').name
const P12: [string, (d: any) => Answer, string | undefined][] = [
	['all ticked by the owner', d => ({ values: ticked(d) }), undefined],
	['text in Changes', d => ({ values: ticked(d, 'Q5: keep v1') }), 'Not approved. The owner wrote in Changes:\nQ5: keep v1'],
	['a box unticked with Changes empty', d => ({ values: { ...ticked(d), [firstBox(d)]: 'false' } }), NOT_APPROVED],
	['no responder reported', d => ({ values: ticked(d), responder: null }), UNCONFIRMED],
	['a responder who is not the owner', d => ({ values: ticked(d), responder: 'user-other' }), NOTHING],
	['dismissed', () => ({ values: undefined }), NOTHING],
	['dismissed with no responder reported', () => ({ values: undefined, responder: null }), NOTHING],
	['failed', () => ({ failed: true }), NOTHING],
	['a non-owner who wrote text in Changes', d => ({ values: ticked(d, 'Release to main now'), responder: 'user-other' }), NOTHING],
]
test.each(P12)('P12 through the tool: kickoff answered with %s', async (_name, answer, expected) => {
	const h = contractHarness(fakeGitHub().github)
	try {
		await h.call('mission_start', { contract: CONTRACT })
		await h.call('mission_preflight')
		h.answer(answer)
		const out = await h.call('mission_approve')
		const s = await h.status()
		expect(h.dialogs).toHaveLength(1)
		if (expected === undefined) {
			expect(out).toStartWith('Kickoff approved by the owner.')
			expect(s.approval).toMatchObject({ responder: OWNER, current: true })
			expect(s.pendingApproval).toBeNull()
		} else {
			expect(out).toBe(expected)
			expect(s.approval).toBeNull()
			expect(s.pendingApproval).toMatchObject({ kind: 'kickoff', digest: s.digest })
		}
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('P15: kickoff is refused before a preflight, after a failed one, and after a baseline change since it', async () => {
	const gh = fakeGitHub(), h = contractHarness(gh.github)
	try {
		await h.call('mission_start', { contract: CONTRACT })
		await expect(h.call('mission_approve')).rejects.toThrow('run the readiness preflight on the current contract first')
		gh.state.push = false
		expect(await h.call('mission_preflight')).toContain('FAIL 1. repository visible with push permission: repository visible without push permission')
		await expect(h.call('mission_approve')).rejects.toThrow('the readiness preflight failed')
		gh.state.push = true
		await h.call('mission_preflight')
		await h.act({ type: 'amend', contract: { ...CONTRACT, outcome: 'A different outcome.' }, reason: 'Changed outcome' })
		await expect(h.call('mission_approve')).rejects.toThrow('run the readiness preflight on the current contract first')
		expect(h.dialogs).toEqual([])
		expect((await h.status()).approval).toBeNull()
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('stop text (SC6, plugin part): a refused stop reason lists the five texts from contract-text.json', async () => {
	const h = contractHarness(fakeGitHub().github)
	try {
		expect(contractText.stopReasons).toEqual(FIVE)
		await h.call('mission_start', { contract: CONTRACT })
		const error = await h.act({ type: 'stop', reason: 'Out of tokens', question: 'Continue?', options: ['Yes'], recommendation: 'Yes', blocks: ['M2'] }).catch((e: Error) => e)
		expect(error).toBeInstanceOf(Error)
		for (const [i, reason] of FIVE.entries()) expect(error.message).toContain(`${i + 1}. ${reason}`)
		expect(h.dialogs).toEqual([])
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})
