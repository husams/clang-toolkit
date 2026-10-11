"""Console commands for server-owned durable batch runs."""

from __future__ import annotations

from typing import Any

from lark import Tree

from clang_toolkit.batches import BatchRun
from clang_toolkit.resources import FileSet

from .batch_execution import _parse_memory, _positive_integer
from .evaluator import EvaluationError


def execute_durable_batch_command(runtime: Any, node: Tree, source: str) -> Any:
    kind = str(node.data)
    if kind == "durable_batch":
        # durable/background token, batch, group name, in, manifest, grouping, options, body
        name = str(node.children[2])
        manifest = runtime._evaluate(node.children[4])
        if not isinstance(manifest, FileSet):
            raise EvaluationError(
                "durable batch input must be a FileSet created with files"
            )
        grouping = next(
            child
            for child in node.children
            if isinstance(child, Tree) and child.data in {"batch_size", "batch_count"}
        )
        mode = str(grouping.data)
        amount = _positive_integer(grouping.children[1], mode.removeprefix("batch_"))
        settings: dict[str, Any] = {
            "size": amount if mode == "batch_size" else None,
            "count": amount if mode == "batch_count" else None,
            "jobs": None,
            "memory_bytes": None,
            "continue_on_error": False,
            "request_id": None,
        }
        seen: set[str] = set()
        for child in node.children:
            if not isinstance(child, Tree):
                continue
            if child.data not in {
                "batch_jobs",
                "batch_memory",
                "batch_error_mode",
                "batch_request_id",
            }:
                continue
            option = str(child.data)
            if option in seen:
                raise EvaluationError(
                    f"durable batch option repeated: {option.removeprefix('batch_')}"
                )
            seen.add(option)
            if option == "batch_jobs":
                settings["jobs"] = _positive_integer(child.children[1], "jobs")
            elif option == "batch_memory":
                settings["memory_bytes"] = _parse_memory(
                    runtime._string(str(child.children[1]))
                )
            elif option == "batch_request_id":
                request_id = runtime._string(str(child.children[1]))
                if not request_id:
                    raise EvaluationError("request id cannot be empty")
                settings["request_id"] = request_id
            else:
                settings["continue_on_error"] = str(child.children[-1]) == "continue"
        body = next(
            child
            for child in node.children
            if isinstance(child, Tree) and child.data == "statement_block"
        )
        body_source = source[body.meta.start_pos + 1 : body.meta.end_pos - 1]
        start = getattr(runtime.client, "start_batch", None)
        if start is None:
            raise EvaluationError("durable batches are unavailable")
        return start(manifest, body_source, group_variable=name, **settings)

    value = runtime._evaluate(node.children[2])
    if kind == "batch_promote":
        if isinstance(value, str):
            value = runtime.client.batch_status(value)
        if not isinstance(value, BatchRun):
            raise EvaluationError("batch promote requires a BatchRun or run id")
        return value.promote()
    if kind == "batch_status":
        return runtime.client.batch_status(
            value.run_id if isinstance(value, BatchRun) else value
        )
    if not isinstance(value, BatchRun | str):
        raise EvaluationError(
            f"{kind.removeprefix('batch_')} requires a BatchRun or run id"
        )
    method = {
        "batch_cancel": "cancel_batch",
        "batch_resume": "resume_batch",
        "batch_retry": "retry_batch",
    }[kind]
    if isinstance(value, str):
        value = runtime.client.batch_status(value)
    return getattr(runtime.client, method)(value)


def render_durable_batch(value: Any) -> str:
    if isinstance(value, BatchRun):
        completed = sum(group.state == "completed" for group in value.groups)
        failed = sum(
            group.state in {"failed", "cancelled", "unknown"} for group in value.groups
        )
        return (
            f"batch {value.run_id}: {value.status}, revision {value.revision}, "
            f"{completed}/{len(value.groups)} groups complete, {failed} failed"
        )
    if isinstance(value, tuple):
        return f"promoted {len(value)} detached batch group result(s)"
    return str(value)
