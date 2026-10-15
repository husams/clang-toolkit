"""Console variableflow command, sharing retained bindings with native queries."""
from __future__ import annotations
from typing import TYPE_CHECKING
from lark import Tree
from .semantic import view, MessageView
from .graph_options import render_graph
from clang_toolkit.match_values import BindingSelection
from clang_toolkit._generated.analysis.v1.variable_flow_pb2 import VariableFlowEvent
if TYPE_CHECKING:
    from .evaluator import Runtime


def execute_variable_flow(runtime: Runtime, statement: Tree) -> MessageView:
    from .evaluator import EvaluationError
    variable = runtime._evaluate(statement.children[1])
    function = runtime._evaluate(statement.children[3])
    if not isinstance(variable, BindingSelection) or not isinstance(function, BindingSelection):
        raise EvaluationError("variableflow requires retained variable and function bindings")
    options = {}
    for option in statement.children[4:]:
        name = str(option.data).removeprefix("flow_")
        key = "max_" + name
        if key in options:
            raise EvaluationError(f"{name} may occur once")
        raw = str(option.children[-1])
        if not raw.isdigit():
            raise EvaluationError(f"{name} must be a positive integer")
        options[key] = int(raw)
    if runtime._active_resource_scope is not None:
        options["scope"] = runtime._active_resource_scope
    if runtime._value_context_depth:
        return view(runtime.client.variable_flow(variable, function, **options))
    def emit(event: VariableFlowEvent) -> None:
        text = runtime._emit_output(render_graph(view(event)))
        if text:
            print(text, flush=True)
    return view(runtime.client.stream_variable_flow(variable, function, on_event=emit, **options))
