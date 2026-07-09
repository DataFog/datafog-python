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

LiteLLM releases with the native DataFog provider can use the shorter
registration below:

```yaml
guardrails:
  - guardrail_name: "datafog-pii"
    litellm_params:
      guardrail: datafog
      mode: ["pre_call", "post_call"]
      default_on: true
      datafog_action: "redact"
```

The bundled `config.yaml` uses DataFog's compatibility class so it also works
with older LiteLLM releases and supports DataFog-specific allowlists.

With `action: redact` (default), a request containing

> email the report to jane.doe@example.invalid

reaches your model provider as

> email the report to [EMAIL_1]

Request scanning covers chat messages, Responses API input and instructions,
text-completion prompts, tool arguments, tool definitions, legacy functions,
and structured-output schemas. Response scanning covers chat and text
completions, Responses API output, Anthropic content, tool-call arguments, and
streaming output. Streaming responses are buffered until the complete text can
be checked, so no partial PII is yielded before detection.

Response-side redaction only runs when `post_call` is included in `mode` (the
example config registers both: `mode: ["pre_call", "post_call"]`). With it,
PII in model _responses_ is redacted before reaching the client.

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
- `allowlist`: exact entity values that should remain unchanged
- `allowlist_patterns`: full-match regular expressions for known-safe values;
  treat these as trusted operator configuration, not user input
- `locales`: locale packs to enable, such as `["de"]` for German identifiers

The compatibility class also accepts the native provider's prefixed forms:
`datafog_action`, `datafog_entity_types`, `datafog_fail_policy`,
`datafog_allowlist`, `datafog_allowlist_patterns`, and `datafog_locales`.
