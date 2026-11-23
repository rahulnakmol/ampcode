import { expect, test } from 'bun:test'
import { assertMergeReady, GitHub, type MilestoneCandidate } from '../plugins/mission-control/lib/github'
import { createMission, advance } from '../plugins/mission-control/lib/mission'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const brief = { markdown: readFileSync(join(import.meta.dir, '../evals/briefing-decisions/brief.md'), 'utf8'), url: 'https://ampcode.com/artifacts/demo-brief' }

const head = 'a'.repeat(40), base = 'b'.repeat(40)
function fixture() {
	let mission = createMission('T-fixture', 'Export safely')
	mission = advance(mission, { type: 'design', bundle: { spec: 'Exact rows', plan: 'Test then fix', technical: 'Offsets', ux: 'CLI recovery', brief }, criteria: ['Exact rows'] })
	mission.candidate = { repo: 'acme/app', pr: 7, head, base, risk: 'low' }
	const pr = { state: 'open', merged: false, isMergeQueueEnabled: false, isInMergeQueue: false, mergeQueueEntry: null, head: { sha: head }, base: { sha: base, ref: 'dev', repo: { full_name: 'acme/app' } } }
	const protection = { enforce_admins: { enabled: true }, required_pull_request_reviews: { bypass_pull_request_allowances: { users: [], teams: [], apps: [] } }, required_status_checks: { strict: true, contexts: ['test'], checks: [{ context: 'test', app_id: 15368 }] } }
	const runs = [{ name: 'test', app: { id: 15368 }, head_sha: head, status: 'completed', conclusion: 'success' }]
	// A milestone candidate is the structural type { repo, pr, head, base }; the v1 Mission stays supported.
	const candidate: MilestoneCandidate = { repo: 'acme/app', pr: 7, head, base }
	return { mission, candidate, pr, protection, runs }
}
const targets = { mission: (f: ReturnType<typeof fixture>) => f.mission, candidate: (f: ReturnType<typeof fixture>) => f.candidate }

for (const [kind, target] of Object.entries(targets)) {
test(`only exact-candidate checks from required pinned apps authorize the adapter (${kind})`, () => {
	const f = fixture()
	expect(() => assertMergeReady(target(f), f.pr, f.protection, f.runs)).not.toThrow()
	for (const change of [
		{ pr: { ...f.pr, isMergeQueueEnabled: true } },
		{ pr: { ...f.pr, isInMergeQueue: true } },
		{ pr: { ...f.pr, mergeQueueEntry: { id: 'queued' } } },
		{ pr: { ...f.pr, isMergeQueueEnabled: undefined } },
		{ protection: {} },
		{ pr: { ...f.pr, base: { ...f.pr.base, sha: 'c'.repeat(40) } } },
		{ pr: { ...f.pr, head: { sha: 'c'.repeat(40) } } },
		{ protection: { ...f.protection, enforce_admins: { enabled: false } } },
		{ protection: { ...f.protection, required_status_checks: { ...f.protection.required_status_checks, strict: false } } },
		{ protection: { ...f.protection, required_status_checks: { strict: true, contexts: [], checks: [] } } },
		{ protection: { ...f.protection, required_status_checks: { strict: true, contexts: ['legacy'], checks: f.protection.required_status_checks.checks } } },
		{ protection: { ...f.protection, required_status_checks: { strict: true, contexts: ['test'], checks: [{ context: 'test', app_id: -1 }] } } },
		{ protection: { ...f.protection, required_pull_request_reviews: null } },
		{ protection: { ...f.protection, required_pull_request_reviews: { bypass_pull_request_allowances: { users: [{}] } } } },
		{ runs: [] },
		{ runs: f.runs.map(r => ({ ...r, head_sha: 'c'.repeat(40) })) },
		{ runs: f.runs.map(r => ({ ...r, status: 'in_progress' })) },
		{ runs: f.runs.map(r => ({ ...r, conclusion: 'skipped' })) },
		{ runs: f.runs.map(r => ({ ...r, conclusion: 'failure' })) },
		{ runs: f.runs.map(r => ({ ...r, app: { id: 999 } })) },
		{ runs: [...f.runs, f.runs[0]] },
	]) {
		const c = { ...f, ...change }
		expect(() => assertMergeReady(target(c), c.pr, c.protection, c.runs)).toThrow()
	}
})

test(`adapter reads remote state before requesting exact-head squash merge (${kind})`, async () => {
	const f = fixture(), effects: string[][] = []
	const gh = new GitHub(async args => {
		effects.push(args)
		if (args[0] === 'pr') return ''
		const path = args[1]
		if (path === 'graphql') return JSON.stringify({ data: { repository: { pullRequest: { isMergeQueueEnabled: false, isInMergeQueue: false, mergeQueueEntry: null } } } })
		return JSON.stringify(path.includes('/protection') ? f.protection : path.includes('/check-runs') ? { total_count: 1, check_runs: f.runs } : f.pr)
	})
	await gh.preflight(target(f))
	await gh.request(target(f))
	expect(effects.at(-1)).toEqual(['pr', 'merge', '7', '--repo', 'acme/app', '--squash', '--match-head-commit', head])
	const bad = new GitHub(async () => { throw new Error('Disconnected') })
	await expect(bad.preflight(target(f))).rejects.toThrow('Disconnected')
})

test(`unready mutation fails without leaving deferred authorization for a later head (${kind})`, async () => {
	let deferred = false
	const gh = new GitHub(async args => {
		if (args.includes('--auto')) { deferred = true; return '' }
		throw new Error('Required conversation unresolved')
	})
	await expect(gh.request(target(fixture()))).rejects.toThrow('Required conversation unresolved')
	expect(deferred).toBe(false)
})
}

// Readiness preflight (contract section 3): six named predicates, checked without a candidate.
const devSha = 'd'.repeat(40)
const httpError = (status: number, message: string) => new Error(`Command failed: gh api\ngh: ${message} (HTTP ${status})\n`)
function remote() {
	return {
		'repos/acme/app': { full_name: 'acme/app', permissions: { admin: false, push: true, pull: true } } as any,
		'repos/acme/app/branches/dev': { name: 'dev', protected: true, commit: { sha: devSha } } as any,
		'repos/acme/app/branches/dev/protection': fixture().protection as any,
		[`repos/acme/app/commits/${devSha}/check-runs?filter=latest&per_page=100`]: { total_count: 1, check_runs: [{ name: 'test', app: { id: 15368 }, head_sha: devSha, status: 'completed', conclusion: 'success' }] } as any,
	}
}
function fakeGh(responses: Record<string, any>) {
	return new GitHub(async args => {
		const response = args[0] === 'api' ? responses[args[1]] : undefined
		if (response instanceof Error) throw response
		if (response === undefined) throw httpError(404, 'Not Found')
		return JSON.stringify(response)
	})
}
const predicates = ['repository visible with push permission', 'dev exists', 'branch protection readable', 'protection enforced', 'required checks pinned to apps', 'dev CI successful']

test('readiness passes all six named predicates on a ready repository', async () => {
	const results = await fakeGh(remote()).readiness('acme/app')
	expect(results.map(r => r.name)).toEqual(predicates)
	for (const r of results) expect(r).toMatchObject({ pass: true, reason: expect.any(String) })
})

for (const [label, change, failing, reason, passing] of [
	['1: no push permission', (r: any) => { r['repos/acme/app'].permissions.push = false }, 1, /push permission/, []],
	['2: dev missing', (r: any) => { r['repos/acme/app/branches/dev'] = httpError(404, 'Branch not found') }, 2, /dev missing: Branch not found \(HTTP 404\)/, [1]],
	['3: protection forbidden (403)', (r: any) => { r['repos/acme/app/branches/dev/protection'] = httpError(403, 'Upgrade to GitHub Pro or make this repository public to enable this feature.') }, 3, /^protection unreadable: needs a plan that supports it, or admin access$/, [1, 2]],
	['3: protection absent', (r: any) => { r['repos/acme/app/branches/dev'].protected = false; r['repos/acme/app/branches/dev/protection'] = httpError(404, 'Branch not protected') }, 3, /^protection absent/, [1, 2]],
	['4: administrators not enforced', (r: any) => { r['repos/acme/app/branches/dev/protection'].enforce_admins.enabled = false }, 4, /administrator enforcement/, [1, 2, 3, 5, 6]],
	['5: required check not pinned', (r: any) => { delete r['repos/acme/app/branches/dev/protection'].required_status_checks.checks[0].app_id }, 5, /pinned source App/, [1, 2, 3, 4]],
	['6: latest dev commit check failed', (r: any) => { r[`repos/acme/app/commits/${devSha}/check-runs?filter=latest&per_page=100`].check_runs[0].conclusion = 'failure' }, 6, /Required check not successful: test/, [1, 2, 3, 4, 5]],
] as const) {
	test(`readiness names predicate ${label}`, async () => {
		const responses = remote()
		change(responses)
		const results = await fakeGh(responses).readiness('acme/app')
		expect(results.map(r => r.name)).toEqual(predicates)
		expect(results[failing - 1].pass).toBe(false)
		expect(results[failing - 1].reason).toMatch(reason)
		results.forEach((r, i) => {
			if ((passing as readonly number[]).includes(i + 1)) expect(r.pass).toBe(true)
			else expect(r.pass).toBe(false)
		})
	})
}
