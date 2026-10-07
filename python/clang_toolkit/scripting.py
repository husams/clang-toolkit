"""Construct atomic server-side DSL requests."""
from __future__ import annotations
from collections.abc import Sequence
from pathlib import Path
from clang_toolkit._generated.analysis.v1 import script_request_pb2 as pb
from clang_toolkit._generated.analysis.v1 import script_compilation_profile_pb2 as profile_pb
from clang_toolkit.cursors import file_request

def script_request(source: str, *, path: str | Path | None = None,
                   working_directory: str | Path | None = None,
                   compile_arguments: Sequence[str] = (), max_steps: int | None = None) -> pb.ScriptRequest:
    request = pb.ScriptRequest(source=source)
    profile = profile_pb.ScriptCompilationProfile(
        working_directory=str(Path(working_directory or Path.cwd()).resolve()),
        compile_arguments=compile_arguments,
    )
    request.profile.CopyFrom(profile)
    if path is not None:
        request.file.CopyFrom(file_request(path, "unused", working_directory=working_directory,
                                          compile_arguments=compile_arguments).file)
    if max_steps is not None:
        if not 1 <= max_steps <= 10000:
            raise ValueError("max_steps must be 1..10000")
        request.max_steps = max_steps
    if len(source.encode("utf-8")) > 1024 * 1024:
        raise ValueError("script source exceeds 1 MiB")
    return request
