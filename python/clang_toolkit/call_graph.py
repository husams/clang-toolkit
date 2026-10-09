"""Typed AST call-graph request construction."""
from __future__ import annotations
from collections.abc import Sequence
from pathlib import Path
from clang_toolkit._generated.analysis.v1 import call_graph_request_pb2 as pb
from clang_toolkit.cursors import file_request
from clang_toolkit.analysis_projection import value_projection

def call_graph_request(path: str | Path, *, working_directory: str | Path | None = None,
                       compile_arguments: Sequence[str] = (), visit_implicit_code: bool | None = None,
                       visit_template_instantiations: bool | None = None, max_nodes: int | None = None,
                       max_edges: int | None = None, projection: str = "shallow",
                      main_file_only: bool = False, payload_depth: int = 24,
                      payload_nodes: int = 10000) -> pb.CallGraphRequest:
    request = pb.CallGraphRequest(file=file_request(path, "unused",
        working_directory=working_directory, compile_arguments=compile_arguments).file)
    for name, value in [("visit_implicit_code", visit_implicit_code),
                        ("visit_template_instantiations", visit_template_instantiations)]:
        if value is not None:
            setattr(request, name, value)
    for name, value, maximum in [("max_nodes", max_nodes, 100000), ("max_edges", max_edges, 1000000)]:
        if value is not None:
            if not 1 <= value <= maximum:
                raise ValueError(f"{name} must be 1..{maximum}")
            setattr(request, name, value)
    request.projection.CopyFrom(value_projection(projection, payload_depth=payload_depth, payload_nodes=payload_nodes))
    request.main_file_only = main_file_only
    return request
