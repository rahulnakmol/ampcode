# Mission control: workflow now, protected integration after setup

`plugins/mission-control/index.ts` coordinates the delivering skill. It is a local
workflow coordinator, **not a hosted controller, scheduler, or security sandbox**.
The repository also supplies a pure decision function for a trusted controller;
it does not supply that controller's authentication service or deployment.
Automatic merging remains blocked until those external prerequisites exist.

## The agreement

1. Start from the user's software requirements; use grilling to produce concrete
   acceptance criteria, scope, and non-goals.
2. Produce the spec, dependency-ordered plan, technical design, and crafting UX
   design where relevant. Record why UX design is inapplicable otherwise.
3. Obtain the initiating owner's acknowledgment of that exact bundle.
4. Defend it at the whiteboard, including alternatives, invariants, threats,
   failure/recovery boundaries, and the implementer's teach-back.
5. Build small outcome-driven TDD slices. Run real journeys, inspect artifacts,
   conduct two distinct review gates, repair/revalidate, and assess customer value.
6. Show what changed, where, the evidence and limitations, and how to try it.
7. Integrate into `dev` only after exact-candidate CI and policy approval.

Low/medium risk defaults to automatic merge without a response or waiting timer.
At build entry the owner can choose ask-before-merge. High risk always requires
owner acknowledgment of the final candidate; unknown risk blocks. Changing the
design reopens acknowledgment and defense; changing head/base invalidates reviews
and evidence. Changing merge preference invalidates presentation and final
acknowledgment, but preserves code-review evidence.

## Install and exercise the coordinator

Copy the **whole** `plugins/mission-control/` directory into an authorized Amp plugin
location. Source integration does not publish it to Personal Plugins. Install
`delivering`, `grilling`, and applicable `crafting` separately through their skill
destination. Do not silently install missing dependencies.

Open the dedicated Git worktree root. Start with `mission_start(requirements)`;
unrelated conversations do not become missions. The tool adds `/.amp/in/` to the
repository-local exclude file, preserving existing rules, and stores records at
`.amp/in/missions/<thread-hash>/state.json`. Do not commit these operational records.

| Tool | Purpose |
| --- | --- |
| `mission_start` | Save original requirements; begin framing |
| `mission_update` | Save design, defense, build, candidate, review, evidence, pause/resume |
| `mission_status` | Reload records, revision fingerprint and blockers |
| `mission_approve` | Owner-restricted design or final-candidate acknowledgment |
| `mission_merge_mode` | Owner-restricted auto/ask preference override |
| `mission_present` | Show the evidence packet in Amp before integration |
| `mission_merge` | Validate remote policy/CI, persist pending state, request squash auto-merge |
| `mission_reconcile` | Read remote integration state without repeating the mutation |
| `mission_recover` | Owner-acknowledged recovery of a settled, unqueued attempt; revalidate before retry |

Use actual text in the design bundle, not a mutable filename standing in for its
contents. Criteria and result entries correspond by array position. Evidence
entries must contain implementation locations, observed outcomes, commands and
artifact references, including limitations. The plugin checks lifecycle and
completeness; it does not infer whether arbitrary prose is true. Publish the
evidence on the PR as well: `mission_present` displays it in Amp, not GitHub.

The installed API cannot authenticate an arbitrary multiplayer mission initiator.
Version one requires the initiator to be the thread owner, or the owner explicitly
to adopt the mission. The confirmation has a masked `secret: true` text field
because the API documents that field as owner-only. Type **ACKNOWLEDGE**, never a
password, key, or other secret. An ordinary `requireHuman` dialog is not owner-only.
No responder ID is returned or invented. These local acknowledgments are useful
workflow records, not externally verifiable authentication receipts.

## External merge enforcement prerequisites

Provisioning these components or changing repository access requires separate
authorization. Do not enable auto-merge by merely writing configuration locally.

- A trusted controller/GitHub App outside the executor owns the mission registry,
  authenticated initiator mapping, risk decisions, approval ledger and signing/App
  credentials. The agent must not modify its code or state, possess its credential,
  or access equivalent privileged MCP operations.
- Protect `dev`, require PRs, disallow agent bypass, and require the controller's
  `mission-policy` check pinned to its App. Include all relevant CI checks, pinned
  to their source Apps, with strict up-to-date requirements and admin enforcement.
- The controller authenticates owner acknowledgment of the exact design bundle
  before defense/build, and final-candidate acknowledgment for high risk or ask
  mode. Local JSON, labels, comments asserting approval, and self-declared risk
  are not authorization. An authenticated approval service is still needed;
  the Amp dialog result alone cannot establish that external trust.
- The controller independently validates evidence, risk, two reviews and customer
  value. Use `lib/gate.ts`'s `evaluateGate` only on controller-assembled trusted
  data. It is a policy decision library, **not an HTTP endpoint accepting agent
  JSON**. Its path classifier supplies a conservative floor, not a full semantic
  security assessment.
- Authorize the exact repository, PR, design, head, base, risk, mode and recovery generation. Publish
  the successful check for that head with `external_id = binding(mission)` from
  `lib/github.ts`, computed from the controller's canonical approved record.
  The controller must revoke/recompute approvals when those identities change.
- Configure the coordinator with `mission-control.policy` containing
  `{ "appId": <trusted App's numeric ID>, "check": "mission-policy" }`.
  This config is a routing hint, not a trust root: branch protection pins the App.

The current GitHub adapter supports REST branch protection, not rulesets-only
repositories, merge queues, legacy commit-status contexts, or more than 100
check runs. It blocks unsupported/incomplete responses rather than guessing.
It refuses unpinned checks, skipped/neutral checks, review bypass allowances,
stale bindings, missing admin enforcement, and head/base motion during preflight.
GitHub must enforce the remaining race after the final read. The agent must not
have credentials able to weaken protections or force a privileged merge.

## Recovery and limits

Atomic replacement, file fsync, an exclusive lock, and stale-revision checks
protect ordinary local updates. This is not a distributed transaction or
tamper-resistant audit log. A leftover lock after process death deliberately
blocks writes: verify no writer is running, preserve state/lock evidence, and
remove only the stale lock with operator authorization. Never delete the mission
record to manufacture a clean state.

Pending state is saved **before** requesting merge. A timeout, cancellation or
restart may leave an unknown outcome. Reconcile GitHub first; never blindly issue
the mutation again. If the request never reached GitHub, the current coordinator
keeps that pending state for operator investigation rather than automatic retry.
After the owner confirms all prior senders have settled, `mission_recover` checks
an open, unmerged, unqueued PR before and after owner acknowledgment. It starts a
new recovery generation and clears reviews, evidence and merge approval without
sending another merge. Register any changed head/base and revalidate; the trusted
controller must authorize the new generation. A live queue, absent remote fields,
moving candidate or active local request blocks recovery. This does not prove
that another executor has stopped; that remains part of the owner's investigation.
A queued request is not delivery. A closed-unmerged or changed PR is not success.

Session opening exposes persisted state; it does not replay interrupted dialogs.
An active build can request at most three continuation turns, stopping on pause,
approval waits, cancellation, errors or completed integration. This does not wake
an offline runner or promise unattended completion after the continuation budget.
Use Amp's authorized exact-head CI/PR event subscriptions for follow-up; this
plugin does not provision an external daemon or subscriptions itself.

The local tools reject out-of-order transitions. They cannot prevent an agent
with unrestricted shell from editing code before approval or bypassing local
files. True isolation requires host permissions and the external merge gate.
No production-scale reliability, native cross-platform approval-dialog behavior,
or live protected-merge proof follows merely from the local test suite.

## Verification

Run `make check`. Mission tests exercise persisted lifecycle and corruption,
owner-dialog contracts with cancellation/stale updates, revision invalidation,
trusted-policy decisions, and GitHub preflight/merge behavior through controlled
transport. Amp CLI plugin loading is also part of the repository check.
Local Git/filesystem journeys are real; controlled GitHub/UI adapters are not a
live GitHub integration or a multiplayer identity test. Before activation, run
an authorized disposable protected-repository trial with the real controller,
including spoofed checks, stale approvals, changed bases, failures and recovery.

Rolling promotion, stable release, deployment, access changes and Personal
extension publication retain their own explicit gates.
