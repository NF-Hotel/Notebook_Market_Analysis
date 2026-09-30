"""Tests of the `llm-providers` command in process and as a subprocess (UC-004, ADR-0008)."""

import io
import json
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from hotel_booking_analysis.adapters.json_provider_listing_serializer import (
    load_provider_listing_schema,
)
from hotel_booking_analysis.infrastructure.cli import main
from tests.adapters import fake_servers as servers
from tests.infrastructure.cli_support import BrokenStdout, Run, run_module

VALIDATOR = Draft202012Validator(load_provider_listing_schema())
OLLAMA_TAGS = {"models": [{"name": "llama3:8b"}, {"name": "qwen2:7b"}]}
LMSTUDIO_MODELS = {"data": [{"id": "phi-3"}]}


def _config(tmp_path: Path, ollama_url: str, lmstudio_url: str, extra: str = "") -> Path:
    path = tmp_path / "providers.toml"
    path.write_text(
        f'[llm]\nollama_url = "{ollama_url}"\nlmstudio_url = "{lmstudio_url}"\n{extra}',
        encoding="utf-8",
    )
    return path


@contextmanager
def _both_broken() -> Iterator[tuple[str, str]]:
    """Two servers that answer HTTP 500: both providers are unreachable, and quickly so."""
    with (
        servers.serve(servers.json_answer({"error": "x"}, status=500)) as first,
        servers.serve(servers.json_answer({"error": "x"}, status=500)) as second,
    ):
        yield first.base_url, second.base_url


def _llm_providers(
    tmp_path: Path, config: Path | str | None = None, stdout: io.BytesIO | None = None
) -> Run:
    out = stdout if stdout is not None else io.BytesIO()
    err = io.StringIO()
    args = ["llm-providers"]
    if isinstance(config, str):
        path = tmp_path / "raw.toml"
        path.write_text(config, encoding="utf-8")
        config = path
    if config is not None:
        args += ["--config", str(config)]
    code = main(args, out, err, tmp_path, {})
    return Run(code, out.getvalue(), err.getvalue(), VALIDATOR)


def test_llm_providers_lists_both_providers_and_their_models(tmp_path: Path) -> None:
    with (
        servers.serve(servers.json_answer(OLLAMA_TAGS)) as ollama,
        servers.serve(servers.json_answer(LMSTUDIO_MODELS)) as lmstudio,
    ):
        run = _llm_providers(tmp_path, _config(tmp_path, ollama.base_url, lmstudio.base_url))

        assert ollama.requests == ["/api/tags"]
        assert lmstudio.requests == ["/v1/models"]
    assert run.code == 0
    document = run.document
    assert document["status"] == "completed"
    assert document["notices"] == []
    assert [p["provider"] for p in document["providers"]] == ["ollama", "lmstudio"]
    assert [p["status"] for p in document["providers"]] == ["reachable", "reachable"]
    assert document["providers"][0]["base_url"] == ollama.base_url
    assert document["providers"][0]["models"] == [{"name": "llama3:8b"}, {"name": "qwen2:7b"}]
    assert document["providers"][1]["models"] == [{"name": "phi-3"}]
    assert run.stdout.endswith(b"\n")
    assert run.stdout.count(b"\n") == 1
    assert "Provider listing delivered" in run.stderr


def test_llm_providers_reports_one_unreachable_provider_and_exits_0(tmp_path: Path) -> None:
    with servers.serve(servers.json_answer(LMSTUDIO_MODELS)) as lmstudio:
        # Windows takes about 2 s to report a refused connection, so allow more than the default
        config = _config(
            tmp_path,
            servers.closed_port_url(),
            lmstudio.base_url,
            "discovery_timeout_seconds = 10\n",
        )
        run = _llm_providers(tmp_path, config)

    assert run.code == 0
    document = run.document
    assert document["providers"][0]["status"] == "unreachable"
    assert document["providers"][0]["reason"] == "CONNECTION_REFUSED"
    assert document["providers"][0]["models"] == []
    assert document["providers"][1]["status"] == "reachable"
    assert document["notices"] == []


def test_llm_providers_with_no_reachable_provider_adds_notice_and_exits_0(tmp_path: Path) -> None:
    with _both_broken() as (ollama_url, lmstudio_url):
        run = _llm_providers(tmp_path, _config(tmp_path, ollama_url, lmstudio_url))

    assert run.code == 0
    document = run.document
    assert document["status"] == "completed"
    assert [n["code"] for n in document["notices"]] == ["NO_PROVIDER_REACHABLE"]
    assert [p["reason"] for p in document["providers"]] == ["UNEXPECTED_ANSWER"] * 2


def test_llm_providers_slow_provider_is_unreachable_within_the_configured_timeout(
    tmp_path: Path,
) -> None:
    with (
        servers.serve(servers.never_answers) as ollama,
        servers.serve(servers.trickling_body) as lmstudio,
    ):
        config = _config(
            tmp_path, ollama.base_url, lmstudio.base_url, "discovery_timeout_seconds = 0.4\n"
        )
        started = time.monotonic()
        run = _llm_providers(tmp_path, config)
        elapsed = time.monotonic() - started

    assert run.code == 0
    assert [p["reason"] for p in run.document["providers"]] == ["TIMEOUT", "TIMEOUT"]
    assert elapsed < 3.0


@pytest.mark.parametrize(
    ("llm_table", "key"),
    [
        ('ollama_url = "http://example.com:11434"', "llm.ollama_url"),
        ('lmstudio_url = "http://192.168.1.5:1234"', "llm.lmstudio_url"),
        ("discovery_timeout_seconds = 0", "llm.discovery_timeout_seconds"),
        ("temperature = 2", "llm.temperature"),
    ],
)
def test_llm_providers_invalid_llm_value_gives_failed_document_naming_the_key(
    tmp_path: Path, llm_table: str, key: str
) -> None:
    run = _llm_providers(tmp_path, f"[llm]\n{llm_table}\n")

    assert run.code == 2
    document = run.document
    assert document["status"] == "failed"
    assert document["error"]["code"] == "CONFIGURATION_ERROR"
    assert key in document["error"]["message"]
    assert "providers" not in document
    assert document["notices"] == []
    assert "Provider listing delivered" not in run.stderr


def test_llm_providers_remote_host_is_allowed_only_with_allow_remote(tmp_path: Path) -> None:
    denied = _llm_providers(tmp_path, '[llm]\nollama_url = "http://ollama.invalid:11434"\n')
    allowed = _llm_providers(
        tmp_path,
        '[llm]\nallow_remote = true\nollama_url = "http://ollama.invalid:11434"\n'
        "discovery_timeout_seconds = 1\n",
    )

    assert denied.code == 2
    assert allowed.code == 0
    assert allowed.document["providers"][0]["reason"] in {"NETWORK_ERROR", "TIMEOUT"}


def test_llm_providers_accepts_loopback_hosts_including_unbracketed_ipv6(tmp_path: Path) -> None:
    run = _llm_providers(
        tmp_path,
        '[llm]\nollama_url = "http://[::1]:9"\nlmstudio_url = "http://localhost:9"\n'
        "discovery_timeout_seconds = 0.5\n",
    )

    assert run.code == 0
    assert run.document["providers"][0]["base_url"] == "http://[::1]:9"


def test_llm_providers_unparsable_config_gives_configuration_error_and_exit_2(
    tmp_path: Path,
) -> None:
    run = _llm_providers(tmp_path, "this is not toml [")

    assert run.code == 2
    document = run.document
    assert document["error"]["code"] == "CONFIGURATION_ERROR"
    assert "providers" not in document


def test_llm_providers_does_not_touch_the_history_or_write_files(tmp_path: Path) -> None:
    with _both_broken() as (ollama_url, lmstudio_url):
        config = _config(tmp_path, ollama_url, lmstudio_url)
        before = sorted(tmp_path.rglob("*"))

        run = _llm_providers(tmp_path, config)

    assert run.code == 0
    assert sorted(tmp_path.rglob("*")) == before
    assert not (tmp_path / "output").exists()


def test_llm_providers_sends_no_booking_data_only_get_requests(tmp_path: Path) -> None:
    with (
        servers.serve(servers.json_answer(OLLAMA_TAGS)) as ollama,
        servers.serve(servers.json_answer(LMSTUDIO_MODELS)) as lmstudio,
    ):
        _llm_providers(tmp_path, _config(tmp_path, ollama.base_url, lmstudio.base_url))

        # the fake servers implement only GET; each was asked once, for the model list
        assert ollama.requests == ["/api/tags"]
        assert lmstudio.requests == ["/v1/models"]


def test_llm_providers_delivery_failure_exits_4_with_message_on_stderr(tmp_path: Path) -> None:
    with _both_broken() as (ollama_url, lmstudio_url):
        config = _config(tmp_path, ollama_url, lmstudio_url)

        run = _llm_providers(tmp_path, config, stdout=BrokenStdout())

    assert run.code == 4
    assert run.stdout == b""
    assert "could not be written" in run.stderr
    assert "nothing was stored" in run.stderr


def test_llm_providers_delivery_failure_of_failed_document_exits_4(tmp_path: Path) -> None:
    run = _llm_providers(tmp_path, "[llm]\ntemperature = 9\n", stdout=BrokenStdout())

    assert run.code == 4
    assert "CONFIGURATION_ERROR" in run.stderr


def test_llm_providers_rejects_unknown_option_with_usage_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["llm-providers", "--years", "2025"], io.BytesIO(), io.StringIO(), tmp_path, {})

    assert exit_info.value.code == 2


def _subprocess(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return run_module("llm-providers", cwd, *args)


def test_module_run_llm_providers_writes_valid_listing_to_stdout(tmp_path: Path) -> None:
    with (
        servers.serve(servers.json_answer(OLLAMA_TAGS)) as ollama,
        servers.serve(servers.json_answer(LMSTUDIO_MODELS)) as lmstudio,
    ):
        config = _config(tmp_path, ollama.base_url, lmstudio.base_url)

        completed = _subprocess(tmp_path, "--config", str(config))

    assert completed.returncode == 0, completed.stderr.decode()
    document = json.loads(completed.stdout)
    VALIDATOR.validate(document)
    assert [p["status"] for p in document["providers"]] == ["reachable", "reachable"]
    assert document["providers"][0]["models"][0] == {"name": "llama3:8b"}
    assert b"\r" not in completed.stdout
    assert not (tmp_path / "output").exists()


def test_module_run_llm_providers_with_unreachable_providers_exits_0_with_notice(
    tmp_path: Path,
) -> None:
    with _both_broken() as (ollama_url, lmstudio_url):
        config = _config(tmp_path, ollama_url, lmstudio_url)

        completed = _subprocess(tmp_path, "--config", str(config))

    assert completed.returncode == 0, completed.stderr.decode()
    document = json.loads(completed.stdout)
    VALIDATOR.validate(document)
    assert [n["code"] for n in document["notices"]] == ["NO_PROVIDER_REACHABLE"]


def test_module_run_llm_providers_with_invalid_config_exits_2_with_failed_document(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad.toml"
    path.write_text('[llm]\nollama_url = "http://example.com"\n', encoding="utf-8")

    completed = _subprocess(tmp_path, "--config", str(path))

    assert completed.returncode == 2
    document = json.loads(completed.stdout)
    VALIDATOR.validate(document)
    assert "llm.ollama_url" in document["error"]["message"]


def test_module_run_llm_providers_with_unknown_option_exits_2_without_json(tmp_path: Path) -> None:
    completed = _subprocess(tmp_path, "--bogus")

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr
