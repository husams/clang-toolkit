"""File inventory and resource status commands for the interactive language."""

from __future__ import annotations

from typing import Any

from lark import Token, Tree

from clang_toolkit.resources import FileHandle, FileSet, InputDescriptor

from .filesystem import File


def discover_files(runtime: Any, node: Tree) -> FileSet:
    """Discover a bounded metadata manifest using the connected server."""
    selected = runtime._evaluate(node.children[1])
    if isinstance(selected, str | File):
        paths: tuple[str, ...] = (
            selected.absolute if isinstance(selected, File) else selected,
        )
    elif isinstance(selected, list | tuple):
        paths_list: list[str] = []
        for item in selected:
            if isinstance(item, File):
                paths_list.append(item.absolute)
            elif isinstance(item, str):
                paths_list.append(item)
            else:
                _raise("files accepts paths, directories, or glob strings")
        paths = tuple(paths_list)
    else:
        _raise("files requires a path or list of paths")
    discover = getattr(runtime.client, "discover_files", None)
    if discover is None:
        _raise("file discovery is unavailable; update and restart the server")
    return discover(
        paths,
        working_directory=runtime.cwd,
        compile_arguments=runtime.config_store.effective["extra_args"],
        compilation_database=runtime.config_store.effective["compile_commands"],
    )


def execute_file_command(runtime: Any, node: Tree) -> str:
    """Execute one fully parsed file/resource command."""
    kind = str(node.data)
    if kind == "file_open":
        path = runtime._evaluate(node.children[2])
        if isinstance(path, File):
            path = path.absolute
        if isinstance(path, InputDescriptor):
            source: str | InputDescriptor = path
        elif isinstance(path, str):
            source = path
        else:
            _raise("file open requires a path or discovered input")
        handle = runtime._scoped_file_call(
            source,
            lambda: runtime.client.open_file(
                source,
                working_directory=runtime.cwd,
                compile_arguments=runtime.config_store.effective["extra_args"],
                compilation_database=runtime.config_store.effective["compile_commands"],
                **(
                    {"scope": runtime._active_resource_scope}
                    if runtime._active_resource_scope is not None
                    else {}
                ),
            ),
        )
        name = _simple_name(runtime, node.children[4])
        _store_binding(runtime, name, handle)
        return f"opened {handle.path} as ${name}"
    if kind == "file_list":
        discovered = next(
            (child for child in node.children if isinstance(child, Tree)), None
        )
        if discovered is not None:
            manifest = runtime._evaluate(discovered)
            if not isinstance(manifest, FileSet):
                _raise("file list discovered in requires a FileSet")
            return _bounded_json({"discovered": manifest})
        return _bounded_json(runtime.client.list_files())
    if kind == "file_info":
        return _bounded_json(
            runtime.client.file_info(runtime._evaluate(node.children[2]))
        )
    if kind == "file_close":
        target = node.children[2]
        if isinstance(target, Token) and target.type == "ALL":
            result = runtime.client.close_all_files()
            return _bounded_json(result)
        return _bounded_json(runtime.client.close_file(runtime._evaluate(target)))
    if kind == "file_refresh":
        previous = runtime._evaluate(node.children[2])
        handle = runtime.client.refresh_file(
            previous,
            **(
                {"scope": runtime._active_resource_scope}
                if runtime._active_resource_scope is not None
                else {}
            ),
        )
        name = _simple_name(runtime, node.children[4])
        _store_binding(runtime, name, handle)
        return f"refreshed {handle.path} as ${name}"
    if kind == "resource_status":
        return _bounded_json(runtime.client.resource_status())
    _raise(f"unsupported file command: {kind}")


def _simple_name(runtime: Any, reference: Tree) -> str:
    if (
        reference.data != "reference"
        or len(reference.children) != 2
        or not isinstance(reference.children[1], Token)
    ):
        _raise("target must be a simple variable such as $source")
    return str(reference.children[1])


def _store_binding(runtime: Any, name: str, value: Any) -> None:
    scope = runtime._scopes[-1] if runtime._scopes else runtime.bindings
    scope[name] = value


def _raise(message: str) -> None:
    from .evaluator import EvaluationError

    raise EvaluationError(message)


def _bounded_json(value: Any) -> str:
    """Render control-plane data with a strict output bound."""
    import json

    from google.protobuf.json_format import MessageToDict
    from google.protobuf.message import Message

    def prepare(item: Any) -> Any:
        if isinstance(item, Message):
            return MessageToDict(item, preserving_proto_field_name=True)
        if isinstance(item, FileSet):
            return {
                "inputs": [prepare(entry) for entry in item.inputs[:100]],
                "input_count": len(item.inputs),
                "diagnostics": list(item.diagnostics[:20]),
                "truncated": len(item.inputs) > 100 or len(item.diagnostics) > 20,
            }
        if isinstance(item, InputDescriptor):
            return {"path": item.path, "profile_id": item.profile_id}
        if isinstance(item, FileHandle):
            return {
                "lease_id": item.lease_id,
                "path": item.path,
                "profile_id": item.profile_id,
                "source_revision": item.source_revision,
                "state": item.state,
            }
        if isinstance(item, (tuple, list)):
            entries = [prepare(entry) for entry in item[:100]]
            if len(item) > 100:
                entries.append({"truncated": True})
            return entries
        if isinstance(item, dict):
            return {str(key): prepare(entry) for key, entry in item.items()}
        return item

    prepared = prepare(value)
    result = json.dumps(prepared, default=repr, sort_keys=True, ensure_ascii=False)
    if len(result) <= 20_000:
        return result
    return json.dumps(
        {"truncated": True, "serialized_chars": len(result)},
        sort_keys=True,
        separators=(",", ":"),
    )
