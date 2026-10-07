"""Typed native CFG request options and bounded results."""
from __future__ import annotations
from collections.abc import Sequence
from pathlib import Path
from clang_toolkit._generated.analysis.v1 import cfg_request_pb2, cfg_options_pb2
from clang_toolkit.cursors import file_request

CfgOptions = cfg_options_pb2.CfgOptions

def cfg_request(path: str | Path, function: str, *, working_directory: str | Path | None = None,
                compile_arguments: Sequence[str] = (), options: CfgOptions | None = None,
                max_functions: int | None = None, max_blocks: int | None = None,
                max_elements: int | None = None) -> cfg_request_pb2.CfgRequest:
    if not function:
        raise ValueError("function name is required")
    request = cfg_request_pb2.CfgRequest(file=file_request(path, "unused",
        working_directory=working_directory, compile_arguments=compile_arguments).file,
        function=function)
    if options is not None:
        request.options.CopyFrom(options)
    for name, value, maximum in [("max_functions", max_functions, 1000),
                                 ("max_blocks", max_blocks, 100000),
                                 ("max_elements", max_elements, 1000000)]:
        if value is not None:
            if not 1 <= value <= maximum:
                raise ValueError(f"{name} must be 1..{maximum}")
            setattr(request, name, value)
    return request
