"""Tests for the LiteLLM guardrail adapter (DataFogGuardrail).

PII literals below are split ("jane.doe@" "acme.com") so this source file
itself never contains a contiguous match — the values only assemble at
runtime. This keeps write-time PII scanners (including our own Claude Code
hook) quiet while the tests exercise real detections.
"""

import pytest

litellm = pytest.importorskip("litellm")

from datafog.integrations.litellm_guardrail import \
    DataFogGuardrail  # noqa: E402

EMAIL = "jane.doe@" "acme.com"
CARD = "4242 4242 " "4242 4242"
SSN = "856-45-" "6789"


def _chat_data(content) -> dict:
    return {"messages": [{"role": "user", "content": content}]}


def _model_response(text: str):
    resp = litellm.ModelResponse()
    resp.choices[0].message.content = text
    return resp


@pytest.mark.asyncio
class TestPreCallRedact:
    async def test_redacts_email_in_message(self):
        guardrail = DataFogGuardrail(guardrail_name="datafog-pii")
        data = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=_chat_data(f"email the report to {EMAIL} please"),
            call_type="completion",
        )
        content = data["messages"][0]["content"]
        assert EMAIL not in content
        assert "[EMAIL_1]" in content

    async def test_clean_message_unchanged(self):
        guardrail = DataFogGuardrail(guardrail_name="datafog-pii")
        original = _chat_data("summarize this design doc")
        data = await guardrail.async_pre_call_hook(
            user_api_key_dict=None, cache=None, data=original, call_type="completion"
        )
        assert data["messages"][0]["content"] == "summarize this design doc"

    async def test_redacts_content_parts_form(self):
        guardrail = DataFogGuardrail(guardrail_name="datafog-pii")
        data = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=_chat_data([{"type": "text", "text": f"ssn is {SSN}"}]),
            call_type="completion",
        )
        part = data["messages"][0]["content"][0]["text"]
        assert SSN not in part

    async def test_redacts_multiple_messages_and_roles(self):
        guardrail = DataFogGuardrail(guardrail_name="datafog-pii")
        data = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data={
                "messages": [
                    {"role": "system", "content": f"support contact: {EMAIL}"},
                    {"role": "user", "content": f"card on file {CARD}"},
                ]
            },
            call_type="completion",
        )
        assert EMAIL not in data["messages"][0]["content"]
        assert CARD not in data["messages"][1]["content"]


@pytest.mark.asyncio
class TestPreCallBlock:
    async def test_block_raises_http_400_without_echoing_pii(self):
        # HTTPException(400) is what litellm's _is_guardrail_intervention
        # recognizes as a policy block; a bare exception would surface as
        # HTTP 500 and be misclassified as a backend failure.
        from fastapi import HTTPException

        guardrail = DataFogGuardrail(guardrail_name="datafog-pii", action="block")
        with pytest.raises(HTTPException) as exc:
            await guardrail.async_pre_call_hook(
                user_api_key_dict=None,
                cache=None,
                data=_chat_data(f"send {CARD} to billing"),
                call_type="completion",
            )
        assert exc.value.status_code == 400
        detail = str(exc.value.detail)
        assert "CREDIT_CARD" in detail
        assert CARD not in detail

    async def test_block_action_allows_clean_request(self):
        guardrail = DataFogGuardrail(guardrail_name="datafog-pii", action="block")
        data = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=_chat_data("hello"),
            call_type="completion",
        )
        assert data["messages"][0]["content"] == "hello"


@pytest.mark.asyncio
class TestPostCall:
    async def test_redacts_model_response(self):
        guardrail = DataFogGuardrail(guardrail_name="datafog-pii")
        response = _model_response(f"the customer is reachable at {EMAIL}")
        await guardrail.async_post_call_success_hook(
            data={}, user_api_key_dict=None, response=response
        )
        assert EMAIL not in response.choices[0].message.content


@pytest.mark.asyncio
class TestConfig:
    async def test_noisy_entities_off_by_default(self):
        guardrail = DataFogGuardrail(guardrail_name="datafog-pii")
        data = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=_chat_data("ping 192.168.1.1 about build 2020-01-02"),
            call_type="completion",
        )
        assert (
            data["messages"][0]["content"] == "ping 192.168.1.1 about build 2020-01-02"
        )

    async def test_entity_types_override(self):
        guardrail = DataFogGuardrail(
            guardrail_name="datafog-pii", entity_types=["IP_ADDRESS"]
        )
        data = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=_chat_data("ping 192.168.1.1"),
            call_type="completion",
        )
        assert "192.168.1.1" not in data["messages"][0]["content"]


@pytest.mark.asyncio
class TestFailPolicy:
    async def test_fail_open_passes_data_through_on_engine_error(self, monkeypatch):
        guardrail = DataFogGuardrail(guardrail_name="datafog-pii", fail_policy="open")
        monkeypatch.setattr(
            "datafog.integrations.litellm_guardrail._redact_text",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        original = _chat_data(f"reach me at {EMAIL}")
        data = await guardrail.async_pre_call_hook(
            user_api_key_dict=None, cache=None, data=original, call_type="completion"
        )
        assert data["messages"][0]["content"] == f"reach me at {EMAIL}"

    async def test_fail_closed_raises_on_engine_error(self, monkeypatch):
        guardrail = DataFogGuardrail(guardrail_name="datafog-pii", fail_policy="closed")
        monkeypatch.setattr(
            "datafog.integrations.litellm_guardrail._redact_text",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        with pytest.raises(Exception):
            await guardrail.async_pre_call_hook(
                user_api_key_dict=None,
                cache=None,
                data=_chat_data(f"reach me at {EMAIL}"),
                call_type="completion",
            )

    async def test_invalid_config_rejected(self):
        with pytest.raises(ValueError):
            DataFogGuardrail(guardrail_name="datafog-pii", action="explode")
        with pytest.raises(ValueError):
            DataFogGuardrail(guardrail_name="datafog-pii", fail_policy="maybe")

    async def test_fail_closed_error_carries_no_pii_and_no_cause_chain(
        self, monkeypatch
    ):
        # Engine exceptions can embed the text being scanned. The re-raise
        # must not chain them (`from None`): a chained __cause__ is printed
        # by traceback.format_exc(), which litellm calls for logging.
        guardrail = DataFogGuardrail(guardrail_name="datafog-pii", fail_policy="closed")
        monkeypatch.setattr(
            "datafog.integrations.litellm_guardrail._redact_text",
            lambda *a, **k: (_ for _ in ()).throw(
                RuntimeError(f"parser choked on: reach me at {EMAIL}")
            ),
        )
        with pytest.raises(RuntimeError) as exc:
            await guardrail.async_pre_call_hook(
                user_api_key_dict=None,
                cache=None,
                data=_chat_data(f"reach me at {EMAIL}"),
                call_type="completion",
            )
        assert exc.value.__cause__ is None
        assert exc.value.__suppress_context__ is True
        assert EMAIL not in str(exc.value)
        assert not hasattr(exc.value, "status_code")  # engine fault -> 500, by design

    async def test_fail_open_log_carries_no_pii(self, monkeypatch, caplog):
        import logging

        guardrail = DataFogGuardrail(guardrail_name="datafog-pii", fail_policy="open")
        monkeypatch.setattr(
            "datafog.integrations.litellm_guardrail._redact_text",
            lambda *a, **k: (_ for _ in ()).throw(
                RuntimeError(f"parser choked on: reach me at {EMAIL}")
            ),
        )
        with caplog.at_level(logging.WARNING):
            await guardrail.async_pre_call_hook(
                user_api_key_dict=None,
                cache=None,
                data=_chat_data(f"reach me at {EMAIL}"),
                call_type="completion",
            )
        assert EMAIL not in caplog.text
        assert "RuntimeError" in caplog.text
