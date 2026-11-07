# One engagement, one shared helper implementation

The host-selected `blueprinting` skill owns shared reference contracts and scripts. Domain skills
own the current task's instructions; they do not carry copies of state schemas or helpers. Existing
references remain here for standalone coordinator use and backwards-compatible helper commands.

1. Load `blueprinting` using Amp's normal skill tool and retain its returned base directory.
   A domain entered directly must do this too. Multiple installed scopes are not ambiguity when
   the host selects one base. Missing or ambiguous resolution stops the affected action.
2. Resolve reference and script paths against that base only. Decode a returned file URI as a URI;
   do not treat percent escapes as literal path characters. Never guess a sibling, use a checkout
   fallback, or switch installations because the selected one is incompatible.
3. Keep the engagement root separate from every skill base. Require the user's explicitly selected
   root and identity; never infer a client from cwd. Read `reference/records.md`, then run status
   from the bound helper path before making retained changes. `status` checks retained records,
   pending operations and registered/declared inputs; it cannot detect unsupplied external facts.
4. Loading a domain is not a request to create a subagent or another thread. Stay in the current
   execution context unless independent review or a separately authorized task requires otherwise.
   If a domain is unavailable, report that dependency. Do not silently install/activate it.

In every reference, `scripts/engagement.py` means `<host-selected-blueprinting-base>/scripts/engagement.py`,
not `<domain-base>/scripts/engagement.py` or `<engagement-root>/scripts/engagement.py`. Use absolute
quoted paths when invoking helpers from another cwd. The same rule applies to other shared scripts.
Their current public commands and schemas are unchanged by this instruction split.

## Check compatibility before domain work

Each package carries `contract.json`. Coordinator contract/helper API 1 retains schema-1 records
and packets; it does not claim the later template, numeric-workbook or visual-packet contracts.
The coordinator manifest lists supported domain versions. A domain manifest names its version
and required coordinator contract. Templates are not bundled or declared compatible yet.

Read the selected domain's manifest and use its `requires` value; do not lower it to make a check
pass. With `BLUEPRINTING_BASE` and `DOMAIN_BASE` set to the absolute paths returned by Amp, run:

```sh
python3 "$BLUEPRINTING_BASE/scripts/contract.py" --base "$BLUEPRINTING_BASE" \
  --requires 1 --domain designing-functions --domain-base "$DOMAIN_BASE"
```

The example is for `designing-functions` version 1. Substitute the domain actually loaded and
its required contract; never resolve its directory from a sibling path. A standalone coordinator
check omits both domain flags and uses `--requires 1`. A missing checker or manifest blocks the
domain operation; an old coordinator remains usable only for its previously supported standalone
commands, not as an unverified replacement for the domain contract.

Success returns explicit bound helper paths and package versions. Retain that result in the
mission's implementation record; it is declared compatibility, not authenticated installation,
consent, acceptance or evidence that all journeys passed. Failure returns `Dependency blocked`
and no helper result; report the selected package and missing/incompatible component. Do not
search for another version, silently install, or execute a helper from a different base. Reload
and recheck after package changes. This instruction/CLI check is not a host security boundary.

## Install complete packages, then inspect the selected files

With explicit installation authority, copy each complete package directory, including its
contract.json and any scripts/reference files. Do not assume a successful installer message
means companion files arrived: the orb's Amp CLI 0.0.1794038434-gd5a1bf local-path `skill add`
copied only SKILL.md during qualification. Inspect the selected installation and run the contract
check before use. Do not repair another person's installation or publish globally implicitly.

The host may retain loaded text after local files are removed, even after reload. A remembered
base or cached skill text is not an available dependency: read the actual selected files on each
binding and stop when they are absent. Do not use cached paths to switch to a source checkout.
