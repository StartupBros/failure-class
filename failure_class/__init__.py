"""Stable failure classes for runtime/provider-vs-model-quality triage.

Extracted from the pi-evals lab, where these classes triage local-endpoint
eval failures (mlx_lm.server, llama.cpp llama-server) against model-quality
misses. The class strings are stable identifiers stored in eval evidence.
"""

from __future__ import annotations

import socket
from builtins import TimeoutError as BuiltinTimeoutError
from enum import StrEnum
from urllib.error import HTTPError, URLError

__all__ = ["FailureClass", "classify_failure"]


class FailureClass(StrEnum):
    NONE = "none"
    CONNECTION = "connection"
    AUTH = "auth"
    CONTEXT_OR_MODEL_FIT = "context-or-model-fit"
    ENDPOINT_PROTOCOL = "endpoint-protocol"
    TIMEOUT_SLA = "timeout-sla"
    HARNESS_ABORT = "harness-abort"
    RUNTIME_PROVIDER_WEDGED = "runtime-provider-wedged"
    MODEL_QUALITY = "model-quality"


_AUTH_MARKERS = ("unauthorized", "forbidden", "authentication", "permission denied", "401", "403")
_CONTEXT_MARKERS = (
    "context length",
    "context window",
    "maximum context",
    "prompt too long",
    "model too large",
    "out of memory",
    "not enough memory",
    "exceeds max",
)
_PROTOCOL_MARKERS = ("malformed", "invalid json", "expected openai", "missing choices", "missing data", "protocol")
_TIMEOUT_MARKERS = ("timeout", "timed out", "deadline", "sla")
_ABORT_MARKERS = ("aborted", "cancelled", "canceled", "limit exceeded", "interrupted")
_WEDGED_MARKERS = ("lazy-load", "eager-load", "wedged", "failed to load", "runtime not healthy", "not healthy", "socket not bound")
_CONNECTION_MARKERS = ("connection refused", "connection error", "connect", "dns", "name resolution", "unreachable")


def _message(exc: BaseException | None = None, message: str | None = None) -> str:
    parts = []
    if message:
        parts.append(message)
    if exc is not None:
        parts.append(f"{type(exc).__name__}: {exc}")
    return " ".join(parts).lower()


def _http_status(exc: BaseException | None, status_code: int | None) -> int | None:
    if status_code is not None:
        return status_code
    if isinstance(exc, HTTPError):
        return exc.code
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        return status
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    return None


def classify_failure(
    exc: BaseException | None = None,
    *,
    status_code: int | None = None,
    message: str | None = None,
    successful_model_response: bool = False,
    scorer_failed: bool = False,
    malformed_response: bool = False,
) -> FailureClass:
    """Classify one primary failure class with explicit precedence.

    A scorer/model-quality miss after a successful response is intentionally not
    collapsed into provider failure. Runtime and provider failures take precedence
    over text markers when status/exception evidence is clearer.
    """
    if scorer_failed and successful_model_response:
        return FailureClass.MODEL_QUALITY

    status = _http_status(exc, status_code)
    text = _message(exc, message)

    if status in (401, 403) or any(marker in text for marker in _AUTH_MARKERS):
        return FailureClass.AUTH
    if status in (408, 429, 504) or isinstance(exc, (TimeoutError, BuiltinTimeoutError, socket.timeout)) or any(marker in text for marker in _TIMEOUT_MARKERS):
        return FailureClass.TIMEOUT_SLA
    if isinstance(exc, (ConnectionError, URLError, socket.gaierror, socket.herror)) or any(marker in text for marker in _CONNECTION_MARKERS):
        return FailureClass.CONNECTION
    if malformed_response or any(marker in text for marker in _PROTOCOL_MARKERS):
        return FailureClass.ENDPOINT_PROTOCOL
    if status in (400, 413, 422) and any(marker in text for marker in _CONTEXT_MARKERS):
        return FailureClass.CONTEXT_OR_MODEL_FIT
    if any(marker in text for marker in _CONTEXT_MARKERS):
        return FailureClass.CONTEXT_OR_MODEL_FIT
    if any(marker in text for marker in _WEDGED_MARKERS):
        return FailureClass.RUNTIME_PROVIDER_WEDGED
    if any(marker in text for marker in _ABORT_MARKERS):
        return FailureClass.HARNESS_ABORT
    if status and status >= 500:
        return FailureClass.RUNTIME_PROVIDER_WEDGED
    if scorer_failed:
        return FailureClass.MODEL_QUALITY
    return FailureClass.NONE
