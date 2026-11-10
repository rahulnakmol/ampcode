# Worked example: month-end close in three days

An operations initiative carried through the planning mission. The company, people, and
numbers are fictional.

| Stage | File | What to notice |
| --- | --- | --- |
| Inputs | `inputs/`: workshop transcript, minutes, Priya's rough draft | Three sources disagree slightly on the target (3 vs 4 days) |
| G1 Evidence | [`evidence.md`](evidence.md) | 18 evidence rows citing source and timestamp; the 3-vs-4-day contradiction and 3 open questions surfaced, not resolved |
| G2–G3 PRD | [`prd.md`](prd.md) | Drivers D-1 (cost) and D-2 (audit control); goals with baselines; R-1 to R-3 with measurable AC-1 to AC-5; the contradiction settled as a recorded decision |
| G4–G7 Backlog | `grooming/reference/examples/operations.json` | 3 features ranked by WSJF; 6 stories and 1 critical bug; FX-rounding feedback accepted into S-2.4; a delivered spike (S-1); a goal measured mid-way (G-2 at 22 hours). S-6 is still draft, so this snapshot is mid-grooming and fails `--require-ready` |

To see the traceability chain, copy the backlog beside these files and run `trace`:

```sh
mkdir -p /tmp/close
cp ../../../grooming/reference/examples/operations.json /tmp/close/backlog.json
cp evidence.md prd.md /tmp/close/
python3 ../../../grooming/scripts/backlog.py trace /tmp/close/backlog.json --today 2027-03-10
```

The only gaps it reports are the four missing sign-offs, because this copy was never synced;
the evidence rows it lists as untraced (E12, E13, E15, E16, E18) are decisions and context the
PRD uses directly or deliberately leaves out.
