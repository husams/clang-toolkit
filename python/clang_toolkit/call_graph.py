"""Typed AST call-graph request construction."""
from __future__ import annotations
from collections.abc import Sequence
from pathlib import Path
from typing import Literal
from clang_toolkit._generated.analysis.v1 import call_graph_request_pb2 as pb
from clang_toolkit.cursors import file_request
from clang_toolkit.analysis_projection import value_projection

def call_graph_request(path: str | Path, *, working_directory: str | Path | None = None,
                       compile_arguments: Sequence[str] = (), visit_implicit_code: bool | None = None,
                       visit_template_instantiations: bool | None = None,
                       max_nodes: int | Literal["all"] | None = None,
                       max_edges: int | None = None, projection: str = "shallow",
                      main_file_only: bool = False,
                      exclude_system_headers: bool = False,
                      node_filter: str | None = None,
                      strict_node_filter: bool = False, payload_depth: int = 24,
                      payload_nodes: int = 10000) -> pb.CallGraphRequest:
    request = pb.CallGraphRequest(file=file_request(path, "unused",
        working_directory=working_directory, compile_arguments=compile_arguments).file)
    for name, value in [("visit_implicit_code", visit_implicit_code),
                        ("visit_template_instantiations", visit_template_instantiations)]:
        if value is not None:
            setattr(request, name, value)
    if max_nodes is not None:
        if max_nodes == "all":
            request.max_nodes = 0
        elif type(max_nodes) is not int or not 0 <= max_nodes < (1 << 64):
            raise ValueError("max_nodes must be a nonnegative uint64 integer or 'all'")
        else:
            request.max_nodes = max_nodes
    for name, value, maximum in [("max_edges", max_edges, 1000000)]:
        if value is not None:
            if not 1 <= value <= maximum:
                raise ValueError(f"{name} must be 1..{maximum}")
            setattr(request, name, value)
    if type(exclude_system_headers) is not bool:
        raise ValueError("exclude_system_headers must be a boolean")
    if node_filter is not None and (
        not isinstance(node_filter, str) or not node_filter.strip()
    ):
        raise ValueError("node_filter must be non-empty matcher text")
    if type(strict_node_filter) is not bool:
        raise ValueError("strict_node_filter must be a boolean")
    if strict_node_filter and node_filter is None:
        raise ValueError("strict_node_filter requires node_filter")
    request.strict_node_filter = strict_node_filter
    request.exclude_system_headers = exclude_system_headers
    if node_filter is not None:
        request.node_filter = node_filter
    request.projection.CopyFrom(value_projection(projection, payload_depth=payload_depth, payload_nodes=payload_nodes))
    request.main_file_only = main_file_only
    return request
