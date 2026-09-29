"""Smoke test: the marimo notebook runs headlessly against a history (MIL-006 criteria 1, 2).

`marimo export html` executes every cell in a subprocess started in `tmp_path`, as the notebook
is started from the working directory, and writes the rendered outputs to an HTML file.
"""

import subprocess
import sys
from pathlib import Path

import hotel_booking_analysis.interface.history_notebook as notebook_module
from tests.interface.builders import run_analysis, with_identity, write_history

NOTEBOOK = Path(notebook_module.__file__)


def _export(working_directory: Path, extra_environment: dict[str, str] | None = None) -> str:
    import os

    output = working_directory / "notebook.html"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "marimo",
            "export",
            "html",
            str(NOTEBOOK),
            "-o",
            str(output),
            "--no-include-code",
            "-f",
        ],
        cwd=working_directory,
        env={**os.environ, **(extra_environment or {})},
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Traceback" not in completed.stderr, completed.stderr
    assert "cells failed" not in completed.stderr, completed.stderr
    return output.read_text(encoding="utf-8")


def test_notebook_shows_newest_result_with_generated_time_and_quality(tmp_path: Path) -> None:
    base = run_analysis(tmp_path)
    older = with_identity(base, "id-older-0001", "2026-01-01T10:00:00.000Z")
    newest = with_identity(base, "id-newest-0002", "2026-03-01T10:00:00.000Z")
    write_history(tmp_path, newest, older)

    html = _export(tmp_path)

    assert "id-newest-0002" in html
    assert "2026-03-01T10:00:00.000Z" in html
    assert "id-older-0001" in html
    assert "Data quality" in html
    assert "not causes" in html
    assert "not realized revenue" in html


def test_notebook_shows_empty_message_when_history_is_missing(tmp_path: Path) -> None:
    html = _export(tmp_path)

    assert "no saved results yet" in html


def test_notebook_reports_skipped_malformed_lines_and_still_shows_results(tmp_path: Path) -> None:
    base = run_analysis(tmp_path)
    write_history(
        tmp_path,
        with_identity(base, "id-readable-0003", "2026-02-01T00:00:00.000Z"),
        extra="not json\n",
    )

    html = _export(tmp_path)

    assert "1 history line could not be read and was skipped." in html
    assert "id-readable-0003" in html


def test_notebook_states_version_it_cannot_fully_display(tmp_path: Path) -> None:
    base = run_analysis(tmp_path)
    old = {
        **with_identity(base, "id-legacy-0004", "2025-01-01T00:00:00.000Z"),
        "schema_version": "0.9",
    }
    write_history(tmp_path, old)

    html = _export(tmp_path)

    assert "id-legacy-0004" in html
    assert "schema version 0.9" in html


def test_notebook_reads_the_history_path_from_the_configured_file(tmp_path: Path) -> None:
    base = run_analysis(tmp_path)
    write_history(tmp_path, with_identity(base, "id-default-0005", "2026-02-01T00:00:00.000Z"))
    other = tmp_path / "custom.jsonl"
    other.write_text(
        write_history(
            tmp_path, with_identity(base, "id-custom-0006", "2026-04-01T00:00:00.000Z")
        ).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    write_history(tmp_path, with_identity(base, "id-default-0005", "2026-02-01T00:00:00.000Z"))
    config = tmp_path / "elsewhere.toml"
    config.write_text("[history]\npath = 'custom.jsonl'\n", encoding="utf-8")

    html = _export(tmp_path, {"HOTEL_ANALYSIS_CONFIG": str(config)})

    assert "id-custom-0006" in html
    assert "id-default-0005" not in html
