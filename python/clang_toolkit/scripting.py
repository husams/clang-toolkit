"""Construct atomic server-side DSL requests."""
from __future__ import annotations
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from clang_toolkit._generated.analysis.v1 import script_request_pb2 as pb
from clang_toolkit._generated.analysis.v1 import script_compilation_profile_pb2 as profile_pb
from clang_toolkit.cursors import file_request
from clang_toolkit.resources import FileHandle, InputDescriptor

def script_request(source: str, *,
                   path: str | Path | FileHandle[object] | InputDescriptor | None = None,
                   working_directory: str | Path | None = None,
                   compile_arguments: Sequence[str] = (), max_steps: int | None = None,
                   profile: InputDescriptor | None = None) -> pb.ScriptRequest:
    request = pb.ScriptRequest(source=source)
    selected_profile = profile_pb.ScriptCompilationProfile(
        working_directory=str(Path(working_directory or Path.cwd()).resolve()),
        compile_arguments=compile_arguments,
    )
    default_descriptor = profile
    file_descriptor: InputDescriptor | None = None
    if isinstance(path, FileHandle):
        file_descriptor = path.input
        path = path.path
    elif isinstance(path, InputDescriptor):
        file_descriptor = path
        path = path.path
    if default_descriptor is None:
        default_descriptor = file_descriptor
    if default_descriptor is not None:
        _apply_profile(selected_profile, default_descriptor)
    request.profile.CopyFrom(selected_profile)
    if path is not None:
        request.file.CopyFrom(file_request(path, "unused", working_directory=working_directory,
                                          compile_arguments=compile_arguments).file)
    if file_descriptor is not None:
        _apply_profile(request.file, file_descriptor, frozen_field="frozen_profile")
    if max_steps is not None:
        if not 1 <= max_steps <= 10000:
            raise ValueError("max_steps must be 1..10000")
        request.max_steps = max_steps
    if len(source.encode("utf-8")) > 1024 * 1024:
        raise ValueError("script source exceeds 1 MiB")
    return request


def _apply_profile(
    target: Any, descriptor: InputDescriptor, *, frozen_field: str = "frozen"
) -> None:
    """Copy a frozen discovered profile into a script profile or file target."""
    target.working_directory = descriptor.working_directory
    target.compile_arguments[:] = descriptor.compile_arguments
    target.compilation_database = descriptor.compilation_database
    setattr(target, frozen_field, descriptor.frozen_profile)
    target.expected_profile_id = descriptor.profile_id
