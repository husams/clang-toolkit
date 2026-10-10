"""Foreground, bounded resource-scope batches for the console runtime."""

from __future__ import annotations

import json
import re
import base64
import dataclasses
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import uuid4

from lark import Token, Tree

from clang_toolkit.resources import FileBatch, FileSet, partition_inputs

from .evaluator import EvaluationError
from .resource_errors import is_known_scope_admission_rejection
from .values import MatchSet

_MEMORY_UNITS = {"b": 1, "kib": 1024, "mib": 1024**2, "gib": 1024**3}
_MAX_REPORT_CHARS = 4_000
_MAX_GROUP_OUTPUT_CHARS = 1_000_000
_MAX_RESULT_ITEMS = 10_000
_MAX_RESULT_BYTES = 1_000_000
_MAX_RESULT_DEPTH = 64
_MAX_GROUP_ERROR_SAMPLES = 4
_MAX_GROUP_ERROR_CHARS = 300


class BatchInterrupted(Exception):
    """The foreground runner stopped after an external interrupt request."""


class BatchResultLimitError(EvaluationError):
    """The detached batch result exceeded its retained value budget."""


def execute_batch(
    runtime: Any,
    node: Tree,
    source: str,
    *,
    value_context: bool = False,
) -> dict[str, Any]:
    """Run manifest groups and return a bounded report with detached results."""
    name = str(node.children[1])
    manifest = runtime._evaluate(node.children[3])
    if not isinstance(manifest, FileSet):
        raise EvaluationError("batch input must be a FileSet created with files")
    grouping = next(
        child
        for child in node.children
        if isinstance(child, Tree) and child.data in {"batch_size", "batch_count"}
    )
    mode = str(grouping.data)
    amount = _positive_integer(grouping.children[1], mode.removeprefix("batch_"))
    # Keep the implicit value aligned with direct multi-file matching, including
    # the client's normal config-file and environment resolution.
    settings = {
        "jobs": runtime._match_setting("pool_size", 4),
        "memory_bytes": None,
        "on_error": "stop",
        "progress": True,
    }
    seen_options: set[str] = set()
    for child in node.children:
        if not isinstance(child, Tree) or child.data not in {
            "batch_jobs",
            "batch_memory",
            "batch_error_mode",
            "batch_progress",
        }:
            continue
        option_name = {
            "batch_jobs": "jobs",
            "batch_memory": "memory",
            "batch_error_mode": "on error",
            "batch_progress": "progress",
        }[str(child.data)]
        if option_name in seen_options:
            raise EvaluationError(f"batch option repeated: {option_name}")
        seen_options.add(option_name)
        if child.data == "batch_jobs":
            settings["jobs"] = _positive_integer(child.children[1], "jobs")
        elif child.data == "batch_memory":
            settings["memory_bytes"] = _parse_memory(
                runtime._string(str(child.children[1]))
            )
        elif child.data == "batch_error_mode":
            settings["on_error"] = str(child.children[-1])
        else:
            progress = str(child.children[-1]).lower()
            if progress not in {"on", "off"}:
                raise EvaluationError("progress must be on or off")
            settings["progress"] = progress == "on"
    jobs = int(settings["jobs"])
    size = amount if mode == "batch_size" else None
    count = amount if mode == "batch_count" else None
    if count is not None and manifest and count > len(manifest):
        raise EvaluationError("count cannot exceed the nonempty input count")
    if not manifest and count is not None:
        batches = iter(())
    else:
        try:
            batches = partition_inputs(manifest, size=size, count=count)
        except ValueError as error:
            raise EvaluationError(str(error)) from error

    body = next(
        child
        for child in node.children
        if isinstance(child, Tree) and child.data == "statement_block"
    )
    _validate_body(body)
    run_id = uuid4().hex[:12]
    report: dict[str, Any] = {
        "run_id": run_id,
        "discovered_inputs": len(manifest),
        "completed_groups": 0,
        "failed_groups": 0,
        "skipped_groups": 0,
        "cancelled_groups": 0,
        "accepted_inputs": 0,
        "completed_files": 0,
        "failed_files": 0,
        "skipped_files": 0,
        "cancelled_files": 0,
        "unknown_files": 0,
        "unattempted_files": 0,
        "exported_outputs": 0,
        "output_chars": 0,
        "peak_group_output_chars": 0,
        "peak_accounted_bytes": 0,
        "peak_reserved_bytes": 0,
        "remaining_external_pins": None,
        "cleanup_acknowledged": True,
        "cleanup_unknown_groups_total": 0,
        "cleanup_unknown_groups_sample": [],
        "group_errors_total": 0,
        "group_errors_sample": [],
        "status": "completed",
        "results": [],
        "result_group_indices": [],
        "results_count": 0,
        "results_bytes": 0,
        "result_items": 0,
        "results_complete": True,
    }
    progress_enabled = bool(settings["progress"]) and not value_context
    if progress_enabled:
        _emit(runtime, f"batch {run_id} started: {len(manifest)} inputs, jobs {jobs}")
    processed_groups = 0
    processed_inputs = 0
    for batch in batches:
        if runtime._batch_cancel_requested.is_set():
            _record_skipped(
                report,
                len(manifest),
                size,
                count,
                processed_groups=processed_groups,
                processed_inputs=processed_inputs,
            )
            report["status"] = "cancelled"
            report["results_complete"] = False
            if progress_enabled:
                _emit(runtime, _short_json(report))
            interruption = BatchInterrupted("batch interrupted before the next group")
            interruption.report = report
            raise interruption
        if progress_enabled:
            _emit(
                runtime,
                f"batch {run_id} group {batch.index} started: {batch.length} inputs",
            )
        try:
            result_budget = [report["result_items"], report["results_bytes"]]
            detached_result = _run_group(
                runtime,
                node,
                body,
                source,
                name,
                batch,
                report,
                settings,
                jobs,
                value_context=value_context,
                result_budget=result_budget,
            )
            report["completed_groups"] += 1
            _record_file_outcomes(report, runtime)
            report["results"].append(detached_result)
            report["result_group_indices"].append(batch.index)
            report["results_count"] += 1
            report["results_bytes"] = result_budget[1]
            report["result_items"] = result_budget[0]
            processed_groups += 1
            processed_inputs += batch.length
            if progress_enabled:
                _emit(runtime, f"batch {run_id} group {batch.index} completed")
        except KeyboardInterrupt as error:
            processed_groups += 1
            processed_inputs += batch.length
            _record_interrupted_group(
                runtime,
                report,
                batch,
                len(manifest),
                size,
                count,
                run_id,
                processed_groups=processed_groups,
                processed_inputs=processed_inputs,
                cancel_in_flight=True,
                progress_enabled=progress_enabled,
            )
            report["status"] = "cancelled"
            report["results_complete"] = False
            error.report = report
            raise
        except BatchInterrupted as error:
            processed_groups += 1
            processed_inputs += batch.length
            _record_interrupted_group(
                runtime,
                report,
                batch,
                len(manifest),
                size,
                count,
                run_id,
                processed_groups=processed_groups,
                processed_inputs=processed_inputs,
                progress_enabled=progress_enabled,
            )
            report["status"] = "cancelled"
            report["results_complete"] = False
            error.report = report
            raise
        except Exception as error:
            if runtime._batch_cancel_requested.is_set():
                processed_groups += 1
                processed_inputs += batch.length
                _record_interrupted_group(
                    runtime,
                    report,
                    batch,
                    len(manifest),
                    size,
                    count,
                    run_id,
                    processed_groups=processed_groups,
                    processed_inputs=processed_inputs,
                    cancel_in_flight=True,
                    progress_enabled=progress_enabled,
                )
                interruption = BatchInterrupted("batch interrupted during scoped work")
                report["status"] = "cancelled"
                report["results_complete"] = False
                interruption.report = report
                raise interruption from error
            report["failed_groups"] += 1
            report["results_complete"] = False
            _record_group_error(report, batch.index, error)
            _record_file_outcomes(report, runtime)
            processed_groups += 1
            processed_inputs += batch.length
            if progress_enabled:
                _emit(
                    runtime,
                    f"batch {run_id} group {batch.index} failed: {_short(str(error), 500)}",
                )
            # A later group may start only after the previous server scope is
            # acknowledged as released, even when the caller requested continue.
            if settings["on_error"] == "stop" or not report["cleanup_acknowledged"]:
                _record_skipped(
                    report,
                    len(manifest),
                    size,
                    count,
                    processed_groups=processed_groups,
                    processed_inputs=processed_inputs,
                )
                break
    report["status"] = (
        "failed"
        if report["failed_groups"] or not report["cleanup_acknowledged"]
        else "completed"
    )
    if report["failed_groups"] or report["skipped_groups"]:
        report["results_complete"] = False
    return report


def _run_group(
    runtime: Any,
    batch_node: Tree,
    body: Tree,
    source: str,
    name: str,
    batch: FileBatch,
    report: dict[str, Any],
    settings: dict[str, Any],
    jobs: int,
    *,
    value_context: bool,
    result_budget: list[int],
) -> Any:
    runtime._last_batch_admitted = False
    runtime._last_batch_file_outcomes = {}
    runtime._last_batch_unknown_file_count = 0
    runtime._last_batch_unattempted_file_count = batch.length
    open_scope = getattr(runtime.client, "open_resource_scope", None)
    if open_scope is None:
        raise EvaluationError(
            "batch resource scopes are unavailable; update the server"
        )
    # Server admission is atomic: no file work begins until this succeeds.
    try:
        scope = open_scope(
            inputs=batch.inputs,
            memory_bytes=settings["memory_bytes"],
            jobs=jobs,
            transient=True,
        )
    except BaseException as error:
        # A lost admission reply cannot distinguish a rejected request from a
        # committed scope whose ID was lost. Stop later groups until server TTL
        # cleanup; never retry this group's body.
        if not is_known_scope_admission_rejection(error):
            report["cleanup_acknowledged"] = False
            _record_cleanup_unknown(report, batch.index)
        raise
    report["accepted_inputs"] += batch.length
    runtime._last_batch_admitted = True
    local_scope = {name: batch}
    previous_resource_scope = getattr(runtime, "_active_resource_scope", None)
    previous_batch_inputs = getattr(runtime, "_active_batch_inputs", None)
    previous_batch_jobs = getattr(runtime, "_batch_jobs", None)
    previous_file_outcomes = runtime._batch_file_outcomes
    previous_unknown_outcomes = runtime._batch_unknown_file_outcomes
    runtime._active_resource_scope = scope
    runtime._active_batch_inputs = batch.inputs
    runtime._batch_jobs = jobs
    runtime._batch_file_outcomes = {}
    runtime._batch_unknown_file_outcomes = set()
    runtime.output.begin_limited_output(_MAX_GROUP_OUTPUT_CHARS)
    before_exports = runtime._successful_exports
    runtime._scopes.append(local_scope)
    runtime._block_owners.append(set())
    last_value: Any = None
    try:
        for child in body.children:
            if not isinstance(child, Tree) or str(child.data) in {
                "batch_separator",
                "statement_block",
            }:
                continue
            if runtime._batch_cancel_requested.is_set():
                raise BatchInterrupted("batch cancellation requested")
            value, output = runtime._evaluate_statement_once(
                child,
                source,
                value_context=value_context,
            )
            last_value = value
            if output and not value_context:
                print(output, flush=True)
        _charge_result_container(result_budget, 2)
        _charge_result(batch.index, result_budget)
        detached_result = _detach_batch_result(last_value, result_budget)
        if runtime._batch_cancel_requested.is_set():
            raise BatchInterrupted("batch cancellation requested")
    except BaseException:
        try:
            scope.cancel()
        finally:
            raise
    finally:
        output_chars = runtime.output.end_limited_output()
        report["exported_outputs"] += runtime._successful_exports - before_exports
        report["output_chars"] += output_chars
        report["peak_group_output_chars"] = max(
            report["peak_group_output_chars"], output_chars
        )
        runtime._block_owners.pop()
        runtime._scopes.pop()
        local_scope.clear()
        runtime._active_resource_scope = previous_resource_scope
        runtime._active_batch_inputs = previous_batch_inputs
        runtime._batch_jobs = previous_batch_jobs
        runtime._last_batch_file_outcomes = dict(runtime._batch_file_outcomes)
        runtime._last_batch_unknown_file_count = len(
            runtime._batch_unknown_file_outcomes
        )
        runtime._last_batch_unattempted_file_count = max(
            0, batch.length - len(runtime._last_batch_file_outcomes)
        )
        runtime._batch_file_outcomes = previous_file_outcomes
        runtime._batch_unknown_file_outcomes = previous_unknown_outcomes
        info = None
        try:
            info = scope.release()
        except BaseException:
            try:
                info = scope.describe()
            except BaseException:
                report["cleanup_acknowledged"] = False
                _record_cleanup_unknown(report, batch.index)
                info = None
        if info is not None and not getattr(info, "cleanup_acknowledged", False):
            try:
                info = scope.describe()
            except BaseException:
                report["cleanup_acknowledged"] = False
                _record_cleanup_unknown(report, batch.index)
                info = None
            if info is not None and not getattr(info, "cleanup_acknowledged", False):
                report["cleanup_acknowledged"] = False
                _record_cleanup_unknown(report, batch.index)
        if info is not None:
            report["peak_accounted_bytes"] = max(
                report["peak_accounted_bytes"],
                int(getattr(info, "peak_accounted_bytes", 0)),
            )
            report["peak_reserved_bytes"] = max(
                report["peak_reserved_bytes"],
                int(getattr(info, "peak_reserved_bytes", 0)),
            )
        try:
            status = runtime.client.resource_status()
            report["remaining_external_pins"] = _external_pins(status)
        except Exception:
            report["remaining_external_pins"] = None
        if not getattr(info, "cleanup_acknowledged", False):
            raise EvaluationError(
                f"resource cleanup is unconfirmed for group {batch.index}"
            )
    return detached_result


def _positive_integer(token: Token, label: str) -> int:
    raw = str(token)
    if not raw.isdecimal() or int(raw) <= 0:
        raise EvaluationError(f"{label} must be a positive integer")
    return int(raw)


def _validate_body(body: Tree) -> None:
    """Reject constructs whose yielded value cannot stay within a group."""
    unscoped_native_work = {
        "cursor_open",
        "cursor_continue",
        "cursor_restart",
        "background",
        "session_start",
        "session_add",
        "session_match",
        "session_resume",
    }
    for child in body.iter_subtrees_topdown():
        if child.data in {"analysis_block", "batch_statement"}:
            raise EvaluationError(
                "yielding analysis blocks and nested batches are not supported inside batch bodies"
            )
        if child.data in unscoped_native_work:
            raise EvaluationError(
                "legacy cursor, background, and query-session work is not scoped for batches; "
                "use match or parse operations inside the batch instead"
            )


def _detach_batch_result(
    value: Any, budget: list[int], seen: set[int] | None = None
) -> Any:
    """Copy a result out of its scope while enforcing aggregate item/byte caps."""
    from clang_toolkit.match_values import (
        BindingSelection,
        MatchRow,
        MatchValue,
        NativeBindingCollection,
        NativeMatchCollection,
        ParsedTree,
    )
    from clang_toolkit.resources import FileHandle, InputDescriptor

    from .matcher_functions import MatcherFunction
    from .filesystem import FileSystemEntry
    from .semantic import (
        BindingMapView,
        EnumValue,
        MapView,
        MessageView,
        RepeatedView,
        _availability_of,
        view,
    )
    from .values import MatcherExpr, QualifiedName

    if seen is None:
        seen = set()
    if value is None or isinstance(value, bool | int | float | str):
        return _charge_result(value, budget)
    if isinstance(value, bytes):
        # Keep a JSON-safe detached representation without retaining a native object.
        encoded_size = 4 * ((len(value) + 2) // 3)
        # Check against the remaining aggregate budget before making the encoded
        # copy. Include a conservative allowance for the DTO's keys and framing.
        if encoded_size + 64 + budget[1] > _MAX_RESULT_BYTES:
            raise BatchResultLimitError(
                f"batch result exceeds {_MAX_RESULT_BYTES} retained bytes"
            )
        encoded = base64.b64encode(value).decode("ascii")
        return _charge_result({"type": "bytes", "base64": encoded}, budget)
    if isinstance(value, (FileHandle, ParsedTree, MatcherFunction)) or callable(value):
        raise EvaluationError(
            f"batch results cannot retain live resource or callable values ({type(value).__name__})"
        )
    if isinstance(value, (MessageView, RepeatedView, MapView)):
        metadata_bytes = len(value._path.encode("utf-8")) + sum(
            len(str(item).encode("utf-8")) for item in value._availability
        )
        return _charge_result(
            value, budget, byte_size=len(value._data) + metadata_bytes + 96
        )
    if isinstance(value, EnumValue):
        return _detach_batch_result(
            {"name": value.name, "number": value.number}, budget, seen
        )
    if isinstance(value, BindingSelection):
        if value._binding_data is not None:
            _charge_result_container(budget, len(value._binding_data) + 96)
            message = value.value
            return MessageView(
                value._binding_data,
                type(message),
                _availability_of(message),
                message.DESCRIPTOR.full_name,
            )
        return _detach_batch_result(view(value.value), budget, seen)
    if isinstance(value, MatchRow):
        # Charge the native row snapshot before parsing/serializing another copy.
        _charge_result_container(budget, len(value._data) + 96)
        message = value._message()
        return MessageView(
            value._data,
            type(message),
            _availability_of(message),
            message.DESCRIPTOR.full_name,
        )
    if isinstance(value, MatchValue | NativeMatchCollection):
        identity = id(value)
        _check_new_container(identity, seen)
        try:
            _charge_result_container(budget, 2)
            rows = []
            iterator = (
                value.iter_rows() if isinstance(value, MatchValue) else iter(value)
            )
            for row in iterator:
                rows.append(_detach_batch_result(row, budget, seen))
            return MatchSet(tuple(rows))
        finally:
            seen.remove(identity)
    if isinstance(value, NativeBindingCollection):
        identity = id(value)
        _check_new_container(identity, seen)
        try:
            _charge_result_container(budget, 2)
            selections = []
            for selection in value:
                selections.append(_detach_batch_result(selection, budget, seen))
            return selections
        finally:
            seen.remove(identity)
    if isinstance(value, BindingMapView):
        identity = id(value)
        _check_new_container(identity, seen)
        try:
            _charge_result_container(budget, len(value._row._data) + 96)
            fields = {
                name: view(binding) for name, binding in value._row.bindings.items()
            }
            return _detach_batch_result(fields, budget, seen)
        finally:
            seen.remove(identity)
    if isinstance(value, MatchSet):
        identity = id(value)
        _check_new_container(identity, seen)
        try:
            _charge_result_container(budget, 2)
            return MatchSet(
                tuple(_detach_batch_result(row, budget, seen) for row in value.rows)
            )
        finally:
            seen.remove(identity)
    if isinstance(value, FileSet):
        identity = id(value)
        _check_new_container(identity, seen)
        try:
            fields = {
                "inputs": list(value.inputs),
                "diagnostics": list(value.diagnostics),
                "metadata_bytes": value.metadata_bytes,
            }
            return _detach_batch_result(fields, budget, seen)
        finally:
            seen.remove(identity)
    if isinstance(value, FileBatch):
        identity = id(value)
        _check_new_container(identity, seen)
        try:
            fields = {
                "index": value.index,
                "length": value.length,
                "inputs": list(value.inputs),
            }
            return _detach_batch_result(fields, budget, seen)
        finally:
            seen.remove(identity)
    if isinstance(value, InputDescriptor):
        fields = {
            field.name: getattr(value, field.name)
            for field in dataclasses.fields(value)
        }
        return _detach_batch_result(fields, budget, seen)
    if isinstance(value, MatcherExpr):
        identity = id(value)
        _check_new_container(identity, seen)
        try:
            _charge_result_container(budget, 2)
            return {
                "name": _detach_batch_result(value.name, budget, seen),
                "arguments": _detach_batch_result(list(value.arguments), budget, seen),
                "binding": _detach_batch_result(value.binding, budget, seen),
            }
        finally:
            seen.remove(identity)
    if isinstance(value, QualifiedName):
        return _detach_batch_result(value.text, budget, seen)
    if isinstance(value, datetime):
        return _detach_batch_result(value.isoformat(), budget, seen)
    if isinstance(value, FileSystemEntry):
        return _detach_batch_result(
            {
                "path": value.path,
                "absolute": value.absolute,
                "size": value.size,
                "modified": value.modified.isoformat(),
            },
            budget,
            seen,
        )
    if isinstance(value, (list, tuple)):
        identity = id(value)
        _check_new_container(identity, seen)
        try:
            _charge_result_container(budget, 2)
            return [_detach_batch_result(item, budget, seen) for item in value]
        finally:
            seen.remove(identity)
    if isinstance(value, Mapping):
        identity = id(value)
        _check_new_container(identity, seen)
        try:
            _charge_result_container(budget, 2)
            result: dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise EvaluationError(
                        "batch result dictionaries require string keys"
                    )
                _charge_result(key, budget)
                _charge_result_container(budget, 1)
                result[key] = _detach_batch_result(item, budget, seen)
            return result
        finally:
            seen.remove(identity)
    raise EvaluationError(
        f"batch result type cannot be detached: {type(value).__name__}"
    )


def _charge_result(
    value: Any, budget: list[int], *, byte_size: int | None = None
) -> Any:
    if byte_size is not None:
        encoded_size = byte_size
    elif isinstance(value, str):
        # Strings may be very large; count their JSON representation incrementally
        # so the budget check does not first allocate another encoded string.
        encoded_size = _json_string_size(value, _MAX_RESULT_BYTES - budget[1] - 32)
    else:
        encoded_size = len(
            json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
    _charge_result_container(budget, encoded_size)
    return value


def _json_string_size(value: str, maximum: int) -> int:
    """Return JSON UTF-8 byte size, stopping once the retained budget is exceeded."""
    size = 2  # surrounding quotes
    if size > maximum:
        raise BatchResultLimitError(
            f"batch result exceeds {_MAX_RESULT_BYTES} retained bytes"
        )
    short_escapes = {"\b", "\f", "\n", "\r", "\t"}
    for character in value:
        if character in {'"', "\\"} or character in short_escapes:
            size += 2
        elif ord(character) < 0x20:
            size += 6
        else:
            size += len(character.encode("utf-8"))
        if size > maximum:
            raise BatchResultLimitError(
                f"batch result exceeds {_MAX_RESULT_BYTES} retained bytes"
            )
    return size


def _charge_result_container(budget: list[int], byte_size: int) -> None:
    budget[0] += 1
    # Leave room for Python object/container overhead alongside serialized data.
    budget[1] += max(byte_size, 32)
    if budget[0] > _MAX_RESULT_ITEMS:
        raise BatchResultLimitError(
            f"batch result exceeds {_MAX_RESULT_ITEMS} retained items"
        )
    if budget[1] > _MAX_RESULT_BYTES:
        raise BatchResultLimitError(
            f"batch result exceeds {_MAX_RESULT_BYTES} retained bytes"
        )


def _check_new_container(identity: int, seen: set[int]) -> None:
    if identity in seen:
        raise EvaluationError("cyclic values cannot be returned from a batch")
    if len(seen) >= _MAX_RESULT_DEPTH:
        raise BatchResultLimitError(
            f"batch result exceeds maximum nesting depth {_MAX_RESULT_DEPTH}"
        )
    seen.add(identity)


def _parse_memory(value: str) -> int:
    match = re.fullmatch(r"\s*([0-9]+)\s*(B|KiB|MiB|GiB)\s*", value, re.IGNORECASE)
    if match is None or int(match.group(1)) <= 0:
        raise EvaluationError('memory must use a positive value such as "768MiB"')
    return int(match.group(1)) * _MEMORY_UNITS[match.group(2).lower()]


def _group_count(total: int, size: int | None, count: int | None) -> int:
    if total == 0:
        return 0
    return (
        count if count is not None else (total + int(size or 1) - 1) // int(size or 1)
    )


def _short(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 16] + "… <truncated>"


def _short_json(value: Any) -> str:
    # The returned dict retains full results; progress keeps the established
    # compact report bound and exposes only result counts/bytes.
    value = {
        key: item
        for key, item in value.items()
        if key not in {"results", "result_group_indices"}
    }
    rendered = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if len(rendered) <= _MAX_REPORT_CHARS:
        return rendered
    # The report is scalar-only except for a fixed-size sample; never cut JSON.
    compact = {
        key: item
        for key, item in value.items()
        if key not in {"cleanup_unknown_groups_sample", "group_errors_sample"}
    }
    compact["cleanup_unknown_groups_sample"] = []
    compact["group_errors_sample"] = []
    compact["report_truncated"] = True
    return json.dumps(
        compact, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _record_group_error(
    report: dict[str, Any], group_index: int, error: BaseException
) -> None:
    report["group_errors_total"] += 1
    samples = report["group_errors_sample"]
    if len(samples) < _MAX_GROUP_ERROR_SAMPLES:
        samples.append(
            {
                "group_index": group_index,
                "message": _short(str(error), _MAX_GROUP_ERROR_CHARS),
            }
        )


def render_batch_report(report: dict[str, Any]) -> str:
    """Render the compact status summary without exposing the full result list."""
    return _short_json(report)


def _record_cleanup_unknown(report: dict[str, Any], group_index: int) -> None:
    report["cleanup_unknown_groups_total"] += 1
    sample = report["cleanup_unknown_groups_sample"]
    if len(sample) < 8:
        sample.append(group_index)


def _record_file_outcomes(
    report: dict[str, Any], runtime: Any, *, cancel_in_flight: bool = False
) -> None:
    outcomes = runtime._last_batch_file_outcomes.values()
    for outcome in outcomes:
        if outcome == "attempting" and cancel_in_flight:
            report["cancelled_files"] += 1
        elif outcome == "attempting":
            report["unknown_files"] += 1
        elif outcome == "completed":
            report["completed_files"] += 1
        elif outcome == "failed":
            report["failed_files"] += 1
        elif outcome == "unknown":
            report["unknown_files"] += 1
        elif outcome == "cancelled":
            report["cancelled_files"] += 1
    report["unknown_files"] += runtime._last_batch_unknown_file_count
    report["unattempted_files"] += runtime._last_batch_unattempted_file_count


def _record_interrupted_group(
    runtime: Any,
    report: dict[str, Any],
    batch: FileBatch,
    total: int,
    size: int | None,
    count: int | None,
    run_id: str,
    *,
    processed_groups: int,
    processed_inputs: int,
    cancel_in_flight: bool = True,
    progress_enabled: bool = True,
) -> None:
    report["cancelled_groups"] += 1
    report["status"] = "cancelled"
    report["results_complete"] = False
    _record_file_outcomes(report, runtime, cancel_in_flight=cancel_in_flight)
    _record_skipped(
        report,
        total,
        size,
        count,
        processed_groups=processed_groups,
        processed_inputs=processed_inputs,
    )
    if progress_enabled:
        _emit(runtime, f"batch {run_id} interrupted in group {batch.index}")
        _emit(runtime, _short_json(report))


def _external_pins(status: Any) -> int | None:
    """Estimate independently pinned leases from typed server inventory."""
    if not hasattr(status, "explicit_file_leases"):
        return None
    explicit = int(status.explicit_file_leases)
    scopes = status.scopes
    scoped = sum(int(getattr(scope, "file_leases", 0)) for scope in scopes)
    return max(0, explicit - scoped)


def _record_skipped(
    report: dict[str, Any],
    total: int,
    size: int | None,
    count: int | None,
    *,
    processed_groups: int,
    processed_inputs: int,
) -> None:
    remaining_groups = max(0, _group_count(total, size, count) - processed_groups)
    report["skipped_groups"] += remaining_groups
    report["skipped_files"] += max(0, total - processed_inputs)


def _emit(runtime: Any, text: str) -> None:
    output = runtime.output.emit(text)
    if output:
        print(output, flush=True)
