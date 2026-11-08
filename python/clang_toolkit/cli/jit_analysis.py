"""Lower shared CTK analysis syntax to the in-process Clang analysis ABI."""

from __future__ import annotations

import ast
from collections.abc import Callable
import json

from lark import Token, Tree

from .jit_language import LanguageIR
from .runtime.graph_options import graph_option
from .runtime.prototype.syntax import Node

Operand = Node | Token | Tree
LowerValue = Callable[[LanguageIR, Operand], str]

ANALYSIS_COMMANDS = {
    "cfg",
    "cfg_file",
    "cfg_binding",
    "callgraph",
    "callgraph_file",
    "callgraph_binding",
    "variable_flow",
    "traverse",
    "step",
    "peek",
}

_LIMITS = {
    "cfg_functions": ("max_functions", 1, 1000),
    "cfg_blocks": ("max_blocks", 1, 100000),
    "cfg_elements": ("max_elements", 1, 1000000),
    "traverse_depth": ("max_depth", 0, 256),
    "traverse_nodes": ("max_nodes", 1, 100000),
    "call_graph_nodes": ("max_nodes", 0, (1 << 64) - 1),
    "call_graph_edges": ("max_edges", 1, 1000000),
    "call_graph_sites": ("max_call_sites", 1, 1000000),
    "call_graph_depth": ("max_depth", 0, 32),
    "flow_blocks": ("max_blocks", 0, (1 << 32) - 1),
    "flow_events": ("max_events", 0, (1 << 32) - 1),
    "flow_iterations": ("max_iterations", 0, (1 << 32) - 1),
}
_FLAGS = {
    "traverse_implicit": "visit_implicit_code",
    "traverse_instantiations": "visit_template_instantiations",
    "call_graph_implicit": "visit_implicit_code",
    "call_graph_instantiations": "visit_template_instantiations",
    "call_graph_exclude_system": "exclude_system_headers",
    "call_graph_strict_node_filter": "strict_node_filter",
}


def _number(value: str, name: str, minimum: int, maximum: int) -> int:
    if not value.isdigit() or not minimum <= int(value) <= maximum:
        raise ValueError(f"{name} must be {minimum}..{maximum}")
    return int(value)


def _options(items: list[Tree]) -> tuple[dict[str, object], bool]:
    projection: dict = {}
    values: dict = {}
    cfg: dict = {}
    json_format = False

    def add(target: dict, key: str, value: object) -> None:
        if key in target:
            raise ValueError(f"duplicate analysis option {key}")
        target[key] = value

    for item in items:
        kind = str(item.data)
        if graph_option(item, projection):
            continue
        if kind == "graph_json":
            if json_format:
                raise ValueError("duplicate callgraph output format")
            json_format = True
            continue
        if kind == "flow_values":
            add(values, "value_domain", "INTERVAL")
            continue
        raw = str(item.children[1])
        if kind in _LIMITS:
            name, low, high = _LIMITS[kind]
            if kind == "call_graph_depth" and raw == "all":
                if "max_depth" in values:
                    raise ValueError("duplicate analysis option max_depth")
                add(values, "unlimited_depth", True)
            elif kind == "call_graph_nodes" and raw == "all":
                add(values, name, 0)
            else:
                if name == "max_depth" and "unlimited_depth" in values:
                    raise ValueError("duplicate analysis option max_depth")
                add(values, name, _number(raw, name, low, high))
        elif kind in _FLAGS:
            add(values, _FLAGS[kind], raw == "true")
        elif kind == "cfg_build_option":
            add(cfg, raw, str(item.children[2]) == "true")
        elif kind == "call_graph_direction":
            if raw not in {"in", "out", "both"}:
                raise ValueError("direction must be in, out or both")
            add(values, "direction", f"CALL_GRAPH_DIRECTION_{raw.upper()}")
        elif kind == "call_graph_node_filter":
            matcher = ast.literal_eval(raw)
            if not matcher.strip():
                raise ValueError("node_filter must be non-empty matcher text")
            add(values, "node_filter", matcher)
        else:
            raise ValueError(f"unsupported analysis option {kind}")
    if cfg:
        values["options"] = cfg
    if "main_file_only" in projection:
        values["main_file_only"] = projection.pop("main_file_only")
    if projection:
        converted = {
            {
                "projection": "mode",
                "payload_depth": "max_depth",
                "payload_nodes": "max_nodes",
            }[name]: value.upper() if name == "projection" else value
            for name, value in projection.items()
        }
        values["projection"] = converted
    return values, json_format


def _function(ir: LanguageIR, value: Operand, lower: LowerValue) -> str:
    if isinstance(value, Token) and value.type == "NAME":
        return ir.literal(str(value))
    if isinstance(value, Tree) and value.data == "qualified_name":
        return ir.literal("".join(str(part) for part in value.children))
    return lower(ir, value)


def _navigate(ir: LanguageIR, tree: Tree, mode: str, lower: LowerValue) -> str:
    axis = str(tree.children[1])
    items = tree.children[2:]
    in_index = items.index("in")
    before = items[:in_index]
    after = items[in_index + 1 :]
    index = None
    if "at" in before:
        at = before.index("at")
        index = _number(str(before[at + 1]), "navigation index", 0, (1 << 64) - 1)
        before = before[:at]
    if len(after) > 2:
        raise ValueError("duplicate navigation nodes option")
    maximum = (
        _number(str(after[1].children[1]), "navigation nodes", 0, (1 << 64) - 1)
        if len(after) == 2
        else 0
    )
    return ir.call(
        "ctk_jit_navigate_v1",
        "ptr",
        ("ptr", "%context"),
        ("ptr", lower(ir, after[0])),
        ("ptr", lower(ir, before[0]) if before else "null"),
        ("ptr", ir.string(axis)),
        ("i64", maximum),
        ("i64", index or 0),
        ("i32", int(index is not None)),
        ("i32", int(tree.data == "step")),
        ("i32", int(mode == "statement")),
    )


def lower_analysis(ir: LanguageIR, tree: Tree, mode: str, lower: LowerValue) -> str:
    kind = str(tree.data)
    if kind in {"peek", "step"}:
        return _navigate(ir, tree, mode, lower)
    if kind in {"cfg", "callgraph"}:
        # The console requires an explicit path/tree or retained selection.
        raise ValueError(f"{kind} requires an explicit analysis target")
    parts = tree.children
    operand = "null"
    operation = kind
    if kind in {"cfg_file", "cfg_binding"}:
        operation = "cfg"
        if kind == "cfg_file":
            operand = _function(ir, parts[1], lower)
            at = 3
        else:
            at = 2
    elif kind == "variable_flow":
        at = 1
        operand = lower(ir, parts[3])
    elif kind in {"callgraph_file", "callgraph_binding"}:
        operation = "callgraph"
        at = 1 if kind == "callgraph_file" else 2
    else:
        at = 1
    target = lower(ir, parts[at])
    options, json_format = _options(
        parts[4:] if kind == "variable_flow" else parts[at + 1 :]
    )
    return ir.call(
        "ctk_jit_analyze_v1",
        "ptr",
        ("ptr", "%context"),
        ("ptr", ir.string(operation + ("_json" if json_format else ""))),
        ("ptr", target),
        ("ptr", operand),
        ("ptr", ir.string(json.dumps(options, separators=(",", ":")))),
        ("i32", int(mode == "statement")),
    )
