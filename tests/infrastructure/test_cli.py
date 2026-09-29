"""Core contract and integration tests through the command line (MIL-004 task 10).

Covers ADR-0002 (schema), ADR-0003 (history, retention, malformed and interrupted lines),
ADR-0004 (invalid configuration), ADR-0005 (exit codes) and UC-001 with real adapters on
`tmp_path`.
"""

import io
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from hotel_booking_analysis.adapters.json_result_serializer import load_result_schema
from hotel_booking_analysis.infrastructure.cli import main
from hotel_booking_analysis.infrastructure.jsonl_history import (
    JsonlHistoryReader,
    lock_path_for,
)
from tests.support import make_line

VALIDATOR = Draft202012Validator(load_result_schema())
REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CSV = REPO_ROOT / "data" / "example" / "nf_hotel_bookings.csv"

BOOKINGS: list[dict[str, Any]] = [  # JSON fixture, values follow ADR-0001
    {
        "booking_id": "1",
        "is_canceled": False,
        "lead_time": 10,
        "booking_date": "2021-03-08",
        "arrival_date": "2021-03-18",
        "stays_in_weekend_nights": 1,
        "stays_in_week_nights": 2,
        "adults": 2,
        "price_per_night": 27.31,
    },
    {
        "booking_id": "2",
        "is_canceled": True,
        "lead_time": 40,
        "booking_date": "2021-04-01",
        "arrival_date": "2021-05-11",
        "stays_in_weekend_nights": 0,
        "stays_in_week_nights": 1,
        "adults": 1,
        "price_per_night": 30.0,
    },
]


class Run:
    def __init__(self, code: int, stdout: bytes, stderr: str) -> None:
        self.code = code
        self.stdout = stdout
        self.stderr = stderr

    @property
    def document(self) -> dict[str, Any]:
        parsed: dict[str, Any] = json.loads(self.stdout)
        return parsed


class BrokenStdout(io.BytesIO):
    def write(self, buffer: Any) -> int:  # noqa: ANN401 - matches io.BytesIO.write signature
        raise OSError("broken pipe")


def _bookings(tmp_path: Path, records: list[dict[str, Any]] | None = None) -> Path:
    path = tmp_path / "bookings.json"
    path.write_text(json.dumps(BOOKINGS if records is None else records), encoding="utf-8")
    return path


def _config(tmp_path: Path, body: str = "") -> Path:
    path = tmp_path / "hotel_analysis.toml"
    path.write_text(body, encoding="utf-8")
    return path


def _history_config(tmp_path: Path, retention: int | None = None) -> Path:
    lines = [f"[history]\npath = '{(tmp_path / 'out' / 'h.jsonl').as_posix()}'"]
    if retention is not None:
        lines.append(f"retention = {retention}")
    return _config(tmp_path, "\n".join(lines) + "\n")


def _history(tmp_path: Path) -> Path:
    return tmp_path / "out" / "h.jsonl"


def _analyze(
    tmp_path: Path,
    *args: str,
    stdout: io.BytesIO | None = None,
    lock_wait_seconds: float = 0.2,
) -> Run:
    out = stdout if stdout is not None else io.BytesIO()
    err = io.StringIO()
    code = main(["analyze", *args], out, err, tmp_path, {}, lock_wait_seconds=lock_wait_seconds)
    return Run(code, out.getvalue(), err.getvalue())


def _analyze_bookings(tmp_path: Path, config: Path | None = None) -> Run:
    arguments = ["--input", str(_bookings(tmp_path))]
    if config is not None:
        arguments += ["--config", str(config)]
    return _analyze(tmp_path, *arguments)


def _stored_ids(path: Path) -> list[str]:
    return [str(r["result_id"]) for r in JsonlHistoryReader().read(path).results]


def test_analyze_result_validates_against_the_adr_0002_schema(tmp_path: Path) -> None:
    run = _analyze_bookings(tmp_path, _history_config(tmp_path))

    assert run.code == 0
    VALIDATOR.validate(run.document)
    assert run.document["status"] == "completed"
    assert run.document["input"]["reference"] == "bookings.json"
    assert run.document["input"]["record_count"] == 2
    assert set(run.document["analyses"]) == {
        "lead_time",
        "holidays",
        "seasonality",
        "cancellations",
        "room_value",
        "guest_mix",
    }


def test_analyze_result_contains_no_raw_booking_records(tmp_path: Path) -> None:
    run = _analyze_bookings(tmp_path, _history_config(tmp_path))

    text = run.stdout.decode()
    assert '"booking_id":"' not in text
    assert '"lead_time":40' not in text
    assert "27.31" not in text
    assert "records" not in run.document


def test_analyze_stdout_is_byte_identical_to_the_history_line(tmp_path: Path) -> None:
    run = _analyze_bookings(tmp_path, _history_config(tmp_path))

    assert run.code == 0
    assert _history(tmp_path).read_bytes() == run.stdout
    assert run.stdout.endswith(b"\n")
    assert run.stdout.count(b"\n") == 1


def test_analyze_stdout_and_history_stay_identical_on_every_run(tmp_path: Path) -> None:
    config = _history_config(tmp_path)
    runs = [_analyze_bookings(tmp_path, config) for _ in range(3)]

    history_lines = _history(tmp_path).read_bytes().splitlines(keepends=True)

    assert history_lines == [run.stdout for run in runs]


@pytest.mark.parametrize(("retention", "runs"), [(3, 6), (1, 4), (5, 8)])
def test_retention_keeps_exactly_the_latest_n_after_n_plus_three_runs(
    tmp_path: Path, retention: int, runs: int
) -> None:
    assert runs == retention + 3
    config = _history_config(tmp_path, retention)

    ids = [_analyze_bookings(tmp_path, config).document["result_id"] for _ in range(runs)]

    assert _stored_ids(_history(tmp_path)) == ids[-retention:]


def test_retention_defaults_to_ten_when_not_configured(tmp_path: Path) -> None:
    config = _history_config(tmp_path)

    ids = [_analyze_bookings(tmp_path, config).document["result_id"] for _ in range(13)]

    assert _stored_ids(_history(tmp_path)) == ids[-10:]


def test_history_defaults_to_output_directory_and_default_retention_without_a_config_file(
    tmp_path: Path,
) -> None:
    ids = [
        _analyze(tmp_path, "--input", str(_bookings(tmp_path))).document["result_id"]
        for _ in range(12)
    ]

    stored = _stored_ids(tmp_path / "output" / "analysis_history.jsonl")
    assert stored == ids[-10:]


def test_analyze_states_missing_configuration_file_in_a_notice(tmp_path: Path) -> None:
    run = _analyze(tmp_path, "--input", str(_bookings(tmp_path)))

    codes = [n["code"] for n in run.document["notices"]]
    assert "CONFIG_FILE_NOT_FOUND" in codes
    assert "ESTIMATE_NOT_REVENUE" in codes


def test_analyze_keeps_malformed_history_line_reports_it_and_stays_readable(
    tmp_path: Path,
) -> None:
    config = _history_config(tmp_path, retention=2)
    history = _history(tmp_path)
    history.parent.mkdir()
    history.write_bytes(
        make_line("old-1").encode() + b"\nnot json at all\n" + make_line("old-2").encode() + b"\n"
    )

    run = _analyze_bookings(tmp_path, config)

    assert run.code == 0
    lines = history.read_text().splitlines()
    assert lines[0] == "not json at all"
    readout = JsonlHistoryReader().read(history)
    assert readout.malformed_line_count == 1
    assert [r["result_id"] for r in readout.results] == ["old-2", run.document["result_id"]]
    assert "malformed" in run.stderr


def test_analyze_survives_an_interrupted_earlier_write(tmp_path: Path) -> None:
    config = _history_config(tmp_path)
    history = _history(tmp_path)
    history.parent.mkdir()
    history.write_bytes(make_line("old").encode() + b'\n{"schema_version":"1.0","result_')

    run = _analyze_bookings(tmp_path, config)

    assert run.code == 0
    readout = JsonlHistoryReader().read(history)
    assert [r["result_id"] for r in readout.results] == ["old", run.document["result_id"]]
    assert readout.malformed_line_count == 1
    assert history.read_bytes().endswith(run.stdout)


@pytest.mark.parametrize(
    ("body", "key"),
    [
        ("[history]\nretention = 0\n", "history.retention"),
        ("[history]\nretention = -2\n", "history.retention"),
        ("[history]\nretention = 2.5\n", "history.retention"),
        ("[history]\nretention = '5'\n", "history.retention"),
        ("[history]\nretention = true\n", "history.retention"),
        ("[analysis]\nmin_group_size = 0\n", "analysis.min_group_size"),
        ("environment = 'staging'\n", "environment"),
    ],
)
def test_analyze_invalid_configuration_fails_with_exit_2_and_leaves_history_alone(
    tmp_path: Path, body: str, key: str
) -> None:
    run = _analyze_bookings(tmp_path, _config(tmp_path, body))

    assert run.code == 2
    VALIDATOR.validate(run.document)
    assert run.document["status"] == "failed"
    assert run.document["error"]["code"] == "CONFIGURATION_ERROR"
    assert key in run.document["error"]["message"]
    assert not _history(tmp_path).exists()
    assert not (tmp_path / "output").exists()


def test_analyze_invalid_configuration_does_not_touch_an_existing_history(
    tmp_path: Path,
) -> None:
    history = _history(tmp_path)
    history.parent.mkdir()
    history.write_bytes(make_line("old").encode() + b"\n")
    config = _config(tmp_path, f"[history]\npath = '{history.as_posix()}'\nretention = 0\n")

    run = _analyze_bookings(tmp_path, config)

    assert run.code == 2
    assert history.read_bytes() == make_line("old").encode() + b"\n"


def test_analyze_unparsable_configuration_fails_with_exit_2(tmp_path: Path) -> None:
    run = _analyze_bookings(tmp_path, _config(tmp_path, "this is = = not toml"))

    assert run.code == 2
    assert run.document["error"]["code"] == "CONFIGURATION_ERROR"


@pytest.mark.parametrize(
    ("content", "code"),
    [("not json", "INPUT_INVALID_JSON"), ('{"a": 1}', "INPUT_NOT_ARRAY"), ("[]", "INPUT_EMPTY")],
)
def test_analyze_invalid_input_fails_with_exit_2_and_stores_nothing(
    tmp_path: Path, content: str, code: str
) -> None:
    source = tmp_path / "bad.json"
    source.write_text(content, encoding="utf-8")

    run = _analyze(tmp_path, "--input", str(source), "--config", str(_history_config(tmp_path)))

    assert run.code == 2
    VALIDATOR.validate(run.document)
    assert run.document["error"]["code"] == code
    assert not _history(tmp_path).exists()


def test_analyze_missing_input_file_fails_with_exit_2(tmp_path: Path) -> None:
    run = _analyze(tmp_path, "--input", str(tmp_path / "absent.json"))

    assert run.code == 2
    assert run.document["error"]["code"] == "INPUT_NOT_FOUND"


def test_analyze_without_input_outside_development_fails_with_exit_2(tmp_path: Path) -> None:
    run = _analyze(tmp_path, "--config", str(_history_config(tmp_path)))

    assert run.code == 2
    assert run.document["error"]["code"] == "NO_INPUT"
    assert not _history(tmp_path).exists()


def test_analyze_history_write_failure_gives_exit_3_and_nothing_on_stdout(
    tmp_path: Path,
) -> None:
    history = _history(tmp_path)
    history.mkdir(parents=True)  # a directory where the history file should be

    run = _analyze_bookings(tmp_path, _history_config(tmp_path))

    assert run.code == 3
    assert run.stdout == b""
    assert "history" in run.stderr.lower()
    assert "No result was delivered" in run.stderr


def test_analyze_history_directory_that_cannot_be_created_gives_exit_3(tmp_path: Path) -> None:
    (tmp_path / "out").write_text("a file where the directory should be")

    run = _analyze_bookings(tmp_path, _history_config(tmp_path))

    assert run.code == 3
    assert run.stdout == b""


def test_analyze_history_lock_held_gives_exit_3_and_nothing_on_stdout(tmp_path: Path) -> None:
    history = _history(tmp_path)
    history.parent.mkdir()
    lock_path_for(history).write_bytes(b"")

    run = _analyze_bookings(tmp_path, _history_config(tmp_path))

    assert run.code == 3
    assert run.stdout == b""
    assert "lock" in run.stderr
    assert not history.exists()


def test_analyze_stdout_failure_gives_exit_4_names_result_id_and_keeps_history(
    tmp_path: Path,
) -> None:
    config = _history_config(tmp_path)
    err = io.StringIO()

    code = main(
        ["analyze", "--input", str(_bookings(tmp_path)), "--config", str(config)],
        BrokenStdout(),
        err,
        tmp_path,
        {},
    )

    assert code == 4
    stored = _stored_ids(_history(tmp_path))
    assert len(stored) == 1
    assert stored[0] in err.getvalue()
    assert "not delivered" in err.getvalue()


def test_analyze_never_reports_success_on_failure(tmp_path: Path) -> None:
    err = io.StringIO()

    main(
        [
            "analyze",
            "--input",
            str(_bookings(tmp_path)),
            "--config",
            str(_history_config(tmp_path)),
        ],
        BrokenStdout(),
        err,
        tmp_path,
        {},
    )

    assert "completed, saved and delivered" not in err.getvalue()


def test_analyze_missing_optional_fields_mark_dependent_analysis_unavailable(
    tmp_path: Path,
) -> None:
    records = [{"booking_id": "1", "lead_time": 5, "adults": 2}]
    source = _bookings(tmp_path, records)

    run = _analyze(tmp_path, "--input", str(source), "--config", str(_history_config(tmp_path)))

    assert run.code == 0
    VALIDATOR.validate(run.document)
    analyses = run.document["analyses"]
    for name, field_name in [
        ("cancellations", "is_canceled"),
        ("room_value", "stays_in_weekend_nights"),
    ]:
        assert analyses[name]["status"] == "unavailable"
        assert field_name in analyses[name]["reason"]
        assert analyses[name]["findings"] == {}
    assert analyses["lead_time"]["status"] == "available"
    assert run.document["status"] == "completed_with_warnings"
    assert run.document["data_quality"]["missing_counts"]["is_canceled"] == 1
    assert run.document["data_quality"]["earliest_booking_date"] is None


def test_analyze_unknown_configuration_keys_give_a_warning_status(tmp_path: Path) -> None:
    config = _config(
        tmp_path,
        f"colour = 'blue'\n[history]\npath = '{_history(tmp_path).as_posix()}'\n",
    )

    run = _analyze_bookings(tmp_path, config)

    assert run.code == 0
    assert run.document["status"] == "completed_with_warnings"
    assert "CONFIG_UNKNOWN_KEYS" in [n["code"] for n in run.document["notices"]]


def test_analyze_environment_variable_selects_configuration_file(tmp_path: Path) -> None:
    config = _history_config(tmp_path, retention=1)
    out = io.BytesIO()
    for _ in range(2):
        main(
            ["analyze", "--input", str(_bookings(tmp_path))],
            out,
            io.StringIO(),
            tmp_path,
            {"HOTEL_ANALYSIS_CONFIG": str(config)},
        )

    assert len(_stored_ids(_history(tmp_path))) == 1


@pytest.mark.skipif(not SAMPLE_CSV.is_file(), reason="development CSV is not present")
def test_analyze_uses_development_csv_when_no_input_in_development(tmp_path: Path) -> None:
    config = _config(
        tmp_path,
        f"environment = 'development'\n[history]\npath = '{_history(tmp_path).as_posix()}'\n",
    )
    out = io.BytesIO()

    code = main(["analyze", "--config", str(config)], out, io.StringIO(), REPO_ROOT, {})

    assert code == 0
    document = json.loads(out.getvalue())
    VALIDATOR.validate(document)
    assert document["input"]["source"] == "development_sample"
    assert document["input"]["reference"] == "nf_hotel_bookings.csv"
    assert "DEVELOPMENT_SAMPLE_USED" in [n["code"] for n in document["notices"]]
    assert _history(tmp_path).read_bytes() == out.getvalue()


def test_analyze_rejects_unknown_command(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["frobnicate"], io.BytesIO(), io.StringIO(), tmp_path, {})
