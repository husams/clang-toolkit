"""Status-message classifiers for resource admission and lost RPC replies."""

from __future__ import annotations

_KNOWN_SCOPE_ADMISSION_REJECTIONS = (
    "resource scope exceeds its memory admission limit",
    "resource scope count limit exceeded",
    "resource scope admission limits exceeded",
)


def is_receive_size_rejection(error: BaseException) -> bool:
    """Whether gRPC rejected a response after the server may have committed it."""
    if getattr(getattr(error, "code", None), "name", None) != "RESOURCE_EXHAUSTED":
        return False
    message = str(error).casefold()
    return "received message larger than max" in message


def is_known_scope_admission_rejection(error: BaseException) -> bool:
    """Whether RESOURCE_EXHAUSTED proves OpenResourceScope admitted no scope."""
    if getattr(getattr(error, "code", None), "name", None) != "RESOURCE_EXHAUSTED":
        return False
    message = str(error).casefold()
    return any(rejection in message for rejection in _KNOWN_SCOPE_ADMISSION_REJECTIONS)
