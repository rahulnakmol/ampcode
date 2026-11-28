# Use Swift, Weave and Prime

[`plugins/amp-custom-mode-dials.ts`](../plugins/amp-custom-mode-dials.ts) targets the gaps in Low → Swift → Medium → Weave → High → Prime → Ultra. Each mode runs its work as a mission through the same shared mission core, with its own workflow doing each work item. These are intended workflow positions, not a benchmark-proven capability ranking:

| Mode | Position | Main agent | Serving |
| --- | --- | --- | --- |
| **Swift** | Low → Medium | Sonnet 5.5, medium | Normal by default |
| **Weave** | Medium → High | GPT-6.1 Sol, high | Normal by default |
| **Weave Fast** | Same Weave rung | GPT-6.1 Sol, high | Fast requested |
| **Prime** | High → Ultra | Fable 5.1, medium | Normal by default |
| **Prime Fast** | Same Prime rung | Fable 5.1, medium | Fast requested |

## Why this routing

- **Swift** keeps a Medium-style workflow but prioritizes direct execution on Sonnet 5.5 at medium effort.
- **Weave** uses GPT-6.1 Sol at high effort for focused implementation and artifact verification.
- **Prime** extends High rather than Ultra, using Fable 5.1 at medium effort and risk-scaled verification.

Select `weave-fast` or `prime-fast` to request Fast without changing the model, effort or workflow. Base modes declare `features: []` to avoid inheriting Fast from a creating thread; callers can still explicitly add it. Fast variants require `features: ['fast']`. Actual acceleration, availability and premium billing depend on the provider route; registration alone does not verify them. No accelerated-serving guarantee is made for either route.

The current Amp plugin API does not expose separate `oracle` or `subagents` model overrides. The obsolete fields have been removed; specialist routing stays with Amp. Opus 5.5 workers are a requested preference, not an enforced configuration. Explicit Opus child agents would require a separate supported delegation mechanism; these modes do not silently substitute child threads for `Task`.

Plugin agent modes cannot enforce a fixed token ceiling, so Prime cannot guarantee a precise percentage below Ultra. Its prompt, effort, delegation, and Oracle policy are deliberately configured to avoid Ultra-style exhaustive exploration.

The [realistic async-cache benchmark](research/custom-mode-dials-benchmark.md) records earlier configurations; it does not validate this new routing.

## Use modes without changing the Dial

The standard Low, Medium, High, and Ultra Dial can remain unchanged. Published plugin modes stay available in the complete mode picker and to Puck.

Example Puck request:

> Start a Weave thread in this project to implement the change, and a Prime thread to review the architecture. Ask both to report back here.

Name the mode explicitly; otherwise Puck uses its normal routing. Threads created in separate orbs have separate checkouts and do not automatically share uncommitted files.

Install or publish the plugin as described in the [repository README](../README.md#publish).
