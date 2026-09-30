"""One JSON GET with the standard library within a total deadline (ADR-0009 "Deadlines").

A socket timeout applies to each connect or read, not to the whole request, so a provider that
keeps sending a few bytes would never trip it. `get_json` therefore takes the start time, sets the
socket timeout to the time that remains before every socket operation, reads the answer in small
chunks and checks the deadline before each read. A timer that shuts the socket down at the
deadline ends a read that is blocked in the answer headers. Proxies and redirects are not used:
discovery talks only to the configured address. `http.client` is used because `urllib` gives no
access to the socket between reads; it is the same standard-library layer, so no dependency is
added. `post_json` is added with the AI insights (MIL-011).
"""

import contextlib
import http.client
import json
import socket
import threading
import time
from urllib.parse import urlsplit

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.llm import ProviderReason

MAX_RESPONSE_BYTES = 1_048_576
CHUNK_BYTES = 8192


class HttpFailure(Exception):  # noqa: N818 - the name is fixed by DCD-001
    """A failed HTTP request with its provider reason; never leaves the adapters."""

    def __init__(self, reason: ProviderReason, detail: str = "") -> None:
        super().__init__(detail or reason.value)
        self.reason = reason


class _Deadline:
    def __init__(self, timeout_seconds: float) -> None:
        self._end = time.monotonic() + timeout_seconds

    def remaining(self) -> float:
        """Seconds left; raises `HttpFailure(TIMEOUT)` when none is left."""
        left = self._end - time.monotonic()
        if left <= 0:
            raise HttpFailure(ProviderReason.TIMEOUT, "The deadline passed.")
        return left

    def passed(self) -> bool:
        return time.monotonic() >= self._end


def get_json(url: str, timeout_seconds: float) -> JsonValue:
    """GET `url` and return the parsed JSON body; the whole call takes at most the timeout.

    Raises `HttpFailure` with `CONNECTION_REFUSED` (nothing listens), `TIMEOUT` (no complete
    answer in time), `UNEXPECTED_ANSWER` (status other than 200, body too large, not JSON) or
    `NETWORK_ERROR` (any other failure to connect or read).
    """
    deadline = _Deadline(timeout_seconds)
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise HttpFailure(ProviderReason.NETWORK_ERROR, "The URL has no http(s) host.")
    connection_class = (
        http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    )
    connection = connection_class(parts.hostname, parts.port, timeout=deadline.remaining())
    try:
        return _exchange(connection, parts.path or "/", parts.query, deadline)
    except HttpFailure:
        raise
    except TimeoutError as error:
        raise HttpFailure(ProviderReason.TIMEOUT, str(error)) from error
    except ConnectionRefusedError as error:
        raise HttpFailure(ProviderReason.CONNECTION_REFUSED, str(error)) from error
    except (http.client.HTTPException, ValueError) as error:
        reason = ProviderReason.TIMEOUT if deadline.passed() else ProviderReason.UNEXPECTED_ANSWER
        raise HttpFailure(reason, str(error)) from error
    except OSError as error:
        reason = ProviderReason.TIMEOUT if deadline.passed() else ProviderReason.NETWORK_ERROR
        raise HttpFailure(reason, str(error)) from error
    finally:
        connection.close()


def _shut_down(sock: socket.socket) -> None:
    with contextlib.suppress(OSError):
        sock.shutdown(socket.SHUT_RDWR)


def _exchange(
    connection: http.client.HTTPConnection, path: str, query: str, deadline: _Deadline
) -> JsonValue:
    connection.connect()  # bounded by the socket timeout set from the remaining time
    # `http.client` drops `connection.sock` after the answer of a connection that will close, so
    # the socket is kept here for the deadline checks and the watchdog.
    sock = connection.sock
    if sock is None:
        raise HttpFailure(ProviderReason.NETWORK_ERROR, "The connection was not opened.")
    watchdog = threading.Timer(deadline.remaining(), _shut_down, args=(sock,))
    watchdog.daemon = True
    watchdog.start()
    try:
        return _talk(connection, sock, path, query, deadline)
    finally:
        watchdog.cancel()


def _talk(
    connection: http.client.HTTPConnection,
    sock: socket.socket,
    path: str,
    query: str,
    deadline: _Deadline,
) -> JsonValue:
    sock.settimeout(deadline.remaining())
    connection.request("GET", f"{path}?{query}" if query else path, headers={"Accept": "*/*"})
    sock.settimeout(deadline.remaining())
    response = connection.getresponse()
    if response.status != 200:
        raise HttpFailure(ProviderReason.UNEXPECTED_ANSWER, f"HTTP status {response.status}.")
    declared = response.getheader("Content-Length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_RESPONSE_BYTES:
        raise HttpFailure(ProviderReason.UNEXPECTED_ANSWER, "The answer is too large.")
    return _parse(_read_body(sock, response, deadline))


def _read_body(
    sock: socket.socket, response: http.client.HTTPResponse, deadline: _Deadline
) -> bytes:
    body = bytearray()
    while not response.isclosed():  # closed by `http.client` once the declared length was read
        sock.settimeout(deadline.remaining())
        chunk = response.read1(CHUNK_BYTES)
        if not chunk:
            break
        body += chunk
        if len(body) > MAX_RESPONSE_BYTES:
            raise HttpFailure(ProviderReason.UNEXPECTED_ANSWER, "The answer is too large.")
    return bytes(body)


def _parse(body: bytes) -> JsonValue:
    try:
        document: JsonValue = json.loads(body.decode("utf-8"))
    except ValueError as error:  # includes UnicodeDecodeError and JSONDecodeError
        raise HttpFailure(ProviderReason.UNEXPECTED_ANSWER, "The answer is not JSON.") from error
    return document
