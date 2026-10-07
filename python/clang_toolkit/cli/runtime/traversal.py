"""Standalone AST visitor commands parsed by the shared formal grammar."""
from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path
from google.protobuf.json_format import MessageToJson
from lark import Tree
from .filesystem import File

if TYPE_CHECKING:
    from .evaluator import Runtime

def execute_traversal(runtime: Runtime, statement: Tree) -> str:
    from .evaluator import EvaluationError
    selected = runtime._evaluate(statement.children[1])
    if isinstance(selected, File):
        selected = selected.path
    if not isinstance(selected, (str, Path)):
        raise EvaluationError("traverse requires a file path")
    options: dict[str, int | bool] = {}
    for option in statement.children[2:]:
        name = str(option.data)
        key = {"traverse_depth": "max_depth", "traverse_nodes": "max_nodes",
               "traverse_implicit": "visit_implicit_code",
               "traverse_instantiations": "visit_template_instantiations"}[name]
        if key in options:
            raise EvaluationError(f"duplicate traversal option {key}")
        text = str(option.children[1])
        if key.startswith("visit_"):
            options[key] = text == "true"
        else:
            if not text.isdigit():
                raise EvaluationError("traversal limits must be unsigned integers")
            value = int(text)
            if (key == "max_depth" and value > 256) or (key == "max_nodes" and not 1 <= value <= 100000):
                raise EvaluationError("max_depth must be 0..256; max_nodes must be 1..100000")
            options[key] = value
    response = runtime.client.traverse(selected, working_directory=runtime.cwd,
        compile_arguments=runtime.config_store.effective["extra_args"], **options)
    return MessageToJson(response, preserving_proto_field_name=True)
