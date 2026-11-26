# Due work and uncertain external effects

Use this reference for deadline calculation, preparing an approved cloud handoff, or recovering
after a tool call whose outcome is unknown. The helpers do not activate a schedule or call Notion.
Routine-save permission applies only inside an explicitly configured engagement boundary.

## Retain the due instant, not a moving promise

Run `python3 scripts/upkeep.py` with schema 1 JSON on standard input:

```json
{"schema":1,"start":"2026-11-06T16:00:00+05:30","calendar":{"zone":"Asia/Kolkata","weekdays":[0,1,2,3,4],"holidays":["2026-11-09"]}}
```

The result is Tuesday 10 November at 16:00 local time, not Saturday after 24 elapsed hours.
Weekday numbers run Monday=0 through Sunday=6. Use the agreed working calendar and IANA zone.
A missing calendar is a gap, not permission to assume weekends or local time. The result records
the input calendar hash. A nonexistent local time advances to the next valid instant; an ambiguous
time uses the earlier instant with its explicit offset. If that advance crosses into a nonworking
date, calculation stops for calendar review rather than silently choosing a new deadline.

Save the start, due instant, calendar revision, owner and next action with the response obligation.
Owner or calendar changes must not silently recalculate it. Amend explicitly with authority and
reason, retaining the former due time. The decision's original age stays separate. A sent follow-up
satisfies that response obligation, not the underlying decision. Create a new response obligation
with an agreed due time, or the consultant's next-working-day check when no agreement exists.
Never relabel that check as a promised client response.

Use [obligations.md](obligations.md) for the local response scan and retained action/receipt contracts.
Bounded qualification observed two out-of-chat reminder wakes with later manual recovery, not continuous monitoring. Do not call a drafted message sent, an unassigned
action owned, or a missed run on time. Inspect every open obligation since the last observed run.
Do not hide an unresolved decision merely because its reminder was already sent.

## Journal the intent before any approved host call

For a reviewed Markdown packet, prepare an intent JSON with `id`, `packet` and `review` record
IDs, `kind` (`notion-new-page` or `native-reminder`), `content_hash` of the actual Markdown export,
named `authorized_by` and timezone-aware `authorized_at`. This is reported permission, not proof
of consent. Retain the actual authorization source. The helper checks the content hash against
the packet's current Markdown export and its recipient/destination review.

Run `engagement.py --root <engagement> external-prepare <intent.json>`. It creates a local retained
artifact with an operation marker; it sends nothing. Equivalent content/destination/kind cannot
be prepared under another ID to evade reconciliation, including pending local records.

Immediately before the one explicitly authorized host call, run `external-attempt <operation-id>`.
It saves `unknown` before the external effect. Only then call the host tool once, with the exact
approved content, destination and marker. If the process stops anywhere after that save, do not
repeat the call. `external-status <operation-id>` shows what remains known.

For Notion, create a new revision page in the approved private area. Do not overwrite human pages
or change sharing. Include the operation marker as transport metadata and keep it distinct from
the reviewed body. Poll an async task to completion, then read back the result. Read human additions
on earlier pages when reconciling them into the engagement repo; never overwrite them silently.

## Reconcile from observation, not an empty search

Retain a `source` containing observed readback, with `operation_marker`, `destination`,
`outcome: verified`, `effect_id`, `content_hash`, `checked_by`, timezone-aware `checked_at` and
precise `location`. The hash covers the reviewed content, excluding transport metadata. Record
how it was obtained. If a provider changes representation, retain the actual response and assess
the discrepancy; do not copy the expected hash into the evidence to force a pass. A different
representation/partial readback stays unresolved until a reviewed comparison method is qualified.

Pass its exact `{id, revision}` JSON file to `external-reconcile <operation-id> <evidence.json>`.
The helper requires matching identity, destination, content and a check after the attempt. A
readback source should cite the stable operation marker, not depend on a changing journal revision.
This avoids making the factual receipt stale merely because it was attached to the journal.

An absent search result is not proof no page exists. No automatic retry or cancellation is offered
for uncertain effects. Reconcile the exact operation/destination with the host or responsible
person; preserve uncertainty when the API cannot establish the outcome. Local pending record
transactions use the normal record recovery path before further external work. A verified old
effect remains historical when a source later changes; it does not authorize resending content.

Qualification included a controlled Notion human-edit simulation and bounded reminder recovery; it does not validate a production engagement's integrations. Verify the actual configured destinations and recovery behavior through authorized integration tests before relying on them. New pages, test reminders and teamspace/access setup each require
their own scope and destination approval; build permission is not production activation.
