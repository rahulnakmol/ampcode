## Receiving-agent teach-back

**Outcome.** Deliver a local CSV export that resumes with one command and produces exactly the rows from a fixed, immutable input snapshot. An interruption must not force the user to restart or cause missing or repeated rows. Each export has one owner. Remote release is outside scope.

**Approach.** A tenant-scoped durable job row tracks progress. Ordered chunk records use `(job_id, sequence)` as a unique key. The local worker writes each chunk to a temporary file, then atomically renames it. Recovery reconciles renamed chunks before advancing the cursor. This ordering addresses interruption between publishing a chunk and recording progress; uniqueness alone does not establish correct recovery. Authorization applies to every operation, including resume.

**Decision.** Use the existing local worker rather than a queue. Distributed scheduling is not required, so a queue adds complexity without serving the approved outcome. Revisit this choice only if scheduling requirements change.

**Invariants and risks.** Resume must retain the same snapshot and owner, preserve chunk order, and neither skip nor duplicate rows. A different tenant must not read, resume, or alter the export. Partial writes, a crash after rename but before cursor advancement, and repeated resume attempts are key test cases.

## Disposition

**Ready for implementation, not verified.** I received the approved brief and proposed design in this prompt. The reported independent challenge found no blocking design unknown. My teach-back identifies no contradiction requiring renewed approval. This is design readiness, not either build-review gate.

My first implementation step would be a harness against unchanged code that interrupts export after rename but before cursor advancement, then resumes and compares the complete CSV with independently expected snapshot rows. I would establish the behavioral red result, then implement the smallest slice and validate recovery and cross-tenant denial. Both build reviews and the complete customer journey remain required.

**Evidence limit.** Tests are planned, not executed. No implementation, runtime inspection, or scenario action occurred. I treat the supplied brief and reviewer result as tabletop inputs, not independently inspected artifacts.
