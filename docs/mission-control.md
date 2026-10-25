# Mission control: local workflow and protected dev integration

`plugins/mission-control/index.ts` coordinates the delivering skill. It is a local
workflow coordinator, **not a scheduler or security sandbox**. It uses existing
GitHub credentials available to `gh` in the Amp execution environment. No custom
controller, GitHub App, approval service, or plugin policy configuration is needed.
Local approval/evidence gates and GitHub's required CI/protection both must pass.

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
7. Integrate into `dev` only after local gates, exact-candidate CI and branch protection pass.

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
| `mission_merge` | Validate required CI/protection, persist pending state, request immediate exact-head squash merge |
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

## GitHub prerequisites and the workflow boundary

Use the existing Amp environment's GitHub authentication through `gh`; do not
create or copy credentials into mission records or introduce an App credential.
The account needs to read PRs, branch protection and check runs, and request the
authorized merge. If that access is unavailable, report the capability gap.

- Protect `dev`, require PRs, enable strict up-to-date required checks and
  administrator enforcement, and leave PR review bypass allowances empty.
- Pin every required CI check to its actual source App in **branch protection**
  (GitHub Actions uses App ID `15368`). The adapter reads those requirements from
  GitHub, not a local policy setting or a hard-coded check name/App allowlist.
- Each required check must be completed successfully on the recorded head. The
  PR must still target the recorded `dev` base/head; preflight reads it twice.
- Keep design acknowledgment, two revision-bound reviews, acceptance evidence,
  presentation and high-risk/ask acknowledgment in the local mission workflow.
  Risk classification and evidence truth remain the implementer/reviewers'
  responsibility; the plugin validates records, not arbitrary prose or code semantics.

The user accepts local workflow enforcement, not protection from a hostile shell.
An unrestricted executor can edit local records or invoke GitHub outside these
tools; GitHub does not authenticate the local mission approvals or reviews.
Do not bypass the workflow, weaken protection, or use administrator overrides.
Configuring CI/protection or changing repository access requires separate approval
and is not performed by loading this plugin. Missing protection or failing CI
still blocks integration; no custom external service is required.

The current GitHub adapter supports REST branch protection, not rulesets-only
repositories, merge queues, legacy commit-status contexts, or more than 100
check runs. It blocks unsupported/incomplete responses rather than guessing.
It refuses unpinned checks, skipped/neutral checks, review bypass allowances,
missing admin enforcement, and head/base motion during preflight. GitHub's strict
checks and exact-head merge precondition govern the race after the final read;
local approval is not an atomic remote approval of a base that moves afterward.

Automatic mission integration does **not** enable GitHub's persistent auto-merge.
The adapter requests an immediate merge with `--match-head-commit`; if remote gates
are no longer satisfied, it fails rather than authorizing a later head. Reconcile
the result and revalidate before recovery/retry. Never add `--auto` as a shortcut.

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
sending another merge. Register any changed head/base and revalidate; renew
local acknowledgment where required for the new generation. A live queue, absent remote fields,
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
files. True isolation would require a separate security design and host permissions;
it is not the boundary promised by this coordinator.
No production-scale reliability, native cross-platform approval-dialog behavior,
or live protected-merge proof follows merely from the local test suite.

## Verification

Run `make check`. Mission tests exercise persisted lifecycle and corruption,
owner-dialog contracts with cancellation/stale updates, revision invalidation,
local risk/approval decisions, and GitHub preflight/merge behavior through controlled
transport. Amp CLI plugin loading is also part of the repository check.
Local Git/filesystem journeys are real; controlled GitHub/UI adapters are not a
live GitHub integration or a multiplayer identity test. Before activation, run
an authorized disposable protected-repository trial with existing GitHub access,
including spoofed checks, stale approvals, changed bases, failures and recovery.

Rolling promotion, stable release, deployment, access changes and Personal
extension publication retain their own explicit gates.
