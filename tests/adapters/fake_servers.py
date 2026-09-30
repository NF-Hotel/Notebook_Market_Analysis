"""Real local HTTP servers on 127.0.0.1 that play a language model provider (test helper).

Every server listens on a port chosen by the operating system, runs in daemon threads and is shut
down when its `with` block ends. Nothing depends on Ollama or LM Studio being installed.
"""

import contextlib
import json
import socket
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

Behavior = Callable[[BaseHTTPRequestHandler, threading.Event], None]


def json_answer(document: object, status: int = 200) -> Behavior:
    """Answer every GET with `document` as JSON."""

    def behave(handler: BaseHTTPRequestHandler, stop: threading.Event) -> None:
        body = json.dumps(document).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    return behave


def raw_answer(body: bytes, status: int = 200) -> Behavior:
    """Answer every GET with `body` as it is."""

    def behave(handler: BaseHTTPRequestHandler, stop: threading.Event) -> None:
        handler.send_response(status)
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    return behave


def never_answers(handler: BaseHTTPRequestHandler, stop: threading.Event) -> None:
    """Accept the request and say nothing until the server is shut down."""
    stop.wait(30)


def trickling_body(handler: BaseHTTPRequestHandler, stop: threading.Event) -> None:
    """Send the headers, then one byte of a large body every 0.05 s."""
    handler.send_response(200)
    handler.send_header("Content-Length", "100000")
    handler.end_headers()
    handler.wfile.flush()
    while not stop.is_set():
        handler.wfile.write(b" ")
        handler.wfile.flush()
        time.sleep(0.05)


def trickling_headers(handler: BaseHTTPRequestHandler, stop: threading.Event) -> None:
    """Send the status line and header bytes one at a time, never finishing the headers."""
    for byte in b"HTTP/1.1 200 OK\r\nX-Slow: " + b"a" * 5000:
        if stop.is_set():
            return
        handler.wfile.write(bytes([byte]))
        handler.wfile.flush()
        time.sleep(0.05)


def endless_body(handler: BaseHTTPRequestHandler, stop: threading.Event) -> None:
    """Send a 200 answer without a length that never ends (until the client gives up)."""
    handler.send_response(200)
    handler.end_headers()
    chunk = b" " * 65536
    while not stop.is_set():
        handler.wfile.write(chunk)
        handler.wfile.flush()


def _handler_class(
    behavior: Behavior, stop: threading.Event, requests: list[str], keep_alive: bool
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1" if keep_alive else "HTTP/1.0"

        def do_GET(self) -> None:
            requests.append(self.path)
            with contextlib.suppress(OSError):  # the client hung up
                behavior(self, stop)

        def log_message(self, format: str, *args: object) -> None:
            pass

    return Handler


class FakeServer:
    """A running fake provider: its base URL and the paths that were requested."""

    def __init__(self, base_url: str, requests: list[str]) -> None:
        self.base_url = base_url
        self.requests = requests


@contextmanager
def serve(behavior: Behavior, keep_alive: bool = False) -> Iterator[FakeServer]:
    """Run a server that plays `behavior` for every GET request (HTTP/1.1 when `keep_alive`)."""
    stop = threading.Event()
    requests: list[str] = []
    handler = _handler_class(behavior, stop, requests, keep_alive)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield FakeServer(f"http://127.0.0.1:{server.server_address[1]}", requests)
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        thread.join(5)


def closed_port_url() -> str:
    """A base URL on which nothing listens: a port that was bound and then released."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return f"http://127.0.0.1:{port}"
