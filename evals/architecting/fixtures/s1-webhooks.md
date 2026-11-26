# Confirmed brief: tenant webhooks

Confirmed by the product owner, Maya Chen, on 10 November 2026.

## Intent

Tenants of our B2B invoicing SaaS want to be told when an invoice is paid, so their own systems
stop polling our API. Today about 40 tenants poll GET /invoices every minute.

## Behaviour

- A tenant administrator registers up to 5 HTTPS endpoints and picks the events
  (`invoice.paid`, `invoice.overdue`).
- We send each event to each subscribed endpoint. The tenant can see delivery attempts for
  30 days and can resend one.
- A tenant must be able to prove a call came from us.
- An endpoint that fails for 24 hours is disabled, and the administrator gets an email.

## Facts

- 1,200 tenants; peak of 30 payments per second across all tenants at month end.
- Stack: ASP.NET Core API on Azure App Service, Azure SQL, Azure Service Bus already in use.
- Two backend engineers; no dedicated operations team.

## Not decided

- Whether to build delivery in-house or use a webhook delivery service.
- How long a tenant may take to respond before we time out.
