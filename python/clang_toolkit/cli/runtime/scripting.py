"""Grammar-driven dispatch to the server DSL."""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Any
from google.protobuf.json_format import MessageToJson
from lark import Tree
from .filesystem import File

if TYPE_CHECKING:
    from .evaluator import Runtime


def execute_script(runtime: Runtime, statement: Tree) -> str:
    from .evaluator import EvaluationError

    source = runtime._evaluate(statement.children[1])
    if not isinstance(source, str):
        raise EvaluationError("script requires a source string")
    options = {
        "working_directory": runtime.cwd,
        "compile_arguments": runtime.config_store.effective["extra_args"],
    }
    selected: Any = None
    if runtime._active_resource_scope is not None:
        options["scope"] = runtime._active_resource_scope
    if len(statement.children) > 2:
        path = runtime._evaluate(statement.children[-1])
        if isinstance(path, File):
            path = path.path
        if not isinstance(path, (str, Path)):
            raise EvaluationError("script target requires a file path")
        options["path"] = path
    response = runtime._scoped_file_call(
        selected, lambda: runtime.client.run_script(source, **options)
    )
    if runtime._active_resource_scope is not None:
        from clang_toolkit.resources import require_complete

        require_complete(response)
    return MessageToJson(response, preserving_proto_field_name=True)
