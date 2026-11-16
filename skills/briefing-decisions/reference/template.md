# Decision brief template

Copy the skeleton, replace every `<...>`, then run `scripts/brief_check.py`. The filled example
below passes the checker; a test keeps it that way.

## Rules the checker applies

| Rule | What passes |
| --- | --- |
| front-matter | Only these keys: `decision` (at most 30 words), `yes` and `no` (at most 40 words each), `risks` (1 to 6 unique items, at most 30 words each), `excluded` (1 to 6 items, at most 20 words each), optional `picture` (an `https` URL on `ampcode.com` or `github.com`; for the document, not shown in the dialog). Each value is one line of plain text: no ` #`, no backslash and no YAML symbol (`& * ! | > { [ % @` or a backtick) at the start |
| summary | The summary (the four labelled lines below) is at most 150 words |
| headings | Exactly the ten `##` headings of the skeleton, in order. `###` subheadings are fine |
| technical-record | One `<details><summary>Technical record</summary>` block ends the file |
| consistency | Each `risks` item is, word for word, a list item under `## Risks you accept`; each `excluded` item under `## Not included` |
| html | No raw HTML, HTML comments, character references (`&amp;`, `&#8203;`) or link reference definitions (`[label]: ...` lines) anywhere, including the front matter, except the technical record's own `<details>` lines |
| markdown | Links are `[text](destination)` with text and a plain destination (no spaces, parentheses, backslashes or quotes), so no link titles. No images, code fences with a label after the opening backticks, GitHub math holding a TeX special character (`\ % & # { } ^ _ ~`, as in `$\phantom{...}$` or `$5 % words$`), or table rows with more cells than the header, also in nested lists and quotes: each renders some words invisibly. Prices such as `$25 ... the $30` are not math |
| length | At most 20,000 characters |
| characters | Plain newlines only: no carriage returns, line separators, other control characters, invisible format characters (zero-width, bidirectional, tag characters) or other invisible characters (variation selectors, fillers) |
| sentence-length | No sentence before the technical record has more than 25 words |
| reading-ease | Flesch reading ease of the prose is at least 50 |
| banned | No hashes, thread or task IDs, JSON, provider/model slugs, or lines that start with a bare code such as `H04:` in the front matter or prose. Put them in the technical record |

The summary at the top of the brief (the checker counts these words):

```text
You are deciding: <decision>
If you say yes: <yes>
If you say no: <no>
Risks you accept:
1. <first risk>
2. <second risk>
```

## Skeleton

````markdown
---
decision: <one sentence: what the reader approves>
yes: <what happens next, and when>
no: <what happens instead; "nothing changes" is a fine answer>
risks:
  - <a risk the reader accepts by saying yes>
excluded:
  - <something a reader might assume is included but is not>
---

## You are deciding

<The decision in two to four sentences, and why now.>

## If you say yes

<The next steps, in order.>

**What it costs you:** <money, time, attention, and what the reader still has to do.>

## If you say no

<What happens instead, and what stays as it is.>

## What changes

<Before and after, as a numbered list a reader can check.>

## What done looks like

<Numbered results a reader can see or test.>

## What we checked and what we did not

**Checked:** <evidence, in plain words.>

**Not checked:** <what is still unknown, and when it gets checked.>

## Risks you accept

- <the same text as each risks item>

## Not included

- <the same text as each excluded item>

## How to undo it

<The steps, how long they take, and what cannot be undone.>

## Words you may not know

- **<word>:** <a plain explanation.>

<details><summary>Technical record</summary>

<IDs, hashes, file paths, commands and anything else only a specialist needs.>

</details>
````

## Filled example (synthetic)

````markdown
---
decision: Approve a two-week trial of a shared calendar for the support team.
yes: The agent sets up the calendar on Monday. The trial ends after two weeks, and you then decide to keep it or not.
no: The support team keeps its paper rota on the office wall.
risks:
  - Two people may book the same shift during the first week.
  - The trial costs 40 US dollars.
excluded:
  - Calendars for other teams.
  - A link to the payroll system.
---

## You are deciding

Approve a two-week trial of a shared calendar for the support team. Today the team uses a paper rota on the office wall. People who work from home cannot see it.

## If you say yes

- The agent sets up the calendar on Monday and invites the six support staff.
- The agent copies the next two weeks of shifts from the paper rota.
- After two weeks, you decide to keep the calendar or stop it.

**What it costs you:** 40 US dollars for the trial. Your time: this approval and a ten-minute review at the end.

## If you say no

Nothing changes. The paper rota stays on the wall. Staff at home keep asking a colleague to send a photo of it.

## What changes

1. Each support person sees the shifts on their phone.
2. Shift swaps happen in the calendar, not by email.
3. The paper rota stays on the wall during the trial, as a backup.

## What done looks like

1. All six staff open the calendar on their phone.
2. Every shift for the two weeks is in the calendar.
3. At the end, you get a one-page note: swaps made, problems found, cost.

## What we checked and what we did not

**Checked:** the calendar works on the phones the team uses. It needs no new hardware.

**Not checked:** how it works with more than ten people. The trial has six.

## Risks you accept

- Two people may book the same shift during the first week.
- The trial costs 40 US dollars.

## Not included

- Calendars for other teams.
- A link to the payroll system.

## How to undo it

Cancel the trial in the calendar settings. Go back to the paper rota, which stays on the wall during the trial. This takes five minutes.

## Words you may not know

- **Rota:** a list of who works which shift.

<details><summary>Technical record</summary>

- Example only; no real system.
- Plan: team calendar trial, 6 seats, 14 days.

</details>
````
