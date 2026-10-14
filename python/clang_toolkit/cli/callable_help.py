"""Source-backed descriptions of locally defined console callables."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class CallableHelp:
    name: str
    signature: str
    definition: str

    @property
    def hint(self) -> str:
        return f"user defined · {self.signature}"

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

        return "\n\n".join(
            (
                f"## {self.name}",
                "User defined expression.",
                "### Signature",
                code(self.signature),
                "### Definition",
                code(self.definition),
            )
        )

    def plain(self) -> str:
        return f"{self.name}: User defined expression.\nSignature:\n  {self.signature}\nDefinition:\n{self.definition}"


def describe_callable(name: str, value: Any) -> CallableHelp:
    """Keep defaults as written, without evaluating the function or its body."""
    parameters = list(value.parameters)
    for default in getattr(value, "default_nodes", ()):
        if default.source_span is not None:
            start, end = default.source_span
            parameters[parameters.index(default.value)] = value.source[start:end]
    return CallableHelp(name, f"{name}({', '.join(parameters)})", value.definition)
