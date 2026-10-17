"""CFG commands using the formal grammar and typed build options."""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
from .semantic import MessageView, view
from .graph_options import graph_option, render_graph
from lark import Token, Tree
from clang_toolkit.control_flow import CfgOptions
from .filesystem import File
from clang_toolkit.match_values import ParsedTree, BindingSelection
from clang_toolkit.resources import FileHandle, InputDescriptor

if TYPE_CHECKING:
    from .evaluator import Runtime


def execute_cfg(runtime: Runtime, statement: Tree, source: str) -> MessageView:
    from .evaluator import EvaluationError

    binding_target = str(statement.data) in {"cfg_binding", "cfg_binding_expression"}
    function_node = statement.children[1]
    if binding_target:
        function = None
    elif isinstance(function_node, Token) and function_node.type == "STRING":
        function = runtime._evaluate(function_node)
    elif isinstance(function_node, Token) and function_node.type == "NAME":
        function = str(function_node)
    elif isinstance(function_node, Tree) and function_node.data == "qualified_name":
        function = "::".join(
            str(child) for child in function_node.children if str(child) != "::"
        )
    elif isinstance(function_node, Tree) and function_node.data == "reference":
        function = runtime._evaluate(function_node)
        if not isinstance(function, str):
            raise EvaluationError("cfg function reference must be a string")
    else:
        raise EvaluationError("cfg requires an exact qualified function name")
    selected = runtime._evaluate(statement.children[2 if binding_target else 3])
    if isinstance(selected, File):
        selected = selected.path
    if not isinstance(selected, (str, Path, ParsedTree, BindingSelection, FileHandle, InputDescriptor)):
        raise EvaluationError("cfg requires a path, parsed tree or native function binding")
    if binding_target and not isinstance(selected, BindingSelection):
        raise EvaluationError("cfg in requires a retained function binding")
    options = CfgOptions()
    limits: dict[str, int] = {}
    seen: set[str] = set()
    for option in statement.children[3 if binding_target else 4:]:
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
            name, maximum = {
                "cfg_functions": ("max_functions", 1000),
                "cfg_blocks": ("max_blocks", 100000),
                "cfg_elements": ("max_elements", 1000000),
            }[str(option.data)]
            raw = str(option.children[1])
            if name in seen or not raw.isdigit() or not 1 <= int(raw) <= maximum:
                raise EvaluationError(f"{name} must occur once and be 1..{maximum}")
            seen.add(name)
            limits[name] = int(raw)
    kwargs = dict(
            working_directory=runtime.cwd,
            compile_arguments=runtime.config_store.effective["extra_args"],
            options=options,
            **(
                {"scope": runtime._active_resource_scope}
                if runtime._active_resource_scope is not None
                else {}
            ),
            **limits,
    )
    def run():
        args = (selected,) if binding_target else (function,)
        target = {} if binding_target else {"path": selected}
        if runtime._value_context_depth:
            return runtime.client.cfg(*args, **target, **kwargs)
        def emit(event):
            if runtime._active_resource_scope is not None:
                from clang_toolkit.resources import ResourceError, require_complete
                if event.HasField("graph_completed"):
                    if not event.graph_completed.is_complete:
                        raise ResourceError("CFG result is incomplete")
                else:
                    require_complete(event)
            text = runtime._emit_output(render_graph(view(event)))
            if text:
                print(text, flush=True)
        return runtime.client.stream_cfg(*args, **target, on_event=emit, **kwargs)
    response = runtime._scoped_file_call(selected, run)
    if runtime._active_resource_scope is not None and runtime._value_context_depth:
        from clang_toolkit.resources import require_complete

        require_complete(response)
    if not runtime._value_context_depth:
        from clang_toolkit._generated.analysis.v1.cfg_stream_pb2 import CfgStreamEvent
        return view(CfgStreamEvent(completed=response))
    return view(response)
