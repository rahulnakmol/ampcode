# Design: appointment reminders by SMS

Intent: confirmed brief "Clinic reminders" (confirmed 9 November 2026)
Status: draft

The clinic booking system sends each patient an SMS reminder 24 hours before an appointment.
Patients can reply "C" to confirm or "X" to cancel. Clinic staff see the replies in the booking
web app.

## Context

| Actor or system | Uses | Through |
| --- | --- | --- |
| Patient | SMS on their own phone | Mobile network, via the SMS provider |
| Clinic receptionist | Booking web app | Browser over HTTPS, clinic single sign-on |
| SMS provider (third party) | Reminder API, reply webhook | HTTPS; API key for sends, shared HMAC secret for webhooks |

## Containers

| Container | Technology | Owns |
| --- | --- | --- |
| Booking API | Node.js 22 service | Appointments, patients (name, mobile number, clinic, appointment time) |
| Reminder scheduler | Node.js worker, runs every 5 minutes | Picks appointments due in 24 hours, sends reminders |
| Reply webhook | Endpoint inside the Booking API | Receives patient replies from the SMS provider |
| Booking database | PostgreSQL 16, private subnet | Appointments, patients, reminder log |

## Contracts

| Contract | Kind | Producer | Consumer | Shape and compatibility |
| --- | --- | --- | --- | --- |
| Send SMS | Provider HTTP API | Reminder scheduler | SMS provider | `{to, body}`; body: "Reminder: <clinic> on <date> at <time>. Reply C to confirm, X to cancel." |
| Reply webhook | HTTP POST | SMS provider | Booking API | `{from, body, receivedAt}`, HMAC-SHA256 signature header; unknown fields ignored |
| Reminder log | Table | Reminder scheduler | Booking API | appointment ID, sent time, provider message ID, reply |

## Decisions

### ADR-1: Use a third-party SMS provider

Status: accepted
Options:
- Third-party SMS provider
- Email reminders only
Decision: SMS provider; most patients do not read email in time.
Consequences: Patient mobile numbers and appointment times leave our network.

## Non-functional requirements

| ID | Quality | Target | Verification |
| --- | --- | --- | --- |
| NFR-1 | Timeliness | 99 % of reminders sent within 10 min of the 24-hour mark | Daily report from the reminder log |
| NFR-2 | Retention | Reminder log rows deleted within 90 days | Scheduled job test; weekly count of rows older than 90 days |

## Trust boundaries

Trust boundaries change: yes
Threat model: docs/threat-models/sms-reminders.md

## Known facts for the model

- The clinic's data protection officer is Amara Okafor. The head of engineering is Tom Becker.
- The backlog uses grooming IDs; the next free bug ID is B-40.
- No test of the webhook signature check exists yet.
