# DataFog v5 Workflow Examples

These examples show the adoption paths for the v5 offline PII firewall API.
They are written as normal Python modules so tests can import them without
network calls or heavyweight integration dependencies.

- `llm_guardrails.py`: OpenAI-style prompt, output, and streaming protection.
- `fastapi_request_filtering.py`: FastAPI request payload filtering recipe.
- `logging_filter.py`: Python `logging.Filter` for redacting log records.
- `langchain_adapter.py`: LangChain-style `invoke` wrapper pattern.
- `llamaindex_adapter.py`: LlamaIndex-style `query` wrapper pattern.

The FastAPI, LangChain, and LlamaIndex examples avoid importing those packages
at module import time. Install optional dependencies only in apps that need
them.

