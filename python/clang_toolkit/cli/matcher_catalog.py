"""Offline matcher names used by console completion and local validation."""

from __future__ import annotations

from ._matcher_catalog_generated import (
    LLVM_VERSION,
    NESTED_MATCHERS,
    ROOT_MATCHERS,
)

# Keep the original narrow validation sets stable. The server's dynamic
# registry remains authoritative for names outside this legacy local guard.
VALIDATION_ROOT_MATCHERS: tuple[str, ...] = (
    "binaryOperator",
    "callExpr",
    "compoundStmt",
    "cxxConstructorDecl",
    "cxxConversionDecl",
    "cxxDestructorDecl",
    "cxxMethodDecl",
    "cxxRecordDecl",
    "declRefExpr",
    "fieldDecl",
    "forStmt",
    "functionDecl",
    "ifStmt",
    "integerLiteral",
    "memberExpr",
    "namespaceDecl",
    "parmVarDecl",
    "returnStmt",
    "varDecl",
)

_VALIDATION_NESTED_ONLY: tuple[str, ...] = (
    "allOf",
    "anyOf",
    "argumentCountIs",
    "callExpr",
    "callee",
    "cxxConstructorDecl",
    "cxxConversionDecl",
    "cxxDestructorDecl",
    "cxxMethodDecl",
    "cxxRecordDecl",
    "declRefExpr",
    "forEachDescendant",
    "forEach",
    "functionDecl",
    "hasAncestor",
    "hasAnyArgument",
    "hasArgument",
    "hasDescendant",
    "hasMethod",
    "hasName",
    "hasParent",
    "hasType",
    "ifStmt",
    "isDefinition",
    "isExpansionInMainFile",
    "isPublic",
    "matchesName",
    "parameterCountIs",
    "pointerType",
    "ofClass",
    "returnStmt",
    "returns",
    "to",
    "unless",
    "varDecl",
)

VALIDATION_NESTED_MATCHERS: tuple[str, ...] = tuple(
    sorted(set(_VALIDATION_NESTED_ONLY).union(VALIDATION_ROOT_MATCHERS))
)

# Backwards-compatible alias for callers that imported the earlier catalog.
DEFAULT_MATCHERS = NESTED_MATCHERS

__all__ = [
    "DEFAULT_MATCHERS",
    "LLVM_VERSION",
    "NESTED_MATCHERS",
    "ROOT_MATCHERS",
    "VALIDATION_NESTED_MATCHERS",
    "VALIDATION_ROOT_MATCHERS",
]
