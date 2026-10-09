"""Formal CLI evaluation for native AST call graphs."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
from .semantic import MessageView, view
from .graph_options import graph_option
from lark import Tree
from .filesystem import File
if TYPE_CHECKING:
    from .evaluator import Runtime

def execute_call_graph(runtime: Runtime, statement: Tree) -> MessageView:
    from .evaluator import EvaluationError
    selected = runtime._evaluate(statement.children[1])
    if isinstance(selected, File):
        selected = selected.path
    if not isinstance(selected, (str, Path)):
        raise EvaluationError("callgraph requires a file path")
    options: dict[str, int | bool] = {}
    for option in statement.children[2:]:
        if graph_option(option, options):
            continue
        key, maximum = {"call_graph_nodes": ("max_nodes", 100000),
                        "call_graph_edges": ("max_edges", 1000000),
                        "call_graph_implicit": ("visit_implicit_code", None),
                        "call_graph_instantiations": ("visit_template_instantiations", None)}[str(option.data)]
        if key in options:
            raise EvaluationError(f"duplicate callgraph option {key}")
        text = str(option.children[1])
        if maximum is None:
            options[key] = text == "true"
        else:
            if not text.isdigit() or not 1 <= int(text) <= maximum:
                raise EvaluationError(f"{key} must be 1..{maximum}")
            options[key] = int(text)
    response = runtime.client.callgraph(selected, working_directory=runtime.cwd,
        compile_arguments=runtime.config_store.effective["extra_args"], **options)
    return view(response)
