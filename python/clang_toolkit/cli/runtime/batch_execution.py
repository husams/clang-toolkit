"""Foreground, bounded resource-scope batches for the console runtime."""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from lark import Token, Tree

from clang_toolkit.resources import FileBatch, FileSet, partition_inputs

from .evaluator import EvaluationError
from .resource_errors import is_known_scope_admission_rejection

_MEMORY_UNITS = {"b": 1, "kib": 1024, "mib": 1024**2, "gib": 1024**3}
_MAX_REPORT_CHARS = 4_000
_MAX_GROUP_OUTPUT_CHARS = 1_000_000


class BatchInterrupted(Exception):
    """The foreground runner stopped after an external interrupt request."""


def execute_batch(runtime: Any, node: Tree, source: str) -> str:
    """Run each manifest group serially and release its server scope."""
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
    }
    seen_options: set[str] = set()
    for child in node.children:
        if not isinstance(child, Tree) or child.data not in {
            "batch_jobs",
            "batch_memory",
            "batch_error_mode",
        }:
            continue
        option_name = {
            "batch_jobs": "jobs",
            "batch_memory": "memory",
            "batch_error_mode": "on error",
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
        else:
            settings["on_error"] = str(child.children[-1])
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
    }
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
            _emit(runtime, _short_json(report))
            raise BatchInterrupted("batch interrupted before the next group")
        _emit(
            runtime,
            f"batch {run_id} group {batch.index} started: {batch.length} inputs",
        )
        try:
            _run_group(runtime, node, body, source, name, batch, report, settings, jobs)
            report["completed_groups"] += 1
            _record_file_outcomes(report, runtime)
            processed_groups += 1
            processed_inputs += batch.length
            _emit(runtime, f"batch {run_id} group {batch.index} completed")
        except KeyboardInterrupt:
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
            )
            raise
        except BatchInterrupted:
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
            )
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
                )
                raise BatchInterrupted(
                    "batch interrupted during scoped work"
                ) from error
            report["failed_groups"] += 1
            _record_file_outcomes(report, runtime)
            processed_groups += 1
            processed_inputs += batch.length
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
    result = _short_json(report)
    if report["failed_groups"]:
        raise EvaluationError(f"batch failed: {result}")
    return runtime.output.emit(result)


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
) -> None:
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
    try:
        for child in body.children:
            if not isinstance(child, Tree) or str(child.data) in {
                "batch_separator",
                "statement_block",
            }:
                continue
            if runtime._batch_cancel_requested.is_set():
                raise BatchInterrupted("batch cancellation requested")
            statement_source = source[child.meta.start_pos : child.meta.end_pos]
            output = runtime._execute_statement(child, statement_source)
            if output:
                print(output, flush=True)
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


def _positive_integer(token: Token, label: str) -> int:
    raw = str(token)
    if not raw.isdecimal() or int(raw) <= 0:
        raise EvaluationError(f"{label} must be a positive integer")
    return int(raw)


def _validate_body(body: Tree) -> None:
    """Reject constructs whose yielded value cannot stay within a group."""
    for child in body.iter_subtrees_topdown():
        if child.data == "analysis_block":
            raise EvaluationError(
                "yielding analysis blocks are not supported inside batch bodies"
            )


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
    import json

    rendered = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if len(rendered) <= _MAX_REPORT_CHARS:
        return rendered
    # The report is scalar-only except for a fixed-size sample; never cut JSON.
    compact = {
        key: item
        for key, item in value.items()
        if key not in {"cleanup_unknown_groups_sample"}
    }
    compact["cleanup_unknown_groups_sample"] = []
    compact["report_truncated"] = True
    return json.dumps(
        compact, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


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
) -> None:
    report["cancelled_groups"] += 1
    _record_file_outcomes(report, runtime, cancel_in_flight=cancel_in_flight)
    _record_skipped(
        report,
        total,
        size,
        count,
        processed_groups=processed_groups,
        processed_inputs=processed_inputs,
    )
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
