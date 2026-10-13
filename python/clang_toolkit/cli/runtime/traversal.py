"""Standalone AST visitor commands parsed by the shared formal grammar."""

from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path
from .semantic import MessageView, view
from .graph_options import graph_option, render_graph
from lark import Tree
from .filesystem import File
from clang_toolkit.match_values import ParsedTree, BindingSelection
from clang_toolkit.resources import FileHandle, InputDescriptor

if TYPE_CHECKING:
    from .evaluator import Runtime


def execute_traversal(runtime: Runtime, statement: Tree) -> MessageView:
    from .evaluator import EvaluationError

    selected = runtime._evaluate(statement.children[1])
    if isinstance(selected, File):
        selected = selected.path
    if not isinstance(selected, (str, Path, ParsedTree, BindingSelection, FileHandle, InputDescriptor)):
        raise EvaluationError("traverse requires a path, parsed tree or native binding")
    options: dict[str, int | bool] = {}
    for option in statement.children[2:]:
        if graph_option(option, options):
            continue
        name = str(option.data)
        key = {
            "traverse_depth": "max_depth",
            "traverse_nodes": "max_nodes",
            "traverse_implicit": "visit_implicit_code",
            "traverse_instantiations": "visit_template_instantiations",
        }[name]
        if key in options:
            raise EvaluationError(f"duplicate traversal option {key}")
        text = str(option.children[1])
        if key.startswith("visit_"):
            options[key] = text == "true"
        else:
            if not text.isdigit():
                raise EvaluationError("traversal limits must be unsigned integers")
            value = int(text)
            if (key == "max_depth" and value > 256) or (
                key == "max_nodes" and not 1 <= value <= 100000
            ):
                raise EvaluationError(
                    "max_depth must be 0..256; max_nodes must be 1..100000"
                )
            options[key] = value
    kwargs = dict(
        working_directory=runtime.cwd,
        compile_arguments=runtime.config_store.effective["extra_args"],
        **({"scope": runtime._active_resource_scope}
           if runtime._active_resource_scope is not None else {}),
        **options,
    )
    def run():
        if runtime._value_context_depth:
            # Assignment is an explicit request to collect an inspectable value.
            return runtime.client.traverse(selected, **kwargs)
        def emit(node):
            text = runtime._emit_output(render_graph(view(node)))
            if text:
                print(text, flush=True)
        return runtime.client.stream_traverse(selected, on_node=emit, **kwargs)
    response = runtime._scoped_file_call(selected, run)
    return view(response)
