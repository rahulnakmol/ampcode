import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import type { Mission } from './mission'

// A milestone candidate is structural, so contract code and this adapter share no import.
// The v1 Mission is still accepted until its call sites move to milestone candidates.
export type MilestoneCandidate = { repo: string; pr: number; head: string; base: string }
type Target = Mission | MilestoneCandidate
const REPO = /^[\w.-]+\/[\w.-]+$/, SHA = /^[a-f0-9]{40}$/

function candidateOf(t: Target, needDesign = false): MilestoneCandidate {
	if ('repo' in t) {
		if (typeof t.repo !== 'string' || !REPO.test(t.repo) || !Number.isSafeInteger(t.pr) || t.pr <= 0 || typeof t.head !== 'string' || !SHA.test(t.head) || typeof t.base !== 'string' || !SHA.test(t.base)) throw new Error('Invalid milestone candidate')
		return t
	}
	if (!t.candidate || (needDesign && !t.design)) throw new Error(needDesign ? 'Mission design and candidate required' : 'Candidate required')
	return t.candidate
}

// Protection and CI predicates shared by the merge check and the readiness preflight.
// Each returns the failure message, or undefined when the predicate holds.
function protectionProblem(protection: any) {
	const required = protection?.required_status_checks
	const reviews = protection?.required_pull_request_reviews
	if (protection?.enforce_admins?.enabled !== true || required?.strict !== true || !reviews) return 'Protected dev with strict checks, PRs and administrator enforcement required'
	if (Object.values(reviews.bypass_pull_request_allowances ?? {}).some(v => !Array.isArray(v) || v.length)) return 'PR review bypass allowances are unsupported'
}
function pinningProblem(required: any) {
	if (!Array.isArray(required?.checks) || !required.checks.length) return 'Required checks pinned to source Apps are required'
	if (!Array.isArray(required.contexts) || required.contexts.some((name: string) => !required.checks.some((r: any) => r.context === name))) return 'Unpinned required status contexts are unsupported'
	if (required.checks.some((r: any) => !Number.isSafeInteger(r.app_id) || r.app_id <= 0)) return 'Every required check needs a pinned source App'
}
function checksProblem(required: any, runs: any[], sha: string) {
	for (const requirement of required.checks) {
		const matches = runs.filter(r => r.name === requirement.context && r.app?.id === requirement.app_id)
		if (matches.length !== 1 || matches[0].head_sha !== sha || matches[0].status !== 'completed' || matches[0].conclusion !== 'success') return `Required check not successful: ${requirement.context}`
	}
}

// GitHub responses are untrusted runtime data; missing/unsupported protection
// forms fail closed. Rulesets-only repositories need a separately tested adapter.
export function assertMergeReady(s: Target, pr: any, protection: any, runs: any[]) {
	const c = candidateOf(s, true)
	if (pr.isMergeQueueEnabled !== false || pr.isInMergeQueue !== false || pr.mergeQueueEntry !== null) throw new Error('Merge queues or unknown queue state are unsupported')
	if (pr.state !== 'open' || pr.merged !== false || pr.head?.sha !== c.head || pr.base?.sha !== c.base || pr.base?.ref !== 'dev' || pr.base?.repo?.full_name !== c.repo) throw new Error('Remote candidate changed; revalidate before merge')
	const problem = protectionProblem(protection) ?? pinningProblem(protection.required_status_checks) ?? checksProblem(protection.required_status_checks, runs, c.head)
	if (problem) throw new Error(problem)
}

// One `gh api` read: the parsed body, or the failure with its HTTP status when gh reports one.
export type Read = { ok: true; data: any } | { ok: false; status?: number; message: string }
export type ReadinessResult = { id: number; name: string; pass: boolean; reason: string }
export type ReadinessReads = { repository: Read; branch?: Read; protection?: Read; checkRuns?: Read }
export const readinessPredicates = ['repository visible with push permission', 'dev exists', 'branch protection readable', 'protection enforced', 'required checks pinned to apps', 'dev CI successful'] as const
export const PROTECTION_FORBIDDEN = 'protection unreadable: needs a plan that supports it, or admin access'

// The readiness preflight: the protection and CI predicates of assertMergeReady, without a candidate.
// A predicate whose prerequisite failed is reported as failed and not checked (fail closed).
export function assessReadiness(reads: ReadinessReads): ReadinessResult[] {
	const out: ReadinessResult[] = []
	const record = (pass: boolean, reason: string) => { out.push({ id: out.length + 1, name: readinessPredicates[out.length], pass, reason }); return pass }
	// Records "not checked" and returns true when a prerequisite predicate failed.
	const skip = (...needs: number[]) => {
		const failed = needs.filter(n => !out[n - 1].pass)
		if (failed.length) record(false, `not checked: needs ${failed.map(n => readinessPredicates[n - 1]).join(', ')}`)
		return failed.length > 0
	}
	const { repository, branch, protection, checkRuns } = reads
	// 1. Repository visible, with push permission.
	if (!repository.ok) record(false, `repository not visible: ${repository.message}`)
	else record(repository.data?.permissions?.push === true, repository.data?.permissions?.push === true ? 'visible with push permission' : 'repository visible without push permission')
	// 2. dev exists.
	// GitHub answers a renamed branch's old name with a redirect that gh follows, so the name is checked.
	const sha = branch?.ok && branch.data?.name === 'dev' ? branch.data?.commit?.sha : undefined
	if (!skip(1)) {
		if (!branch) record(false, 'dev missing: not read')
		else if (!branch.ok) record(false, `dev missing: ${branch.message}`)
		else if (branch.data?.name !== 'dev') record(false, `dev missing: the branch read returned '${branch.data?.name}'`)
		else record(typeof sha === 'string' && SHA.test(sha), typeof sha === 'string' && SHA.test(sha) ? `dev at ${sha}` : 'dev missing: no head commit in the response')
	}
	// 3. Branch protection readable; a 403 and an absent protection are named apart.
	if (!skip(2)) {
		if (!protection) record(false, 'protection unreadable: not read')
		else if (protection.ok) record(typeof protection.data === 'object' && protection.data !== null, protection.data && typeof protection.data === 'object' ? 'protection readable' : 'protection unreadable: unexpected response')
		else if (protection.status === 403 && !/rate limit/i.test(protection.message)) record(false, PROTECTION_FORBIDDEN)
		else if (protection.status === 404 && (/not protected/i.test(protection.message) || (branch as any).data?.protected === false)) record(false, `protection absent: dev is not protected (${protection.message})`)
		else record(false, `protection unreadable: ${protection.message}`)
	}
	const rules = protection?.ok ? protection.data : undefined
	// 4. Administrators enforced, strict checks, PR reviews configured, no bypass allowances.
	if (!skip(3)) { const p = protectionProblem(rules); record(!p, p ?? 'administrators enforced, strict checks, PR reviews, no bypass allowances') }
	// 5. Every required check pinned to an app.
	if (!skip(3)) { const p = pinningProblem(rules.required_status_checks); record(!p, p ?? `pinned: ${rules.required_status_checks.checks.map((r: any) => `${r.context} (app ${r.app_id})`).join(', ')}`) }
	// 6. The latest dev commit has every required check completed with success.
	if (!skip(2, 3, 5)) {
		const runs = checkRuns?.ok ? checkRuns.data : undefined
		if (!checkRuns) record(false, 'check runs not read')
		else if (!checkRuns.ok) record(false, `check runs unreadable: ${checkRuns.message}`)
		else if (!Array.isArray(runs?.check_runs) || runs.total_count !== runs.check_runs.length) record(false, 'Incomplete check-run response')
		else { const p = checksProblem(rules.required_status_checks, runs.check_runs, sha); record(!p, p ?? `every required check succeeded on ${sha}`) }
	}
	return out
}

export class GitHub {
	constructor(private run: (args: string[]) => Promise<string> = async args => (await promisify(execFile)('gh', args, { timeout: 30_000, maxBuffer: 4 * 1024 * 1024 })).stdout) {}
	private async api(path: string) { return JSON.parse(await this.run(['api', path])) }
	private async read(path: string): Promise<Read> {
		try { return { ok: true, data: await this.api(path) } } catch (e) {
			const text = e instanceof Error ? e.message : String(e)
			const line = text.split('\n').map(l => l.trim()).find(l => l.startsWith('gh: '))?.slice(4) ?? text.trim().split('\n')[0]
			const status = Number(/\(HTTP (\d{3})\)/.exec(line)?.[1])
			return Number.isInteger(status) ? { ok: false, status, message: line } : { ok: false, message: line }
		}
	}
	// Read-only readiness preflight for a repository; reads only what the next predicate needs.
	async readiness(repo: string): Promise<ReadinessResult[]> {
		if (typeof repo !== 'string' || !REPO.test(repo)) return assessReadiness({ repository: { ok: false, message: 'invalid repository name' } })
		const reads: ReadinessReads = { repository: await this.read(`repos/${repo}`) }
		if (reads.repository.ok) reads.branch = await this.read(`repos/${repo}/branches/dev`)
		if (reads.branch?.ok) reads.protection = await this.read(`repos/${repo}/branches/dev/protection`)
		const sha = reads.branch?.ok ? reads.branch.data?.commit?.sha : undefined
		if (reads.protection?.ok && typeof sha === 'string' && SHA.test(sha)) reads.checkRuns = await this.read(`repos/${repo}/commits/${sha}/check-runs?filter=latest&per_page=100`)
		return assessReadiness(reads)
	}
	async pull(s: Target) {
		const c = candidateOf(s), [owner, name] = c.repo.split('/')
		const pr = await this.api(`repos/${c.repo}/pulls/${c.pr}`)
		const query = 'query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){isMergeQueueEnabled isInMergeQueue mergeQueueEntry{id}}}}'
		const response = JSON.parse(await this.run(['api', 'graphql', '-f', `query=${query}`, '-f', `owner=${owner}`, '-f', `name=${name}`, '-F', `number=${c.pr}`]))
		const queue = response.data?.repository?.pullRequest
		if (response.errors || !queue || typeof queue.isMergeQueueEnabled !== 'boolean' || typeof queue.isInMergeQueue !== 'boolean' || !Object.hasOwn(queue, 'mergeQueueEntry')) throw new Error('Authoritative merge queue state unavailable')
		return { ...pr, isMergeQueueEnabled: queue.isMergeQueueEnabled, isInMergeQueue: queue.isInMergeQueue, mergeQueueEntry: queue.mergeQueueEntry }
	}
	async preflight(s: Target) {
		const c = candidateOf(s)
		const pr = await this.pull(s)
		const protection = await this.api(`repos/${c.repo}/branches/dev/protection`)
		const checks = await this.api(`repos/${c.repo}/commits/${c.head}/check-runs?filter=latest&per_page=100`)
		if (!Array.isArray(checks.check_runs) || checks.total_count !== checks.check_runs.length) throw new Error('Incomplete check-run response; automatic merge is blocked')
		assertMergeReady(s, pr, protection, checks.check_runs)
		// Detect head/base motion during the reads. GitHub's strict required checks
		// and head precondition still govern the race after this read.
		assertMergeReady(s, await this.pull(s), protection, checks.check_runs)
	}
	async request(s: Target) {
		const c = candidateOf(s)
		// Automatic workflow, not persistent GitHub auto-merge authorization:
		// an unmet remote gate must not authorize a future, unreviewed head.
		await this.run(['pr', 'merge', String(c.pr), '--repo', c.repo, '--squash', '--match-head-commit', c.head])
	}
}
