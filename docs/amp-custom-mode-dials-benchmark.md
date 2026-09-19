# Amp Custom Mode Dials benchmark

Tested on 19 September 2026. This benchmark is a routing check, not a universal model leaderboard: it uses one compact but subtle TypeScript concurrency task to distinguish the intended Low–Medium, Medium–High, and High–Ultra modes.

## Result

| Rank | Mode / candidate | Configuration | Score | Delivery | Result |
| --- | --- | --- | ---: | --- | --- |
| 1 | **Prime / C** | Opus 5 high; Fable 5.1 max; automatic specialists | **91** | ~3m16s | Best production and test completeness |
| 2 | **Weave / B3** | Opus 5 medium; Fable 5.1 x-high; Sonnet 5 medium subagents | **88** | ~2m35s | Near-Prime quality, faster, with two test/API gaps |
| 3 | **Swiftstep / A** | GPT-5.6 Luna medium + Fast; Fable 5.1 medium; automatic specialists | **52** | Completed | Sound core approach, but a real pre-abort bug and a non-isolated test suite |
| 4 | **Original Weave / B** | Opus 4.8 + Fast | **5** | No timely result | Reliability failure in the judge window |

The first judge report printed Prime as 86, but its published components were 36 + 27 + 14 + 9 + 5 = **91**. The independent final judge retained those components and corrected the arithmetic.

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
- **Swiftstep:** the cache algorithm was mostly sound, but its delivered suite failed 4/5 because module-level state leaked between tests. A pre-aborted caller also started work before its wait rejected.
- **Original Weave:** missed the initial six-minute judge window and arrived much later. It was replaced because latency and routing reliability are part of mode quality.

## Routing decision

Keep the current routes:

- **Swiftstep** remains the economical direct-execution mode. This benchmark is above its normal sweet spot, and its lower score is consistent with its intended position rather than a reason to spend Prime-level tokens on routine work.
- **Weave** uses Opus 5 at medium effort without Fast. It recovered from the earlier Opus 4.8/Sonnet routing reliability issues and delivered near-Prime quality more quickly.
- **Prime** remains Opus 5 at high effort with max-effort Fable reserved for unresolved high-impact decisions. It won without using an Ultra-style default.

The plugin cannot enforce a hard token ceiling. Cost control therefore comes from effort levels, direct-execution instructions, bounded delegation, and reserving Oracle calls for consequential uncertainty.

## Evidence

- [Swiftstep candidate](https://ampcode.com/threads/T-01a0baf3-0be0-737e-b77c-161e57ae4bc2)
- [Original Weave candidate](https://ampcode.com/threads/T-01a0baf3-11e1-703c-8411-b63a9bf04a7b)
- [Final Weave candidate](https://ampcode.com/threads/T-01a0bb09-5dbb-766d-8d91-7d8e19e29991)
- [Prime candidate](https://ampcode.com/threads/T-01a0baf3-177c-74cb-aeb7-ef1b76be74f6)
- [Initial Fable judge](https://ampcode.com/threads/T-01a0bafa-3c12-746a-bf04-8923c81d3980)
- [Independent final Fable judge](https://ampcode.com/threads/T-01a0bb0d-c685-751c-8231-cbe9b2fd7037)

Thread links may require the owner's Amp account. The scores are evidence for this task and date only; the weekly model review should trigger a new benchmark before routing changes are published.
