"""Command-line entry: `analyze`, `holidays`, `llm-providers`, `serve` (ADR-0006, ADR-0013).

The result JSON goes to standard output; messages go to standard error. `serve` starts the HTTP
service instead and writes nothing to standard output.
"""

import argparse
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import BinaryIO, TextIO

from hotel_booking_analysis.application.analyze_bookings import AnalyzeOutcome, RunStatus
from hotel_booking_analysis.application.listing_outcome import ListingOutcome
from hotel_booking_analysis.infrastructure.bootstrap import (
    build_analyze_bookings,
    build_list_holidays,
    build_list_llm_providers,
)
from hotel_booking_analysis.infrastructure.file_lock import LOCK_WAIT_SECONDS

EXIT_SUCCESS = 0
EXIT_INPUT_ERROR = 2
EXIT_HISTORY_FAILURE = 3
EXIT_DELIVERY_FAILURE = 4

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

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
    analyze.add_argument(
        "--insights",
        action="store_true",
        help="Also ask a local language model for an AI-generated summary of each analysis.",
    )
    holidays = commands.add_parser(
        "holidays", help="List the Cambodian public holidays of the requested years."
    )
    holidays.add_argument(
        "--years", help="Years to list: 2025, a range 2024-2026 or a list 2024,2026."
    )
    holidays.add_argument("--config", type=Path, help="TOML configuration file.")
    providers = commands.add_parser(
        "llm-providers", help="List the reachable language model providers and their models."
    )
    providers.add_argument("--config", type=Path, help="TOML configuration file.")
    serve = commands.add_parser("serve", help="Start the HTTP service (no authentication).")
    serve.add_argument("--host", default=DEFAULT_HOST, help="Address to bind (default loopback).")
    serve.add_argument("--port", type=_port, default=DEFAULT_PORT, help="Port to listen on.")
    serve.add_argument("--config", type=Path, help="TOML configuration file for every request.")
    return parser


def _port(text: str) -> int:
    if not text.isascii() or not text.isdigit() or not 1 <= int(text) <= 65535:
        raise argparse.ArgumentTypeError(f"{text!r} is not a port from 1 to 65535.")
    return int(text)


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
        if arguments.command == "holidays":
            return _list_holidays(arguments, stdout, working_directory, environ)
        if arguments.command == "llm-providers":
            return _list_llm_providers(arguments, stdout, working_directory, environ)
        if arguments.command == "serve":
            return _serve(arguments, working_directory, environ, lock_wait_seconds)
        use_case = build_analyze_bookings(stdout, working_directory, environ, lock_wait_seconds)
        _LOGGER.info("Analysis started.")
        outcome = use_case.run(arguments.input, arguments.config, arguments.insights)
        _report(outcome)
        return _EXIT_CODES[outcome.status]
    finally:
        _LOGGER.removeHandler(handler)


def _list_holidays(
    arguments: argparse.Namespace,
    stdout: BinaryIO,
    working_directory: Path,
    environ: Mapping[str, str],
) -> int:
    use_case = build_list_holidays(stdout, working_directory, environ)
    outcome = use_case.run(arguments.years, arguments.config)
    _report_listing(outcome)
    return _EXIT_CODES[outcome.status]


def _list_llm_providers(
    arguments: argparse.Namespace,
    stdout: BinaryIO,
    working_directory: Path,
    environ: Mapping[str, str],
) -> int:
    use_case = build_list_llm_providers(stdout, working_directory, environ)
    outcome = use_case.run(arguments.config)
    _report_listing(outcome, "Provider listing")
    return _EXIT_CODES[outcome.status]


def _serve(
    arguments: argparse.Namespace,
    working_directory: Path,
    environ: Mapping[str, str],
    lock_wait_seconds: float,
) -> int:
    # Imported here so the other commands do not pay for loading the web framework.
    from hotel_booking_analysis.infrastructure.http_api import ServiceSettings, serve

    settings = ServiceSettings(working_directory, environ, arguments.config, lock_wait_seconds)
    return serve(arguments.host, arguments.port, settings)


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
    if outcome.insights_unavailable:
        _LOGGER.warning(
            "AI insights are unavailable for %d analysis(es); the analyses are unchanged. "
            "See the INSIGHTS_UNAVAILABLE notice and the insight reasons in the result.",
            outcome.insights_unavailable,
        )
    if outcome.status is RunStatus.SUCCEEDED:
        _LOGGER.info("Analysis %s completed, saved and delivered.", outcome.result_id)
    else:
        _LOGGER.error("%s", outcome.message)


def _report_listing(outcome: ListingOutcome, name: str = "Holiday listing") -> None:
    if outcome.status is RunStatus.SUCCEEDED:
        _LOGGER.info("%s delivered.", name)
    else:
        _LOGGER.error("%s", outcome.message)
