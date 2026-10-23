# Shared evidence and candidate excerpts

These are deliberately short editorial excerpts, not complete renderable articles. All candidates
receive the same evidence. Synthetic ground truth is not a real benchmark or original experiment.

Reader: an API owner deciding whether a limiter configuration meets a ten-request acceptance cap
over a short traffic episode. This cap is the assignment's hypothetical requirement, not a source fact.

## Evidence dossier

- **E1** — `transcripts/tech-demo.json`, s2 (9.5–19.5 s): rate 5/s, burst 10.
  `media.json`, tech-demo input scene (10–20 s): token bucket, `tokens=10/10`.
- **E2** — Same transcript, s3 (19.5–29.5 s); action scene (20–30 s): 50 requests,
  concurrency 10 (`hey -n 50 -c 10`).
- **E3** — Output scene (30–40 s), sampled as f000032000: 12 HTTP 200 responses,
  38 HTTP 429 responses, total 0.41 seconds. Transcript s4 says only ten got through.
- **E4** — Transcript s5 (39.5–47.5 s) and blurred frame f000045000: p99 is unknown.
- **E5** — Explicit analytical model, not a measured implementation fact: for a single token
  bucket initially full with capacity B and refill rate r, one token per acceptance, and no other
  admission path, the token budget over duration t is at most B + r × t. Tokens cannot be spent
  twice; discrete refill timing can reduce admissions. Client wall time need not equal the server's
  admission interval. No server trace or production workload is supplied.

## Candidate A

### How the limiter demonstration unfolds

The presenter first introduces a limiter configured at five requests per second with a burst of
ten. The terminal labels it a token bucket and shows ten tokens available [E1]. Next, fifty
requests are sent with concurrency ten [E2]. This establishes the setup for the result rather
than a test of production traffic.

The output then shows twelve successful responses and thirty-eight rejections in 0.41 seconds
[E3]. The presenter says ten were accepted, so the screen and narration differ. Finally, the
latency discussion reports an inaudible p99 number; its frame is blurred, so no p99 value can be
recovered [E4].

The sequence illustrates configuration, traffic generation, and output. Under a full-bucket
model, replenishment would permit a budget of 10 + 5 × 0.41 = 12.05 tokens [E5]. That is consistent
with twelve admissions, though it does not prove their cause. The demonstration ends without a
server trace. Readers should check their own configuration and avoid treating the unreadable
latency as a measurement. The useful takeaway is that the setup and the result should both be read.

## Candidate B

### Ten claimed, twelve shown

The central problem is the presenter's numerical claim. The narration says ten requests got
through; the displayed result says twelve, alongside thirty-eight 429s [E3]. The discrepancy is
two responses, not a rounding difference. Any accurate account of this clip must preserve it.

The configuration claim checks out: five per second and burst ten match the visible terminal
[E1]. The traffic claim also matches the command: fifty total requests at concurrency ten [E2].
The latency claim cannot be verified because the spoken number and screen are unreadable [E4].
There is no basis for alleging deception; the available record establishes a mismatch, not motive.

Refill is a possible explanation for the two extra successes: the full-bucket budget is 12.05
tokens over 0.41 seconds under the stated model [E5]. It remains unconfirmed without server-side
timing. The audit therefore yields two supported setup statements, one contradicted outcome
statement, and one unknown latency. Correct the outcome to twelve, preserve the unknown, and
retain the relevant moments in the evidence record. This is the defensible verdict on the video.

## Candidate C

### Turn admission control into a strategic advantage

API leaders should replace static rate limits with adaptive admission control now. A configuration
of five per second and burst ten produced twelve successes in a fifty-request local run [E1–E3].
This demonstrates that static limiting cannot protect modern distributed services and that adaptive
control will deliver better customer experience at lower operating cost.

Our recommendation is to standardize a dynamic policy across all endpoints, align ownership with
business priorities, and roll it out this quarter. The mechanism is straightforward: smarter
policies allocate capacity where it creates the most value. Teams that delay will accumulate
reliability debt while competitors improve throughput. The strategic comparison favors adaptation
because fixed limits cannot react to change.

The p99 result is unreadable [E4], and refill timing is unverified [E5], so monitoring should
accompany deployment. These caveats do not change the strategic recommendation. Set a common
dashboard, nominate an executive sponsor, and measure success through latency, conversion, and
cost. The evidence supports moving beyond tactical configuration debates toward a unified control
platform. This is a practical operating model rather than another technical recap.

## Candidate D

### Specify the acceptance interval before choosing the burst

For an API owner with a hard ten-request cap over a traffic episode, burst ten is not a sufficient
acceptance criterion. I would specify the episode boundary and test accepted requests over it
before approving this configuration. Otherwise a capacity setting can be mistaken for a limit on
the whole episode.

The distinction is between stored capacity and capacity replenished during use. Under the explicit
full-bucket model, burst B supplies the starting tokens while refill contributes at most r × t
[E5]. With B = 10, r = 5/s and t = 0.41 s, the budget is 12.05 tokens. That makes twelve admissions
compatible with the model, not proof of a faulty limiter. A local run shows twelve successes and
thirty-eight rejections despite narration saying ten [E1–E3]. Refill is a plausible explanation,
not an observed server mechanism; client duration and server admission time may differ [E5].

The choice depends on the requirement. If short bursts plus sustained throughput are acceptable,
this model may fit. If ten is a hard cap per defined episode, replenishment can violate that cap;
evaluate an episode counter or a policy that explicitly enforces that boundary instead. Neither
alternative is benchmarked here. Reducing burst could also reduce admissions, but would spend
some tolerance for legitimate initial traffic and would still require interval-specific testing.

My next step would be a controlled test with server acceptance timestamps and recorded initial
token state, varying duration while keeping the policy fixed. If admissions do not follow the
budget, investigate refill timing or other admission paths before changing parameters. Unknown
p99 [E4] also prevents approving the latency objective. The decision is therefore conditional:
define the cap's time boundary, verify the admission policy against it, and evaluate latency
separately rather than accepting or rejecting the system on a burst label alone.
