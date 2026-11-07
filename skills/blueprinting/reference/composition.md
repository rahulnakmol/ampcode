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
   from the bound helper path before making retained changes. Existing `status` checks retained
   records/pending operations only; it does not yet detect arbitrary edits to working notes.
4. Loading a domain is not a request to create a subagent or another thread. Stay in the current
   execution context unless independent review or a separately authorized task requires otherwise.
   If a domain is unavailable, report that dependency. Do not silently install/activate it.

In every reference, `scripts/engagement.py` means `<host-selected-blueprinting-base>/scripts/engagement.py`,
not `<domain-base>/scripts/engagement.py` or `<engagement-root>/scripts/engagement.py`. Use absolute
quoted paths when invoking helpers from another cwd. The same rule applies to other shared scripts.
Their current public commands and schemas are unchanged by this instruction split.
