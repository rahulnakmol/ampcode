# Start a Blueprinting engagement

Use **Blueprinting** when you are a consultant or business analyst turning client evidence into a functional specification, operating model, implementation kickoff or commercial proposal. It covers ERP, CRM and enterprise SaaS business processes, not technical solution architecture. Use [planning](mission-driven-planning.md) instead when your primary outcome is a PRD and executable backlog in a tracker; use [delivering](mission-driven-development.md) to implement software.

## Start with a decision, not a document collection

The six skills are published to Rahul's **Amp User Skills**. New threads discover them automatically; an existing thread may need a skill reload. Other users must separately install the complete packages into their own authorized destination. Cloning this GitHub repository does not install them. Ask Amp to load `blueprinting`, check its selected package and verify its shared helpers and domain contracts. A remembered skill name is not proof that its files are available.

Open a thread in the environment where the engagement files will live, then paste this prompt and replace the brackets:

```text copy Copy Blueprinting Kickoff
Use blueprinting to start a [discovery / implementation kickoff / pre-sales / RFP]
engagement for [business problem]. The next decision is [decision], for [audience],
by [date]. Success means [observable outcome].

Proposed engagement ID: [stable ID, such as close-discovery].
Proposed private engagement root: [absolute path on this thread's machine].
Template package: [absolute local path, or unavailable].
Available evidence: [file locations and source owners, or none yet].
Named client decision authority: [role/name, or unknown].
Processing, storage and sharing restrictions: [rules, or unknown].

Check the published skill packages. Clarify only the missing decisions needed for
the first workshop. Confirm the engagement root, journey, permitted processing,
retention, working calendar/timezone, audience and destinations before intake.
Show the available template choices and a no-write Start preview. If the separate
template package is unavailable, report that dependency and stop before setup;
continue only with a draft workshop agenda and questions that need no client data.
Wait for my confirmation of the exact preview before creating the engagement.
Do not create remotes, activate Notion or reminders, or send anything to the client.
```

Choose a location on the machine running the thread, not a path that is accessible only on your laptop. An orb cannot read an unshared local directory. Use an explicitly selected absent or empty engagement directory with an existing parent; never use the extensions repository or a skill installation directory. Keep one private, Obsidian-compatible Git repository per engagement. Git history alone does not make data confidential, and private remote backup needs separate authorization and configuration.

### The template package is a separate dependency

**The six published skills do not include the separate `blueprinting-engagement-template` repository.** Its source has been qualified locally but has not been published to a remote. There is no public clone URL to assume. If you have an authorized local copy on the execution machine, give Amp its absolute path; otherwise arrange template delivery separately. Workshop planning can begin without creating a vault, but the supported template-backed Start flow cannot.

Amp reads that package's `template.json`, proposes actual template IDs and prepares a configuration with the engagement ID, journey, policy and selected templates. The helper's journey values are `opportunity`, `pre-sales`, `rfp`, `discovery`, `kickoff` and `post-engagement`. It runs `start` without confirmation to show the intended root and content. Only after you approve that exact preview does it repeat Start with the returned confirmation hash. Changed inputs require a new preview; cancellation creates no engagement.

Start initializes the local record and activates the selected **templates only**. It does not initialize Git, create a remote, grant client consent, connect Notion, schedule reminders or accept a business decision. The hash binds a preview; it is not an authenticated approval receipt. See the [Start/Resume contract](../skills/blueprinting/reference/templates.md) for helper commands and interruption recovery.

## Give the first workshop a useful finish

Before supplying real client evidence, agree permitted processors, storage, retention, decision authority, calendar and sharing destinations. Unknown policy is a gap, not permission. Start with synthetic or redacted examples if those decisions remain open.

Give Amp what you have: business drivers, desired outcomes, stakeholder roles, existing process notes, questionnaires, RFP/addenda and attributed transcripts. Preserve dates, speakers, source locations and conflicting accounts. Audio needs explicit processing permission and available supported dependencies; machine transcripts remain provisional. Missing voices and uncertain words should become follow-up questions, not plausible facts.

Ask for a first-session packet containing:

- The business decision, scope and observable success criteria.
- A workshop agenda and client questionnaire tied to evidence gaps.
- Actors, responsibilities and receiving teams that must attend or answer.
- Contradictions, missing evidence and follow-up questions with owners.
- The deliverables needed for this journey, rather than every available format.

Your confirmation of a workshop plan is not client acceptance of its business conclusions. A business baseline needs reported written confirmation from the named authorized client covering the exact decision and version. Output review, permission to share and external delivery remain separate.

## Let the coordinator choose the domain

You do not need six threads or a fixed sequence of six skills. `blueprinting` keeps engagement continuity and loads the domain needed for the current task. You can also name a domain directly; it binds to the host-selected coordinator before using shared helpers.

| Current task | Skill | Useful result |
| --- | --- | --- |
| Start, resume, retain evidence and track unresolved work | `blueprinting` | Current engagement state, gaps and next decision |
| Prepare workshops, questionnaires or ingest attributed evidence | `discovering-requirements` | Cited findings, contradictions, follow-ups and full debrief |
| Reimagine processes, roles, rules, exceptions and handoffs | `designing-functions` | Traceable functional specification or explicitly incomplete draft |
| Qualify pre-sales or respond to an RFP | `shaping-engagements` | Grounded offer, fit-gap, assumptions and bounded estimates; RFP obligations remain distinct |
| Prepare a document, executive deck or selected handoff | `publishing-engagements` | Reviewed content and inspected editable exports, not automatic delivery |
| Challenge claims, functional coverage or output consistency | `reviewing-engagements` | Findings tied to sources and exact output revisions |

For example: “Use discovering-requirements in the current engagement to prepare tomorrow's workshop from the unresolved receiving-team questions. Draft the questionnaire; do not send it.”

## Resume without restarting discovery

```text copy Copy Blueprinting Resume
Use blueprinting to resume engagement [expected ID] at [absolute engagement root].
Load the published coordinator and check its selected package. Inspect retained
state before changing anything: policy, pending operations, changed or unregistered
inputs, stale dependencies, active templates and response obligations.
Summarize the current decision, unresolved gaps and next safe action. Reuse settled
answers unless evidence changed. Do not retry uncertain external effects, activate
integrations or send client communications without the relevant approval.
```

For a template-backed engagement, Amp uses `resume` with the expected ID; a mismatched identity blocks. Older records created with `init` use `status` and do not acquire Start metadata automatically. If setup or an external action was interrupted, inspect the retained state before retrying. Do not reset the directory to make an error disappear.

## Know what publication does not promise

Supported local handoffs include Markdown, editable Word/PowerPoint/Excel, PDF and selected exact-inspected-byte ZIPs. Export dependencies and fonts must be available; an installed skill does not install them automatically. Excel scenario edits require supported native recalculation and review, not just reading cached totals. Google Slides/Docs remain deferred.

Qualification used English synthetic/redacted cases, inspected LibreOffice handoffs, controlled Notion interleaving and two reminder wakes with later manual recovery. It is not production-client validation, Microsoft desktop certification, authenticated client authority or continuous monitoring. No scheduler or automatic two-way Notion sync starts when you load a skill. Establish real engagement permissions and inspect the actual outputs before relying on them.
