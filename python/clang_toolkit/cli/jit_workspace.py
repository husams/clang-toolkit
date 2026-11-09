"""Decode read-only native workspace projections for the shared console UI."""

from __future__ import annotations

import asyncio
from base64 import b64decode
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from google.protobuf import descriptor_pool, message_factory
from google.protobuf.json_format import ParseDict
from google.protobuf.message import Message

from clang_toolkit._generated.match.v1 import match_result_pb2
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.batches import BatchRun
from clang_toolkit.call_graph_values import CallGraph, CallGraphNodeValue
from clang_toolkit.match_values import BindingSelection, MatchRow
from clang_toolkit.resources import FileHandle, FileSet, InputDescriptor

from .runtime.filesystem import Directory, File
from .runtime.progress import BatchProgress, durable_progress
from .runtime.semantic import EnumValue, MessageView, property_value, view
from .jit_workspace_state import (
    ProjectedCollection,
    display_snapshot,
    outline_snapshot,
)
from .workspace_state import PanelEntry, resource_snapshot

_Request = Callable[[dict[str, Any]], dict[str, Any]]
_DETACHED_OWNER = CursorOwner(None, "", 0, lambda _: None)


def wire_message(value: dict[str, Any]) -> Message:
    descriptor = descriptor_pool.Default().FindMessageTypeByName(value["type"])
    return message_factory.GetMessageClass(descriptor).FromString(
        b64decode(value["data"], validate=True)
    )


@dataclass(frozen=True)
class Opaque:
    outline_type: str
    text: str = ""

    def __str__(self) -> str:
        return self.text or self.outline_type


def projected(value: Any, *, raw_message: bool = False) -> Any:
    if not isinstance(value, dict):
        return value
    kind, data = value["kind"], value["data"]
    if kind in {"list", "tuple", "matches", "record"}:
        if kind == "record":
            children = tuple((key, projected(item)) for key, item in data)
        else:
            children = tuple(projected(item, raw_message=raw_message) for item in data)
        return ProjectedCollection(kind, value["length"], value["start"], children)
    if kind == "match_row":
        wire = dict(data)
        path = wire.pop("source_file", None)
        row = ParseDict(wire, match_result_pb2.MatchResult())
        return MatchRow(row.SerializeToString(), _DETACHED_OWNER, 0, path)
    if kind == "binding":
        message = wire_message(value)
        return BindingSelection(
            value["name"],
            _DETACHED_OWNER,
            value["index"],
            _binding_data=message.SerializeToString(),
            source_file=value.get("path"),
        )
    if kind == "file_handle":
        info = wire_message(value)
        return FileHandle(
            info.lease_id,
            InputDescriptor.from_proto(info.input),
            None,
            info.source_revision,
            info.snapshot_id,
            info.state,
        )
    if kind == "message":
        message = wire_message(value)
        if raw_message:
            return message
        projected_message = (
            MessageView(
                message.SerializeToString(),
                type(message),
                tuple(tuple(item) for item in value["availability"]),
                value["path"],
            )
            if "path" in value
            else view(message)
        )
        if field := value.get("field"):
            return property_value(projected_message, field)
        if message.DESCRIPTOR.full_name == "ctk.match.v1.DiscoverFilesResponse":
            return FileSet(
                tuple(InputDescriptor.from_proto(item) for item in message.inputs),
                tuple(message.diagnostics),
                message.metadata_bytes,
            )
        if message.DESCRIPTOR.full_name == "ctk.match.v1.InputDescriptor":
            return InputDescriptor.from_proto(message)
        owner = _DETACHED_OWNER if value.get("retained") else None
        if message.DESCRIPTOR.full_name == "ctk.analysis.v1.CallGraphResponse":
            return CallGraph(message, owner=owner)
        if message.DESCRIPTOR.full_name == "ctk.analysis.v1.CallGraphNode":
            return CallGraphNodeValue(message, owner, message.location.file)
        return projected_message
    if kind in {"file", "directory"}:
        cls = File if kind == "file" else Directory
        return cls(
            data["path"],
            data["absolute"],
            data["size"],
            datetime.fromisoformat(data["modified"]),
        )
    if kind == "enum":
        return EnumValue(*data)
    if kind == "tree":
        return Opaque("ParsedTree", f"parsed {data}")
    if kind == "matcher":
        return Opaque("MatcherExpr", data)
    return Opaque(data)


@dataclass(frozen=True)
class Outcome:
    output: str | None
    success: bool = True
    markdown: str | None = None
    outline_value: tuple[str, int] | None = None
    parts: tuple[Outcome, ...] = ()
    exit_requested: bool = False
    result_key: str | None = None


def command_outcome(reply: dict[str, Any]) -> Outcome:
    data = reply["output"].encode()
    parts = []
    start = 0
    for preview in reply.get("previews", ()):
        end = preview["offset"]
        if end > start:
            parts.append(Outcome(data[start:end].decode().removesuffix("\n")))
        if markdown := preview.get("markdown"):
            parts.append(Outcome(markdown, markdown=markdown))
        else:
            parts.append(
                Outcome(
                    "",
                    outline_value=(preview["kind"], preview["id"]),
                    result_key=preview.get("key") or None,
                )
            )
        start = end
    if start < len(data):
        parts.append(Outcome(data[start:].decode().removesuffix("\n")))
    if reply["error"]:
        parts.append(Outcome(reply["error"], False))
    return Outcome(
        "",
        not reply["error"],
        parts=tuple(parts),
        exit_requested=bool(reply.get("exit")),
    )


def batch_progress(message: dict[str, Any]) -> BatchProgress:
    if "durable" in message:
        return durable_progress(BatchRun(wire_message(message["durable"])))
    return BatchProgress(**message["progress"])


class NativeWorkspace:
    def __init__(self, request: _Request, lock: asyncio.Lock):
        self.request = request
        self.lock = lock

    async def read(self, kind: str, **options: Any) -> Any:
        async with self.lock:
            task = asyncio.create_task(
                asyncio.to_thread(self.request, {"inspect": kind, **options})
            )
            try:
                reply = await asyncio.shield(task)
            except asyncio.CancelledError:
                await task
                raise
        if reply.get("error"):
            raise ValueError(reply["error"])
        return reply["value"]

    async def outline(
        self, expanded: frozenset[str], pages: dict[str, int]
    ) -> list[PanelEntry]:
        values = await self.read("outline", expanded=sorted(expanded), pages=pages)
        return outline_snapshot(
            {name: projected(value) for name, value in values.items()}, expanded, pages
        )

    async def result(
        self, kind: str, result: int, expanded: frozenset[str], pages: dict[str, int]
    ) -> list[PanelEntry] | None:
        value = await self.read(
            "outline", result=result, expanded=sorted(expanded), pages=pages
        )
        if value is None:
            return [
                PanelEntry(
                    ":expired", "Preview expired. Run the command again to expand it."
                )
            ]
        if kind == "bindings_list":
            return outline_snapshot(
                {name: projected(item) for name, item in value.items()}, expanded, pages
            )
        return display_snapshot(
            kind,
            projected(
                value, raw_message=kind == "file_list" and value["kind"] == "tuple"
            ),
            expanded,
            pages,
        )

    async def resources(self, expanded: frozenset[str]) -> list[PanelEntry]:
        value = await self.read("resources")
        return resource_snapshot(
            tuple(wire_message(value["files"]).files),
            wire_message(value["sessions"]),
            value["attach_name"],
            expanded,
        )

    async def status(self) -> Message:
        return wire_message(await self.read("status"))

    async def batch(self, run_id: str, *, cancel: bool = False) -> BatchProgress:
        wire = await self.read(
            "batch_cancel" if cancel else "batch_status", run_id=run_id
        )
        return durable_progress(BatchRun(wire_message(wire)))
