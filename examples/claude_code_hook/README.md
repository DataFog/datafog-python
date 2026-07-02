# DataFog PII Firewall for Claude Code

Stop PII from leaving your machine through agent tool calls. This hook scans
every outbound tool invocation (shell commands, web requests, file writes,
MCP tools) in ~70ms and asks for confirmation — or blocks outright — when it
finds emails, phone numbers, credit cards, or SSNs.

## Install

```bash
pip install datafog
```

Then add the hook to `~/.claude/settings.json` (all projects) or
`.claude/settings.json` (one project):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|WebFetch|WebSearch|Write|Edit|mcp__.*",
        "hooks": [
          {"type": "command", "command": "datafog-hook", "timeout": 10}
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {"type": "command", "command": "datafog-hook", "timeout": 10}
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Read|Bash|WebFetch|mcp__.*",
        "hooks": [
          {"type": "command", "command": "datafog-hook", "timeout": 10}
        ]
      }
    ]
  }
}
```

That's it. Try asking Claude to `curl` something containing a test credit
card number — the call is intercepted before it runs:

> DataFog PII firewall: Bash input contains CREDIT_CARD x1, EMAIL x1.
> Redact or tokenize these values before sending them anywhere.

## What each hook does

| Event | Behavior |
|---|---|
| `PreToolUse` | Gates the tool call. Default `ask` shows you what was found; `deny` blocks and tells Claude to redact and retry. |
| `UserPromptSubmit` | Non-blocking. Warns Claude your prompt contains PII so it avoids repeating it into files, code, or logs. |
| `PostToolUse` | Non-blocking. Warns when a tool result (file read, API response) carries PII into the conversation. |

## Configuration

Environment variables (set in `settings.json` `env` or your shell):

- `DATAFOG_HOOK_ACTION` — `ask` (default) or `deny` for PreToolUse.
  **Important:** `ask` defers to your permission mode — in
  `--dangerously-skip-permissions` or auto-accept sessions, the ask is
  silently approved and nothing is intercepted. If you run with permissions
  relaxed (exactly when you most need a firewall), use `deny`:

  ```json
  {"type": "command", "command": "DATAFOG_HOOK_ACTION=deny datafog-hook", "timeout": 10}
  ```

  In `deny` mode the tool call is hard-blocked before it executes, the
  model is told what was found, and it self-corrects by redacting.
- `DATAFOG_HOOK_ENTITIES` — comma-separated entity types. Default:
  `EMAIL,PHONE,CREDIT_CARD,SSN`. Noisier types (`IP_ADDRESS`, `DOB`, `ZIP`)
  are available but opt-in — version strings, dates, and 5-digit numbers are
  everywhere in coding sessions.

## Design notes

- **Offline.** DataFog's core makes zero network calls and has one
  dependency (pydantic). Nothing about your session leaves your machine.
- **Fast.** ~70ms per invocation including process startup; the scan itself
  is microseconds.
- **Fail-open.** A bug in the hook exits non-blocking — it will never brick
  your Claude Code session. The flip side: a hook failure means that call
  went unscanned, so treat this as a seatbelt, not a guarantee.
- **Bounded scanning.** Each string is scanned up to 1MB (8MB per payload
  total). PII hidden beyond those caps in a single enormous field is missed
  by design — the hook must stay fast enough to run on every tool call.
- **No PII in output.** Findings are reported as type counts
  (`EMAIL x2`), never as the matched values — hook output itself lands in
  transcripts.
