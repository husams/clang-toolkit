"""Compile temporary C++ source using an optional borrowed compilation profile."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lark import Tree

from .filesystem import File

if TYPE_CHECKING:
    from .evaluator import Runtime


def source_text(literal: str) -> str:
    """Decode only an escaped backtick; C++ escapes and interpolation stay raw."""
    content = literal[4:-1]
    parts: list[str] = []
    position = 0
    while position < len(content):
        if content[position] == "\\" and position + 1 < len(content):
            following = content[position + 1]
            parts.append("`" if following == "`" else "\\" + following)
            position += 2
        else:
            parts.append(content[position])
            position += 1
    return "".join(parts)


def parse_cpp(runtime: Runtime, node: Tree) -> Any:
    from .evaluator import EvaluationError

    options: Any = {}
    if len(node.children) > 3 and node.children[3] is not None:
        options = runtime._evaluate(node.children[3])
    if isinstance(options, File):
        options = options.absolute
    if isinstance(options, str):
        options = {"file": options}
    if not isinstance(options, dict):
        raise EvaluationError("parse cpp using requires a file path or options object")
    allowed = {
        "file", "compile_arguments", "working_directory", "compilation_database",
        "includes", "translation_unit",
    }
    unknown = set(options) - allowed
    if unknown:
        raise EvaluationError("unknown parse cpp option: " + sorted(unknown)[0])
    for name in ("file", "working_directory", "compilation_database"):
        if name in options and not isinstance(options[name], str):
            raise EvaluationError(f"parse cpp {name} must be a string")
    for name in ("compile_arguments", "includes"):
        if name in options and (
            not isinstance(options[name], list)
            or any(not isinstance(value, str) for value in options[name])
        ):
            raise EvaluationError(f"parse cpp {name} must be a list of strings")
    if "translation_unit" in options and not isinstance(options["translation_unit"], bool):
        raise EvaluationError("parse cpp translation_unit must be a boolean")
    arguments = {
        "working_directory": runtime.cwd,
        **options,
        "compile_arguments": [
            *runtime.config_store.effective["extra_args"],
            *options.get("compile_arguments", []),
        ],
    }
    if runtime._active_resource_scope is not None:
        arguments["scope"] = runtime._active_resource_scope
    return runtime._track_native_value(
        runtime.client.parse_cpp(source_text(str(node.children[1])), **arguments)
    )
