# Threat model file format

A threat model is one JSON file. `scripts/threat_check.py check` reads it and checks rules M1 to
M12; `render` prints it as Markdown tables. [example.json](example.json) is a complete model of
the tenant integration path of the order export from `architecting`'s filled example: a flow in
each direction for every contract (requests F1, responses with the signed link F6, the event F2
and F7, the file F3 to F5). The Web UI consumer is listed under `not_examined`. It passes.

## Fields

| Field | Holds | Required |
| --- | --- | --- |
| `name` | What is modelled, in a few words | yes |
| `scope` | The design path and revision, repository or service, and what the model covers | yes |
| `standard` | The standard reviewed against: `OWASP ASVS 4.0.3` | yes |
| `summary` | Counts and labels: what was found, what ran, what was not examined | no |
| `zones` | Trust zones: `{id, name}` | yes |
| `elements` | Actors, processes, stores and external systems: `{id, name, kind, zone, entry_point}` | yes |
| `flows` | Data flows: `{id, from, to, data, personal_data, stride, linddun}` | yes |
| `threats` | `{id, title, disposition, ...}`, see Dispositions | yes |
| `abuse_cases` | `{id, actor, goal, how, threats}` | yes |
| `review` | Standard requirements reviewed: `{ref, result, evidence, reason, threats}` | yes |
| `not_examined` | What the model does not cover, one line each | no |

- **Zones and boundaries.** Put each element in one trust zone. A flow whose two ends sit in
  different zones crosses a trust boundary. `render` lists each crossing as a boundary.
- **kind:** `actor`, `process`, `store` or `external`.
- **entry_point:** `true` for an element that accepts input from a less trusted zone.
  `scanning-vulnerabilities` reads entry points to judge reachability.
- **personal_data:** `true` or `false` on every flow. Say `true` when the flow carries data about
  an identified or identifiable person.
- **stride** and **linddun:** an object with one key per category (see
  [stride.md](stride.md) and [linddun.md](linddun.md)). Each value is a list of threat IDs, or the
  text `n/a: <reason>`. A flow inside one zone may also carry `stride`, for example where the
  receiver acts on what the flow says (F7 in the example); the check then applies M3 to it.
- **Responses are flows.** Model each direction of a contract that carries something of value: a
  response with a token or a signed link is its own flow (F6 in the example).

## Dispositions

Every threat ends in one of three dispositions.

| `disposition` | Also needs | Optional |
| --- | --- | --- |
| `mitigate` | `mitigation` (the control, starting with `Existing (<source>):` or `Planned:`) and `verification` (the test or check that proves it: kind, tool, where, when) | `evidence`: the run that proved it. Without it, `render` says "not run" |
| `accept` | `owner` (a named person, not a team or role) and `reason` | `accepted`: where the owner accepted in writing. Without it, `render` says "acceptance not recorded" |
| `backlog` | `item`: the backlog or tracker ID, such as `B-12`, `S-4`, `SEC-431` or `#88` | |

A threat may also list `asvs` references. `grooming` backlog IDs (`B-n` for a bug, `S-n` for a
story) fit `item`.

## Standard review

`review` lists the requirements of the standard that apply, each with a `result`:

| `result` | Needs |
| --- | --- |
| `met` | `evidence` a reader can check: a test run, a file, a configuration |
| `gap` | `threats`: the threats whose dispositions close the gap |
| `not applicable` | `reason` |
| `not examined` | nothing; `render` lists it under "Not examined" |

A planned mitigation whose verification has not run is a `gap` that names its threat, not `met`.

## Rules

| Rule | Fails when |
| --- | --- |
| M1 | The file is not a JSON object; `name` or `scope` is empty; `zones`, `elements`, `flows` or `threats` is missing or empty; an ID is missing or repeated; an element `kind` is unknown; a flow has no `data` or no `personal_data` true or false; `not_examined` is present but not a list of texts |
| M2 | A flow starts or ends at an unknown element, or an element sits in an unknown zone |
| M3 | A boundary-crossing flow, or a flow inside one zone that carries `stride`, lacks one of the six STRIDE categories; a value is not a non-empty list of known threat IDs or `n/a: <reason>`; or an `n/a` reason says "not examined" or "unexamined" (any case) and names no threat ID of the model |
| M4 | A personal-data flow lacks one of the seven LINDDUN categories, with the same value rules |
| M5 | A threat has no disposition, or one other than `mitigate`, `accept` or `backlog` |
| M6 | An accepted risk has no named owner, or no reason. The owner fails when it is empty or a placeholder. Otherwise the check reads only the name, the text before the first "(" or ",". The name fails when it is a word such as "owner", "security", "someone" or "we"; holds any of the words team, group, department, squad, function or role (case-insensitive, plural too); starts with TBD, TODO, TBC or unknown; or is only a `<...>` placeholder. Role text after the name is free unless it is only a team word (team, group, department, squad or function, plural too): "Priya Shah (Head of Platform)", "Dana Reyes (Platform Group lead)", "Kim Lee, Security Department head" and "Dana Reyes <dana@example.com>" pass; "Platform team (Dana Reyes)", "Finance (team)" and "IT, department" fail. A bare role such as "CISO" passes the check: the reviewer catches it |
| M7 | A backlog disposition has no item ID of the form `ABC-12` or `#12` |
| M8 | A mitigation has no `mitigation` text or no `verification`, or its `mitigation` does not start with `Existing (<source>):` (a non-empty source) or `Planned:` followed by text |
| M9 | `standard` is missing or unknown, or a reference is not in the standard's form: for ASVS 4.0.3, `V<chapter>.<section>.<requirement>` with chapter 1 to 14 (for example `V2.1.1`) |
| M10 | There is no abuse case, or one lacks an actor, a goal or known threats |
| M11 | `review` is empty, a row breaks the result rules above, or a threat's `asvs` reference has no `review` row (any result covers it) |
| M12 | Text that `render` prints claims what no evidence shows. The check reads `name`, `scope`, `summary`, zone and element names, flow `data`, each `n/a` reason, a threat's `title`, `mitigation`, `verification` and `reason`, an abuse case's `actor`, `goal` and `how`, a review row's `reason`, and each `not_examined` line. Evidence records (a threat's `evidence` and `accepted`, a review row's `evidence`) are not read. Claim words: "secure", "secured", "securely", "no vulnerabilities", "no known vulnerabilities", "zero vulnerabilities", "vulnerability-free" or "vulnerability free", "risk-free" or "risk free", or "verified" (any case). Write a control or attribute name in backticks (`` `Secure` ``): backticks are the only way to name one, and the check skips backtick spans in every field. Quoted text ("...", “...”, '...') is read in every field, including a threat's `title`, `mitigation` and `verification`, as the model's own words ("Overall result: 'secure'." and "The export path is then 'secure'." fail). A quote is skipped only right after a verb that names a third party's words: calls it, claims, claimed, says, said, states, stated (the vendor "calls it 'secure by design'"), and not when the model's author is the subject: the check reads back to the start of the clause, and I, we, us, my, the or this model, threat model, review, assessment, author or team, or "our" before review, model, threat model, assessment or team, keeps the quote read ("Our review says "secure and verified"." and "This model states "no known vulnerabilities"." fail; "Our vendor says 'secure by design'" is a third party's words and passes); "called" is not one, because the model could use it about itself ("The model is called 'secure'" fails). "marked" and "labelled" are not such verbs ("Model status: marked "secure"." fails). Not claims: the exact word "secure" before shell, cookie, flag, attribute, boot, file transfer, socket or enclave ("Secure Shell", "secure-cookie", "Secure Boot", "secure file transfer"; "secured channel" and "secure elements" fail); the cookie attribute named in a list ("the Secure and HttpOnly flags", "the Secure, HttpOnly and SameSite=Strict attributes"); in a threat's `title`, `mitigation` and `verification`, "verified" right before with, against, using or by and then a means within three words (HMAC, HMAC-SHA256, SHA-256, Ed25519, signature, checksum, key, test, CI, scan or similar, or a tool's version or file such as "semgrep 1.85" or testssl.sh; a bare vendor or standard name such as AWS or SOC2 is not a means) and no team word in the rest of the clause, or right before signature, token, hash, checksum, certificate, signer, input, request or payload, after at most a determiner ("is verified with HMAC-SHA256", "verified against the old key", "verified the signature", "only verified tokens"). Any other "verified" is a claim, as is one after "fully" or "all" ("the system is verified end to end", "Verified by the security team", "verified by AWS", "verified one way or another", "accepted as verified", "fully verified with HMAC"); and "no vulnerability" followed by scan, scanning, scanner, test, database, data or feed ("No vulnerability scan ran"). An honest negation just before the word passes: "not" or "never" with at most one word between, except only, just or merely ("Not secure yet: 3 gaps", "not yet verified", "Never verified"; "not only secure" fails); "nothing" with at most two words between ("Nothing here is secure"); and "cannot be called" ("Cannot be called secure") |

A placeholder is empty text, `TBD`, `TODO`, `TBC`, `n/a`, `none`, `later`, `-`, `?`, `<...>`,
`not relevant`, `not applicable`, `irrelevant`, `handled elsewhere` or `does not apply`, with or
without a final full stop. So `n/a: not relevant` and `n/a: none` fail M3 and M4.

A value of the wrong type where an ID is expected (a list or an object as a flow end, a zone or a
threat ID) fails the rule for that field with one line, like any unknown ID.

The check proves the model is complete and consistent. It cannot prove that the threat list is
complete, that a control works, or that a verification ran.
