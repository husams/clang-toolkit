"""Local parameterized matcher definitions evaluated through the shared runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from lark import Tree

from .values import MatcherExpr

if TYPE_CHECKING:
    from .evaluator import Runtime


@dataclass(frozen=True)
class MatcherFunction:
    name: str
    parameters: tuple[str, ...]
    _body: Tree

    def __str__(self) -> str:
        return f"{self.name}({', '.join(self.parameters)})"

    def call(self, runtime: Runtime, arguments: list[Any]) -> MatcherExpr:
        from .evaluator import EvaluationError

        if len(arguments) != len(self.parameters):
            raise EvaluationError(
                f"{self.name} expects {len(self.parameters)} argument(s), got {len(arguments)}"
            )
        if runtime._matcher_call_depth >= 64:
            raise EvaluationError("parameterized matcher call depth exceeds 64")
        runtime._matcher_call_depth += 1
        runtime._scopes.append(dict(zip(self.parameters, arguments, strict=True)))
        try:
            value = runtime._evaluate(self._body)
            if not isinstance(value, MatcherExpr):
                raise EvaluationError(f"{self.name} must return a matcher expression")
            return value
        finally:
            runtime._scopes.pop()
            runtime._matcher_call_depth -= 1
