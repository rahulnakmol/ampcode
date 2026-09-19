# Amp Custom Mode Dials benchmark

Tested on 19 September 2026. This benchmark is a routing check, not a universal model leaderboard: it uses one compact but subtle TypeScript concurrency task to distinguish the intended Low–Medium, Medium–High, and High–Ultra modes.

## Result

| Rank | Mode / candidate | Configuration | Score | Delivery | Result |
| --- | --- | --- | ---: | --- | --- |
| 1 | **Prime / C** | Opus 5 high; Fable 5.1 max; automatic specialists | **91** | ~3m16s | Best production and test completeness |
| 2 | **Weave / B3** | Opus 5 medium; Fable 5.1 x-high; Sonnet 5 medium subagents | **88** | ~2m35s | Near-Prime quality, faster, with two test/API gaps |
| 3 | **Swift Terra / TF** | Terra medium + Fast; Fable 5.1 medium; automatic specialists | **77** | 16.4s | Best tested balance for Swift |
| 4 | **Swift Grok / S** | Grok 4.6 medium + Fast; Fable 5.1 medium; automatic specialists | **74** | 43m53s via an error state | Good eventual code; unusable routing reliability |
| 5 | **Swiftstep / A** | Luna medium + Fast; Fable 5.1 medium; automatic specialists | **52** | 12.8s | Sound core approach, but a real pre-abort bug and a non-isolated test suite |
| 6 | **Original Weave / B** | Opus 4.8 + Fast | **5** | No timely result | Reliability failure in the judge window |

The first judge report printed Prime as 86, but its published components were 36 + 27 + 14 + 9 + 5 = **91**. The independent final judge retained those components and corrected the arithmetic.

### Grok Fast reevaluation

After renaming Swiftstep to Swift, `xai/grok-4.6` at medium effort with Fast was tested against the identical task. The benchmark produced no assistant text and was observed in an error state after 7m50.9s, but unexpectedly resumed much later and completed after 43m53s. A separate `SWIFT_OK` smoke prompt produced no output and hard-failed after 2m26.6s. Neither thread exposed a provider diagnostic.

The eventual implementation passed its own 11 tests and scored **74/100**, above Luna's 52 on output quality. It deliberately starts shared work for a pre-aborted cold caller, ships a TypeScript config that cannot type-check its own `.ts` import, and has gaps around delayed stale cleanup, settled-hit aborts, and module isolation. It also violated the blind prompt's no-tools constraint by installing packages and iterating against test feedback.

Grok Fast is not the production Swift route because the latency, error-state recovery, and failed trivial smoke overwhelm its stronger eventual code. This may be a transient provider incident, but adoption requires a later 3/3 smoke pass within 30 seconds followed by a blind no-tools benchmark.

Grok 4.6 was retested at **high** effort with Fast. Three concurrent `SWIFT_OK` smokes passed in 20–21s, but the identical blind cache benchmark produced no answer within 13 minutes. Higher effort fixed the trivial smoke reliability seen in the earlier window, not full-task delivery, so it was not promoted.

After restoring Luna under the renamed `swift` key, the same `SWIFT_OK` smoke prompt completed correctly in 15.4s.

### Terra Fast reevaluation

GPT-5.6 Terra at medium effort with Fast completed the blind cache benchmark in 16.4s without tools and scored **77/100**, versus Luna's 52 in 12.8s. Its production implementation was correct under the stated requirements, but its five-test suite was order-dependent, omitted a direct stale-cleanup case and post-abort cache-health assertion, and replaced `signal.reason` with a fresh `AbortError`.

Three additional no-tools prompts completed in 17–33s. The autocomplete and interval-merging answers were correct; the PostgreSQL transfer answer had a real constraint bug in its temporary idempotency row. This confirms reliable completion and useful coding quality, while showing that Swift remains a Low–Medium mode rather than a substitute for Weave or Prime.

## Task

Each mode received the same self-contained prompt and was told not to use tools or external sources. The starting point was this shared async cache:

```ts
type Entry<T> = { expiresAt: number; promise: Promise<T> }
const entries = new Map<string, Entry<unknown>>()

export async function load<T>(
  key: string,
  ttlMs: number,
  signal: AbortSignal,
  fetcher: (signal: AbortSignal) => Promise<T>,
): Promise<T> {
  const current = entries.get(key) as Entry<T> | undefined
  if (current && current.expiresAt > Date.now()) return current.promise

  const promise = fetcher(signal)
  entries.set(key, { expiresAt: Date.now() + ttlMs, promise })
  try {
    return await promise
  } catch (error) {
    entries.delete(key)
    throw error
  }
}
```

The required rewrite had to:

1. share exactly one in-flight fetch per key even when its runtime exceeds the TTL;
2. start TTL at successful completion;
3. never cache failures;
4. make abort caller-local without poisoning shared work;
5. prevent stale rejection cleanup from deleting a newer entry; and
6. stay small, with complete focused Vitest tests covering asymmetric cancellation and TTL boundaries.

This exercises diagnosis, API judgment, promise ordering, cancellation semantics, boundary handling, and whether tests distinguish plausible wrong implementations.

## Independent judge

Claude Fable 5.1 executed the candidates under Node 26.8.2 and Vitest 5.0.1, type-checked final Weave with strict TypeScript, cross-ran candidate test suites, and applied targeted mutants.

| Check | Prime | Final Weave |
| --- | --- | --- |
| Own baseline | 7/7 pass | 8/8 pass; stable over five reruns |
| Cross-run | Weave tests: 8/8 | Prime tests: 7/7 |
| TTL-at-start mutant | Killed | Killed |
| Inclusive-boundary mutant | Killed | Killed |
| Cache-failures mutant | Killed | Killed |
| Abort ignored / poisons shared work | Killed | Killed |
| Missing pre-abort guard | Killed | Killed |
| Immediate unconditional delete | Survived; structurally equivalent with an in-flight `Infinity` sentinel | Survived; same reason |
| Deferred stale delete | Killed at one timer turn; survived three microtasks | Killed at both one timer turn and three microtasks |
| Settled cache hit bypasses abort | Killed | Survived |

### Material findings

- **Prime:** strongest overall. Its production code guards synchronous fetcher throws and its tests cover aborting a caller waiting on a settled cache hit. Its stale-cleanup test is weaker than Weave's for delayed cleanup.
- **Weave:** behaviourally equivalent to Prime on both complete suites and stronger against delayed stale-cleanup mutants. It lets a synchronous fetcher throw synchronously, omits a settled-cache-hit abort test, and carries a redundant rejection guard plus a `null as never` initialization.
- **Swift / Luna (tested as Swiftstep):** the cache algorithm was mostly sound, but its delivered suite failed 4/5 because module-level state leaked between tests. A pre-aborted caller also started work before its wait rejected.
- **Swift / Terra:** scored 77 with clean, no-tools delivery in 16.4s. Its weak spots were test order dependence, missing cleanup/abort-health cases, and non-idiomatic abort reasons; follow-up prompts completed reliably with one substantive SQL bug across three tasks.
- **Swift / Grok Fast:** eventually produced a solid 74-point implementation, but only after 43m53s, an observed error state, and prohibited tool-driven iteration. Its one-line smoke prompt hard-failed. The route is therefore unsuitable despite better eventual code than Luna.
- **Original Weave:** missed the initial six-minute judge window and arrived much later. It was replaced because latency and routing reliability are part of mode quality.

## Routing decision

Keep the current routes:

- **Swift** uses Terra at medium effort with Fast. It improved benchmark quality from Luna's 52 to 77 at similar latency and completed three follow-up prompts reliably. Grok Fast remains excluded because full-task reliability stayed poor even after high-effort smoke tests passed.
- **Weave** uses Opus 5 at medium effort without Fast. It recovered from the earlier Opus 4.8/Sonnet routing reliability issues and delivered near-Prime quality more quickly.
- **Prime** remains Opus 5 at high effort with max-effort Fable reserved for unresolved high-impact decisions. It won without using an Ultra-style default.

The plugin cannot enforce a hard token ceiling. Cost control therefore comes from effort levels, direct-execution instructions, bounded delegation, and reserving Oracle calls for consequential uncertainty.

## Evidence

- [Swiftstep candidate](https://ampcode.com/threads/T-01a0baf3-0be0-737e-b77c-161e57ae4bc2)
- [Swift Terra candidate](https://ampcode.com/threads/T-01a0bb9d-b3f9-734b-b1c9-ac3a71b28dd8)
- [Terra autocomplete follow-up](https://ampcode.com/threads/T-01a0bba5-698d-7796-ac95-dcc157116ed5)
- [Terra PostgreSQL follow-up](https://ampcode.com/threads/T-01a0bba5-70d9-73fb-a689-6277f38d3d6d)
- [Terra interval follow-up](https://ampcode.com/threads/T-01a0bba5-764c-71ad-95c2-eff0566e1288)
- [Swift Grok Fast candidate](https://ampcode.com/threads/T-01a0bb21-e08a-751e-b977-1445d9bcc220)
- [Swift Grok Fast smoke test](https://ampcode.com/threads/T-01a0bb28-32d7-773b-bb40-2e67e2588801)
- [Grok high Fast benchmark](https://ampcode.com/threads/T-01a0bb9c-acde-756c-b0d7-e6ea16e6a11c)
- [Final Swift Luna smoke test](https://ampcode.com/threads/T-01a0bb2d-57d9-7149-be10-bb34920e926d)
- [Original Weave candidate](https://ampcode.com/threads/T-01a0baf3-11e1-703c-8411-b63a9bf04a7b)
- [Final Weave candidate](https://ampcode.com/threads/T-01a0bb09-5dbb-766d-8d91-7d8e19e29991)
- [Prime candidate](https://ampcode.com/threads/T-01a0baf3-177c-74cb-aeb7-ef1b76be74f6)
- [Initial Fable judge](https://ampcode.com/threads/T-01a0bafa-3c12-746a-bf04-8923c81d3980)
- [Independent final Fable judge](https://ampcode.com/threads/T-01a0bb0d-c685-751c-8231-cbe9b2fd7037)

Thread links may require the owner's Amp account. The scores are evidence for this task and date only; the weekly model review should trigger a new benchmark before routing changes are published.
