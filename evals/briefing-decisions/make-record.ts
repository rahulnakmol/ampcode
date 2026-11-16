// Regenerates record.json and plugins/mission-control/fixtures/demo-mission.json from brief.md.
// Run from the repository root: bun evals/briefing-decisions/make-record.ts
import { readFileSync, writeFileSync } from 'node:fs'
import { advance, createMission, fingerprint } from '../../plugins/mission-control/lib/mission'
const markdown = readFileSync('evals/briefing-decisions/brief.md', 'utf8')
let s = createMission('T-00000000-0000-0000-0000-000000000000', 'Keep the sales demo website available when the office computer is off, at a known monthly cost. Synthetic example; no real system.')
s = advance(s, { type: 'design', criteria: [
	'The new address opens the demo site from a phone and from a laptop outside the office.',
	'The site stays up when the office computer is off.',
	'The old address sends visitors to the new one for 30 days.',
	'The monthly bill shows 25 US dollars.',
], bundle: {
	spec: 'Move the static demo site to managed hosting; keep a 30-day redirect from the old address; no customer data.',
	plan: 'Copy the site, test the new address, switch the redirect, tell the sales team, turn off the office server after a week.',
	technical: 'Static files built by the existing script and uploaded to the host; HTTP 301 redirect on the old host for 30 days.',
	ux: 'Sales staff get the new address by email and in the team chat; no other change for visitors.',
	brief: { markdown },
} })
s = advance(s, { type: 'approve-design', digest: s.design!.digest })
s = advance(s, { type: 'defense', digest: s.design!.digest, record: 'Synthetic defense.' })
s = advance(s, { type: 'build' })
s = advance(s, { type: 'candidate', candidate: { repo: 'acme/demo-site', pr: 12, head: '1'.repeat(40), base: '2'.repeat(40), risk: 'medium' } })
const fp = fingerprint(s)
for (const gate of [1, 2]) s = advance(s, { type: 'review', gate, fingerprint: fp, passed: true, reviewer: 'synthetic reviewer', record: 'Synthetic review.' })
s = advance(s, { type: 'evidence', fingerprint: fp, results: ['Opened from a phone on mobile data and from a home laptop.', 'Office computer turned off for one hour; the site stayed up.', 'The old address returned a permanent redirect to the new one.', 'The first invoice shows 25 US dollars.'], tryIt: 'Open the new address on your phone.', value: 'Sales calls no longer fail when the office computer is off.' })
s.events.forEach(e => { e.at = '2026-11-16T00:00:00.000Z' })
const out = JSON.stringify(s, null, 2) + '\n'
writeFileSync('evals/briefing-decisions/record.json', out)
writeFileSync('plugins/mission-control/fixtures/demo-mission.json', out)
