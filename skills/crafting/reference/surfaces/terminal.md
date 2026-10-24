# Terminal surfaces: CLI and TUI

Terminals are text, time, and keys. Craft lives in hierarchy without color dependence, honest
progress, and paths that work equally well for a person at a prompt and an agent in a pipeline.

## CLI (`cli`)

Craft:

- Follow clig.dev. Human output by default, `--json` for machines, consistent nouns and verbs,
  `--help` with examples first, suggestions on typos, and a next-step hint after success.
- Output hierarchy with weight and dim, not a rainbow: one accent color, red only for errors,
  yellow only for warnings. Symbols (`✓`, `✗`, `!`, `→`) always paired with words.
- Respect `NO_COLOR`, `TERM=dumb`, and non-TTY output: no color, spinners, or cursor movement when
  piped; plain lines that `grep` can use. Stable exit codes, documented.
- Progress: nothing under 100 ms; a spinner with a verb under about 2 s; a progress bar with counts
  and an estimate beyond that; for parallel work, one line per task that settles in place.
- Errors say what happened, why, and the exact command to fix it. Never a stack trace by default.
- Prompts only on a TTY, each with a flag equivalent (`--yes`, `--name`), so agents never block.
- Destructive commands show the impact and require confirmation or `--force`.

Mockup and verification: write each state as a script that prints the exact output (or run the
prototype), then capture it. Prefer `vhs` (Charm) tapes for screenshots and GIFs at 80 and 120
columns; otherwise render with a terminal and screenshot it. Also capture `--json` output and the
piped (`| cat`) and `NO_COLOR=1` variants as text.

## TUI (`tui`)

Craft:

- Pick the stack the project uses: Bubble Tea and Lip Gloss (Go), Ratatui (Rust), Textual (Python),
  Ink (TypeScript).
- Layout in cells: design for 80×24 first, then 120×40 and resize. Truncate with an ellipsis in the
  middle for paths and at the end for prose. Never wrap a table row.
- Keyboard first: visible focus, a footer of the three to five most useful keys, `?` for all keys,
  `q` or `Esc` to back out, `/` to filter, vim keys as an alternative and not the only way. Mouse
  support as a bonus.
- Color: design in 16 ANSI colors first so user themes apply, then enhance for 256 and truecolor.
  Check light and dark terminal backgrounds. Box-drawing lines in a dim tone; one accent.
- Motion: redraw only what changed, cap animation at about 30 to 60 fps, spring-based movement
  (Harmonica) for panes and cursors sparingly, spinners at about 80 to 120 ms per frame. No flicker:
  use the alternate screen and synchronized output where supported.

Mockup and verification: run the prototype in a pseudo-terminal and capture it with `vhs` at 80×24
and 120×40, in a light and a dark theme, with `NO_COLOR=1`, and with focus on each region.

