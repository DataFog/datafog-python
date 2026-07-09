# DataFog PII Scrubbing for Sentry

Scrub PII from every Sentry event before it leaves your process — offline,
in-process, microseconds per string scanned.

## Why this over Sentry's built-in scrubbing

|                  | DataFog integration                        | Sentry `EventScrubber`            | Server-side scrubbing            |
| ---------------- | ------------------------------------------ | --------------------------------- | -------------------------------- |
| Detection        | content-based (validated regex)            | sensitive *key names* only        | basic regexes, no phone detector |
| Where it runs    | in your process, pre-egress                | in your process                   | after data reaches Sentry        |
| Catches          | PII inside messages, exception text, local variables, breadcrumbs | values under keys like `password` | whatever survives the SDK        |

Sentry's client-side `EventScrubber` never inspects values: an email in an
exception message, an SSN in a stack-frame local, or a card number in a
breadcrumb sails straight through. Server-side scrubbing inspects content,
but only after the data has already left your machine.

## Install

```bash
pip install datafog[sentry]        # or: pip install datafog sentry-sdk
```

```python
import sentry_sdk
from datafog.integrations.sentry import DataFogSentryIntegration

sentry_sdk.init(
    dsn="https://...@o0.ingest.sentry.io/0",
    integrations=[DataFogSentryIntegration()],
)
```

An exception message like

> could not send reset link to jane.doe@example.invalid

arrives in Sentry as

> could not send reset link to [EMAIL_1]

The integration registers a global event processor, so it covers both error
events and transactions (span descriptions and data), and your own
`before_send` stays free — it runs after the scrub and sees clean events.

Prefer explicit wiring? The scrubber is also a drop-in `before_send`:

```python
from datafog.integrations.sentry import scrub_event

sentry_sdk.init(dsn="...", before_send=scrub_event)
```

## What gets scrubbed

Every string value in the event, including:

- `message` / `logentry` and exception values
- **stack-frame local variables** (`include_local_variables` is on by
  default in sentry-sdk — every error event snapshots live values)
- breadcrumbs (messages and data — log lines, SQL, HTTP query strings)
- request URL, headers, cookies, and body
- `extra`, `tags`, `user`, and contexts
- span descriptions and data in transactions

Machine identifiers (`event_id`, `release`, `environment`, `sdk`,
`modules`, ...) are never touched.

## Options

```python
DataFogSentryIntegration(
    entity_types=["EMAIL", "PHONE", "CREDIT_CARD", "SSN"],  # default set
    allowlist=["support@yourco.example"],   # exact values to exempt
    allowlist_patterns=[r".*@yourco\.example"],  # full-match regexes
    fail_policy="open",                     # or "closed"
)
```

- `entity_types`: defaults to `EMAIL, PHONE, CREDIT_CARD, SSN`; noisier
  types (`IP_ADDRESS`, `DOB`, `ZIP`) are opt-in
- `allowlist` / `allowlist_patterns`: exempt known-safe values (your own
  support address, test fixtures) from redaction
- `fail_policy`: `open` (engine error → event is sent unscanned, so a
  scrubber bug never costs you crash reports) or `closed` (engine error →
  event is dropped; for compliance deployments where unscanned egress is
  worse than a missing event)

Findings are reported as entity-type counts only — matched values are never
echoed into logs or exceptions.
