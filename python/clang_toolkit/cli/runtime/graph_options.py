"""Shared semantic projection options for graph expressions."""
from __future__ import annotations
from lark import Tree
from google.protobuf.json_format import MessageToJson
from .semantic import MessageView


def render_graph(value: MessageView) -> str:
    """Preserve standalone ProtoJSON output; expressions keep typed access."""
    return MessageToJson(value._message(), preserving_proto_field_name=True)


def graph_option(option: Tree, options: dict) -> bool:
    from .evaluator import EvaluationError
    name = str(option.data)
    keys = {"graph_projection": "projection", "graph_main_file": "main_file_only",
            "graph_payload_depth": "payload_depth", "graph_payload_nodes": "payload_nodes"}
    if name not in keys:
        return False
    key = keys[name]
    if key in options:
        raise EvaluationError(f"duplicate graph option {key}")
    raw = str(option.children[1])
    if key == "projection":
        if raw not in {"shallow", "recursive"}:
            raise EvaluationError("projection must be shallow or recursive")
        options[key] = raw
    elif key == "main_file_only":
        options[key] = raw == "true"
    else:
        maximum = 64 if key == "payload_depth" else 100000
        if not raw.isdigit() or not 1 <= int(raw) <= maximum:
            raise EvaluationError(f"{key} must be 1..{maximum}")
        options[key] = int(raw)
    return True
