"""Formal CLI evaluation for native AST call graphs."""

from __future__ import annotations
import ast
from pathlib import Path
from typing import Any, TYPE_CHECKING

import grpc
from lark import Tree

from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1.call_graph_stream_pb2 import (
    CallGraphStreamEvent,
)
from clang_toolkit._generated.analysis.v1.call_graph_response_pb2 import (
    CallGraphResponse,
)
from clang_toolkit.call_graph_values import CallGraph, is_unresolved_call_site
from .filesystem import File
from .graph_options import graph_option
from clang_toolkit.match_values import BindingSelection, ParsedTree
from clang_toolkit.resources import FileHandle, InputDescriptor

if TYPE_CHECKING:
    from .evaluator import Runtime


def execute_call_graph(runtime: Runtime, statement: Tree) -> CallGraph | str:
    from .evaluator import EvaluationError

    target_index = 2 if statement.data == "callgraph_binding" else 1
    selected = runtime._evaluate(statement.children[target_index])
    if isinstance(selected, File):
        selected = selected.path
    allowed = (str, Path, BindingSelection, ParsedTree, FileHandle, InputDescriptor)
    if not isinstance(selected, allowed):
        raise EvaluationError(
            "callgraph requires a file path or retained native target"
        )
    options: dict[str, int | bool | str] = {}
    output_format = "compact"
    for option in statement.children[target_index + 1 :]:
        if option.data == "graph_json":
            if output_format == "json":
                raise EvaluationError("duplicate callgraph output format")
            output_format = "json"
            continue
        if graph_option(option, options):
            continue
        if option.data == "call_graph_node_filter":
            if "node_filter" in options:
                raise EvaluationError("duplicate callgraph option node_filter")
            text = ast.literal_eval(str(option.children[1]))
            if not text.strip():
                raise EvaluationError("node_filter must be non-empty matcher text")
            options["node_filter"] = text
            continue
        key, maximum = {
            "call_graph_nodes": ("max_nodes", (1 << 64) - 1),
            "call_graph_edges": ("max_edges", 1000000),
            "call_graph_depth": ("max_depth", 32),
            "call_graph_sites": ("max_call_sites", 1000000),
            "call_graph_direction": ("direction", None),
            "call_graph_implicit": ("visit_implicit_code", None),
            "call_graph_instantiations": ("visit_template_instantiations", None),
            "call_graph_exclude_system": ("exclude_system_headers", None),
        }[str(option.data)]
        if key in options:
            raise EvaluationError(f"duplicate callgraph option {key}")
        text = str(option.children[1])
        if maximum is None:
            if key == "direction":
                if text not in {"in", "out", "both"}:
                    raise EvaluationError("direction must be in, out or both")
                options[key] = text
            else:
                options[key] = text == "true"
        else:
            minimum = 0 if key in {"max_depth", "max_nodes"} else 1
            if key in {"max_depth", "max_nodes"} and text == "all":
                options[key] = "all"
            else:
                if not text.isdigit() or not minimum <= int(text) <= maximum:
                    suffix = " or all" if key in {"max_depth", "max_nodes"} else ""
                    raise EvaluationError(f"{key} must be {minimum}..{maximum}{suffix}")
                options[key] = int(text)
    call_options = {
        "working_directory": runtime.cwd,
        "compile_arguments": runtime.config_store.effective["extra_args"],
        **(
            {"scope": runtime._active_resource_scope}
            if runtime._active_resource_scope is not None
            else {}
        ),
        **options,
    }
    standalone = runtime._value_context_depth == 0
    if standalone and output_format == "compact":
        summary: dict[str, int | bool] = {
            "root": (1 << 64) - 1,
            "focus": (1 << 64) - 1,
            "functions": 0,
            "edges": 0,
            "call_sites": 0,
            "unresolved": 0,
            "external_edges_omitted": 0,
            "is_complete": False,
        }
        # Keep only display strings from node records. Recursive payloads can
        # be large, so retaining node protobufs would defeat stream mode.
        nodes: dict[int, tuple[str, str, str]] = {}
        calls_by_caller: dict[int, int] = {}

        def compact_node(node: Any) -> tuple[str, str, str]:
            name = (
                node.function.qualified_name
                if node.HasField("function")
                else node.declaration_kind
            )
            signature = (
                node.function.type.spelling
                if (node.HasField("function") and node.function.HasField("type"))
                else ""
            )
            location = node.location
            where = (
                f"{location.file}:{location.line}:{location.column}"
                if location.valid
                else "?"
            )
            return name, signature, where

        received_events = False

        def observe(event: CallGraphStreamEvent) -> None:
            nonlocal received_events
            received_events = True
            kind = event.WhichOneof("event")
            if kind == "graph_started":
                summary["root"] = event.graph_started.graph.root_node
                summary["external_edges_omitted"] = (
                    event.graph_started.graph.external_edges_omitted
                )
                if event.graph_started.graph.HasField("focus_node"):
                    summary["focus"] = event.graph_started.graph.focus_node
            elif kind == "node":
                node = event.node.node
                if not node.is_virtual_root and node.node_index != summary["root"]:
                    summary["functions"] += 1
                    nodes[node.node_index] = compact_node(node)
            elif kind == "edge" and not event.edge.edge.is_virtual_root_edge:
                summary["edges"] += 1
            elif kind == "call_site":
                site = event.call_site.call_site
                summary["call_sites"] += 1
                calls_by_caller[site.caller_node] = (
                    calls_by_caller.get(site.caller_node, 0) + 1
                )
                if is_unresolved_call_site(site):
                    summary["unresolved"] += 1
            elif kind == "completed":
                summary["is_complete"] = event.completed.is_complete

        try:
            runtime._scoped_file_call(
                selected,
                lambda: runtime.client.stream_callgraph(
                    selected, on_event=observe, **call_options
                ),
            )
        except AnalysisError as error:
            # Older servers may not implement streaming. Preserve the previous
            # path-target console behavior without reparsing retained values.
            if error.code != grpc.StatusCode.UNIMPLEMENTED or received_events:
                raise
            if not isinstance(selected, str | Path | InputDescriptor):
                raise
            response = runtime._scoped_file_call(
                selected,
                lambda: runtime.client.callgraph(selected, **call_options),
            )
            summary["functions"] = sum(
                not node.is_virtual_root and node.node_index != response.root_node
                for node in response.nodes
            )
            summary["edges"] = sum(
                not edge.is_virtual_root_edge for edge in response.edges
            )
            summary["call_sites"] = len(response.call_sites)
            summary["unresolved"] = sum(
                is_unresolved_call_site(site) for site in response.call_sites
            )
            summary["is_complete"] = response.is_complete
            summary["external_edges_omitted"] = response.external_edges_omitted
            nodes = {
                node.node_index: compact_node(node)
                for node in response.nodes
                if not node.is_virtual_root and node.node_index != response.root_node
            }
            calls_by_caller = {}
            for site in response.call_sites:
                calls_by_caller[site.caller_node] = (
                    calls_by_caller.get(site.caller_node, 0) + 1
                )
            summary["focus"] = (
                response.focus_node
                if response.HasField("focus_node")
                else (1 << 64) - 1
            )
        if runtime._active_resource_scope is not None:
            from clang_toolkit.resources import require_complete

            coverage = CallGraphResponse(
                is_complete=bool(summary["is_complete"]),
                external_edges_omitted=int(summary["external_edges_omitted"]),
            )
            require_complete(coverage)
        status = "complete" if summary["is_complete"] else "partial"
        lines = [
            f"Call graph: {summary['functions']} functions, {summary['edges']} calls, "
            f"{summary['call_sites']} call sites, {summary['unresolved']} unresolved; {status}"
        ]
        for index, (name, signature, where) in sorted(nodes.items()):
            seed = " [seed]" if index == summary["focus"] else ""
            signature_text = f" {signature}" if signature else ""
            lines.append(
                f"  {name}{signature_text} @ {where}: "
                f"{calls_by_caller.get(index, 0)} call sites{seed}"
            )
        return "\n".join(lines)

    response = runtime._scoped_file_call(
        selected,
        lambda: runtime.client.callgraph(selected, **call_options),
    )
    if runtime._active_resource_scope is not None:
        from clang_toolkit.resources import require_complete

        require_complete(response)
    value = CallGraph(response, selector=runtime.client.callgraph)
    if standalone and output_format == "json":
        from .graph_options import render_graph

        return render_graph(value)
    return value
