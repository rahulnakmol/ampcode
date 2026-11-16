---
decision: Approve moving the sales demo website from the office computer to a paid hosting service.
yes: The agent moves the demo site this week. Sales staff use a new web address from Monday.
no: The demo site stays on the office computer. It stops working when that computer is off.
risks:
  - The demo site is offline for up to one hour during the move.
  - Old links in sent emails stop working after 30 days.
  - The hosting service costs 25 US dollars each month.
excluded:
  - The main company website.
  - Customer data. The demo site uses invented data only.
  - A custom domain name. That is a separate decision.
---

## You are deciding

Approve moving the sales demo website to a paid hosting service. Today the site runs on one computer in the office. When someone turns that computer off, the demo stops working. Last month this happened during two customer calls.

## If you say yes

- The agent copies the demo site to the hosting service this week.
- The agent tests the new address and sends it to the sales team.
- From Monday, sales staff use the new address.

**What it costs you:** 25 US dollars each month, paid by card. Your time: this approval and five minutes to try the new address.

## If you say no

Nothing changes. The demo site stays on the office computer. It still stops when that computer is off or restarts.

## What changes

1. The demo site runs on the hosting service, not on the office computer.
2. The site has a new web address.
3. The old address sends visitors to the new one for 30 days. After that, the old address stops.
4. The office computer no longer needs to stay on at night.

## What done looks like

1. The new address opens the demo site from a phone and from a laptop outside the office.
2. The site stays up when the office computer is off.
3. The old address sends visitors to the new one.
4. The monthly bill shows 25 US dollars.

## What we checked and what we did not

**Checked:** the hosting service runs this kind of site. A test copy worked for one day. The site holds no customer data.

**Not checked:** how fast the site is for visitors in Asia. We will check this after the move.

## Risks you accept

- The demo site is offline for up to one hour during the move.
- Old links in sent emails stop working after 30 days.
- The hosting service costs 25 US dollars each month.

## Not included

- The main company website.
- Customer data. The demo site uses invented data only.
- A custom domain name. That is a separate decision.

## How to undo it

The agent turns the office computer back on and points the old address back to it. This takes about ten minutes. Then cancel the hosting plan. You pay for the current month only.

## Words you may not know

- **Hosting service:** a company that runs websites on its own computers, all day and night.
- **Web address:** the text you type in a browser to open a site.
- **Custom domain name:** a web address with the company's own name in it, such as a shop name.
- **The agent:** the AI assistant that does the work. A person checks the result.

<details><summary>Technical record</summary>

- Mission: demo-hosting (synthetic example; no real system).
- Current host: office workstation, static site served on port 8080.
- Target: managed static hosting, plan "Starter", 25 USD per month.
- Redirect: HTTP 301 from the old address for 30 days.
- Acceptance IDs: DH-1 to DH-4 map to "What done looks like" items 1 to 4.

</details>
