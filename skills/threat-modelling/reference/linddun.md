# LINDDUN for personal-data flows

LINDDUN names seven kinds of privacy threat. It comes from the DistriNet research group at
KU Leuven; the definitions below paraphrase https://linddun.org/threat-types/.

This skill applies LINDDUN to every flow with `personal_data: true`, whether or not it crosses a
trust boundary. For each category, list the threat IDs, or write `n/a: <reason>`. The reason
rules are those of [stride.md](stride.md): "not relevant" alone fails the check, and 'Not
examined' is not an `n/a` reason: write a threat for it, such as a backlog item to examine it.

Staff and operator identities (session, user ID) are personal data too. A flow that carries a
staff single sign-on session, or a log line with a user ID, is `personal_data: true`.

| Key | Category | What it is | Ask on the flow |
| --- | --- | --- | --- |
| `linking` | Linking | Associating data items or user actions to learn more about a person or group | Can this data be joined with other data to build a profile, even without a name? |
| `identifying` | Identifying | Learning a person's identity through leaks, deduction or inference | Can someone learn who a person is when that is not intended, for example from a small result set? |
| `non_repudiation` | Non-repudiation | Being able to attribute a claim or action to a person | Does the system keep evidence that a person would reasonably want to deny? |
| `detecting` | Detecting | Deducing a person's involvement by observation, without reading the data | Do responses, errors, timing or side effects reveal that a record about a person exists? |
| `data_disclosure` | Data disclosure | Collecting, storing, processing or sharing more personal data than needed | Is every field needed? Is the volume, the retention or the number of recipients more than needed? |
| `unawareness` | Unawareness and unintervenability | Not informing, involving or empowering people in the processing of their data | Do the people know about this flow, and can they see, correct, export or delete their data? |
| `non_compliance` | Non-compliance | Deviating from data-protection law, standards or good practice | Does the flow have a lawful basis, a retention limit and the controls the law requires? |

## Notes

- Non-repudiation is a privacy threat in LINDDUN and a security property in STRIDE. The same
  audit log can mitigate a STRIDE repudiation threat and cause a LINDDUN non-repudiation threat.
  Model both when they apply.
- A threat the system owner cannot fix (for example, notice that a customer of the system must
  give) can be an accepted risk, with the owner who accepts it named. Say who carries it in the
  reason.
- LINDDUN does not decide what the law requires. Name the law or policy in the threat when it
  matters, and have someone qualified confirm it.
