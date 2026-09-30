"""End-to-end acceptance of the AI insights (MIL-011 criteria 6 and 8; UC-002, UC-005, ADR-0005).

`python -m hotel_booking_analysis analyze --insights` runs as a subprocess against a fake Ollama
server. The returned JSON, the history line and the view models built from the history are the
same insights, and a history of 1.0 and 1.1 results is listed and displayed.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from hotel_booking_analysis.interface.history_source import load_history
from hotel_booking_analysis.interface.history_view import build_history_view, version_notice
from hotel_booking_analysis.interface.insight_view import (
    SAVED_WITHOUT_MESSAGE,
    STATE_AVAILABLE,
    STATE_SAVED_WITHOUT,
    STATE_UNAVAILABLE,
    reason_text,
)
from tests.adapters import fake_servers as servers
from tests.infrastructure.insight_servers import answer_for, fake_providers, ollama_answering
from tests.infrastructure.test_analyze_insights_cli import RECORD_COUNT
from tests.insight_fakes import result_1_1_validator
from tests.insight_samples import SAMPLE_CSV
from tests.interface.builders import export_notebook
from tests.interface.conftest import REPO_ROOT
from tests.interface.insight_builders import ANALYSES
from tests.interface.insight_view_checks import (
    assert_view_matches_stored_insight,
    views_of_history,
)

VALIDATOR = result_1_1_validator()

pytestmark = pytest.mark.skipif(not SAMPLE_CSV.is_file(), reason="development CSV is not present")


def _write_config(tmp_path: Path, llm_table: str) -> Path:
    config = tmp_path / "hotel_analysis.toml"
    history = (tmp_path / "history.jsonl").as_posix()
    config.write_text(
        f"environment = 'development'\n[history]\npath = '{history}'\n{llm_table}",
        encoding="utf-8",
    )
    return config


def _analyze(config: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        [sys.executable, "-m", "hotel_booking_analysis", "analyze", "--config", str(config), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr.decode()
    return completed


def test_insights_are_the_same_in_the_returned_json_the_history_line_and_the_views(
    tmp_path: Path,
) -> None:
    with fake_providers(ollama_answering(answer_for(RECORD_COUNT))) as (ollama, llm_table):
        config = _write_config(tmp_path, llm_table)
        completed = _analyze(config, "--insights")

        assert len(ollama.requests) == 7
    returned = json.loads(completed.stdout)
    VALIDATOR.validate(returned)
    assert returned["status"] == "completed"
    assert returned["schema_version"] == "1.1"
    assert (tmp_path / "history.jsonl").read_bytes() == completed.stdout

    [(stored, views)] = views_of_history(config, tmp_path)

    assert stored == returned
    assert set(views) == set(returned["analyses"]) == set(ANALYSES)
    for name, view in views.items():
        assert_view_matches_stored_insight(
            view, returned["analyses"][name]["insight"], RECORD_COUNT
        )
    assert returned["insights"]["provider"] == "ollama"
    assert returned["insights"]["model"] == "m1"


def test_a_history_of_a_1_0_and_a_1_1_result_is_listed_and_displayed(tmp_path: Path) -> None:
    with fake_providers(ollama_answering(answer_for(RECORD_COUNT))) as (_, llm_table):
        config = _write_config(tmp_path, llm_table)
        first = json.loads(_analyze(config).stdout)
        second = json.loads(_analyze(config, "--insights").stdout)
    assert (first["schema_version"], second["schema_version"]) == ("1.0", "1.1")

    loaded = load_history(tmp_path, {"HOTEL_ANALYSIS_CONFIG": str(config)})
    listed = build_history_view(loaded.readout)
    (newer, newer_views), (older, older_views) = views_of_history(config, tmp_path)

    assert loaded.readout.malformed_line_count == 0
    assert [row.schema_version for row in listed.rows] == ["1.1", "1.0"]
    assert all(row.fully_supported for row in listed.rows)
    assert (newer["result_id"], older["result_id"]) == (second["result_id"], first["result_id"])
    assert all(version_notice(result) is None for result in listed.results)
    assert {view.state for view in newer_views.values()} == {STATE_AVAILABLE}
    assert {view.state for view in older_views.values()} == {STATE_SAVED_WITHOUT}
    assert all(view.lines() == [SAVED_WITHOUT_MESSAGE] for view in older_views.values())
    html = export_notebook(tmp_path, {"HOTEL_ANALYSIS_CONFIG": str(config)})
    assert second["result_id"] in html
    assert first["result_id"] in html
    assert "AI-generated" in html
    assert "provider: ollama" in html
    assert str(newer_views["lead_time"].executive_summary) in html


def test_the_notebook_shows_a_result_saved_without_insights_clearly(tmp_path: Path) -> None:
    with fake_providers(ollama_answering(answer_for(RECORD_COUNT))) as (_, llm_table):
        config = _write_config(tmp_path, llm_table)
        _analyze(config)

    html = export_notebook(tmp_path, {"HOTEL_ANALYSIS_CONFIG": str(config)})

    assert html.count(SAVED_WITHOUT_MESSAGE) == len(ANALYSES)
    assert "AI-generated" not in html


def test_unreachable_provider_leaves_the_analyses_intact_and_viewable(tmp_path: Path) -> None:
    llm_table = (
        f'[llm]\nollama_url = "{servers.closed_port_url()}"\n'
        f'lmstudio_url = "{servers.closed_port_url()}"\n'
    )
    config = _write_config(tmp_path, llm_table)

    completed = _analyze(config, "--insights")

    returned = json.loads(completed.stdout)
    VALIDATOR.validate(returned)
    assert returned["status"] == "completed_with_warnings"
    assert returned["notices"][-1]["code"] == "INSIGHTS_UNAVAILABLE"
    assert returned["insights"]["provider"] is None
    assert all(entry["findings"] for entry in returned["analyses"].values())
    assert (tmp_path / "history.jsonl").read_bytes() == completed.stdout
    [(stored, views)] = views_of_history(config, tmp_path)
    assert stored == returned
    for name, view in views.items():
        assert returned["analyses"][name]["insight"]["reason"] == "NO_PROVIDER"
        assert view.state == STATE_UNAVAILABLE
        assert view.reason == "NO_PROVIDER"
        assert view.reason_text == reason_text("NO_PROVIDER")
        assert view.executive_summary is None
        assert view.suggestions == ()
    html = export_notebook(tmp_path, {"HOTEL_ANALYSIS_CONFIG": str(config)})
    assert reason_text("NO_PROVIDER") in html
    assert "Lead time" in html
    assert "Cancellations" in html
