# Written client decisions

Run `python3 scripts/engagement.py --root <engagement-directory> baseline <decision-id>` before
describing a business baseline as agreed. Read `ready`, not the process exit code: a valid check
can return `ready: false` with specific gaps. The evidence class is always `reported`. The
consultant must actually inspect the source, authorship, authority and meaning; filling fields
is not verification. This command does not authorize publishing, client contact or changing scope.

Use ordinary records with the following structured `data`. Each exact reference is an object
with `id` and `revision`, also present in the record's `inputs` edges. Retain sources before
authority/confirmation records, and those records before the decision that depends on them.

| Record kind | Required data for a passing baseline |
| --- | --- |
| `authority` | `actor`: named client decision maker; `scopes`: explicit scope names; `status`: `confirmed`; `verified_by`: consultant; `basis`: exact source reference supporting this authority. |
| `source` containing client confirmation | `medium`: `written`; `origin`: `client`; `author` matching the authority's actor; `identity`: `confirmed`; ISO `date`; precise `location`; `uncertainties`: empty only after checks. `confirmation` contains `scope`, `target` exact reference and `response`: `accept`. |
| `decision` | `state`: `accepted`; `scope`; exact `target`, `authority`, `confirmation` references; `verified_by`: consultant; timezone-aware ISO `verified_at`. |

The target is the exact requirement, mission or artifact version the client decided upon.
An accepted mission or artifact does not automatically approve unrelated requirements. A new
source, authority amendment, target version or pending correction makes dependent decisions
stale. Preserve prior decisions as history; obtain fresh scoped confirmation for revised content.
Never relabel a transcript or consultant-authored recap as a written client source. A clear
client reply to an identified confirmation request may be sufficient; retain that request and
explain the version binding. Ambiguous replies, disputed authority and silence do not qualify.

Drafts can retain incomplete data and visible uncertainty. A failure is useful: prepare the
specific follow-up that would close the gap, name its owner, and preserve the original decision
age. The response-obligation/reminder layer is separate; an accepted record does not itself
send a message or prove anyone was notified.
