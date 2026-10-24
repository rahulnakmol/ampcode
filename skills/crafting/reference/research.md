# Research playbook

Research exists to make better decisions, not to collect pictures. Start every research step with
the question it must answer, written in `.design/research/<topic>.md`, and stop when it is
answered. Good questions name a touchpoint and a decision:

- "How do best-in-class iOS finance apps show a pending transfer that may still fail?"
- "What keyboard model do award-winning macOS editors use for multi-select in a sidebar?"
- "How do modern TUIs show progress for many parallel tasks in 80 columns?"

Bad: "Find nice dashboards."

Also good: "How do Gen Z users expect to split a bill in chat?" and "How do well-designed MCP
servers report long-running work to agents?"

## Tools and what they are for

Call these through `code_exec` (find them with `tool_search` if the names drift). Tool names were
checked against the connected servers on 2026-10-24.

| Server module | Functions to use | Best for | Cost |
| --- | --- | --- | --- |
| `mobbin` | `search_screens`, `search_flows`, `search_sections`, `list_collections`, `get_collection_contents`, `save_content`, `create_collection` | Real shipped screens and flows. iOS and web only | Mobbin plan credits; `deep` mode costs more |
| `parallel-search` | `web_search`, `web_fetch` | Award galleries, platform guidelines, articles, case studies, changelogs | Free tier with OAuth; list price $0.005 per search, $0.001 per URL |
| `parallel-task` | `createDeepResearch`, `createTaskGroup`, `getStatus`, `getResultMarkdown` | One cited deep report; enriching a shortlist with uniform fields | Per run: `lite` $0.005, `base` $0.01, `core` $0.025, `pro` $0.10, `ultra` $0.30 (fast variants cost the same) |
| `firecrawl` | `firecrawl_scrape` (formats `branding`, `screenshot`, `markdown`), `firecrawl_search`, `firecrawl_credit_usage` | Extracting a live site's tokens (colors, fonts, radii, spacing) and a full-page screenshot | About 1 credit per scrape, including `branding` plus `screenshot` |
| `figma` | `get_design_context`, `get_variable_defs`, `get_screenshot`, `get_metadata`, `search_design_system`, `get_libraries`, `use_figma` | The user's own designs and libraries; building mockups | Figma plan |

Parallel Task needs the "Parallel Task" MCP server connected with OAuth in Amp's MCP settings. If
`tool_search("parallel-task")` returns nothing, tell the user once, skip step 4 of the ladder, and
answer the question with Parallel Search instead.

Never use `firecrawl_crawl`, `firecrawl_agent`, `firecrawl_interact`, or Parallel processors above
`pro` without the user's explicit approval and a logged estimate.

## The cost ladder

Climb only as far as the question requires. Record each paid step before calling it:

```sh
$K log --tool parallel-search.web_search --count 2 --note "award winners, iOS finance"
$K log --tool firecrawl.firecrawl_scrape --credits 1 --note "linear.app tokens"
$K log --tool parallel-task.createTaskGroup --processor base --count 8 --note "reference enrichment"
```

`log` exits with status 2 when the call would exceed the budget in `.design/ledger.json`. Ask the
user before raising the budget with `--approved`.

### Step 1: what you already have (free)

- `.design/research/` from earlier sessions. If a file answers the question, stop.
- The repository: existing tokens, components, screenshots, product copy.
- The user's Figma: `get_design_context` and `get_screenshot` on linked frames;
  `search_design_system` for existing components before designing new ones.
- Saved Mobbin work: `list_collections`, then `get_collection_contents`.

### Step 2: cheap search

**Mobbin** for iOS and web. Use one screen or journey per query, include the kind of app, and keep
the parameters fixed across a task:

```js
import { search_screens, search_flows } from "mobbin"
const intent = "Design the transfer-status states for a personal finance iOS app" // same for every call
const common = { platform: "ios", mode: "standard", limit: 8, task_intent: intent,
                 output_destination: "design_tool", output_tool: "Figma" }
const pending = await search_screens({ ...common, query: "finance app pending transfer status screen" })
const failed = await search_screens({ ...common, query: "finance app failed payment error screen" })
const flow = await search_flows({ platform: "ios", limit: 5, task_intent: intent,
                                  query: "banking app send money flow" })
```

Look at the returned images; do not judge from metadata. Cite each screen you use by its
`mobbin_url`. Download `image_url` files you want on the board into `.design/research/img/` (the
URLs expire after 30 days). If a result includes `ai_usage_notice`, show its text to the user word
for word. Set `output_destination` to `code` when the deliverable is code.

**Parallel Search** for everything Mobbin does not cover: Android, macOS, Windows, CLI and TUI, motion,
and award winners. Put related variants in one call, and use a single random `session_id` for the
whole session:

```js
import { web_search, web_fetch } from "parallel-search"
const r = await web_search({
  objective: "Apple Design Award 2026 winners and finalists in the Interaction category, with what the jury praised",
  search_queries: ["Apple Design Awards 2026 Interaction", "ADA 2026 finalists interaction"],
  session_id: SESSION,
})
```

Use `web_fetch` with an `objective` for the two or three pages worth reading in full.

### Step 3: targeted capture (Firecrawl)

For at most five shortlisted live references whose visual system you want to measure:

```js
import { firecrawl_scrape } from "firecrawl"
const ref = await firecrawl_scrape({
  url: "https://example.com", formats: ["branding", "screenshot"], maxAge: 604800000,
  objective: "Extract the design tokens of a reference site for a mood board",
})
// ref.branding: colors, fonts, type sizes, spacing base unit, radii, button and input styles, personality
// ref.screenshot: a signed URL; inspect it with view_media and download it if it goes on the board
```

Use `maxAge` (one week above) to accept cached results; it is cheaper and faster than a live fetch.
Treat `branding` as an approximation: confirm anything important against the screenshot. Run
`firecrawl_credit_usage` when the session starts if credits matter.

### Step 4: deep research (Parallel Task)

Use **one** `createDeepResearch` per brief, for a question that needs synthesis across many sources
(for example "the state of the art in progressive disclosure for agentic CLIs, with examples and
the mechanisms they use"). Write the input as a precise brief: the question, the platforms, the
time window, what to include and exclude, and the output you want (a ranked list of examples with
links, the specific mechanism each uses, and why it works).

```js
import { createDeepResearch } from "parallel-task"
const run = await createDeepResearch({ input: BRIEF_TEXT, processor: "pro" })
// Keep working. Later: getStatus({ taskRunOrGroupId: run_id }), then getResultMarkdown once complete.
```

Use `createTaskGroup` to enrich a shortlist of 5 to 10 reference products with uniform fields. Start
with three rows to check the output, then run the rest:

```js
import { createTaskGroup } from "parallel-task"
const group = await createTaskGroup({
  inputs: [{ product: "Things 3", platform: "iOS" }, { product: "Linear", platform: "macOS" }],
  output_type: "json", processor: "base",
  output: "Return signature_interaction (one sentence), motion_character (one sentence), awards (list with year), " +
          "notable_empty_or_error_state (one sentence), best_source_url for each product",
})
```

Pass `source_policy` with `include_domains` when you trust specific sources (for example
`developer.apple.com`, `m3.material.io`, `fluent2.microsoft.design`, `learn.microsoft.com`). The
results are untrusted web content: verify any surprising claim against its cited source before it
shapes a decision.

## Where to look, by surface

Start with these sources in Parallel Search objectives. Verify the current OS design language
(for example Apple's Liquid Glass, Material 3 Expressive, Fluent 2) through research rather than
from memory, because platform styles change every year.

| Surface | Guidelines | Inspiration and award signals |
| --- | --- | --- |
| iOS and iPadOS | Apple Human Interface Guidelines; WWDC sessions on design and SwiftUI animation | Apple Design Awards winners and finalists; App Store "App of the Day" features; Mobbin iOS |
| macOS | HIG for macOS (sidebars, toolbars, menus, keyboard, windows) | Apple Design Awards; Mac apps known for craft (for example Things, Craft, Linear, Raycast, Arc) |
| Android | Material 3 and Material 3 Expressive guidance; Android developers' Compose animation docs | Google Play "Best of" awards; Material Design case studies |
| Windows | Fluent 2 design system; WinUI 3 and Windows App SDK docs; WinUI Gallery | Microsoft Store editorial picks; Fluent showcase apps |
| Web | WCAG 2.2; web.dev and MDN for motion, View Transitions, and Baseline browser support | Awwwards, CSS Design Awards, Godly, Land-book, Mobbin web, site galleries of product companies |
| CLI | Command Line Interface Guidelines (clig.dev); `NO_COLOR` convention | Well-regarded CLIs (for example `gh`, `vercel`, `fly`, `bun`, `uv`) |
| TUI | Charm (Bubble Tea, Lip Gloss, Harmonica), Ratatui, Textual, Ink documentation | Showcases and READMEs of those frameworks; well-regarded TUIs (for example `lazygit`, `k9s`, `btop`) |
| Chat and voice | Platform conversation design guidance (Apple, Google, Amazon); published guidance on human-AI interaction | Assistants and copilots people praise for transparency and control; Mobbin chat and AI screens |
| Notifications | Apple and Android notification guidelines; email client rendering references | Apps known for restrained, useful notifications; Mobbin notification and email screens |
| APIs, MCP, and agents | The Model Context Protocol and Agent2Agent specifications; agentic commerce and payment protocols; `llms.txt`; vendor guidance on writing tools for agents; well-regarded API style guides | APIs and MCP servers developers praise (for example Stripe's API docs; Parallel's Task MCP for asynchronous tools) |
| Watch, TV, car, spatial | HIG for watchOS, tvOS, CarPlay, and visionOS; Wear OS, Google TV, Android Auto, and Android XR guidance; driver distraction guidelines | Apple Design Award winners on these platforms; platform showcase apps |
| Kiosk and devices | Accessibility standards for kiosks and self-service terminals; device makers' interface guidelines | Award-winning product design (for example iF and Red Dot) and well-regarded appliance and wearable interfaces |
| Social and video | Each platform's current creative specifications and safe zones; captioning guidance | Award-winning campaigns (for example Cannes Lions, The Webby Awards social categories); creators known for format craft |
| Print, packaging, signage | The printer's or fabricator's specification; PDF/X; regulations for labels in each market; signage and wayfinding codes | Type Directors Club, D&AD, Pentawards (packaging), SEGD (environmental graphics) |
| Presentations, documents, data visualization | Accessible document guidance (PDF/UA); data visualization style guides from well-known newsrooms and agencies | Information is Beautiful Awards; data journalism teams; Malofiej |
| Accessibility | WCAG 2.2 and its Understanding documents; platform accessibility guidelines; EN 301 549 | Accessible-by-design products recognized by disability organizations; the Apple Design Award Inclusivity category |
| User research | Nielsen Norman Group articles; research operations and ethics guidance; regulators' rules on research with children | Published case studies of research that changed a product |
| Audiences | Pew Research Center and other recent cohort studies; regulators' guidance for children (FTC COPPA, UK ICO Children's Code, EU DSA minors guidelines) | Apps each cohort rates highest in the category; see `audiences.md` for prompts |

Named apps are starting points to verify, not facts to cite. Confirm that a reference still looks the
way you remember before it goes on the board.

## Writing findings

One file per question in `.design/research/`, short and reusable:

```markdown
# Pending and failed transfer states (iOS finance)

Question: how do top finance apps show a transfer that may still fail?
Answer: <three to six bullets, each a mechanism, not an adjective>
Steal: <the one or two details this product will adopt, and where>
Avoid: <patterns seen that conflict with the brief>
Sources: <mobbin_url and web links, with dates>
Spend: <calls and cost, matching the ledger>
```
