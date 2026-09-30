"""Tests for the retained-results list (US-001.10, UC-002)."""

import json
from pathlib import Path

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.history import HistoryReadout
from hotel_booking_analysis.infrastructure.jsonl_history import JsonlHistoryReader
from hotel_booking_analysis.interface.history_source import load_history
from hotel_booking_analysis.interface.history_view import (
    NO_RESULTS_MESSAGE,
    HistoryView,
    build_history_view,
    version_notice,
)
from tests.interface.builders import (
    HISTORY_RELATIVE,
    run_analysis,
    with_identity,
    write_history,
)
from tests.interface.insight_builders import with_insights
from tests.support import make_line


def _view(tmp_path: Path) -> HistoryView:
    return build_history_view(JsonlHistoryReader().read(tmp_path / HISTORY_RELATIVE))


def test_history_view_is_empty_with_message_when_file_is_missing(tmp_path: Path) -> None:
    view = _view(tmp_path)

    assert view.rows == ()
    assert view.empty_message == NO_RESULTS_MESSAGE
    assert view.malformed_message is None


def test_history_view_is_empty_with_message_when_file_is_empty(tmp_path: Path) -> None:
    (tmp_path / HISTORY_RELATIVE).parent.mkdir()
    (tmp_path / HISTORY_RELATIVE).write_text("", encoding="utf-8")

    view = _view(tmp_path)

    assert view.rows == ()
    assert view.empty_message == NO_RESULTS_MESSAGE


def test_history_view_lists_results_newest_first(tmp_path: Path) -> None:
    base = run_analysis(tmp_path)
    older = with_identity(base, "old", "2026-01-01T10:00:00.000Z")
    newest = with_identity(base, "new", "2026-03-01T10:00:00.000Z")
    middle = with_identity(base, "mid", "2026-02-01T10:00:00.000Z")
    write_history(tmp_path, older, newest, middle)

    view = _view(tmp_path)

    assert [row.result_id for row in view.rows] == ["new", "mid", "old"]
    assert view.empty_message is None
    assert [r["result_id"] for r in view.results] == ["new", "mid", "old"]


def test_history_view_rows_carry_time_status_source_and_count(tmp_path: Path) -> None:
    write_history(tmp_path, run_analysis(tmp_path))

    row = _view(tmp_path).rows[0]

    assert row.generated_at.endswith("Z")
    assert row.status == "completed"
    assert row.source == "supplied"
    assert row.record_count == 7
    assert row.fully_supported is True
    assert row.generated_at in row.label(1)
    assert row.as_table_row()["record_count"] == 7


def test_history_view_reports_malformed_line_count_and_keeps_readable_results(
    tmp_path: Path,
) -> None:
    base = run_analysis(tmp_path)
    write_history(tmp_path, base, extra='{"broken":\nnot json\n')

    view = _view(tmp_path)

    assert len(view.rows) == 1
    assert view.malformed_message == "2 history lines could not be read and were skipped."


def test_history_view_uses_singular_wording_for_one_malformed_line(tmp_path: Path) -> None:
    write_history(tmp_path, run_analysis(tmp_path), extra="garbage\n")

    assert _view(tmp_path).malformed_message == "1 history line could not be read and was skipped."


def test_history_view_states_version_for_older_major_result(tmp_path: Path) -> None:
    base = run_analysis(tmp_path)
    old = {**with_identity(base, "old", "2025-01-01T00:00:00.000Z"), "schema_version": "0.9"}
    write_history(tmp_path, old)

    view = _view(tmp_path)

    assert view.rows[0].fully_supported is False
    notice = version_notice(view.results[0])
    assert notice is not None
    assert "0.9" in notice
    assert "cannot be fully displayed" in notice


def test_history_view_lists_1_0_and_1_1_results_of_one_history_as_fully_supported(
    tmp_path: Path,
) -> None:
    base = run_analysis(tmp_path)
    old = with_identity(base, "old-1-0", "2026-01-01T10:00:00.000Z")
    new = with_identity(with_insights(base), "new-1-1", "2026-02-01T10:00:00.000Z")
    path = write_history(tmp_path, old, new)
    before = path.read_bytes()

    view = _view(tmp_path)

    assert [(r.result_id, r.schema_version) for r in view.rows] == [
        ("new-1-1", "1.1"),
        ("old-1-0", "1.0"),
    ]
    assert all(row.fully_supported for row in view.rows)
    assert all(version_notice(result) is None for result in view.results)
    assert view.malformed_message is None
    assert path.read_bytes() == before


def test_history_view_shows_unknown_major_result_with_its_version_and_readable_parts(
    tmp_path: Path,
) -> None:
    base = with_insights(run_analysis(tmp_path))
    future = {**with_identity(base, "future", "2027-01-01T00:00:00.000Z"), "schema_version": "2.0"}
    write_history(tmp_path, future)

    view = _view(tmp_path)

    assert view.rows[0].schema_version == "2.0"
    assert view.rows[0].record_count == 7
    assert view.rows[0].fully_supported is False
    notice = version_notice(view.results[0])
    assert notice is not None
    assert "2.0" in notice


def test_version_notice_is_none_for_supported_minor_versions() -> None:
    assert version_notice({"schema_version": "1.7"}) is None


def test_version_notice_names_unreadable_version() -> None:
    notice = version_notice({"schema_version": 3})

    assert notice is not None
    assert "unknown" in notice


def test_history_view_sorts_unreadable_time_last_and_keeps_file_order_for_ties() -> None:
    lines = [make_line("a"), make_line("b")]
    readout = HistoryReadout(
        (
            *({**_parse(line), "generated_at": "2026-09-29T12:00:00.000Z"} for line in lines),
            {**_parse(make_line("c")), "generated_at": "not a time"},
        ),
        0,
    )

    view = build_history_view(readout)

    assert [row.result_id for row in view.rows] == ["b", "a", "c"]


def test_history_view_tolerates_results_without_input_details() -> None:
    view = build_history_view(HistoryReadout((_parse(make_line("x")),), 0))

    assert view.rows[0].source == "unknown"
    assert view.rows[0].record_count is None
    assert view.rows[0].as_table_row()["record_count"] == "unknown"


def test_load_history_reads_default_location_from_working_directory(tmp_path: Path) -> None:
    write_history(tmp_path, run_analysis(tmp_path))

    loaded = load_history(tmp_path, {})

    assert len(loaded.readout.results) == 1
    assert loaded.error is None
    assert loaded.location == HISTORY_RELATIVE


def test_load_history_uses_path_from_configuration_named_by_environment(tmp_path: Path) -> None:
    config = tmp_path / "elsewhere.toml"
    config.write_text("[history]\npath = 'custom.jsonl'\n", encoding="utf-8")
    (tmp_path / "custom.jsonl").write_text(make_line("z") + "\n", encoding="utf-8")

    loaded = load_history(tmp_path, {"HOTEL_ANALYSIS_CONFIG": str(config)})

    assert [r["result_id"] for r in loaded.readout.results] == ["z"]


def test_load_history_reports_invalid_configuration_without_raising(tmp_path: Path) -> None:
    (tmp_path / "hotel_analysis.toml").write_text("[history\n", encoding="utf-8")

    loaded = load_history(tmp_path, {})

    assert loaded.readout.results == ()
    assert loaded.error is not None


def test_load_history_reports_unreadable_history_without_raising(tmp_path: Path) -> None:
    (tmp_path / "output" / "analysis_history.jsonl").mkdir(parents=True)

    loaded = load_history(tmp_path, {})

    assert loaded.readout.results == ()
    assert loaded.error is not None


def test_load_history_never_modifies_the_history(tmp_path: Path) -> None:
    path = write_history(tmp_path, run_analysis(tmp_path), extra="garbage\n")
    before = path.read_bytes()

    load_history(tmp_path, {})

    assert path.read_bytes() == before


def _parse(line: str) -> dict[str, JsonValue]:
    parsed: dict[str, JsonValue] = json.loads(line)
    return parsed
