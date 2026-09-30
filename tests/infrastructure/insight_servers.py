"""Fake language model providers (real local HTTP servers) shared by the insight tests."""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from tests.adapters import fake_servers as servers


def answer_for(record_count: int) -> str:
    """A model answer that passes the guardrails when the input has `record_count` records."""
    return json.dumps(
        {
            "executive_summary": "The findings describe the observed bookings only.",
            "improvement_suggestions": [
                {
                    "suggestion": "Consider testing a change; it may or may not help.",
                    "evidence": f"Observed across {record_count} records.",
                    "sample_size": record_count,
                }
            ],
        }
    )


def ollama_answering(answer: str) -> servers.Behavior:
    """Lists one model on GET and answers every chat request with `answer`."""

    def behave(handler: Any, stop: Any) -> None:  # noqa: ANN401 - the handler type of http.server
        if handler.command == "GET":
            document: object = {"models": [{"name": "m1"}]}
        else:
            document = {"message": {"role": "assistant", "content": answer}, "done": True}
        servers.json_answer(document)(handler, stop)

    return behave


@contextmanager
def fake_providers(
    behavior: servers.Behavior | None = None,
) -> Iterator[tuple[servers.FakeServer, str]]:
    """A fake Ollama (broken when `behavior` is None) and a broken LM Studio; returns the config."""
    broken = servers.json_answer({"error": "x"}, status=500)
    with servers.serve(behavior or broken) as first, servers.serve(broken) as second:
        yield first, f'[llm]\nollama_url = "{first.base_url}"\nlmstudio_url = "{second.base_url}"\n'


def held_ollama(release: threading.Event, answer: str, wait_seconds: float) -> servers.Behavior:
    """Lists one model at once and answers a chat request only after `release` is set."""

    def behave(handler: Any, stop: Any) -> None:  # noqa: ANN401 - the handler type of http.server
        if handler.command == "GET":
            servers.json_answer({"models": [{"name": "m1"}]})(handler, stop)
        else:
            release.wait(wait_seconds)
            ollama_answering(answer)(handler, stop)

    return behave
