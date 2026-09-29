"""Domain errors and notices (ADR-0001, ADR-0004, ADR-0005)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Notice:
    """A non-fatal message carried by the result (ADR-0002 `notices`)."""

    code: str
    message: str


class InputError(Exception):
    """The run cannot start or continue because of the input (ADR-0001, ADR-0005 exit code 2)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ConfigurationError(InputError):
    """A configuration file or value is invalid; names the key when known (ADR-0004)."""

    def __init__(self, message: str, key: str | None = None) -> None:
        super().__init__("CONFIGURATION_ERROR", message)
        self.key = key


class HistoryError(Exception):
    """The result history could not be updated (ADR-0003, ADR-0005 exit code 3)."""


class HistoryWriteError(HistoryError):
    """The result could not be appended, or the history lock could not be taken (ADR-0003)."""


class HistoryRetentionError(HistoryError):
    """Retention failed after a successful append; the appended result stays (ADR-0003)."""


class HistoryReadError(HistoryError):
    """The history file exists but cannot be read (ADR-0003)."""


class ResultDeliveryError(Exception):
    """The result could not be written to the caller (ADR-0005 exit code 4)."""
