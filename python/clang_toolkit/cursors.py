"""Typed request builders and status errors for independent match cursors."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import grpc

from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit._generated.match.v1 import match_result_pb2 as results


class CursorError(RuntimeError):
    """A failed cursor RPC; failed operations preserve the prior revision."""

    def __init__(self, code: grpc.StatusCode, message: str) -> None:
        self.code = code
        super().__init__(message)


def file_request(
    path: str | Path, query: str, *, working_directory: str | Path | None = None,
    compile_arguments: Sequence[str] = (),
    traversal_mode: int = pb.MATCH_TRAVERSAL_MODE_AS_IS,
) -> pb.MatchRequest:
    working = str(Path(working_directory or Path.cwd()).resolve())
    return pb.MatchRequest(
        query=query, traversal_mode=traversal_mode,
        file=pb.FileMatchTarget(
            file_path=str(path), working_directory=working,
            compile_arguments=compile_arguments,
        ),
    )


def retained_request(
    session_id: str, query: str, *, bind: str | None = None,
    match_index: int | None = None,
    scope: int = results.BINDING_MATCH_SCOPE_SUBTREE,
    expected_result_revision: int | None = None,
    traversal_mode: int = pb.MATCH_TRAVERSAL_MODE_AS_IS,
) -> pb.MatchRequest:
    request = pb.MatchRequest(query=query, traversal_mode=traversal_mode)
    if bind is None:
        if match_index is not None:
            raise ValueError("match_index requires a binding selector")
        target = request.session
    else:
        target = request.binding
        target.bind = bind
        target.scope = scope
        if match_index is not None:
            target.match_index = match_index
    target.session_id = session_id
    if expected_result_revision is not None:
        target.expected_result_revision = expected_result_revision
    return request
