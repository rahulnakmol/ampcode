# Mission owner acknowledgment

Acknowledge design before proceeding.

Mission requirements: Keep the sales demo website available when the office computer is off, at a known monthly cost. Synthetic example; no real system.

Design: a65ec13bf6a882bb990fa16d8fb43ddb1f5b61e5783e6624667e82edffcbf440

{
  "spec": "Move the static demo site to managed hosting; keep a 30-day redirect from the old address; no customer data.",
  "plan": "Copy the site, test the new address, switch the redirect, tell the sales team, turn off the office server after a week.",
  "technical": "Static files built by the existing script and uploaded to the host; HTTP 301 redirect on the old host for 30 days.",
  "ux": "Sales staff get the new address by email and in the team chat; no other change for visitors."
}

1. The new address opens the demo site from a phone and from a laptop outside the office.
Not yet verified

2. The site stays up when the office computer is off.
Not yet verified

3. The old address sends visitors to the new one for 30 days.
Not yet verified

4. The monthly bill shows 25 US dollars.
Not yet verified

Try it: Not yet supplied

Customer value: Not yet established

Merge preference: auto; high risk always requires owner acknowledgment.

Approvals and evidence are local workflow gates, not a hostile-shell security boundary. Required CI and protected dev must also permit integration.

Only the thread owner may approve/adopt this mission. Type ACKNOWLEDGE. This is not a password or credential; the masked field restricts the dialog to the owner.

Field: Type ACKNOWLEDGE (not a secret)
