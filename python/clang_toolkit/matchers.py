"""Immutable composable Clang matcher expressions for the Python SDK.

The server remains the authority for matcher names, argument arity, and AST
node compatibility. This module only builds and safely serializes expressions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TypeAlias, Union

MatcherLiteral: TypeAlias = str | bool | int | float
MatcherArg: TypeAlias = Union[MatcherLiteral, "Matcher"]


def _literal(value: MatcherLiteral) -> str:
    if type(value) is str:
        if '"' not in value:
            quote = '"'
        elif "'" not in value:
            quote = "'"
        else:
            raise ValueError(
                "matcher strings containing both quote delimiters cannot be represented safely"
            )
        return f"{quote}{value}{quote}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("matcher numeric literals must be finite")
        return repr(value)
    raise TypeError(f"unsupported matcher argument: {type(value).__name__}")


@dataclass(frozen=True, init=False)
class Matcher:
    """An immutable matcher call tree with deterministic DSL serialization.

    ``Matcher`` intentionally accepts any server matcher name. It does not
    claim compile-time validation of Clang matcher node types.
    """

    name: str
    arguments: tuple[MatcherArg, ...]
    binding: str | None

    def __init__(self, name: str, *arguments: MatcherArg, binding: str | None = None) -> None:
        if type(name) is not str or not name or not name.isidentifier():
            raise ValueError("matcher name must be a nonempty identifier")
        if binding is not None and (type(binding) is not str or not binding):
            raise ValueError("binding name must be a nonempty string")
        for argument in arguments:
            if type(argument) not in (str, bool, int, float, Matcher):
                raise TypeError(f"unsupported matcher argument: {type(argument).__name__}")
            if isinstance(argument, float) and not math.isfinite(argument):
                raise ValueError("matcher numeric literals must be finite")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "arguments", tuple(arguments))
        object.__setattr__(self, "binding", binding)

    def bind(self, name: str) -> Matcher:
        """Return a copy that binds matched nodes under *name*."""
        if type(name) is not str or not name:
            raise ValueError("binding name must be a nonempty string")
        return Matcher(self.name, *self.arguments, binding=name)

    def to_query(self) -> str:
        """Serialize this expression as deterministic matcher DSL text."""
        args = ", ".join(
            arg.to_query() if isinstance(arg, Matcher) else _literal(arg)
            for arg in self.arguments
        )
        query = f"{self.name}({args})"
        if self.binding is not None:
            query += f".bind({_literal(self.binding)})"
        return query

    def __str__(self) -> str:
        return self.to_query()


MatcherInput: TypeAlias = str | Matcher


def matcher_query(value: MatcherInput) -> str:
    """Normalize an SDK matcher argument; reject implicit object stringification."""
    if type(value) is Matcher:
        return value.to_query()
    if type(value) is str:
        return value
    raise TypeError("matcher must be a string or Matcher")


# Common matcher factories use the original Clang AST matcher spelling. Their
# precise signatures catch common API mistakes; generic Matcher remains the
# escape hatch for other names and overload shapes. Clang validates semantics.
def functionDecl(*predicates: Matcher) -> Matcher: return Matcher("functionDecl", *predicates)
def cxxMethodDecl(*predicates: Matcher) -> Matcher: return Matcher("cxxMethodDecl", *predicates)
def cxxConstructorDecl(*predicates: Matcher) -> Matcher: return Matcher("cxxConstructorDecl", *predicates)
def cxxRecordDecl(*predicates: Matcher) -> Matcher: return Matcher("cxxRecordDecl", *predicates)
def recordDecl(*predicates: Matcher) -> Matcher: return Matcher("recordDecl", *predicates)
def varDecl(*predicates: Matcher) -> Matcher: return Matcher("varDecl", *predicates)
def parmVarDecl(*predicates: Matcher) -> Matcher: return Matcher("parmVarDecl", *predicates)
def fieldDecl(*predicates: Matcher) -> Matcher: return Matcher("fieldDecl", *predicates)
def decl(*predicates: Matcher) -> Matcher: return Matcher("decl", *predicates)
def declRefExpr(*predicates: Matcher) -> Matcher: return Matcher("declRefExpr", *predicates)
def callExpr(*predicates: Matcher) -> Matcher: return Matcher("callExpr", *predicates)
def cxxMemberCallExpr(*predicates: Matcher) -> Matcher: return Matcher("cxxMemberCallExpr", *predicates)
def memberExpr(*predicates: Matcher) -> Matcher: return Matcher("memberExpr", *predicates)
def cxxConstructExpr(*predicates: Matcher) -> Matcher: return Matcher("cxxConstructExpr", *predicates)
def binaryOperator(*predicates: Matcher) -> Matcher: return Matcher("binaryOperator", *predicates)
def integerLiteral(*predicates: Matcher) -> Matcher: return Matcher("integerLiteral", *predicates)
def floatLiteral(*predicates: Matcher) -> Matcher: return Matcher("floatLiteral", *predicates)
def cxxBoolLiteral(*predicates: Matcher) -> Matcher: return Matcher("cxxBoolLiteral", *predicates)
def stringLiteral(*predicates: Matcher) -> Matcher: return Matcher("stringLiteral", *predicates)
def stmt(*predicates: Matcher) -> Matcher: return Matcher("stmt", *predicates)
def expr(*predicates: Matcher) -> Matcher: return Matcher("expr", *predicates)
def equals(value: MatcherLiteral) -> Matcher: return Matcher("equals", value)
def hasName(name: str) -> Matcher: return Matcher("hasName", name)
def hasType(predicate: Matcher) -> Matcher: return Matcher("hasType", predicate)
def returns(predicate: Matcher) -> Matcher: return Matcher("returns", predicate)
def qualType(*arguments: MatcherArg) -> Matcher: return Matcher("qualType", *arguments)
def pointerType(*arguments: MatcherArg) -> Matcher: return Matcher("pointerType", *arguments)
def referenceType(*arguments: MatcherArg) -> Matcher: return Matcher("referenceType", *arguments)
def hasDeclaration(predicate: Matcher) -> Matcher: return Matcher("hasDeclaration", predicate)
def hasArgument(index: int, predicate: Matcher) -> Matcher: return Matcher("hasArgument", index, predicate)
def hasParameter(index: int, predicate: Matcher) -> Matcher: return Matcher("hasParameter", index, predicate)
def hasAnyArgument(predicate: Matcher) -> Matcher: return Matcher("hasAnyArgument", predicate)
def hasDescendant(predicate: Matcher) -> Matcher: return Matcher("hasDescendant", predicate)
def hasAncestor(predicate: Matcher) -> Matcher: return Matcher("hasAncestor", predicate)
def hasParent(predicate: Matcher) -> Matcher: return Matcher("hasParent", predicate)
def callee(predicate: Matcher) -> Matcher: return Matcher("callee", predicate)
def to(predicate: Matcher) -> Matcher: return Matcher("to", predicate)
def hasAnyBase(predicate: Matcher) -> Matcher: return Matcher("hasAnyBase", predicate)
def cxxBaseSpecifier(*arguments: MatcherArg) -> Matcher: return Matcher("cxxBaseSpecifier", *arguments)
def recordType(*arguments: MatcherArg) -> Matcher: return Matcher("recordType", *arguments)
def isDefinition() -> Matcher: return Matcher("isDefinition")
def isExpansionInMainFile() -> Matcher: return Matcher("isExpansionInMainFile")
def isImplicit() -> Matcher: return Matcher("isImplicit")
def forEachDescendant(*predicates: Matcher) -> Matcher: return Matcher("forEachDescendant", *predicates)
def allOf(*predicates: Matcher) -> Matcher: return Matcher("allOf", *predicates)
def anyOf(*predicates: Matcher) -> Matcher: return Matcher("anyOf", *predicates)
def unless(predicate: Matcher) -> Matcher: return Matcher("unless", predicate)


__all__ = [
    "Matcher", "MatcherArg", "MatcherInput", "MatcherLiteral", "matcher_query",
    "functionDecl", "cxxMethodDecl", "cxxConstructorDecl", "cxxRecordDecl",
    "recordDecl", "varDecl", "parmVarDecl", "fieldDecl", "decl", "declRefExpr", "callExpr",
    "cxxMemberCallExpr", "memberExpr", "cxxConstructExpr", "binaryOperator", "integerLiteral",
    "floatLiteral", "cxxBoolLiteral", "stringLiteral", "stmt", "expr", "equals",
    "hasName", "hasType", "returns",
    "qualType", "pointerType", "referenceType", "hasDeclaration",
    "hasArgument", "hasParameter", "hasAnyArgument", "hasDescendant", "hasAncestor", "hasParent",
    "callee", "to", "hasAnyBase", "cxxBaseSpecifier", "recordType", "isDefinition",
    "isExpansionInMainFile", "isImplicit",
    "forEachDescendant", "allOf", "anyOf", "unless",
]
