#!/usr/bin/env python3
"""Pick the model a fresh reviewer starts on, so a review runs on another model by construction.

  python3 reviewer_model.py --kind <kind> --implementer <model> [--implementer <model> ...]
                            [--not <model> ...]

Pass every model that wrote the change or the artifact, read from the host (on Amp,
`get_thread_status` returns a thread's `model`), and --not for a model another review of the same
candidate already uses (gate 1's reviewer, when picking gate 2). Prints the Amp model ID on the
first line and the reason on the second; start the reviewer on that model (on Amp,
`create_thread` with `model`) and record it in the review record. Exits 1 on an empty model name,
or when every listed model wrote or reviewed the candidate.

Kinds (../reference/reviewer-models.md says when each applies):
  code-1     review gate one, an item review, or a single code review
  code-2     review gate two
  document   a fresh review of a document, plan or design
  ui         a UI or UX review of a bounded change: one screen or component, few states
  ui-complex a UI or UX review of a new flow, several screens, rich interaction, motion, a
             design-system change or an accessibility audit

Code and document reviews take the first model in their order whose provider wrote none of the
change, so the reviewer does not share the author's blind spots; when every provider wrote some of
it, the first model no author used. UI reviews take a Gemini 4 model: Carbon for complex UI, Neon
for bounded UI; when an author or an earlier review used that one, the other; when both are
taken, GPT-6 Astra. Standard library only.
"""

import argparse
import sys

ASTRA, OPUS = "openai/gpt-6-astra", "anthropic/claude-opus-5-5"
CARBON, NEON = "google-vertex/gemini-4-carbon", "google-vertex/gemini-4-neon"
ORDER = {
    "code-1": [ASTRA, OPUS, CARBON],
    "document": [ASTRA, OPUS, CARBON],
    "code-2": [CARBON, ASTRA, OPUS],
    "ui": [NEON, CARBON, ASTRA],
    "ui-complex": [CARBON, NEON, ASTRA],
}


def provider(model):
    """openai/gpt-6-astra gives openai; google-vertex/... gives google."""
    name = model.strip().lower().split("/", 1)[0]
    return "google" if name.startswith(("google", "gemini")) else name


def same(a, b):
    return "".join(a.split()).lower() == "".join(b.split()).lower()


def pick(kind, implementers, taken=()):
    """(model, reason) for a reviewer of this kind."""
    used = list(implementers) + list(taken)
    free = [m for m in ORDER[kind] if not any(same(m, u) for u in used)]
    if not free:
        return None, "every listed reviewer model wrote or reviewed this candidate"
    if kind.startswith("ui"):
        model, first = free[0], ORDER[kind][0]
        if model == first:
            reason = "Gemini 4 Carbon for a complex UI" if model == CARBON else "Gemini 4 Neon for a bounded UI"
        elif model in (CARBON, NEON):
            reason = f"the other Gemini 4 model: {first} wrote or reviewed this candidate"
        else:
            reason = "both Gemini 4 models wrote or reviewed this candidate"
        return model, reason
    authors = {provider(m) for m in implementers}
    other = [m for m in free if provider(m) not in authors]
    if other:
        return other[0], f"first {kind} reviewer from a provider that wrote none of it ({', '.join(sorted(authors))})"
    if free:
        return free[0], "every provider wrote some of it: first model that wrote none of it"
    return None, "every listed reviewer model wrote or reviewed this candidate"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kind", required=True, choices=sorted(ORDER))
    parser.add_argument("--implementer", action="append", required=True, help="a model that wrote the change")
    parser.add_argument("--not", dest="taken", action="append", default=[], help="a model another review uses")
    args = parser.parse_args(argv)
    if not all(m.strip() for m in args.implementer + args.taken):
        print("an empty model name: read each model from the host")
        return 1
    model, reason = pick(args.kind, args.implementer, args.taken)
    if not model:
        print(f"no reviewer model: {reason}; choose one by hand and say why")
        return 1
    print(model)
    print(f"reason: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
