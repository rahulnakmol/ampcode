---
name: threat-modelling
description: "Builds a threat model as one JSON file: a data-flow model of actors, processes, stores and trust zones, STRIDE on every flow that crosses a trust boundary, LINDDUN on every flow with personal data, abuse cases, and a review against a named standard (OWASP ASVS 4.0.3). Every threat ends in a mitigation with a verification, an accepted risk with a named owner, or a backlog item with an ID. A standard-library checker enforces the rules and renders the model as Markdown tables. Use when a design's trust boundaries change (architecting links the result), when asked to threat model a system, feature, service or design, to run STRIDE or LINDDUN, to list abuse cases, or for the threat-model step of a security-review, software-delivery or product-assessment mission. Not for drawing diagrams, running scanners (use scanning-vulnerabilities), reviewing a diff (use interrogating-changes), or designing the system (use architecting)."
---

# Threat modelling

A threat model says what can go wrong where trust changes hands, and what happens about each
threat. This skill builds one from a design or a running system, in one JSON file that
`scripts/threat_check.py` checks and renders. The check proves the model is complete and
consistent. It does not prove the system resists attack.

## When to use it

- **Input:** a design (from `architecting`: its Context, Containers and Contracts sections), or a
  scope for a running system: a repository, a service, an environment, at a named revision.
  Read the material before you ask what it already answers.
- **Callers:** `architecting`, when a design says `Trust boundaries change: yes`; the
  `missioning` playbooks for security review (step 3, build the threat model), software delivery
  and product assessment. `scanning-vulnerabilities` reads the model's entry points to judge
  reachability. Read-only callers may load this skill; see "Without a shell".
- **Output:** `<name>.json`, checked, and `<name>.md`, rendered from it. Write both where the
  design's `Threat model:` line points (for example `docs/threat-models/order-export.md` and
  `docs/threat-models/order-export.json`). Without such a line, write them beside the design or
  where the caller says. The design links the `.md` file.

## 1. Draw the data flows

Write the model in the format of [reference/model.md](reference/model.md). Start from
[reference/example.json](reference/example.json).

1. **Zones:** one per trust level: the public internet, the application network, a database
   subnet, a managed service, a partner. Two parts with different owners or credentials are in
   different zones.
2. **Elements:** every actor, process, store and external system from the design's Context and
   Containers. Put each in one zone. Mark each element that accepts input from a less trusted
   zone as an `entry_point`.
3. **Flows:** every data flow from the Contracts, one direction each. A response that carries a
   token or a signed link is a flow of its own, and so is each hop of an event (producer to
   queue, queue to consumer). Say what data it carries and whether it carries personal data. A
   flow between zones crosses a trust boundary.

## 2. Find the threats

1. **STRIDE** on every boundary-crossing flow: all six categories, each with threat IDs or
   `n/a: <reason>`. Questions and controls: [reference/stride.md](reference/stride.md).
2. **LINDDUN** on every personal-data flow, crossing or not: all seven categories, the same way.
   See [reference/linddun.md](reference/linddun.md).
3. **Abuse cases:** at least one per motivated actor: who, what they want, how they try, and the
   threats they exercise. Abuse cases find threats that category lists miss, such as a former
   employee with a kept secret.

One threat can sit on several flows. Give it one ID and list it under each.

## 3. End every threat

| Disposition | Write | It counts only with |
| --- | --- | --- |
| `mitigate` | The control | A verification: the test or check, the tool, where and when. Add `evidence` only after it ran |
| `accept` | Why the risk is acceptable | A named person as owner. Add `accepted` only when that person accepted in writing |
| `backlog` | What remains to do | A backlog item ID from `grooming` (`B-12`) or the tracker (`SEC-431`) |

Start each `mitigation` with `Existing (<source>):` or `Planned:`. `Existing` needs the source
that states the control: a design section, a file, a configuration. A control you propose is
`Planned`, even when you write it in the present tense. The check fails a mitigation without
either (M8). When the system is not built yet, write `Existing (<design section>, not built):`, or
say in `summary` that no control is in place.

When the backlog item does not exist yet, give it the next free ID in the backlog's scheme and
list it in the handoff as proposed, not filed, until `grooming` or the tracker holds it.

Never accept a risk on the owner's behalf. Propose it, name the owner, and leave `accepted`
empty until they confirm in writing. In a mission, the acceptance is a human gate that
`missioning` records.

## 4. Review against the standard

Name the standard in `standard` and list the requirements that apply in `review`. See
[reference/asvs.md](reference/asvs.md) for the reference form, the chapters and the levels. A
requirement is `met` only with evidence a reader can check; a planned control is a `gap` that
names its threat. List what you did not review as `not examined`. Never quote a requirement
text you have not read in the source.

## 5. Check and render

```bash
python3 scripts/threat_check.py check docs/threat-models/order-export.json
python3 scripts/threat_check.py render docs/threat-models/order-export.json > docs/threat-models/order-export.md
```

`check` prints `pass` and exits 0, or prints one line per broken rule (M1 to M12) and exits 1.
`render` refuses a model that fails. Fix the model, not the rule. Re-render after every change,
so the Markdown never differs from the JSON.

Then have the model reviewed with `goldfishing`, critic lens: the reviewer gets the model, the
design and its sources, and checks for a missing flow, a weak `n/a` reason and a control whose
verification would not prove it. Repair and recheck as `goldfishing` says. Trust boundaries are
a high-risk gate there. At the round cap, follow the calling contract's disposition policy
(fixed, replanned or filed). Without a contract, the owner decides, as `goldfishing` says.

## Without a shell

When you have no shell (for example in a read-only subagent, or on a chat-only host), do not
run or simulate the check. Return the model JSON for the caller to save at a path it approves,
and give the exact commands with that path (or a placeholder when you do not know it):

```bash
python3 /path/to/skills/threat-modelling/scripts/threat_check.py check docs/threat-models/order-export.json
python3 /path/to/skills/threat-modelling/scripts/threat_check.py render docs/threat-models/order-export.json > docs/threat-models/order-export.md
```

Label the check `threat_check.py: not run`. You may read the model against M1 to M12 by hand,
but report that as a manual reading, never as a pass. Do not start the `goldfishing` review
either: record it as "not run" and give the caller the review to run.

## Hand it over

Give the caller the model path and revision, the check result (or "not run"), the counts by
disposition, the open backlog items, the risks waiting for written acceptance, and what was not
examined. `architecting` puts the `.md` path on its `Threat model:` line.

This skill writes only the model files. It never writes to a tracker, publishes a report or
changes the system. Backlog items go to `grooming`; a tracker write through `syncing`, or a report
release, runs only when the mission contract pre-authorizes that exact effect, or the owner
approves the exact plan (its digest). Outside a contract mission, the owner approves the exact
plan.

## Common rationalizations

| Excuse | Answer |
| --- | --- |
| "It is an internal flow, so STRIDE does not apply." | Check the zones. If the ends have different owners or credentials, it crosses a boundary |
| "Repudiation is n/a everywhere." | Ask who could deny the action and what would prove it. Write that reason, or a threat |
| "The data is only an email address." | An email address identifies a person. Mark the flow personal and run LINDDUN |
| "The team owns this risk." | A team cannot accept a risk. Name the person who does |
| "We will fix it later." | Then it is a backlog item with an ID, not a free-text promise |
| "The control is standard, it needs no test." | A mitigation without a verification fails the check (M8) |
| "The check passed, so the system is safe." | The check proves the model's form. Tests, scans and reviews prove the controls |
| "I have no shell, so I checked it in my head." | Give the exact command and label the check "not run" |

## Red flags

- A flow between two zones with `n/a` in most STRIDE categories and thin reasons.
- An `n/a` reason that depends on a bound or control the sources do not state, or that is only
  planned.
- Personal data on a flow marked `personal_data: false`.
- An accepted risk whose owner is a role, a team or the author, or an `accepted` field filled
  before the owner confirmed.
- A `met` review row whose evidence is a plan, not a run.
- "Secure" (or "secured", "securely"), "no known vulnerabilities", "zero vulnerabilities",
  "vulnerability free", "risk-free" or "verified" in the model or the handoff. M12 fails them
  in any text the rendered report prints, except evidence records, unless a negation comes just
  before ("not verified", "Never verified", "Not secure yet: 3 gaps"; "not only secure" still
  fails). "Secure Shell", "Secure Boot", "the Secure flag" and "No vulnerability scan ran" are
  not claims. Write a control name in backticks (`` `Secure` ``): the check skips only backtick
  spans. Quotes do not hide a claim in any field; only a third party's words pass, right after
  "calls it", "claims", "says" or "states", and not when the author says them ("I", "we", "my
  review", "our assessment", "this threat model", "the author"). In a mitigation, "verified with
  HMAC" or "verified by semgrep 1.85" passes; "verified by AWS" and "the system is verified" fail.
- A claim inside backticks or a third party's quote. Backticks are an escape for names, not
  proof: the reviewer reads backticked text and quotes for hidden claims.
- Threat IDs renumbered after a backlog item, a test or a brief cites them.

## Adapt it

- **Another standard or ASVS version:** add its name and reference form to `STANDARDS` in
  `scripts/threat_check.py`, describe it in `reference/asvs.md` (or a new reference file), and add
  a test case.
- **Category lists:** `STRIDE` and `LINDDUN` in the script must match the keys in
  `reference/stride.md` and `reference/linddun.md`; a test compares them.
- **Item IDs:** change `ITEM_ID` in the script and the Dispositions table in
  `reference/model.md` together.
- **Overclaim words:** change `OVERCLAIM` in the script and rule M12 in `reference/model.md`.

## Check your work

- `threat_check.py check` prints `pass` on the model in this session, or the handoff says "not
  run" with the exact command.
- The rendered `.md` was produced from the current JSON.
- Every boundary-crossing flow has six STRIDE entries; every personal-data flow has seven
  LINDDUN entries; every `n/a` has a real reason.
- Every threat is mitigated with a verification, accepted by a named person, or a backlog item
  with an ID. Unrun verifications say "not run"; unconfirmed acceptances say "not recorded".
- The review names the standard, cites only requirements read in the source, and lists what was
  not examined.
- A fresh reviewer read the model, or the review is recorded as not run.
