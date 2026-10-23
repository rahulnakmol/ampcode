# Edge-case lenses

Use this catalog during the edge-case sweep in `SKILL.md`. It is a prompt for your thinking, not a
form to fill in. Pick the lenses that fit the task, generate concrete scenarios, and drop every
lens that does not apply. Ten sharp scenarios beat fifty generic ones.

## How to write an edge case

Each edge case names a specific actor, input, or state and what happens next:

- Weak: "Handle errors."
- Strong: "The payment provider times out after charging the card. The order stays `pending`, the
  user retries, and is charged twice."

Score each one quickly:

| Field | Values |
| --- | --- |
| Severity | 1 cosmetic · 2 degraded · 3 broken feature or wrong result · 4 data loss, security, money, safety, or legal exposure |
| Likelihood | rare · possible · likely |
| Detectability | obvious · noticed later · silent (for plans and events: noticed early · late · never) |

Silent, severe cases come first even when rare. Then recommend one handling:

- **Handle**: build the correct behavior; it becomes an acceptance criterion.
- **Guard**: reject or validate early with a clear message.
- **Degrade**: fall back to a safe reduced behavior.
- **Defer**: explicitly out of scope for now; record it as a non-goal.
- **Accept**: a known, documented risk with a revisit trigger.

## Thinking techniques

- **Pre-mortem.** "It is three months after launch and this failed badly. What happened?" List the
  three to five most plausible causes before walking the lenses.
- **Inversion.** "How would I guarantee this fails?" Then check the plan prevents each move.
- **Boundary walk.** For every quantity: zero, one, many, the maximum, one past the maximum.
- **Actor swap.** Replay the main flow as a new user, a power user, an admin, an attacker, an
  automated client, and the on-call engineer at 3 a.m.
- **Time travel.** Replay it at first run, after a year of data, mid-migration, during an outage,
  across a time zone or daylight-saving change, and after rollback.
- **Success too well.** What breaks at ten or a hundred times the expected use?
- **Second order.** Who or what else is affected that nobody mentioned?

## Lenses

### Premise and scope

- Is this the right problem, or a proposed solution to an unstated problem? Ask why until the
  underlying outcome is clear.
- What happens if we do nothing? Is there a smaller change or an existing tool that solves it?
- Which neighbouring problems will people assume are included?

### Inputs and boundaries

- Empty, missing, null, zero, negative, one, maximum, maximum plus one, enormous.
- Wrong type or format, extra fields, duplicates, ordering differences.
- Unicode, emoji, right-to-left text, whitespace, case, very long strings, file names with spaces.
- Dates and times: time zones, daylight saving, leap days, end of month, clock skew.
- Money and numbers: rounding, currency, precision, locale formats.
- Untrusted content: injection payloads, oversized uploads, malicious files.

### State and lifecycle

- First run and empty states; partially completed work; resumption after interruption.
- Retries and idempotency: the same request twice, a timeout after success.
- Concurrency: two actors editing at once, races, ordering, stale reads, locks that never release.
- Cancellation, undo, and deletion while something still references the item.
- Long-lived state: expiry, cleanup, growth without bound.

### Failures and dependencies

- A dependency is slow, down, rate-limited, returns errors, or silently changes its contract.
- Partial failure: step two of three fails. What is left behind, and who cleans it up?
- Crash mid-write, disk full, out of memory, lost connection, offline clients.
- Retry storms, thundering herds, cascading failure.

### Scale, performance, and cost

- Ten and a hundred times the expected volume; one unusually large item; long-tail users.
- Pagination, batching, cold starts, cache misses, timeouts.
- Cost growth: per-request spend, storage, third-party fees, model tokens.

### Security, privacy, and abuse

- Authentication and authorization: wrong tenant, another user's ID, privilege escalation,
  expired or revoked sessions.
- STRIDE prompt: spoofing, tampering, repudiation, information disclosure, denial of service,
  elevation of privilege.
- Secrets handling, logging of sensitive data, audit trail.
- Abuse: spam, scraping, enumeration, automated misuse, cost-exhaustion attacks.
- Personal data: consent, retention, deletion requests, residency.

### Data and migration

- Existing data that violates the new rules; backfill strategy and duration.
- Forward and backward compatibility while old and new versions run together.
- Rollback after new-format data has been written.
- Backups, restore, and verification that nothing was lost.

### Compatibility and integration

- Old clients, cached assets, existing API consumers, saved links, scripts that parse output.
- Platforms: browsers, operating systems, devices, screen sizes, architectures.
- Differences between local, CI, staging, and production configuration.

### People and experience

- First-time user, expert, someone in a hurry, someone who misunderstands the feature.
- Accessibility: keyboard, screen readers, contrast, motion, captions.
- Internationalization: translation length, plural rules, local formats.
- Error messages: does the user know what happened and what to do next?
- Conflicting expectations between two kinds of users or stakeholders.

### Operations and rollout

- Deploy order across services; feature flags; gradual rollout; kill switch.
- How we notice failure: metrics, alerts, logs, user reports.
- Rollback path and its cost; runbook; who is on call.
- Support load and documentation for whoever answers questions.

### AI and agent work

- Nondeterministic or confidently wrong output; how correctness is checked.
- Prompt injection through retrieved content, files, or tool results.
- Tool failures, partial tool results, rate limits, context overflow, token budget.
- Irreversible actions that need a human approval gate.
- An evaluation set that would catch a regression.

### Non-software plans

Use for events, processes, business, content, research, or personal plans.

- A key person, approval, vendor, or budget is unavailable or late.
- Timeline slips; what is the minimum that still delivers value?
- Unclear ownership or decision rights; stakeholders who disagree.
- Legal, contractual, regulatory, or reputational exposure.
- Communication: who must know what, and when.
- The plan succeeds beyond expectations and capacity runs out.
