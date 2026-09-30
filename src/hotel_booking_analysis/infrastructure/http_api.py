"""HTTP API: a second driving adapter over the same use cases (ADR-0013, ADR-0008, ADR-0005).

Each route runs the use case the command line runs, through the composition root, and returns
the bytes the command writes to standard output: the serialized JSON and one newline. The result
of the analysis route is the line that was appended to the history. Routes are plain functions,
which the framework runs in its thread pool, so a long insight request does not block the others.
"""

import io
import json
import logging
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import Response

from hotel_booking_analysis.adapters.json_holiday_listing_serializer import (
    load_holiday_listing_schema,
)
from hotel_booking_analysis.adapters.json_provider_listing_serializer import (
    load_provider_listing_schema,
)
from hotel_booking_analysis.adapters.json_result_serializer import (
    load_result_schema,
    load_result_schema_1_1,
)
from hotel_booking_analysis.application.analyze_bookings import RunStatus
from hotel_booking_analysis.infrastructure.bootstrap import (
    build_analyze_bookings,
    build_list_holidays,
    build_list_llm_providers,
)
from hotel_booking_analysis.infrastructure.file_lock import LOCK_WAIT_SECONDS

# The `input.reference` of a result made from a request body; the server never reads a client path.
BODY_REFERENCE = "request-body.json"

JSON_MEDIA_TYPE = "application/json"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

HTTP_STATUS: dict[RunStatus, int] = {
    RunStatus.SUCCEEDED: 200,
    RunStatus.INPUT_FAILED: 422,
    RunStatus.HISTORY_FAILED: 500,
    RunStatus.DELIVERY_FAILED: 500,
}
_DOCUMENT_STATUSES = frozenset({RunStatus.SUCCEEDED, RunStatus.INPUT_FAILED})

_LOGGER = logging.getLogger("hotel_booking_analysis.http_api")

_SCHEMAS = "#/components/schemas/"
_ERROR_OBJECT = "ErrorObject"
_FRAMEWORK_ERROR = "FrameworkError"
RESULT_1_0 = "AnalysisResult_1_0"
RESULT_1_1 = "AnalysisResult_1_1"
HOLIDAY_LISTING = "HolidayCalendar_1_0"
PROVIDER_LISTING = "LlmProviders_1_0"


def _ref(name: str) -> dict[str, object]:
    return {"$ref": f"{_SCHEMAS}{name}"}


def _one_of(*names: str) -> dict[str, object]:
    return _ref(names[0]) if len(names) == 1 else {"oneOf": [_ref(name) for name in names]}


def _json_response(description: str, *names: str) -> dict[str, object]:
    content = {JSON_MEDIA_TYPE: {"schema": _one_of(*names)}}
    return {"description": description, "content": content}


def _document_responses(
    success: tuple[str, ...], failed: tuple[str, ...], *extra: tuple[int, str, str]
) -> dict[int | str, dict[str, object]]:
    """The documented answers of a route; `extra` are (status, description, schema) triples."""
    responses: dict[int | str, dict[str, object]] = {
        200: _json_response("The JSON document the command writes.", *success),
        422: _json_response(
            "Input or configuration error; the body is the failed document, or the framework's "
            "list of rejected arguments.",
            *failed,
            _FRAMEWORK_ERROR,
        ),
        500: _json_response(
            "History or delivery failure; the body is a small error object.", _ERROR_OBJECT
        ),
    }
    for status, description, schema in extra:
        responses[status] = _json_response(description, schema)
    return responses


_ANALYZE_RESPONSES = _document_responses(
    (RESULT_1_0, RESULT_1_1),
    (RESULT_1_0,),
    (415, "The Content-Type is not application/json.", _FRAMEWORK_ERROR),
)
_HOLIDAY_RESPONSES = _document_responses((HOLIDAY_LISTING,), (HOLIDAY_LISTING,))
_PROVIDER_RESPONSES = _document_responses((PROVIDER_LISTING,), (PROVIDER_LISTING,))

_ERROR_OBJECT_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["status", "error"],
    "additionalProperties": False,
    "properties": {
        "status": {"const": "error"},
        "result_id": {"type": "string"},
        "error": {
            "type": "object",
            "required": ["code", "message"],
            "additionalProperties": False,
            "properties": {
                "code": {"enum": ["HISTORY_FAILED", "DELIVERY_FAILED"]},
                "message": {"type": ["string", "null"]},
            },
        },
    },
}
_FRAMEWORK_ERROR_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["detail"],
    "properties": {"detail": {"type": ["string", "array"]}},
}


def _rebased(node: Any, own: str, names: Mapping[str, str]) -> Any:  # noqa: ANN401 - JSON
    """`node` with every `$ref` turned into a pointer inside the OpenAPI document."""
    if isinstance(node, list):
        return [_rebased(child, own, names) for child in node]
    if not isinstance(node, dict):
        return node
    rebased = {key: _rebased(child, own, names) for key, child in node.items()}
    reference = node.get("$ref")
    if isinstance(reference, str):
        document, _, pointer = reference.partition("#")
        rebased["$ref"] = f"{_SCHEMAS}{names[document] if document else own}{pointer}"
    return rebased


def _as_component(name: str, document: dict[str, Any], names: Mapping[str, str]) -> dict[str, Any]:
    body = {key: value for key, value in document.items() if key not in ("$id", "$schema")}
    rebased: dict[str, Any] = _rebased(body, name, names)
    return rebased


def openapi_components() -> dict[str, Any]:
    """The schemas the responses refer to.

    The four documents of ADR-0002 and ADR-0011 are the repository's JSON Schema files. Only their
    `$ref`s change, from a pointer inside the file or a reference by `$id` to a pointer inside the
    OpenAPI document, and `$id` and `$schema` are dropped, so that every OpenAPI tool resolves them
    (OpenAPI 3.1 schema objects are JSON Schema 2020-12).
    """
    documents = {
        RESULT_1_0: load_result_schema(),
        RESULT_1_1: load_result_schema_1_1(),
        HOLIDAY_LISTING: load_holiday_listing_schema(),
        PROVIDER_LISTING: load_provider_listing_schema(),
    }
    names = {document["$id"]: name for name, document in documents.items()}
    components = {name: _as_component(name, doc, names) for name, doc in documents.items()}
    return {
        **components,
        _ERROR_OBJECT: _ERROR_OBJECT_SCHEMA,
        _FRAMEWORK_ERROR: _FRAMEWORK_ERROR_SCHEMA,
    }


@dataclass(frozen=True, slots=True)
class ServiceSettings:
    """What the service needs from its process: fixed at start, never taken from a request.

    `stream_factory` makes the stream that plays standard output for one request.
    """

    working_directory: Path
    environ: Mapping[str, str]
    config_path: Path | None = None
    lock_wait_seconds: float = LOCK_WAIT_SECONDS
    stream_factory: Callable[[], io.BytesIO] = io.BytesIO


async def _json_body(request: Request) -> bytes:
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != JSON_MEDIA_TYPE:
        raise HTTPException(status_code=415, detail="The Content-Type must be application/json.")
    return await request.body()


def _error_response(status: RunStatus, message: str | None, result_id: str | None) -> Response:
    error: dict[str, object] = {"code": status.name, "message": message}
    document: dict[str, object] = {"status": "error", "error": error}
    if result_id is not None:
        document["result_id"] = result_id
    _LOGGER.error("%s", message)
    return Response(json.dumps(document), HTTP_STATUS[status], media_type=JSON_MEDIA_TYPE)


def _respond(
    status: RunStatus, stream: io.BytesIO, message: str | None, result_id: str | None = None
) -> Response:
    """The document of the run with its status code, or the error object of a failed step."""
    if status in _DOCUMENT_STATUSES:
        return Response(stream.getvalue(), HTTP_STATUS[status], media_type=JSON_MEDIA_TYPE)
    return _error_response(status, message, result_id)


class _Service:
    def __init__(self, settings: ServiceSettings) -> None:
        self._settings = settings

    def analyze(
        self, body: Annotated[bytes, Depends(_json_body)], insights: bool = False
    ) -> Response:
        stream = self._settings.stream_factory()
        use_case = build_analyze_bookings(
            stream,
            self._settings.working_directory,
            self._settings.environ,
            self._settings.lock_wait_seconds,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / BODY_REFERENCE
            path.write_bytes(body)
            outcome = use_case.run(path, self._settings.config_path, insights)
        result_id = outcome.result_id if outcome.status is RunStatus.DELIVERY_FAILED else None
        return _respond(outcome.status, stream, outcome.message, result_id)

    def holidays(self, years: str | None = None) -> Response:
        stream = self._settings.stream_factory()
        use_case = build_list_holidays(
            stream, self._settings.working_directory, self._settings.environ
        )
        outcome = use_case.run(years, self._settings.config_path)
        return _respond(outcome.status, stream, outcome.message)

    def llm_providers(self) -> Response:
        stream = self._settings.stream_factory()
        use_case = build_list_llm_providers(
            stream, self._settings.working_directory, self._settings.environ
        )
        outcome = use_case.run(self._settings.config_path)
        return _respond(outcome.status, stream, outcome.message)


def _health() -> dict[str, str]:
    return {"status": "ok"}


def _openapi_of(app: FastAPI) -> Callable[[], dict[str, Any]]:
    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            description = get_openapi(title=app.title, version=app.version, routes=app.routes)
            schemas = description.setdefault("components", {}).setdefault("schemas", {})
            schemas.update(openapi_components())
            app.openapi_schema = description
        return app.openapi_schema

    return openapi


def create_app(settings: ServiceSettings) -> FastAPI:
    """Create the ASGI application; it holds no state besides `settings` (ADR-0013)."""
    app = FastAPI(title="Hotel booking analysis", version="0.1.0")
    service = _Service(settings)
    body_schema = {"type": "array", "items": {"type": "object"}}
    app.add_api_route(
        "/analyze",
        service.analyze,
        methods=["POST"],
        response_class=Response,
        responses=_ANALYZE_RESPONSES,
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {JSON_MEDIA_TYPE: {"schema": body_schema}},
            }
        },
    )
    app.add_api_route(
        "/holidays",
        service.holidays,
        methods=["GET"],
        response_class=Response,
        responses=_HOLIDAY_RESPONSES,
    )
    app.add_api_route(
        "/llm-providers",
        service.llm_providers,
        methods=["GET"],
        response_class=Response,
        responses=_PROVIDER_RESPONSES,
    )
    app.add_api_route("/health", _health, methods=["GET"])
    app.openapi = _openapi_of(app)  # type: ignore[method-assign]  # documented FastAPI hook
    return app


def serve(host: str, port: int, settings: ServiceSettings) -> int:
    """Run the service until it is stopped; it has no authentication (ADR-0013)."""
    if host not in LOOPBACK_HOSTS:
        _LOGGER.warning(
            "The service listens on %s and has no authentication; put it behind a gateway.", host
        )
    uvicorn.run(create_app(settings), host=host, port=port)
    return 0
