"""Source-backed descriptions of locally defined console callables."""

from __future__ import annotations

from dataclasses import dataclass
import re
from inspect import Parameter, signature
from typing import Any


@dataclass(frozen=True)
class CallableHelp:
    name: str
    signature: str
    definition: str
    origin: str = "user defined"
    pipeline_signature: str | None = None
    pipeline_parameters: tuple[str, ...] = ()
    parameter_names: tuple[str, ...] = ()
    arguments: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()

    @property
    def usage(self) -> tuple[str, ...]:
        return (self.signature, f"VALUE | {self.pipeline_signature}")

    @property
    def summary(self) -> str:
        return "User defined expression." if self.origin == "user defined" else self.definition

    @property
    def hint(self) -> str:
        return f"{self.origin} · {self.signature}"

    @property
    def pipeline_hint(self) -> str:
        return (
            f"pipeline stage · {self.pipeline_signature or self.signature} "
            "(input supplied by |)"
        )

    def markdown(self) -> str:
        def code(source: str) -> str:
            fence = "`" * max(
                3,
                1
                + max(
                    (len(match[0]) for match in re.finditer(r"`+", source)), default=0
                ),
            )
            return f"{fence}ctk\n{source}\n{fence}"

        if self.origin == "built-in":
            return "\n\n".join(
                (
                    f"## {self.name}",
                    self.definition,
                    "### Usage",
                    *(code(source) for source in self.usage),
                    "### Arguments, options and defaults",
                    "\n".join(f"- {note}" for note in self.arguments),
                    "### Examples",
                    *(code(source) for source in self.examples),
                )
            )
        return "\n\n".join(
            (
                f"## {self.name}",
                self.summary,
                "### Signature",
                code(self.signature),
                "### Definition",
                code(self.definition),
            )
        )

    def plain(self) -> str:
        if self.origin == "built-in":
            return "\n".join(
                (
                    f"{self.name}: {self.definition}",
                    "Usage:",
                    *(f"  {source}" for source in self.usage),
                    "Arguments, options and defaults:",
                    *(f"  {note}" for note in self.arguments),
                    "Examples:",
                    *(f"  {source}" for source in self.examples),
                )
            )
        label = self.summary
        return (
            f"{self.name}: {label}\nSignature:\n  {self.signature}"
            f"\nDefinition:\n{self.definition}"
        )


def describe_callable(name: str, value: Any) -> CallableHelp:
    """Keep defaults as written, without evaluating the function or its body."""
    if not hasattr(value, "parameters") and callable(value):
        parameters = signature(value).parameters.values()
        return CallableHelp(
            name,
            f"{name}{_python_signature(value)}",
            "Alias for a built-in callable.",
            pipeline_signature=f"{name}{_python_signature(value, skip_first=True)}",
            pipeline_parameters=_parameter_names(tuple(signature(value).parameters.values())[1:]),
            parameter_names=_parameter_names(tuple(signature(value).parameters.values())),
        )
    parameters = [_format_pattern(item) for item in value.parameters]
    labels = tuple(getattr(value, "parameter_labels", ()))
    if len(labels) < len(parameters):
        labels += (None,) * (len(parameters) - len(labels))
    parameters = [
        f"{label}: {local}" if label else local
        for local, label in zip(parameters, labels)
    ]
    defaults = tuple(getattr(value, "default_nodes", ()))
    first_default = len(parameters) - len(defaults)
    for offset, default in enumerate(defaults):
        span = getattr(default, "source_span", None)
        if span is not None:
            start, end = span
            default_text = value.source[start:end]
            assignment = re.search(r"(?<![<>=!])=(?!=)", default_text)
            if assignment is not None:
                default_text = default_text[assignment.end():].strip()
            parameters[first_default + offset] += " = " + default_text
    # Keep public names aligned with parameter slots until after slicing off
    # the pipeline input. Destructured positional parameters have no keyword,
    # but still occupy the first slot in the signature.
    public_slots = tuple(
        label or _pattern_keyword(item)
        for item, label in zip(value.parameters, labels)
    )
    public_names = tuple(name for name in public_slots if name)
    return CallableHelp(
        name,
        f"{name}({', '.join(parameters)})",
        value.definition,
        pipeline_signature=f"{name}({', '.join(parameters[1:])})",
        pipeline_parameters=tuple(name for name in public_slots[1:] if name),
        parameter_names=public_names,
    )


def _python_signature(function: Any, *, skip_first: bool = False) -> str:
    from clang_toolkit.cli.runtime.prototype.filters import _MISSING

    parameters = tuple(signature(function).parameters.values())
    if skip_first:
        parameters = parameters[1:]
    parts: list[str] = []
    keyword_only = False
    variadic_positional = False
    for parameter in parameters:
        if (
            parameter.kind is Parameter.KEYWORD_ONLY
            and not keyword_only
            and not variadic_positional
        ):
            parts.append("*")
            keyword_only = True
        part = _parameter_display(parameter)
        if parameter.default is not Parameter.empty:
            default = parameter.default
            literal = "omitted" if default is _MISSING else "null" if default is None else (
                "true" if default is True else "false" if default is False else repr(default)
            )
            part += "=" + literal
        parts.append(part)
        variadic_positional |= parameter.kind is Parameter.VAR_POSITIONAL
    return "(" + ", ".join(parts) + ")"


def _parameter_display(parameter: Parameter) -> str:
    prefix = "**" if parameter.kind is Parameter.VAR_KEYWORD else (
        "*" if parameter.kind is Parameter.VAR_POSITIONAL else ""
    )
    return prefix + parameter.name


def _parameter_names(parameters: tuple[Parameter, ...]) -> tuple[str, ...]:
    return tuple(
        parameter.name for parameter in parameters
        if parameter.kind not in {Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD}
    )


def _format_pattern(pattern: Any) -> str:
    """Render simple and nested tuple parameter patterns in runnable signatures."""
    if isinstance(pattern, str):
        return pattern
    if isinstance(pattern, (tuple, list)):
        items = ", ".join(_format_pattern(item) for item in pattern)
        return "(" + items + ("," if len(pattern) == 1 else "") + ")"
    kind = getattr(pattern, "kind", None)
    value = getattr(pattern, "value", None)
    if kind in {"pattern_name", "name_pattern"}:
        return str(value)
    if kind in {"pattern_discard", "discard_pattern"}:
        return "_"
    if kind in {"pattern_tuple", "tuple_pattern"}:
        return _format_pattern(value)
    return str(pattern)


def _pattern_keyword(pattern: Any) -> str | None:
    """Return the local keyword for simple-name parameters only."""
    if isinstance(pattern, str):
        return pattern if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", pattern) else None
    kind = getattr(pattern, "kind", None)
    value = getattr(pattern, "value", None)
    if kind in {"pattern_name", "name_pattern"}:
        return str(value)
    return None


def builtin_callable_help(functions: dict[str, Any] | None = None) -> dict[str, CallableHelp]:
    """Build shared offline help from the pipe-filter registry and bound callables."""
    from clang_toolkit.cli.runtime.prototype.filters import (
        FILTER_DESCRIPTIONS,
        FILTER_SIGNATURES,
    )
    from clang_toolkit.cli.callable_reference import BUILTIN_ARGUMENTS, BUILTIN_EXAMPLES

    result: dict[str, CallableHelp] = {}
    signatures = {
        **FILTER_SIGNATURES,
        "len": "(value)",
        "range": "(*args)",
        "ctk": "(command)",
    }
    descriptions = {
        **FILTER_DESCRIPTIONS,
        "len": "Count a sized value locally.",
        "range": "Construct a bounded integer sequence with an exclusive stop.",
        "ctk": "Evaluate a console command string in the current session.",
    }
    for name, registered in signatures.items():
        function = (functions or {}).get(name)
        actual_parameters = ()
        if function is not None:
            try:
                actual_parameters = tuple(signature(function).parameters.values())
            except (TypeError, ValueError):
                pass
        # Registered signatures use CTK literals and a stable 'omitted' marker,
        # rather than leaking Python's private first/last sentinel address.
        inner = registered[1:-1]
        pipeline = registered if inner.startswith("*") else f"({inner.partition(', ')[2]})"
        arguments = [
            "Compiled/tree console callable; VALUE | stage(...) supplies VALUE as the first argument. Ordinary calls supply it explicitly.",
            *BUILTIN_ARGUMENTS[name],
        ]
        if name in {"map", "filter", "sort_by", "unique_by"}:
            arguments.append(
                "callback may be a named runnable, inline (item) EXPR, or trailing { (item) EXPR } block. Two or more required parameters unpack tuple items; a unary callback receives the whole item. See help pipes and help let."
            )
        arguments.append("Collection work and callbacks share execution and item budgets.")
        result[name] = CallableHelp(
            name=name,
            signature=f"{name}{registered}",
            definition=descriptions[name],
            origin="built-in",
            pipeline_signature=f"{name}{pipeline}",
            pipeline_parameters=_parameter_names(actual_parameters[1:]),
            parameter_names=_parameter_names(actual_parameters),
            arguments=tuple(arguments),
            examples=BUILTIN_EXAMPLES[name],
        )
    return result
