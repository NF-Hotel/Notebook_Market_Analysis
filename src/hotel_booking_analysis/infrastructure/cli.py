"""Command-line entry `analyze` (ADR-0006, ADR-0005 exit codes, UC-001, US-001.08).

The result JSON goes to standard output; messages go to standard error.
"""

import argparse
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import BinaryIO, TextIO

from hotel_booking_analysis.application.analyze_bookings import AnalyzeOutcome, RunStatus
from hotel_booking_analysis.infrastructure.bootstrap import build_analyze_bookings
from hotel_booking_analysis.infrastructure.file_lock import LOCK_WAIT_SECONDS

EXIT_SUCCESS = 0
EXIT_INPUT_ERROR = 2
EXIT_HISTORY_FAILURE = 3
EXIT_DELIVERY_FAILURE = 4

_EXIT_CODES: dict[RunStatus, int] = {
    RunStatus.SUCCEEDED: EXIT_SUCCESS,
    RunStatus.INPUT_FAILED: EXIT_INPUT_ERROR,
    RunStatus.HISTORY_FAILED: EXIT_HISTORY_FAILURE,
    RunStatus.DELIVERY_FAILED: EXIT_DELIVERY_FAILURE,
}

_LOGGER = logging.getLogger("hotel_booking_analysis.cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m hotel_booking_analysis")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze = commands.add_parser("analyze", help="Analyze a JSON file of hotel bookings.")
    analyze.add_argument("--input", type=Path, help="JSON file of booking records.")
    analyze.add_argument("--config", type=Path, help="TOML configuration file.")
    return parser


def main(
    argv: Sequence[str],
    stdout: BinaryIO,
    stderr: TextIO,
    working_directory: Path,
    environ: Mapping[str, str],
    lock_wait_seconds: float = LOCK_WAIT_SECONDS,
) -> int:
    """Run the command line and return the process exit code (ADR-0005)."""
    arguments = build_parser().parse_args(argv)
    handler = _attach_stderr(stderr)
    try:
        use_case = build_analyze_bookings(stdout, working_directory, environ, lock_wait_seconds)
        _LOGGER.info("Analysis started.")
        outcome = use_case.run(arguments.input, arguments.config)
        _report(outcome)
        return _EXIT_CODES[outcome.status]
    finally:
        _LOGGER.removeHandler(handler)


def _attach_stderr(stderr: TextIO) -> logging.Handler:
    handler = logging.StreamHandler(stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False
    return handler


def _report(outcome: AnalyzeOutcome) -> None:
    if outcome.malformed_history_lines:
        _LOGGER.warning(
            "The history holds %d malformed line(s); they were skipped and kept.",
            outcome.malformed_history_lines,
        )
    if outcome.status is RunStatus.SUCCEEDED:
        _LOGGER.info("Analysis %s completed, saved and delivered.", outcome.result_id)
    else:
        _LOGGER.error("%s", outcome.message)
