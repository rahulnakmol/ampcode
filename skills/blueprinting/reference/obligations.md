# Response work and recovery scans

Run `engagement.py --root <engagement> obligations --at <offset-aware-time>
--cadence-seconds <configured-interval> [--last-check <record-id>]` on every authorized check.
This reads every retained decision and response obligation, not only recent items. It sends
nothing and changes no records. A zero exit code means the scan ran; read `gaps`, `decisions`,
`obligations`, `pending_operations` and `recovery` before relying on it.

Use the existing prepare/commit protocol to retain the records below. Every exact `{id, revision}`
reference must also be an input edge. Structured fields validate reported evidence; the consultant
must check actual authority, message meaning and readback. No helper grants permission to contact
a client or activate a schedule.

## A decision is not its next response

Keep `first_raised`, `question` and the business `scope` on the first open `decision` revision. The scan preserves that original
time even after a later follow-up or owner transfer. Missing original time remains a gap. Business
closure requires the existing current `baseline` check. A bare `accepted` or `withdrawn` label is
not closure. To withdraw an open question, retain a **separate** decision with `intent: withdraw`
and the written confirmation/authority fields from [decisions.md](decisions.md). Its exact `target`
is the open decision, not a requirement; its scope must match. Both decision and client confirmation
must say `intent: withdraw`. Keep the original open record and age intact. The withdrawal review
time must follow the original question and the written confirmation, and not be in the future.

The scan reports qualified `withdrawals`, marks their questions and current matching responses
`withdrawn`, and withholds new reminder work. Due times remain visible; `late_seconds` measures
time until the reported withdrawal review, or the earlier qualifying sent response when present.
Unknown sends and pending operations still require reconciliation. Stale withdrawal evidence
reopens current qualification without erasing its history. A response created after the withdrawal,
or one with unresolved data/amendment gaps, stays visible for review rather than being suppressed.
This does not accept a business baseline, exclude a requirement, undo a previously accepted business
decision, delete history or prove client authorship. Those are different decisions and reviews.

Retain an `artifact` with `purpose: response-obligation` for each action due:

| Field | Meaning |
| --- | --- |
| `decision` | Exact decision reference; not just a free-text title. |
| `owner` | Named response owner, or null for an explicit unassigned gap. |
| `start`, `due` | Stored ISO instants with offsets. A transfer never silently resets these. |
| `calendar` | Exact source reference whose `data.calendar` has zone, weekdays and holidays. |
| `due_basis` | `next-working-day` or `agreed`. Use the deadline calculator for the former. |
| `next_action` | Specific action that could unblock the decision. |
| `agreement` | For `agreed`, exact source with outcome `agreed`, matching decision/owner/due, `agreed_by`, `at` and evidence `location`. |
| `follows` | For a follow-up's next response, exact response-action reference. |

At the exact due instant the response is pending/due; after it, it is overdue. The original due time
and lateness stay visible. Missing, stale, pending and unassigned work must not disappear from the
consultant's view. A source change can make a previously recorded action unusable for current
qualification without erasing the historical receipt.

## Record delivery only after observing it

A `review` for a follow-up has purpose `followup`, status `approved`, exact `obligation`, SHA-256
`content_hash`, exact `destination`, named `reviewer` and offset-aware `at`. Retain the reviewed
message and evidence location in its body; the hash does not prove that its question is useful.

A sent `source` receipt has outcome `sent`, matching `content_hash` and `destination`, `sent_at`,
`checked_at`, `checked_by`, provider `effect_id` and readback `location`. A draft, acknowledgment or
empty search is not a receipt. Review must precede sending; readback must follow sending.

An `artifact` response action has purpose `response-action`, state `sent`, and exact `obligation`,
`review` and `receipt` references. The scan marks the response `action-recorded`, preserving any
lateness. It does not resolve the decision. Retain a new owned response obligation whose `follows`
points to that action and whose `start` is the actual send time. Use an agreed due time, or the
consultant's next-working-day check; do not describe that fallback as a promised client response.
A missing next response remains a gap.

## Make deadline and owner amendments explicit

Before revising a response, retain a `review` with purpose `obligation-amendment`, status `approved`,
`previous_revision` equal to the former obligation hash, named `reviewer`, offset-aware `at`,
`reason` and `changes_hash`. Compute the latter using the record helper's canonical JSON SHA-256
over these keys, using null for absent values:

`decision`, `owner`, `start`, `due`, `calendar`, `due_basis`, `next_action`, `follows`, `agreement`.

The revised obligation references that review as `amendment`. Its predecessor remains immutable.
The amendment binds a prior hash rather than depending on a superseded record's currentness.
An unreviewed change leaves the last qualified fields visible, with an amendment gap. An agreed
extension still needs its agreement source; amendment review alone does not create a client promise.
Correct a rejected revision by appending a reviewed revision against the last effective hash.
Historical failures remain in `rejected_amendments`; they need not prevent a qualified repair.

## Do not mistake reminder deduplication for resolution

The scan returns a `reminder_marker` for the exact obligation revision and stage (`upcoming`,
`due`, `overdue`). It is a deduplication key, not permission or a suggested notification time.
Apply the engagement's approved cadence and early-warning policy before a host call.

Retain a `source` with purpose `reminder-receipt`, exact `obligation`, `marker`, `stage`, outcome
`sent` or `unknown`, `checked_by`, `checked_at` and `location`; `sent` also needs `effect_id`.
A matching sent stage is reported as recorded, but the overdue decision remains in the report.
An unknown outcome requires reconciliation even when the deadline progresses to another stage.
Changing the receipt's label or replacing it with a draft does not clear that uncertainty. Append
matching sent readback on the same receipt ID with `reconciles` listing the unknown revision hashes.
Retain the same obligation, marker and stage, provider effect ID, checker, location and a later
check time. Until that evidence qualifies, `notification: reconcile` takes precedence. Pending
local operations also block notification eligibility until local recovery is complete.
Historical delivery reconciliation retains the original obligation reference even after an owner
transfer. That one historical edge need not remain current; other readback dependencies must.
A reconciled old marker never counts as delivery for an amended obligation's new marker.
Use the external-effect journal before authorized host calls; never infer retry permission from
a scan. Neither source hashes nor reported receipts establish host-side idempotency.

After inspecting a successful scan, retain an `artifact` check with purpose `obligation-check`,
outcome `observed`, actual `checked_at`, and the report/snapshot in its body. Supply that record on
the next check. Recovery reports elapsed seconds and scheduled intervals strictly missed before
the current scan. Without a prior observation, coverage is unknown. Do not claim a later successful
run made earlier missed checks timely. Persist actual effect IDs and reconcile unknown effects.

This local protocol is not a scheduled service. Live out-of-chat timing, native delivery, outage
recovery and destination privacy still require authorized platform tests. It does not qualify
R14 by itself.
