"""Typed client values and request helpers for durable server-owned batches."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from typing import Any
from uuid import uuid4

from clang_toolkit._generated.analysis.v1 import batch_pb2
from clang_toolkit._generated.analysis.v1 import script_value_pb2
from clang_toolkit._generated.match.v1 import match_result_pb2
from clang_toolkit.resources import FileSet, InputDescriptor


@dataclass(frozen=True, slots=True)
class BatchRun:
    """A revisioned durable run whose group results are detached values."""

    _value: batch_pb2.BatchRun

    @property
    def run_id(self) -> str:
        return self._value.run_id

    @property
    def revision(self) -> int:
        return self._value.revision

    @property
    def status(self) -> str:
        return self._value.state

    @property
    def state(self) -> str:
        return self._value.state

    @property
    def results_complete(self) -> bool:
        return self._value.results_complete

    @property
    def groups(self) -> tuple[batch_pb2.BatchGroup, ...]:
        values: list[batch_pb2.BatchGroup] = []
        for group in self._value.groups:
            copy = batch_pb2.BatchGroup()
            copy.CopyFrom(group)
            values.append(copy)
        return tuple(values)

    @property
    def result_group_indices(self) -> tuple[int, ...]:
        return tuple(
            group.index
            for group in self._value.groups
            if group.state == "completed" and _final_value(group) is not None
        )

    @property
    def results(self) -> tuple[DetachedScriptValue, ...]:
        """Return immutable copies of successful groups' final ScriptValues."""
        values: list[DetachedScriptValue] = []
        for group in self._value.groups:
            final = _final_value(group) if group.state == "completed" else None
            if final is None:
                continue
            values.append(DetachedScriptValue(final.SerializeToString()))
        return tuple(values)

    def promote(self) -> tuple[Any, ...]:
        """Promote completed detached final values into the caller's local result set."""
        budget = [10_000, 1_000_000]
        return tuple(value.to_python(budget) for value in self.results)

    def to_proto(self) -> batch_pb2.BatchRun:
        result = batch_pb2.BatchRun()
        result.CopyFrom(self._value)
        return result


def start_batch_request(
    inputs: FileSet | Sequence[InputDescriptor],
    body_source: str,
    *,
    group_variable: str = "part",
    size: int | None = None,
    count: int | None = None,
    jobs: int | None = None,
    memory_bytes: int | None = None,
    continue_on_error: bool = False,
    request_id: str | None = None,
) -> batch_pb2.StartBatchRequest:
    """Build a durable request while preserving frozen compilation profiles."""
    if (size is None) == (count is None):
        raise ValueError("choose exactly one of size or count")
    if not group_variable.isidentifier():
        raise ValueError("group_variable must be an identifier")
    manifest = inputs.inputs if isinstance(inputs, FileSet) else tuple(inputs)
    if any(not isinstance(item, InputDescriptor) for item in manifest):
        raise TypeError("inputs must be a FileSet or InputDescriptor sequence")
    if size is not None and size <= 0:
        raise ValueError("size must be positive")
    if count is not None and count < 0:
        raise ValueError("count cannot be negative")
    if count == 0 and manifest:
        raise ValueError("count may be zero only for an empty input manifest")
    if jobs is not None and jobs <= 0:
        raise ValueError("jobs must be positive")
    if memory_bytes is not None and memory_bytes <= 0:
        raise ValueError("memory_bytes must be positive")
    request = batch_pb2.StartBatchRequest(
        request_id=request_id or str(uuid4()),
        inputs=[item.to_proto() for item in manifest],
        body_source=body_source,
        group_variable=group_variable,
        jobs=jobs,
        memory_bytes=memory_bytes,
        continue_on_error=continue_on_error,
    )
    if size is not None:
        request.size = size
    else:
        request.count = count or 0
    return request


def batch_run(value: Any) -> BatchRun:
    """Copy a protobuf report into its public typed wrapper."""
    report = batch_pb2.BatchRun()
    report.CopyFrom(value)
    return BatchRun(report)


@dataclass(frozen=True, slots=True)
class DetachedMatchRow:
    """Inspectable semantic bindings copied from a completed durable group."""

    _data: bytes

    def _message(self) -> match_result_pb2.MatchResult:
        value = match_result_pb2.MatchResult()
        value.ParseFromString(self._data)
        return value

    @property
    def bindings(self) -> dict[str, match_result_pb2.MatchBinding]:
        result: dict[str, match_result_pb2.MatchBinding] = {}
        for name, binding in self._message().bindings.items():
            copy = match_result_pb2.MatchBinding()
            copy.CopyFrom(binding)
            result[name] = copy
        return result

    def binding_view(self, name: str) -> Any:
        """Return a read-only semantic view for one copied binding."""
        from clang_toolkit.cli.runtime.semantic import view

        try:
            return view(self.bindings[name])
        except KeyError as error:
            raise KeyError(f"unknown binding: {name}") from error

    @property
    def source_file(self) -> str | None:
        return None

    @property
    def source_match_index(self) -> int | None:
        value = self._message()
        return (
            value.source_match_index if value.HasField("source_match_index") else None
        )

    def to_dict(self) -> dict[str, Any]:
        from google.protobuf.json_format import MessageToDict

        return MessageToDict(self._message(), preserving_proto_field_name=True)


@dataclass(frozen=True, slots=True)
class DetachedScriptValue:
    """Immutable serialized copy of a native ScriptValue emission."""

    _data: bytes

    def to_proto(self) -> script_value_pb2.ScriptValue:
        value = script_value_pb2.ScriptValue()
        value.ParseFromString(self._data)
        return value

    @property
    def kind(self) -> str | None:
        return self.to_proto().WhichOneof("value")

    def to_python(self, _budget: list[int] | None = None) -> Any:
        if len(self._data) > 1_000_000:
            raise ValueError("durable batch promotion exceeds 1000000 estimated bytes")
        budget = _budget if _budget is not None else [10_000, 1_000_000]
        return _convert_script_value(self.to_proto(), budget)


def _final_value(group: batch_pb2.BatchGroup) -> script_value_pb2.ScriptValue | None:
    if not group.HasField("result"):
        return None
    selected = None
    for emission in group.result.emissions:
        if emission.name == "__final__":
            selected = emission.value
    return selected


def _convert_script_value(
    value: script_value_pb2.ScriptValue, budget: list[int], depth: int = 0
) -> Any:
    if depth >= 64:
        raise ValueError("durable batch promotion exceeds 64 value levels")
    budget[0] -= 1
    if budget[0] < 0:
        raise ValueError("durable batch promotion exceeds 10000 values")
    kind = value.WhichOneof("value")
    if kind is None:
        return None
    if kind == "scalar":
        scalar_kind = value.scalar.WhichOneof("value")
        if scalar_kind is None:
            return None
        result = getattr(value.scalar, scalar_kind)
        if scalar_kind == "text":
            budget[1] -= len(result.encode("utf-8"))
        else:
            budget[1] -= 16
        _check_promotion_bytes(budget)
        return result
    if kind == "list":
        return [
            _convert_script_value(item, budget, depth + 1) for item in value.list.values
        ]
    if kind == "object":
        result = {}
        for key, item in value.object.fields.items():
            budget[1] -= len(key.encode("utf-8"))
            _check_promotion_bytes(budget)
            result[key] = _convert_script_value(item, budget, depth + 1)
        return result
    if kind == "matches":
        from clang_toolkit.cli.runtime.values import MatchSet

        rows = []
        for row in value.matches.rows:
            budget[0] -= 1
            if budget[0] < 0:
                raise ValueError("durable batch promotion exceeds 10000 values")
            budget[1] -= len(row.SerializeToString())
            _check_promotion_bytes(budget)
            rows.append(DetachedMatchRow(row.SerializeToString()))
        return MatchSet(tuple(rows))
    serialized = getattr(value, kind).SerializeToString()
    budget[1] -= len(serialized)
    _check_promotion_bytes(budget)
    from clang_toolkit.cli.runtime.semantic import view

    return view(getattr(value, kind))


def _check_promotion_bytes(budget: list[int]) -> None:
    if budget[1] < 0:
        raise ValueError("durable batch promotion exceeds 1000000 estimated bytes")
