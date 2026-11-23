import { expect, test } from 'bun:test'
import { execFileSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, readdirSync, rmSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import register from '../plugins/mission-control'
import { GitHub } from '../plugins/mission-control/lib/github'
import { digest } from '../plugins/mission-control/lib/mission'
import { NOT_APPROVED, UNCONFIRMED } from '../plugins/mission-control/lib/brief'
import contractText from '../plugins/mission-control/lib/contract-text.json'

// Schema 3 contract missions through the plugin's tools (W4). The fixture is adapted from this mission's
// own contract: 2 milestones (M2 with W1 and W3, M3 with W12), 6 open questions, 3 pre-authorized effects.
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
	const tools: Record<string, any> = {}, hooks: Record<string, any> = {}, commands: Record<string, any> = {}, dialogs: any[] = []
	const notes: string[] = [], posted: any[] = [], quick: any[] = []
	let answer: (dialog: any) => Answer | Promise<Answer> = d => ({ values: ticked(d) })
	// The thread's quick actions (live until unsubscribed) and the messages appended to it.
	const thread = {
		id: 'T-test',
		createQuickAction: (definition: any) => {
			const action = { definition, unsubscribe: () => { if (quick.includes(action)) quick.splice(quick.indexOf(action), 1) }, update: (d: any) => { action.definition = d } }
			quick.push(action)
			return action
		},
		appendUserMessage: async (message: any) => { posted.push(message) },
	}
	const ui = {
		confirm: async (dialog: any) => {
			dialogs.push(dialog)
			const a = await answer(dialog)
			if (a.failed) throw new Error('Dialog failed')
			await dialog.onAnswered?.({ responder: a.responder === null ? undefined : { userID: a.responder ?? OWNER } })
			return a.values
		},
		notify: async (message: string) => { notes.push(message) },
	}
	const ctx = { thread, signal: new AbortController().signal, ui }
	const amp = { system: { workspaceRoot: root, user: { id: OWNER, email: 'owner@example.com' } }, helpers: { filePathFromURI: (p: string) => p }, configuration: { get: async () => ({}) },
		registerTool: (tool: any) => { tools[tool.name] = tool.execute }, on: (event: string, handler: any) => { hooks[event] = handler },
		registerCommand: (id: string, options: any, handler: any) => { commands[id] = { options, handler } },
	}
	register(amp as any, github)
	const call = (name: string, input: any = {}, signal = ctx.signal) => tools[name](input, { ...ctx, signal })
	return {
		root, dialogs, call, answer: (f: typeof answer) => { answer = f }, commands, notes, posted, tools: () => Object.keys(tools),
		quickActions: () => quick.map(q => q.definition),
		// A command context has no abort signal.
		command: (id: string) => commands[id].handler({ thread, ui }),
		hook: (name: string) => hooks[name]({ thread: { id: 'T-test' }, message: 'Continue', id: 1, status: 'done', messages: [] }, ctx),
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
async function prepare(h: ContractHarness, gh: ReturnType<typeof fakeGitHub>, milestone: string, pr: number, until: typeof STAGES[number] = 'evidence', base = DEV) {
	for (const item of itemsOf(milestone)) {
		await h.act({ type: 'delegate', itemId: item.id, executor: { kind: 'thread', id: CHILD } })
		await h.act({ type: 'item-done', itemId: item.id, evidence: results(item.done), review: { reviewer: 'TU-item-review', record: 'No findings' } })
	}
	if (until === 'items') return
	gh.state.prs.set(pr, { head: HEAD(pr), base, merged: false, queued: false })
	await h.act({ type: 'candidate', milestoneId: milestone, pr, head: HEAD(pr), base })
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

// The stop variant: the same contract with the dev-merge effect left out.
const STOP = { ...CONTRACT, effects: CONTRACT.effects.filter((e: any) => e.kind !== 'dev-merge') }

test('journey, stop variant: without a dev-merge effect 2 milestones chain on open pull requests: 1 dialog, 0 merges, close-out', async () => {
	const gh = fakeGitHub(), h = contractHarness(gh.github)
	try {
		await kickoff(h, STOP)
		await prepare(h, gh, 'M2', 10)
		expect((await h.status()).next).toBe('Record M2 as ready with mission_merge; its pull request stays open')
		expect(await h.call('mission_merge', { milestoneId: 'M2' })).toContain('M2 is ready and was not merged')
		expect(await h.call('mission_report', { kind: 'checkpoint' })).toContain('## Checkpoint: milestone M2 ready; its pull request stays open')
		await prepare(h, gh, 'M3', 11, 'evidence', HEAD(10))
		await h.call('mission_merge', { milestoneId: 'M3' })
		expect(h.dialogs).toHaveLength(1)
		expect(gh.state.merges).toEqual([])
		const s = await h.status()
		expect(s.variant).toBe('stop')
		expect(s.milestones.map((m: any) => [m.id, m.status, m.candidate.base, m.mergeCommit])).toEqual([['M2', 'ready', DEV, null], ['M3', 'ready', HEAD(10), null]])
		expect(s.next).toBe('Every milestone is ready with its pull request left open: write the close-out report with mission_report')
		expect(await h.hook('agent.end')).toBeUndefined()
		expect(await h.call('mission_report', { kind: 'close-out' })).toContain('## Close-out: every milestone ready, pull requests left open')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('stop variant: mission_merge records nothing when the pull request would merge on its own or left the reviewed head', async () => {
	const gh = fakeGitHub(), h = contractHarness(gh.github)
	try {
		await kickoff(h, STOP)
		await prepare(h, gh, 'M2', 10)
		gh.state.view = pr => ({ ...pr, auto_merge: { merge_method: 'squash' } })
		await expect(h.call('mission_merge', { milestoneId: 'M2' })).rejects.toThrow('would merge on its own')
		gh.state.view = pr => ({ ...pr, head: { sha: HEAD(99) } })
		await expect(h.call('mission_merge', { milestoneId: 'M2' })).rejects.toThrow('no longer open on the reviewed head')
		gh.state.prs.get(10)!.queued = true; gh.state.view = pr => pr
		await expect(h.call('mission_merge', { milestoneId: 'M2' })).rejects.toThrow('would merge on its own')
		expect((await h.status()).milestones[0].status).toBe('candidate')
		gh.state.prs.get(10)!.queued = false
		expect(await h.call('mission_merge', { milestoneId: 'M2' })).toContain('M2 is ready')
		expect(gh.state.merges).toEqual([])
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

test('P2: a contract changed and changed back while the kickoff dialog is open is still stale', async () => {
	const h = contractHarness(fakeGitHub().github)
	try {
		await h.call('mission_start', { contract: CONTRACT })
		await h.call('mission_preflight')
		h.answer(async d => {
			await h.act({ type: 'amend', contract: { ...CONTRACT, outcome: 'A different outcome.' }, reason: 'Changed' })
			await h.act({ type: 'amend', contract: CONTRACT, reason: 'Changed back' })
			await h.call('mission_preflight')
			return { values: ticked(d) }
		})
		await expect(h.call('mission_approve')).rejects.toThrow('Stale')
		expect((await h.status()).approval).toBeNull()
		// A dialog opened on the restored contract approves.
		h.answer(d => ({ values: ticked(d) }))
		expect(await h.call('mission_approve')).toStartWith('Kickoff approved by the owner.')
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('P2: a second dialog opened after the change does not make the first one current', async () => {
	const h = contractHarness(fakeGitHub().github)
	const contract = structuredClone(CONTRACT)
	contract.effects.push({ id: 'E4', effect: 'Promote dev to rolling', preAuthorized: false, source: 'Held by the owner' })
	const changed = { ...contract, outcome: 'A different outcome.' }
	try {
		await h.call('mission_start', { contract })
		await h.call('mission_preflight')
		for (const [tool, input] of [['mission_approve', {}], ['mission_effect', { effectId: 'E4' }]] as const) {
			let first = true
			h.answer(async d => {
				if (!first) return { values: undefined }
				first = false
				await h.act({ type: 'amend', contract: changed, reason: 'Changed' })
				await h.act({ type: 'amend', contract, reason: 'Changed back' })
				await h.call('mission_preflight')
				expect(await h.call(tool, input)).toBe(NOTHING)
				return { values: ticked(d) }
			})
			await expect(h.call(tool, input)).rejects.toThrow('Stale')
		}
		const s = await h.status()
		expect([s.approval, s.performed]).toEqual([null, []])
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

// W5: hooks, reopen and preview.
const REOPEN_COMMAND = 'mission-reopen-approval'
const REMINDER = 'An owner approval is pending'
const NEW_EFFECT = { effect: 'Post the release notes to the team channel', why: 'The owner asked for an announcement' }
const quickAction = (kind: string) => ({ text: `Open ${kind} approval`, icon: 'check', action: 'run-command', args: { command: REOPEN_COMMAND } })
const changesPosted = (kind: string, text: string) => ({ type: 'user-message', content: `The mission owner answered the ${kind} approval dialog: not approved. The owner wrote in Changes:\n${text}` })
const startContent = async (h: ContractHarness) => (await h.hook('agent.start'))?.message?.content as string

test('P14: agent.end sends no nudge for a delegated item, every unmerged milestone blocked, kickoff pending or complete; one "continue" (at most 3 in a row) when work is ready', async () => {
	const gh = fakeGitHub(), h = contractHarness(gh.github)
	const nudges: [string, any][] = []
	const end = async (state: string) => {
		const before = h.dialogs.length
		nudges.push([state, await h.hook('agent.end')])
		expect(h.dialogs.length).toBe(before)
	}
	try {
		await h.call('mission_start', { contract: CONTRACT })
		await h.call('mission_preflight')
		await end('kickoff pending')
		h.answer(() => ({ values: undefined }))
		await h.call('mission_approve')
		await end('kickoff pending, dismissed')
		h.answer(d => ({ values: ticked(d) }))
		await h.call('mission_approve')
		await end('work ready')
		// M2 is blocked through its item W3, M3 by name.
		await h.act({ type: 'stop', reason: 3, question: 'Which guide comes first?', options: ['Mission control', 'Using skills'], recommendation: 'Mission control', blocks: ['W3', 'M3'] })
		await end('every unmerged milestone blocked')
		await h.act({ type: 'resume', stopId: 'S-1', answer: 'Mission control', source: 'Owner reply in the mission thread' })
		// One unmerged milestone (M3) is not blocked: work is ready.
		await h.act({ type: 'stop', reason: 3, question: 'Which name?', options: ['A', 'B'], recommendation: 'A', blocks: ['M2'] })
		expect(await h.hook('agent.end')).toMatchObject({ action: 'continue' })
		await h.act({ type: 'resume', stopId: 'S-2', answer: 'A', source: 'Owner reply in the mission thread' })
		await h.act({ type: 'delegate', itemId: 'W1', executor: { kind: 'thread', id: CHILD } })
		await end('an item delegated')
		for (const [milestone, pr] of [['M2', 10], ['M3', 11]] as const) {
			await prepare(h, gh, milestone, pr)
			await h.call('mission_merge', { milestoneId: milestone })
			await h.call('mission_reconcile', { milestoneId: milestone })
		}
		await end('complete')
		expect(nudges.map(([state, result]) => [state, result?.action ?? 'no nudge'])).toEqual([
			['kickoff pending', 'no nudge'], ['kickoff pending, dismissed', 'no nudge'], ['work ready', 'continue'],
			['every unmerged milestone blocked', 'no nudge'], ['an item delegated', 'no nudge'], ['complete', 'no nudge'],
		])
		expect(nudges[2][1]).toEqual({ action: 'continue', maxContinuations: 3, userMessage: expect.stringContaining('Next action: M2: Items not done: W1, W3') })
		expect(h.dialogs).toHaveLength(2)
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('P11: the 3 hook paths (session.start, agent.start, agent.end) open 0 dialogs; session.start and agent.start show the compact status and the next action', async () => {
	const h = contractHarness(fakeGitHub().github)
	const covered = new Set<string>()
	const hooks = async (next: string) => {
		const before = h.dialogs.length
		await h.hook('session.start')
		const content = await startContent(h)
		await h.hook('agent.end')
		expect(h.dialogs.length).toBe(before)
		for (const shown of [h.notes.at(-1)!, content]) {
			expect(shown).toContain(`Contract mission ${CONTRACT.missionId} on ${REPO}`)
			expect(shown).toContain('M2: ')
			expect(shown).toContain(`Next action: ${next}`)
			expect(shown).not.toContain('undefined')
			expect(shown).not.toContain('Preserve owner-approved requirements')
		}
		expect(next).toBe((await h.status()).next)
		covered.add(next)
	}
	try {
		await h.call('mission_start', { contract: CONTRACT })
		await hooks('Run mission_preflight on the current contract')
		await h.call('mission_preflight')
		await hooks('Open the kickoff approval with mission_approve')
		await h.call('mission_approve')
		await hooks('M2: Items not done: W1, W3')
		expect(covered.size).toBe(3)
		expect(h.dialogs).toHaveLength(1)
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

const REOPEN_CASES: [string, (d: any) => Answer, boolean][] = [
	['all ticked by the owner', d => ({ values: ticked(d) }), false],
	['text in Changes', d => ({ values: ticked(d, 'Q5: keep v1') }), false],
	['a box unticked with Changes empty', d => ({ values: { ...ticked(d), [firstBox(d)]: 'false' } }), false],
	['no responder reported (case 2)', d => ({ values: ticked(d), responder: null }), true],
	['a responder who is not the owner (case 3)', d => ({ values: ticked(d), responder: 'user-other' }), true],
	['a non-owner who wrote text in Changes (case 3)', d => ({ values: ticked(d, 'Release to main now'), responder: 'user-other' }), true],
	['dismissed (case 1)', () => ({ values: undefined }), true],
	['failed (case 1)', () => ({ failed: true }), true],
]
const KINDS: [string, (h: ContractHarness) => Promise<unknown>, (h: ContractHarness) => Promise<string>][] = [
	['kickoff', async h => { await h.call('mission_start', { contract: CONTRACT }); await h.call('mission_preflight') }, h => h.call('mission_approve')],
	['effect', h => kickoff(h), h => h.call('mission_effect', NEW_EFFECT)],
]
test.each(KINDS.flatMap(([kind, setup, open]) => REOPEN_CASES.map(([name, answer, reopen]) => [kind, name, setup, open, answer, reopen] as const)))('Reopen (%s answered with %s): the pending entry and the quick action exist exactly in cases 1 to 3', async (kind, _name, setup, open, answer, reopen) => {
	const h = contractHarness(fakeGitHub().github)
	try {
		await setup(h)
		h.answer(answer)
		await open(h)
		const s = await h.status()
		if (reopen) {
			expect(s.pendingApproval).toMatchObject({ kind, digest: s.digest })
			expect(h.quickActions()).toEqual([quickAction(kind)])
			expect(await startContent(h)).toContain(`${REMINDER}: the ${kind} approval dialog ended without the owner's answer`)
		} else {
			expect(h.quickActions()).toEqual([])
			expect(await startContent(h)).not.toContain(REMINDER)
		}
		expect(h.posted).toEqual([])
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test.each(KINDS)('Reopen (%s): after a dismissed dialog, the owner approves through mission-reopen-approval: recorded, the quick action is removed, nothing is posted', async (kind, setup, open) => {
	const h = contractHarness(fakeGitHub().github)
	try {
		await setup(h)
		const before = h.dialogs.length
		h.answer(() => ({ values: undefined }))
		expect(await open(h)).toBe(NOTHING)
		expect(await open(h)).toBe(NOTHING)
		// Dismissed twice: one quick action, not two.
		expect(h.quickActions()).toEqual([quickAction(kind)])
		expect(h.commands[REOPEN_COMMAND].options).toMatchObject({ title: 'Reopen mission approval' })
		h.answer(d => ({ values: ticked(d) }))
		await h.command(REOPEN_COMMAND)
		expect(h.dialogs.length).toBe(before + 3)
		expect(h.dialogs.at(-1).title).toBe(kind === 'kickoff' ? 'Approve the mission contract' : 'Approve an outside effect')
		const s = await h.status()
		if (kind === 'kickoff') expect(s.approval).toMatchObject({ responder: OWNER, current: true })
		else expect(s.performed.at(-1)).toMatchObject({ ...NEW_EFFECT, preAuthorized: false, responder: OWNER })
		expect(s.pendingApproval).toBeNull()
		expect(h.quickActions()).toEqual([])
		expect(h.posted).toEqual([])
		// The agent's next turn says once what the owner approved, and no longer reminds it.
		const next = await startContent(h)
		expect(next).not.toContain(REMINDER)
		expect(next).toContain(kind === 'kickoff' ? 'The owner approved the kickoff in the reopened approval dialog.' : `${NEW_EFFECT.effect}. Perform it now, exactly as described.`)
		expect(await startContent(h)).not.toContain('reopened approval dialog')
		if (kind === 'kickoff') expect(await h.hook('agent.end')).toMatchObject({ action: 'continue' })
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test.each(KINDS)("Reopen (%s): Changes written by the owner in the reopened dialog are posted to the thread as the owner's dialog answer; a non-owner's are not", async (kind, setup, open) => {
	const h = contractHarness(fakeGitHub().github)
	try {
		await setup(h)
		const recorded = await h.status()
		h.answer(() => ({ values: undefined }))
		await open(h)
		// Case 3 and case 2 through the command: nothing posted, the quick action stays.
		h.answer(d => ({ values: ticked(d, 'Release to main now'), responder: 'user-other' }))
		await h.command(REOPEN_COMMAND)
		h.answer(d => ({ values: ticked(d, 'Release to main now'), responder: null }))
		await h.command(REOPEN_COMMAND)
		expect(h.notes.at(-1)).toContain(UNCONFIRMED)
		expect(h.posted).toEqual([])
		expect(h.quickActions()).toEqual([quickAction(kind)])
		h.answer(d => ({ values: ticked(d, 'Use a smaller first milestone') }))
		await h.command(REOPEN_COMMAND)
		expect(h.posted).toEqual([changesPosted(kind, 'Use a smaller first milestone')])
		expect(h.quickActions()).toEqual([])
		const s = await h.status()
		expect([s.approval?.digest, s.performed]).toEqual([recorded.approval?.digest, recorded.performed])
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test.each(KINDS)('Reopen (%s): a dialog that ends because the turn was stopped still leaves the pending entry, the quick action and the reminder', async (kind, setup, open) => {
	const h = contractHarness(fakeGitHub().github)
	try {
		await setup(h)
		const stop = new AbortController()
		h.answer(() => { stop.abort(); return { failed: true } })
		const name = kind === 'kickoff' ? 'mission_approve' : 'mission_effect'
		await expect(h.call(name, kind === 'kickoff' ? {} : NEW_EFFECT, stop.signal)).rejects.toThrow()
		expect((await h.status()).pendingApproval).toMatchObject({ kind })
		expect(h.quickActions()).toEqual([quickAction(kind)])
		expect(await startContent(h)).toContain(REMINDER)
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('Reopen: an answer from a dialog the contract changed under offers no quick action and posts no Changes', async () => {
	const h = contractHarness(fakeGitHub().github)
	try {
		await h.call('mission_start', { contract: CONTRACT })
		await h.call('mission_preflight')
		h.answer(() => ({ values: undefined }))
		await h.call('mission_approve')
		let n = 0
		const amendThen = (answer: (d: any) => Answer) => async (d: any) => {
			await h.act({ type: 'amend', contract: { ...CONTRACT, outcome: `Changed outcome ${++n}.` }, reason: 'Changed outcome' })
			await h.call('mission_preflight')
			return answer(d)
		}
		h.answer(amendThen(d => ({ values: ticked(d, 'Use a smaller first milestone') })))
		await h.command(REOPEN_COMMAND)
		expect(h.posted).toEqual([])
		expect(h.notes.at(-1)).toContain('Stale')
		expect(h.quickActions()).toEqual([])
		// The same for a dismissed answer through the tool.
		h.answer(amendThen(() => ({ values: undefined })))
		await h.call('mission_approve')
		expect(h.quickActions()).toEqual([])
		expect((await h.status()).approval).toBeNull()
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('Reopen: the command opens no dialog when nothing is pending or the pending entry is stale, and then removes the quick action', async () => {
	const h = contractHarness(fakeGitHub().github)
	try {
		await h.call('mission_start', { contract: CONTRACT })
		await h.call('mission_preflight')
		await h.command(REOPEN_COMMAND)
		expect(h.dialogs).toHaveLength(0)
		expect(h.notes.at(-1)).toBe('No mission approval is pending in this thread.')
		h.answer(() => ({ values: undefined }))
		await h.call('mission_approve')
		expect(h.quickActions()).toEqual([quickAction('kickoff')])
		// A baseline change voids the pending entry.
		await h.act({ type: 'amend', contract: { ...CONTRACT, outcome: 'A different outcome.' }, reason: 'Changed outcome' })
		expect(await startContent(h)).not.toContain(REMINDER)
		await h.command(REOPEN_COMMAND)
		expect(h.dialogs).toHaveLength(1)
		expect(h.notes.at(-1)).toBe('No mission approval is pending in this thread.')
		expect(h.quickActions()).toEqual([])
		expect((await h.status()).approval).toBeNull()
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})

test('the preview plugin shows the kickoff and effect dialogs for the contract fixture, records nothing and registers nothing else', async () => {
	const path = join(import.meta.dir, '../plugins/mission-control/fixtures/contract-mission.json')
	const fixture = readFileSync(path, 'utf8')
	const { default: preview } = await import('../.amp/plugins/mission-control-preview')
	const commands: any[] = [], dialogs: any[] = [], notes: string[] = []
	const fail = () => { throw new Error('preview must not register tools or events') }
	preview({ system: { user: { id: OWNER } }, registerCommand: (id: string, options: any, handler: any) => commands.push({ id, options, handler }), registerTool: fail, on: fail } as any)
	expect(commands.map(c => [c.id, c.options.title])).toEqual([['preview-approval-dialogs', 'Preview approval dialogs']])
	const run = (answer: (d: any) => Answer) => commands[0].handler({ ui: {
		confirm: async (d: any) => {
			dialogs.push(d)
			const a = answer(d)
			await d.onAnswered?.({ responder: a.responder === null ? undefined : { userID: a.responder ?? OWNER } })
			return a.values
		},
		notify: async (m: string) => { notes.push(m) },
	} })
	await run(d => ({ values: ticked(d) }))
	expect(dialogs.map(d => d.title)).toEqual(['Approve the mission contract', 'Approve an outside effect'])
	for (const d of dialogs) {
		expect(d).toMatchObject({ requireHuman: true, endTurnOnDecline: true, confirmButtonText: 'Submit' })
		expect(d.message).toStartWith('Preview only: nothing is recorded or approved.')
		expect(d.fields[0]).toEqual({ type: 'link', name: 'brief', label: 'Open the contract brief', value: CONTRACT.brief.url })
		expect(d.fields.some((f: any) => f.secret)).toBe(false)
	}
	const boxes = (d: any) => d.fields.filter((f: any) => f.type === 'checkbox').map((f: any) => f.name)
	expect(boxes(dialogs[0])).toEqual([...CONTRACT.openQuestions.map((q: any) => `default-${q.id}`), 'effect-E1', 'effect-E2', 'effect-E3'])
	expect(boxes(dialogs[0])).toHaveLength(9)
	expect(boxes(dialogs[1])).toEqual(['effect'])
	expect(notes).toEqual(['Kickoff preview: this answer would approve. Nothing was recorded.', 'Effect preview: this answer would approve. Nothing was recorded.'])
	await run(() => ({ values: undefined }))
	expect(notes.slice(2)).toEqual([
		'Kickoff preview: no answer from the owner, so the quick action "Open kickoff approval" would appear. Nothing was recorded.',
		'Effect preview: no answer from the owner, so the quick action "Open effect approval" would appear. Nothing was recorded.',
	])
	expect(readFileSync(path, 'utf8')).toBe(fixture)
})

// P17: minimal records with the retired schemas' version keys and top-level fields (v1 single-PR flow,
// v2 shadow flow). Stored compact, unlike any current writer, so a rewrite changes the bytes.
const V1 = { version: 1, thread: 'T-test', requirements: 'Export rows exactly', phase: 'requirements', mode: 'auto', generation: 0, riskFloor: 'unknown', reviews: [], events: [{ sequence: 1, at: '2026-11-01T08:00:00.000Z', type: 'start', fingerprint: '4fe29e8e7cf8b4fad3d74b152597a87a2ac1c901f8454488ae1f5427b148f9ca' }] }
const RETIRED: Record<string, any> = {
	v1: V1,
	// A v1 merge request whose outcome was never reconciled.
	'v1 merge-pending': { ...V1, phase: 'merge-pending', riskFloor: 'low', candidate: { repo: 'acme/app', pr: 7, head: 'a'.repeat(40), base: 'b'.repeat(40), risk: 'low' } },
	v2: { schemaVersion: 2, thread: 'T-test', manifest: { schemaVersion: 2, missionId: 'M-1', repository: 'acme/app' }, intentAuthority: 'local-reported', status: 'framing', snapshots: [], units: [{ id: 'U-1', status: 'planned', riskFloor: 'unknown', attempts: [], postDelivery: [] }], closureReports: [], postReports: [], dispositions: [], events: [{ sequence: 1, action: { type: 'design', manifest: {} } }] },
}
const TOOLS = ['mission_approve', 'mission_effect', 'mission_merge', 'mission_preflight', 'mission_reconcile', 'mission_recover', 'mission_report', 'mission_start', 'mission_status', 'mission_update']
const INPUTS: Record<string, any> = {
	mission_start: { contract: CONTRACT }, mission_update: { action: { type: 'assume', question: 'Which branch?', assumption: 'dev', why: 'The default' } },
	mission_merge: { milestoneId: 'M2' }, mission_reconcile: { milestoneId: 'M2' }, mission_recover: { milestoneId: 'M2' },
	mission_effect: { effectId: 'E4' }, mission_report: { kind: 'checkpoint' },
}

test('retired (P17): every tool, hook and the reopen command report a v1 or v2 record as a retired schema, open no dialog and leave its bytes unchanged', async () => {
	for (const [schema, record] of Object.entries(RETIRED)) {
		const gh = fakeGitHub(), h = contractHarness(gh.github)
		try {
			const dir = join(h.root, '.amp/in/missions', digest('T-test')), path = join(dir, 'state.json')
			mkdirSync(dir, { recursive: true })
			writeFileSync(path, JSON.stringify(record))
			// A migrated v2 record has its v1 backup beside it; it stays untouched too.
			const backup = schema === 'v2' ? join(dir, `state.json.v1-${'c'.repeat(64)}.json`) : undefined
			if (backup) writeFileSync(backup, JSON.stringify(V1))
			const bytes = readFileSync(path), files = readdirSync(dir).sort()
			// Only v1 sent merges, so only its message points at an open pull request.
			const v1 = schema.startsWith('v1')
			const retired = new RegExp(`^Retired schema: .*\\b${v1 ? 'v1' : 'v2'}\\b.*${v1 ? 'pull request on GitHub' : 'as it was\\. To continue'}.*mission_start \\{ contract \\}`)
			expect(h.tools().sort()).toEqual(TOOLS)
			const messages: string[] = []
			for (const name of TOOLS) {
				const error = await h.call(name, INPUTS[name]).then(() => undefined, (e: Error) => e)
				expect([name, error?.message]).toEqual([name, expect.stringMatching(retired)])
				messages.push(error!.message)
			}
			// Every tool reports the same message.
			expect(new Set(messages).size).toBe(1)
			if (schema === 'v1') console.log(`Retired-schema message for a v1 record:\n${messages[0]}`)
			await h.hook('session.start')
			expect(h.notes).toEqual([messages[0]])
			expect(await h.hook('agent.start')).toEqual({ message: { content: messages[0] } })
			expect(await h.hook('agent.end')).toBeUndefined()
			await h.command('mission-reopen-approval')
			expect(h.notes).toEqual([messages[0], messages[0]])
			expect(h.dialogs).toHaveLength(0)
			expect(gh.state.merges).toHaveLength(0)
			expect(readFileSync(path).equals(bytes)).toBe(true)
			expect(readdirSync(dir).sort()).toEqual(files)
			if (backup) expect(readFileSync(backup, 'utf8')).toBe(JSON.stringify(V1))
		} finally { rmSync(h.root, { recursive: true, force: true }) }
	}
})

test('retired: mission_start starts only a contract mission; v1 requirements and a v2 manifest are refused naming contract', async () => {
	const h = contractHarness(fakeGitHub().github)
	try {
		for (const input of [{}, { requirements: 'Export rows exactly' }, { schemaVersion: 2, manifest: RETIRED.v2.manifest }, { contract: CONTRACT, requirements: 'Export rows exactly' }]) {
			await expect(h.call('mission_start', input)).rejects.toThrow('Refused (contract)')
		}
		expect(readdirSync(h.root)).toEqual(['.git'])
	} finally { rmSync(h.root, { recursive: true, force: true }) }
})
