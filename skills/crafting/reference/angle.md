# Finding the angle

The need tells you what the experience must do. The angle is what makes it matter: the one idea
that makes a person feel something, the take that would be obvious in hindsight but that nobody in
the category has shipped. Most products are a competent version of the category default. The
ceiling of this skill is set here, not in the polish.

Keep it proportional: a Refine task needs one sentence on the angle it keeps; a new product needs
this whole pass, before any research for references.

## 1. Live the moment

Write the moment of truth as the person lives it, in plain words, before and after:

- **Before**: where they are, what they are doing, what they are worried about or putting off, what
  it costs them. ("Sunday night, Priya opens the banking app to see if rent cleared, again, because
  last month it bounced and her landlord texted before she knew.")
- **After**: what changed, and how they feel. ("She never checks. On the 1st her phone says 'Rent
  paid, all square with Arun' and she goes back to her evening.")
- **The tell-a-friend line**: the sentence they would say about it to someone else. If you cannot
  write one, there is no angle yet.

For agents, the moment is a call: what the agent is trying to do, what it has to guess today, and
what the call returns. An agent's delight is **zero guesses**: it completes a task it has never
seen from the descriptions alone. A guess in a consequential action is the agent version of a
joyless product.

## 2. Where joy comes from

Joy is earned by the need. Use these sources; never bolt delight on.

| Source | What it feels like | Example |
| --- | --- | --- |
| **Relief** | A worry removed at the moment it is felt | "Nothing needs you today" before standup |
| **Competence** | "I did that, and it was easy" | One gesture that does exactly what the hand expected |
| **Being understood** | It anticipated me, without being creepy | The form remembers the hard part and asks only the new part |
| **Earned surprise** | A detail that rewards attention | The settle animation that draws a ledger line |
| **Connection** | It brings people closer, not into conflict | Two partners sign one money note |
| **Play** | Lightness that never costs time | A pull-to-refresh that is fun on the hundredth pull |
| **Respect** | It does not waste me or trick me | A cancel that is as easy as the sign-up |

Not joy: confetti on routine actions, cuteness that delays the task, streaks and guilt for adults
who did not ask, celebration of spending, and any delight that a person in distress would find
tone-deaf. Design the hard moment (the failed payment, the bad news) with as much care as the happy
one; that is where trust is won.

## 3. Question the touchpoint

Before designing anything new, ask whether the need is better met with less:

- Could a default, a removed step, or a better order of steps meet it?
- Could an agent or the system do it in the background and report only exceptions?
- Could one message at the right moment replace a screen people have to visit? Send it where the
  person already is (Slack, WhatsApp, the lock screen), not a channel you assume.
- Could it live inside a surface people already use (the lock screen, the share sheet, the chat)?
- Who else is in the moment? Close the loop for the person helped at the end (the engineer whose
  blocker got an owner, the partner who signed) with a rendered touchpoint, not only copy.

"No new screen" is a valid, often the best, answer. If you still design the requested touchpoint,
write why checking or visiting it is the job.

## 4. Generate angles fast

Write eight to twelve angles, one line each, before judging any. Use several of these moves:

- **Invert** the category default: do the opposite of what everyone ships.
- **Remove** the screen, the step, the form, or the choice.
- **Change the actor**: the agent does it, the other person does it, the group does it.
- **Change the moment**: before the pain, at the exact moment, or after it is resolved.
- **Change the unit**: the customer, not the invoice; the couple, not the person; the week, not the
  transaction.
- **Borrow an object or ritual** from another domain: a ledger, a carbon copy, a duet, a receipt, a
  boarding pass, a recipe card. Check that its meaning survives (see `taste.md`).
- **Make the invisible visible**, or make the noisy visible thing go away.
- **Design the ending first**: what is the last thing they see, and work back.
- **Add a hard constraint**: one tap, no text, offline only, voice only, thirty seconds.
- **Design for the extreme user**: a screen-reader user, a nine-year-old, someone in a hurry, an
  agent with no eyes. Angles that serve them often serve everyone.
- **Make it a gift**: what would it be if someone made it by hand for this person?

## 5. Choose

Score each angle 1 to 5 on **truth** (serves the job and the hard moment), **distance** (how far it
is from the category default), and **feasibility** (this team, this platform, this budget). Pick
the angle with the best truth and distance that is still feasible; keep a safe angle as a fallback.
Then test it:

- **Hindsight**: once explained, would a senior designer say "of course"? If not, it is novelty,
  not an angle.
- **Nearest analogue**: search for the mechanic itself outside the category ("answer privately,
  reveal together", "agenda that ends when every item has an owner") and name the closest thing
  that exists. Distance is claimed against it, not only against the category.
- **Connotation**: read the metaphor as the most reluctant actor would (a partner who did not choose
  the app, the person being assigned work). A contract can read as a prenup; a receipt as a bill.
- **Proof state**: name the state that proves the angle (the reveal, the live meeting). It gets the
  most design, and the change it shows is legible at thumbnail size, not a hairline.

Write it into `.design/BRIEF.md`; `design_kit.py check` requires this section when `BRIEF.md`
exists:

```markdown
## Angle
Moment before: <the scene, as lived>
Moment after: <what changed and how it feels>
Tell a friend: "<the sentence they would say>"
Category default: <what any team would ship>
Touchpoint question: <could less do it? what you decided and why>
Angles considered:
- <angle> (truth 4, distance 2, feasibility 5)
- ... eight to twelve lines
Chosen angle: <one sentence> because <reason tied to the job>
Fallback: <the safe angle>
```

The chosen angle drives everything after it: the board looks for references that serve it, the
directions are ways of expressing it, and the critic checks that the shipped states still carry it.
