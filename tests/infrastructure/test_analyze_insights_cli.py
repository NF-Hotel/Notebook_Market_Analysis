"""Tests of `analyze --insights` in process and as a subprocess against fake providers (UC-005).

The fake providers are real local HTTP servers (see `tests/adapters/fake_servers.py`); the
in-process runs use the production adapters, so this also proves the composition root wiring.
"""

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hotel_booking_analysis.infrastructure.cli import main
from tests.infrastructure.insight_servers import (
    answer_for,
    fake_providers,
    ollama_answering,
)
from tests.insight_fakes import result_1_1_validator
from tests.insight_samples import SAMPLE_CSV

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD_COUNT = 8538
VALIDATOR = result_1_1_validator()
ANSWER = answer_for(RECORD_COUNT)

pytestmark = pytest.mark.skipif(not SAMPLE_CSV.is_file(), reason="development CSV is not present")


def _config(tmp_path: Path, llm_table: str) -> Path:
    path = tmp_path / "config.toml"
    history = (tmp_path / "history.jsonl").as_posix()
    path.write_text(
        f"environment = 'development'\n[history]\npath = '{history}'\n{llm_table}", encoding="utf-8"
    )
    return path


def _analyze(config: Path, *args: str) -> tuple[int, bytes, str]:
    out, err = io.BytesIO(), io.StringIO()
    code = main(["analyze", "--config", str(config), *args], out, err, REPO_ROOT, {})
    return code, out.getvalue(), err.getvalue()


def test_analyze_with_insights_returns_six_labeled_insights_that_validate_against_schema_1_1(
    tmp_path: Path,
) -> None:
    with fake_providers(ollama_answering(ANSWER)) as (ollama, llm_table):
        code, stdout, stderr = _analyze(_config(tmp_path, llm_table), "--insights")

        assert ollama.requests == ["/api/tags", *["/api/chat"] * 6]
    document = json.loads(stdout)
    VALIDATOR.validate(document)
    assert code == 0
    assert document["schema_version"] == "1.1"
    assert document["status"] == "completed"
    assert document["insights"]["provider"] == "ollama"
    assert document["insights"]["model"] == "m1"
    insights = [entry["insight"] for entry in document["analyses"].values()]
    assert [i["status"] for i in insights] == ["available"] * 6
    assert {i["label"] for i in insights} == {"AI-generated"}
    assert (tmp_path / "history.jsonl").read_bytes() == stdout
    assert "unavailable" not in stderr


def test_analyze_with_insights_and_no_provider_still_exits_0_with_warnings(tmp_path: Path) -> None:
    with fake_providers() as (_, llm_table):
        code, stdout, stderr = _analyze(_config(tmp_path, llm_table), "--insights")

    document = json.loads(stdout)
    VALIDATOR.validate(document)
    assert code == 0
    assert document["status"] == "completed_with_warnings"
    assert document["notices"][-1]["code"] == "INSIGHTS_UNAVAILABLE"
    assert {e["insight"]["reason"] for e in document["analyses"].values()} == {"NO_PROVIDER"}
    assert "AI insights are unavailable for 6 analysis" in stderr
    assert (tmp_path / "history.jsonl").read_bytes() == stdout


def test_analyze_with_insights_and_a_bad_answer_keeps_the_analyses_and_exits_0(
    tmp_path: Path,
) -> None:
    with fake_providers(ollama_answering("this is not json")) as (ollama, llm_table):
        code, stdout, _ = _analyze(_config(tmp_path, llm_table), "--insights")

        assert len(ollama.requests) == 7
    document = json.loads(stdout)
    VALIDATOR.validate(document)
    assert code == 0
    assert {e["insight"]["reason"] for e in document["analyses"].values()} == {"BAD_STRUCTURE"}
    assert all(e["findings"] for e in document["analyses"].values())


def test_analyze_with_insights_and_invalid_llm_value_fails_naming_the_key(tmp_path: Path) -> None:
    config = _config(tmp_path, "[llm]\ntemperature = 9\n")

    code, stdout, _ = _analyze(config, "--insights")

    document = json.loads(stdout)
    assert code == 2
    assert document["status"] == "failed"
    assert document["schema_version"] == "1.0"
    assert "llm.temperature" in document["error"]["message"]
    assert not (tmp_path / "history.jsonl").exists()


def test_analyze_without_insights_ignores_the_llm_table_and_contacts_no_provider(
    tmp_path: Path,
) -> None:
    with fake_providers(ollama_answering(ANSWER)) as (ollama, llm_table):
        code, stdout, _ = _analyze(_config(tmp_path, llm_table + "temperature = 9\n"))

        assert ollama.requests == []
    document = json.loads(stdout)
    assert code == 0
    assert document["schema_version"] == "1.0"
    assert "insights" not in document


def _module(config: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "hotel_booking_analysis", "analyze", "--config", str(config), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        timeout=120,
    )


def test_module_run_without_insights_does_not_contact_the_fake_provider(tmp_path: Path) -> None:
    with fake_providers(ollama_answering(ANSWER)) as (ollama, llm_table):
        completed = _module(_config(tmp_path, llm_table))

        assert ollama.requests == []
    assert completed.returncode == 0, completed.stderr.decode()
    document = json.loads(completed.stdout)
    assert document["schema_version"] == "1.0"
    assert "insights" not in document


def test_module_run_with_insights_delivers_the_insights(tmp_path: Path) -> None:
    with fake_providers(ollama_answering(ANSWER)) as (ollama, llm_table):
        completed = _module(_config(tmp_path, llm_table), "--insights")

        assert len(ollama.requests) == 7
    assert completed.returncode == 0, completed.stderr.decode()
    document = json.loads(completed.stdout)
    VALIDATOR.validate(document)
    assert document["schema_version"] == "1.1"
    assert (tmp_path / "history.jsonl").read_bytes() == completed.stdout
