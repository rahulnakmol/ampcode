import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { digest, type Mission } from './mission'

export type Policy = { appId: number; check: string }
export function binding(s: Mission) { return digest([s.thread, s.design?.digest, s.candidate, s.mode, s.generation]) }

// GitHub responses are untrusted runtime data; missing/unsupported protection
// forms fail closed. Rulesets-only repositories need a separately tested adapter.
export function assertMergeReady(s: Mission, policy: Policy | undefined, pr: any, protection: any, runs: any[]) {
	const c = s.candidate
	if (!c || !s.design || !policy || !Number.isSafeInteger(policy.appId) || policy.appId <= 0 || !policy.check?.trim()) throw new Error('Trusted policy App configuration required')
	if (pr.isMergeQueueEnabled !== false || pr.isInMergeQueue !== false || pr.mergeQueueEntry !== null) throw new Error('Merge queues or unknown queue state are unsupported')
	if (pr.state !== 'open' || pr.merged !== false || pr.head?.sha !== c.head || pr.base?.sha !== c.base || pr.base?.ref !== 'dev' || pr.base?.repo?.full_name !== c.repo) throw new Error('Remote candidate changed; revalidate before merge')
	const required = protection.required_status_checks
	const reviews = protection.required_pull_request_reviews
	if (protection.enforce_admins?.enabled !== true || required?.strict !== true || !reviews) throw new Error('Protected dev with strict checks, PRs and administrator enforcement required')
	if (Object.values(reviews.bypass_pull_request_allowances ?? {}).some(v => !Array.isArray(v) || v.length)) throw new Error('PR review bypass allowances are unsupported')
	if (!Array.isArray(required.checks) || !required.checks.length || !required.checks.some((r: any) => r.context === policy.check && r.app_id === policy.appId)) throw new Error('Required mission-policy check must be pinned to trusted App')
	if (!Array.isArray(required.contexts) || required.contexts.some((name: string) => !required.checks.some((r: any) => r.context === name))) throw new Error('Unpinned required status contexts are unsupported')
	for (const requirement of required.checks) {
		if (!Number.isSafeInteger(requirement.app_id) || requirement.app_id <= 0) throw new Error('Every required check needs a pinned source App')
		const matches = runs.filter(r => r.name === requirement.context && r.app?.id === requirement.app_id)
		if (matches.length !== 1 || matches[0].head_sha !== c.head || matches[0].status !== 'completed' || matches[0].conclusion !== 'success') throw new Error(`Required check not successful: ${requirement.context}`)
		if (requirement.context === policy.check && matches[0].external_id !== binding(s)) throw new Error('Policy authorization is stale for this mission, design, revision or merge mode')
	}
}

export class GitHub {
	constructor(private run: (args: string[]) => Promise<string> = async args => (await promisify(execFile)('gh', args, { timeout: 30_000, maxBuffer: 4 * 1024 * 1024 })).stdout) {}
	private async api(path: string) { return JSON.parse(await this.run(['api', path])) }
	async pull(s: Mission) {
		if (!s.candidate) throw new Error('Candidate required')
		const c = s.candidate, [owner, name] = c.repo.split('/')
		const pr = await this.api(`repos/${c.repo}/pulls/${c.pr}`)
		const query = 'query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){isMergeQueueEnabled isInMergeQueue mergeQueueEntry{id}}}}'
		const response = JSON.parse(await this.run(['api', 'graphql', '-f', `query=${query}`, '-f', `owner=${owner}`, '-f', `name=${name}`, '-F', `number=${c.pr}`]))
		const queue = response.data?.repository?.pullRequest
		if (response.errors || !queue || typeof queue.isMergeQueueEnabled !== 'boolean' || typeof queue.isInMergeQueue !== 'boolean' || !Object.hasOwn(queue, 'mergeQueueEntry')) throw new Error('Authoritative merge queue state unavailable')
		return { ...pr, isMergeQueueEnabled: queue.isMergeQueueEnabled, isInMergeQueue: queue.isInMergeQueue, mergeQueueEntry: queue.mergeQueueEntry }
	}
	async preflight(s: Mission, policy: Policy | undefined) {
		if (!policy) throw new Error('Trusted policy App configuration required; automatic merge is blocked')
		const c = s.candidate!
		const pr = await this.pull(s)
		const protection = await this.api(`repos/${c.repo}/branches/dev/protection`)
		const checks = await this.api(`repos/${c.repo}/commits/${c.head}/check-runs?filter=latest&per_page=100`)
		if (!Array.isArray(checks.check_runs) || checks.total_count !== checks.check_runs.length) throw new Error('Incomplete check-run response; automatic merge is blocked')
		assertMergeReady(s, policy, pr, protection, checks.check_runs)
		// Detect head/base motion during the reads. GitHub's strict required checks
		// and head precondition still govern the race after this read.
		assertMergeReady(s, policy, await this.pull(s), protection, checks.check_runs)
	}
	async request(s: Mission) {
		const c = s.candidate!
		await this.run(['pr', 'merge', String(c.pr), '--repo', c.repo, '--auto', '--squash', '--match-head-commit', c.head])
	}
}
