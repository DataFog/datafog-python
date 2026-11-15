"""Review regressions for request/response coverage and safe stream failures."""

# ruff: noqa: E402
# Optional proxy dependencies must be present before importing the adapter.
import copy
import json

import pytest

pytest.importorskip("litellm")
pytest.importorskip("fastapi")
from fastapi import HTTPException  # noqa: E402
from litellm import ModelResponseStream  # noqa: E402
from litellm.types.utils import Delta, StreamingChoices  # noqa: E402

import datafog  # noqa: E402
from datafog.integrations import claude_code as hook  # noqa: E402
from datafog.integrations import litellm_guardrail as gateway  # noqa: E402

EMAIL_A = "alice@" "example.com"
EMAIL_B = "bob@" "example.com"
SSN = "123-45-" "6789"


def guard(**kwargs):
    return gateway.DataFogGuardrail(guardrail_name="review", **kwargs)


async def pre(adapter, data):
    return await adapter.async_pre_call_hook(None, None, data, "completion")


async def source(chunks):
    for chunk in chunks:
        yield chunk


async def streamed(adapter, chunks):
    return [
        chunk
        async for chunk in adapter.async_post_call_streaming_iterator_hook(
            None, source(chunks), {}
        )
    ]


@pytest.mark.asyncio
async def test_request_shares_tokens_without_existing_token_collisions():
    original = {
        "messages": [
            {"role": "user", "content": f"[EMAIL_1] {EMAIL_A}"},
            {"role": "user", "content": f"other {EMAIL_B}; same {EMAIL_A}"},
        ],
        "prompt": EMAIL_B,
        "input": [{"content": EMAIL_A}],
    }
    before = copy.deepcopy(original)
    result = await pre(guard(), original)
    assert result["messages"][0]["content"] == "[EMAIL_1] [EMAIL_2]"
    assert result["messages"][1]["content"] == "other [EMAIL_3]; same [EMAIL_2]"
    assert (
        result["prompt"] == "[EMAIL_3]" and result["input"][0]["content"] == "[EMAIL_2]"
    )
    assert original == before
    another = await pre(guard(), {"prompt": EMAIL_A})
    assert another["prompt"] == "[EMAIL_1]"


@pytest.mark.asyncio
async def test_request_scans_tool_arguments_and_structured_input_values():
    data = {
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "save",
                            "arguments": json.dumps({"email": EMAIL_A, "ssn": SSN}),
                        },
                    }
                ],
            }
        ],
        "input": {"name": EMAIL_B, "id": SSN, "url": "send " + EMAIL_A},
    }
    result = await pre(guard(), data)
    assert (
        EMAIL_A not in result["messages"][0]["tool_calls"][0]["function"]["arguments"]
    )
    assert SSN not in result["messages"][0]["tool_calls"][0]["function"]["arguments"]
    assert result["input"] == {
        "name": "[EMAIL_2]",
        "id": "[SSN_1]",
        "url": "send [EMAIL_1]",
    }
    assert result["messages"][0]["tool_calls"][0]["id"] == "call_1"


@pytest.mark.asyncio
async def test_multimodal_media_remains_intact_and_text_is_scanned():
    image = {
        "type": "image_url",
        "image_url": {
            "url": "data:image/png;base64,AA4242424242424242",
            "detail": "high",
        },
    }
    audio = {
        "type": "input_audio",
        "input_audio": {"data": "4242424242424242", "format": "wav"},
    }
    result = await pre(
        guard(),
        {
            "messages": [
                {
                    "role": "user",
                    "content": [image, audio, {"type": "text", "text": EMAIL_A}],
                }
            ]
        },
    )
    assert result["messages"][0]["content"][:2] == [image, audio]
    assert result["messages"][0]["content"][2]["text"] == "[EMAIL_1]"


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["messages", "prompt", "input"])
async def test_surrogate_cannot_disable_blocking(field):
    value = f"ssn {SSN} \ud83d"
    data = (
        {field: [{"role": "user", "content": value}]}
        if field == "messages"
        else {field: value}
    )
    with pytest.raises(HTTPException) as error:
        await pre(guard(action="block"), data)
    assert error.value.status_code == 400 and SSN not in str(error.value.detail)


@pytest.mark.asyncio
async def test_response_reserves_tokens_in_tools_and_covers_legacy_and_text():
    response = {
        "choices": [
            {
                "index": 0,
                "message": {
                    "content": EMAIL_A,
                    "tool_calls": [
                        {
                            "function": {
                                "name": "save",
                                "arguments": f"[EMAIL_1] {EMAIL_B}",
                            }
                        }
                    ],
                },
            },
            {
                "index": 1,
                "message": {
                    "content": None,
                    "function_call": {"name": "old", "arguments": EMAIL_A},
                },
            },
            {"index": 2, "text": EMAIL_B},
        ]
    }
    result = await guard().async_post_call_success_hook({}, None, response)
    assert result is response
    assert result["choices"][0]["message"]["content"] == "[EMAIL_2]"
    assert (
        result["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
        == "[EMAIL_1] [EMAIL_3]"
    )
    assert result["choices"][1]["message"]["function_call"]["arguments"] == "[EMAIL_2]"
    assert result["choices"][2]["text"] == "[EMAIL_3]"


@pytest.mark.asyncio
@pytest.mark.parametrize("policy", ["open", "closed"])
async def test_response_scanning_is_atomic_and_respects_fail_policy(
    monkeypatch, policy
):
    actual = gateway._redact_text

    def failing(text, *args, **kwargs):
        if text == "second":
            raise RuntimeError(EMAIL_A)
        return actual(text, *args, **kwargs)

    monkeypatch.setattr(gateway, "_redact_text", failing)
    response = {
        "choices": [
            {"message": {"content": EMAIL_A}},
            {"message": {"content": "second"}},
        ]
    }
    before = copy.deepcopy(response)
    if policy == "closed":
        with pytest.raises(RuntimeError) as error:
            await guard(fail_policy=policy).async_post_call_success_hook(
                {}, None, response
            )
        assert EMAIL_A not in str(error.value)
    else:
        assert (
            await guard(fail_policy=policy).async_post_call_success_hook(
                {}, None, response
            )
            is response
        )
    assert response == before


@pytest.mark.asyncio
async def test_stream_scans_all_choice_and_tool_argument_fragments():
    chunks = [
        {
            "id": "first",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": "[EMAIL_1] alice@",
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_a",
                                "function": {
                                    "name": "save",
                                    "arguments": '{"ssn":"123-',
                                },
                            },
                            {
                                "index": 1,
                                "id": "call_b",
                                "function": {"name": "save", "arguments": "bob@"},
                            },
                        ],
                    },
                },
                {
                    "index": 1,
                    "delta": {
                        "content": "bob@",
                        "function_call": {"name": "old", "arguments": "alice@"},
                    },
                },
                {"index": 2, "text": "bob@"},
            ],
        },
        {
            "id": "last",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": "example.com",
                        "tool_calls": [
                            {"index": 0, "function": {"arguments": '45-6789"}'}},
                            {"index": 1, "function": {"arguments": "example.com"}},
                        ],
                    },
                    "finish_reason": "tool_calls",
                },
                {
                    "index": 1,
                    "delta": {
                        "content": "example.com",
                        "function_call": {"arguments": "example.com"},
                    },
                    "finish_reason": "stop",
                },
                {"index": 2, "text": "example.com", "finish_reason": "stop"},
            ],
        },
    ]
    original = copy.deepcopy(chunks)
    output = await streamed(guard(), chunks)
    first, last = output
    assert first["choices"][0]["delta"]["content"] == "[EMAIL_1] [EMAIL_2]"
    calls = first["choices"][0]["delta"]["tool_calls"]
    assert calls[0]["function"]["arguments"] == '{"ssn":"[SSN_1]"}'
    assert calls[1]["function"]["arguments"] == "[EMAIL_3]"
    assert first["choices"][1]["delta"]["content"] == "[EMAIL_3]"
    assert first["choices"][1]["delta"]["function_call"]["arguments"] == "[EMAIL_2]"
    assert first["choices"][2]["text"] == "[EMAIL_3]"
    assert last["choices"][0]["delta"]["content"] == ""
    assert last["choices"][0]["delta"]["tool_calls"][0]["function"]["arguments"] == ""
    assert last["choices"][0]["finish_reason"] == "tool_calls"
    assert chunks == original
    assert first["id"] == "first" and last["id"] == "last"


@pytest.mark.asyncio
async def test_stream_handles_real_litellm_native_chunks():
    chunks = [
        ModelResponseStream(
            id="same", choices=[StreamingChoices(index=0, delta=Delta(content=part))]
        )
        for part in ("alice@", "example.com")
    ]
    output = await streamed(guard(), chunks)
    assert output[0].choices[0].delta.content == "[EMAIL_1]"
    assert output[1].choices[0].delta.content == ""
    assert chunks[0].choices[0].delta.content == "alice@"


@pytest.mark.asyncio
async def test_stream_snapshots_reused_mutable_chunks():
    async def reused():
        chunk = {"choices": [{"index": 0, "delta": {"content": "alice@"}}]}
        yield chunk
        chunk["choices"][0]["delta"]["content"] = "example.com"
        yield chunk

    output = [
        chunk
        async for chunk in guard().async_post_call_streaming_iterator_hook(
            None, reused(), {}
        )
    ]
    assert output[0]["choices"][0]["delta"]["content"] == "[EMAIL_1]"
    assert output[1]["choices"][0]["delta"]["content"] == ""


@pytest.mark.asyncio
@pytest.mark.parametrize("policy", ["open", "closed"])
async def test_stream_source_errors_emit_nothing_and_hide_provider_text(policy):
    async def broken():
        yield {"choices": [{"delta": {"content": EMAIL_A}}]}
        raise RuntimeError("provider failed on " + EMAIL_A)

    emitted = []
    with pytest.raises(RuntimeError) as error:
        async for chunk in guard(
            fail_policy=policy
        ).async_post_call_streaming_iterator_hook(None, broken(), {}):
            emitted.append(chunk)
    assert not emitted and EMAIL_A not in str(error.value)
    assert error.value.__cause__ is None and error.value.__suppress_context__


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", ["MAX_STREAM_CHARS", "MAX_STREAM_CHUNKS"])
async def test_stream_limits_reject_without_emission(monkeypatch, limit):
    monkeypatch.setattr(gateway, limit, 1)
    chunks = [{"choices": [{"delta": {"content": "ab"}}]}] * 2
    emitted = []
    with pytest.raises(RuntimeError, match="scan budget"):
        async for chunk in guard().async_post_call_streaming_iterator_hook(
            None, source(chunks), {}
        ):
            emitted.append(chunk)
    assert not emitted


@pytest.mark.asyncio
@pytest.mark.parametrize("policy", ["open", "closed"])
async def test_stream_engine_failures_follow_documented_policy(monkeypatch, policy):
    def failing(*args, **kwargs):
        raise RuntimeError(EMAIL_A)

    monkeypatch.setattr(gateway, "_redact_text", failing)
    chunks = [{"choices": [{"delta": {"content": EMAIL_A}}]}]
    if policy == "open":
        assert await streamed(guard(fail_policy=policy), chunks) == chunks
    else:
        with pytest.raises(RuntimeError, match="fail_policy is 'closed'") as error:
            await streamed(guard(fail_policy=policy), chunks)
        assert EMAIL_A not in str(error.value)


@pytest.mark.parametrize("action", ["ask", "deny"])
def test_hook_oversize_never_silently_allows_unscanned_tail(action):
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"content": "x" * (hook.MAX_SCAN_CHARS + 1) + " " + SSN},
    }
    code, output = hook.run(payload, {"DATAFOG_HOOK_ACTION": action})
    decision = json.loads(output)["hookSpecificOutput"]
    assert code == 0 and decision["permissionDecision"] == action
    assert (
        "not fully scanned" in decision["permissionDecisionReason"]
        and SSN not in output
    )


def test_hook_surrogate_and_total_budget_cannot_disable_pii_gate(monkeypatch):
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_input": {"command": "echo " + SSN, "description": "\udc00"},
    }
    code, output = hook.run(payload, {})
    assert code == 0 and "SSN x1" in output
    monkeypatch.setattr(hook, "TOTAL_SCAN_CHARS", 20)
    code, output = hook.run(
        {"hook_event_name": "PreToolUse", "tool_input": ["a" * 15, "b" * 15]}, {}
    )
    assert (
        code == 0
        and json.loads(output)["hookSpecificOutput"]["permissionDecision"] == "ask"
    )


@pytest.mark.asyncio
async def test_decorator_awaits_and_rejects_non_string_returns():
    adapter = datafog.create_guardrail()

    @adapter
    async def generated():
        return EMAIL_A

    assert await generated() == "[EMAIL_1]"

    @adapter
    async def structured():
        return [EMAIL_A]

    with pytest.raises(TypeError, match="must return a string"):
        await structured()

    @adapter
    def sync_structured():
        return {"text": EMAIL_A}

    with pytest.raises(TypeError, match="must return a string"):
        sync_structured()
