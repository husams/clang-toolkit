"""Shared recovery and cleanup semantics for both execution engines."""

from __future__ import annotations

import sys
from typing import Any, Callable

from .semantics import CancelledError, Context, ExecutionLimitError, _error


class LoopBreak(BaseException):
    """Internal transfer to the nearest lexical loop."""


class LoopContinue(BaseException):
    """Internal transfer to the next iteration."""


FATAL_ERRORS = (CancelledError, ExecutionLimitError)


def split_handlers(statements: tuple[Any, ...]) -> tuple[dict[str, Any], tuple[Any, ...]]:
    handlers = {}
    body = []
    for statement in statements:
        node = statement.children[0] if statement.kind == "observe" else statement
        if node.kind == "handler":
            handlers[node.value] = node.children[0]
        else:
            body.append(statement)
    return handlers, tuple(body)


def recover(context: Context, body: Callable[[Context], Any],
            fallback: Callable[[Context], Any]) -> Any:
    try:
        return body(context)
    except FATAL_ERRORS:
        raise
    except Exception:
        return fallback(context)


def cleanup(context: Context, action: Callable[[Context], Any]) -> None:
    # Cleanup has a bounded shared reserve, so cancellation or an exhausted
    # ordinary step budget cannot prevent resource release from starting.
    pending = sys.exception()
    session = getattr(context, "session", None)
    previous_tail = getattr(session, "last_tail", None)
    context.cleanup_depth += 1
    try:
        action(context)
    finally:
        context.cleanup_depth -= 1
        if session is not None:
            session.last_tail = previous_tail
    if not context.cleanup_depth and not isinstance(pending, FATAL_ERRORS):
        if context.cancel_hook is not None and context.cancel_hook():
            raise _error(context, None, "execution cancelled", CancelledError)
        if context.steps > context.max_steps:
            raise _error(context, None, "execution step limit exceeded", ExecutionLimitError)
