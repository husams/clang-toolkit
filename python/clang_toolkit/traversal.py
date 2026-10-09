"""Typed requests for the native recursive AST visitor."""
from __future__ import annotations
from collections.abc import Sequence
from pathlib import Path
from clang_toolkit._generated.analysis.v1 import traverse_request_pb2 as pb
from clang_toolkit.cursors import file_request
from clang_toolkit.analysis_projection import value_projection

def traversal_request(path: str | Path, *, working_directory: str | Path | None = None,
                      compile_arguments: Sequence[str] = (), visit_implicit_code: bool = False,
                      visit_template_instantiations: bool = False, max_depth: int | None = None,
                      max_nodes: int | None = None, projection: str = "shallow",
                      main_file_only: bool = False, payload_depth: int = 24,
                      payload_nodes: int = 10000) -> pb.TraverseRequest:
    request = pb.TraverseRequest(
        file=file_request(path, "unused", working_directory=working_directory,
                          compile_arguments=compile_arguments).file,
        visit_implicit_code=visit_implicit_code,
        visit_template_instantiations=visit_template_instantiations,
    )
    if max_depth is not None:
        if not 0 <= max_depth <= 256:
            raise ValueError("max_depth must be 0..256")
        request.max_depth = max_depth
    if max_nodes is not None:
        if not 1 <= max_nodes <= 100000:
            raise ValueError("max_nodes must be 1..100000")
        request.max_nodes = max_nodes
    request.projection.CopyFrom(value_projection(projection, payload_depth=payload_depth, payload_nodes=payload_nodes))
    request.main_file_only = main_file_only
    return request
