import { expect, test } from 'bun:test'
import { assertMergeReady, binding, GitHub } from '../plugins/mission-control/lib/github'
import { createMission, advance } from '../plugins/mission-control/lib/mission'

const head = 'a'.repeat(40), base = 'b'.repeat(40)
function fixture() {
	let mission = createMission('T-fixture', 'Export safely')
	mission = advance(mission, { type: 'design', bundle: { spec: 'Exact rows', plan: 'Test then fix', technical: 'Offsets', ux: 'CLI recovery' }, criteria: ['Exact rows'] })
	mission.candidate = { repo: 'acme/app', pr: 7, head, base, risk: 'low' }
	const policy = { appId: 123, check: 'mission-policy' }
	const pr = { state: 'open', merged: false, isMergeQueueEnabled: false, isInMergeQueue: false, mergeQueueEntry: null, head: { sha: head }, base: { sha: base, ref: 'dev', repo: { full_name: 'acme/app' } } }
	const protection = { enforce_admins: { enabled: true }, required_pull_request_reviews: { bypass_pull_request_allowances: { users: [], teams: [], apps: [] } }, required_status_checks: { strict: true, contexts: ['mission-policy', 'test'], checks: [{ context: 'mission-policy', app_id: 123 }, { context: 'test', app_id: 456 }] } }
	const runs = [{ name: 'mission-policy', app: { id: 123 }, head_sha: head, status: 'completed', conclusion: 'success', external_id: binding(mission) }, { name: 'test', app: { id: 456 }, head_sha: head, status: 'completed', conclusion: 'success' }]
	return { mission, policy, pr, protection, runs }
}
test('only exact-candidate checks from required pinned apps authorize the adapter', () => {
	const f = fixture()
	expect(() => assertMergeReady(f.mission, f.policy, f.pr, f.protection, f.runs)).not.toThrow()
	for (const change of [
		{ pr: { ...f.pr, isMergeQueueEnabled: true } },
		{ pr: { ...f.pr, isInMergeQueue: true } },
		{ pr: { ...f.pr, mergeQueueEntry: { id: 'queued' } } },
		{ pr: { ...f.pr, isMergeQueueEnabled: undefined } },
		{ policy: undefined }, { protection: {} },
		{ pr: { ...f.pr, base: { ...f.pr.base, sha: 'c'.repeat(40) } } },
		{ pr: { ...f.pr, head: { sha: 'c'.repeat(40) } } },
		{ protection: { ...f.protection, enforce_admins: { enabled: false } } },
		{ protection: { ...f.protection, required_status_checks: { ...f.protection.required_status_checks, strict: false } } },
		{ runs: f.runs.map(r => ({ ...r, external_id: 'old-policy-binding' })) },
		{ runs: f.runs.map(r => ({ ...r, conclusion: 'skipped' })) },
		{ runs: f.runs.map(r => ({ ...r, app: { id: 999 } })) },
		{ runs: [...f.runs, f.runs[0]] },
	]) {
		const c = { ...f, ...change }
		expect(() => assertMergeReady(c.mission, c.policy, c.pr, c.protection, c.runs)).toThrow()
	}
	expect(binding({ ...f.mission, mode: 'ask' })).not.toBe(binding(f.mission))
})

test('adapter reads remote state before requesting exact-head squash merge', async () => {
	const f = fixture(), effects: string[][] = []
	const gh = new GitHub(async args => {
		effects.push(args)
		if (args[0] === 'pr') return ''
		const path = args[1]
		if (path === 'graphql') return JSON.stringify({ data: { repository: { pullRequest: { isMergeQueueEnabled: false, isInMergeQueue: false, mergeQueueEntry: null } } } })
		return JSON.stringify(path.includes('/protection') ? f.protection : path.includes('/check-runs') ? { total_count: 2, check_runs: f.runs } : f.pr)
	})
	await gh.preflight(f.mission, f.policy)
	await gh.request(f.mission)
	expect(effects.at(-1)).toEqual(['pr', 'merge', '7', '--repo', 'acme/app', '--auto', '--squash', '--match-head-commit', head])
	const bad = new GitHub(async () => { throw new Error('Disconnected') })
	await expect(bad.preflight(f.mission, f.policy)).rejects.toThrow('Disconnected')
})
