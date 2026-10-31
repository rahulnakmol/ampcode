import { expect, test } from 'bun:test'
import { assertMergeReady, GitHub } from '../plugins/mission-control/lib/github'
import { createMission, advance } from '../plugins/mission-control/lib/mission'

const head = 'a'.repeat(40), base = 'b'.repeat(40)
function fixture() {
	let mission = createMission('T-fixture', 'Export safely')
	mission = advance(mission, { type: 'design', bundle: { spec: 'Exact rows', plan: 'Test then fix', technical: 'Offsets', ux: 'CLI recovery' }, criteria: ['Exact rows'] })
	mission.candidate = { repo: 'acme/app', pr: 7, head, base, risk: 'low' }
	const pr = { state: 'open', merged: false, isMergeQueueEnabled: false, isInMergeQueue: false, mergeQueueEntry: null, head: { sha: head }, base: { sha: base, ref: 'dev', repo: { full_name: 'acme/app' } } }
	const protection = { enforce_admins: { enabled: true }, required_pull_request_reviews: { bypass_pull_request_allowances: { users: [], teams: [], apps: [] } }, required_status_checks: { strict: true, contexts: ['test'], checks: [{ context: 'test', app_id: 15368 }] } }
	const runs = [{ name: 'test', app: { id: 15368 }, head_sha: head, status: 'completed', conclusion: 'success' }]
	return { mission, pr, protection, runs }
}
test('only exact-candidate checks from required pinned apps authorize the adapter', () => {
	const f = fixture()
	expect(() => assertMergeReady(f.mission, f.pr, f.protection, f.runs)).not.toThrow()
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
		expect(() => assertMergeReady(c.mission, c.pr, c.protection, c.runs)).toThrow()
	}
})

test('adapter reads remote state before requesting exact-head squash merge', async () => {
	const f = fixture(), effects: string[][] = []
	const gh = new GitHub(async args => {
		effects.push(args)
		if (args[0] === 'pr') return ''
		const path = args[1]
		if (path === 'graphql') return JSON.stringify({ data: { repository: { pullRequest: { isMergeQueueEnabled: false, isInMergeQueue: false, mergeQueueEntry: null } } } })
		return JSON.stringify(path.includes('/protection') ? f.protection : path.includes('/check-runs') ? { total_count: 1, check_runs: f.runs } : f.pr)
	})
	await gh.preflight(f.mission)
	await gh.request(f.mission)
	expect(effects.at(-1)).toEqual(['pr', 'merge', '7', '--repo', 'acme/app', '--squash', '--match-head-commit', head])
	const bad = new GitHub(async () => { throw new Error('Disconnected') })
	await expect(bad.preflight(f.mission)).rejects.toThrow('Disconnected')
})

test('unready mutation fails without leaving deferred authorization for a later head', async () => {
	let deferred = false
	const gh = new GitHub(async args => {
		if (args.includes('--auto')) { deferred = true; return '' }
		throw new Error('Required conversation unresolved')
	})
	await expect(gh.request(fixture().mission)).rejects.toThrow('Required conversation unresolved')
	expect(deferred).toBe(false)
})
