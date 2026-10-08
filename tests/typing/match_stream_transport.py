"""Strict type exercise for the private unary-stream transport boundary."""

from __future__ import annotations

import inspect

import grpc

from clang_toolkit._generated.match.v1 import match_service_pb2, match_stream_pb2
from clang_toolkit.client import _MatchStreamCall, _MatchStreamStub  # pyright: ignore[reportPrivateUsage]


async def consume_stream(stub: _MatchStreamStub,
                         request: match_service_pb2.MatchRequest) -> int:
    call: _MatchStreamCall = stub.StreamMatch(request)
    rows = 0
    async for event in call:
        kind = event.WhichOneof("event")
        if kind == "row":
            rows += 1
        elif kind == "completed":
            assert isinstance(event.completed, match_stream_pb2.MatchStreamCompleted)
    status_result = call.code()
    status = await status_result if inspect.isawaitable(status_result) else status_result
    if status != grpc.StatusCode.OK:
        details_result = call.details()
        details = await details_result if inspect.isawaitable(details_result) else details_result
        raise RuntimeError(details)
    return rows
