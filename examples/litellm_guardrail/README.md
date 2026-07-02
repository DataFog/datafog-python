# DataFog PII Guardrail for LiteLLM

Redact PII from every LLM request and response passing through your LiteLLM
proxy — offline, in-process, microseconds per scan.

## Why this over the Presidio guardrail

|                    | DataFog                                   | Presidio integration               |
| ------------------ | ----------------------------------------- | ---------------------------------- |
| Deployment         | in-process, `pip install datafog litellm` | separate sidecar service           |
| Extra dependencies | pydantic only                             | spaCy + models                     |
| Latency per scan   | microseconds                              | tens of milliseconds + network hop |
| Network calls      | none                                      | HTTP to the sidecar                |

## Install

```bash
pip install datafog litellm
litellm --config config.yaml   # see config.yaml in this directory
```

With `action: redact` (default), a request containing

> email the report to jane.doe@example.invalid

reaches your model provider as

> email the report to [EMAIL_1]

Response-side redaction only runs when `post_call` is included in `mode`
(the example config registers both: `mode: ["pre_call", "post_call"]`).
With it, PII in model _responses_ is redacted before reaching the client.

In `block` mode, rejected requests return **HTTP 400** with an entity-type
summary — litellm classifies them as guardrail interventions, not backend
errors, so monitoring stays accurate.

## Options

- `action`: `redact` (rewrite in place) or `block` (reject the request with
  an entity-type summary — matched values are never echoed)
- `entity_types`: defaults to `EMAIL, PHONE, CREDIT_CARD, SSN`; noisier
  types (`IP_ADDRESS`, `DOB`, `ZIP`) are opt-in
- `fail_policy`: `open` (engine error → traffic passes unscanned, gateway
  stays up) or `closed` (engine error → traffic rejected; for compliance
  deployments where unscanned egress is worse than downtime)
