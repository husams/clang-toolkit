"""CFG commands using the formal grammar and typed build options."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
from .semantic import MessageView, view
from .graph_options import graph_option
from lark import Token, Tree
from clang_toolkit.control_flow import CfgOptions
from .filesystem import File
if TYPE_CHECKING:
    from .evaluator import Runtime

def execute_cfg(runtime: Runtime, statement: Tree, source: str) -> MessageView:
    from .evaluator import EvaluationError
    function_node = statement.children[1]
    if isinstance(function_node, Token) and function_node.type == "STRING":
        function = runtime._evaluate(function_node)
    elif isinstance(function_node, Token) and function_node.type == "NAME":
        function = str(function_node)
    elif isinstance(function_node, Tree) and function_node.data == "qualified_name":
        function = "::".join(str(child) for child in function_node.children if str(child) != "::")
    elif isinstance(function_node, Tree) and function_node.data == "reference":
        function = runtime._evaluate(function_node)
        if not isinstance(function, str):
            raise EvaluationError("cfg function reference must be a string")
    else:
        raise EvaluationError("cfg requires an exact qualified function name")
    selected = runtime._evaluate(statement.children[3])
    if isinstance(selected, File):
        selected = selected.path
    if not isinstance(selected, (str, Path)):
        raise EvaluationError("cfg requires a file path")
    options = CfgOptions()
    limits: dict[str, int] = {}
    seen: set[str] = set()
    for option in statement.children[4:]:
        if graph_option(option, limits):
            continue
        if option.data == "cfg_build_option":
            name = str(option.children[1])
            if name not in options.DESCRIPTOR.fields_by_name:
                raise EvaluationError(f"unknown CFG build option {name}")
            if name in seen:
                raise EvaluationError(f"duplicate CFG option {name}")
            seen.add(name)
            setattr(options, name, str(option.children[2]) == "true")
        else:
            name, maximum = {"cfg_functions": ("max_functions", 1000),
                             "cfg_blocks": ("max_blocks", 100000),
                             "cfg_elements": ("max_elements", 1000000)}[str(option.data)]
            raw = str(option.children[1])
            if name in seen or not raw.isdigit() or not 1 <= int(raw) <= maximum:
                raise EvaluationError(f"{name} must occur once and be 1..{maximum}")
            seen.add(name)
            limits[name] = int(raw)
    response = runtime.client.cfg(function, path=selected, working_directory=runtime.cwd,
        compile_arguments=runtime.config_store.effective["extra_args"], options=options, **limits)
    return view(response)
