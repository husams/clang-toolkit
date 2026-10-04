"""Small, offline matcher catalog for interactive completion."""

from __future__ import annotations

NESTED_MATCHERS: tuple[str, ...] = (
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

# Node matchers accepted as the root of `match ...` and `let name = ...`.
ROOT_MATCHERS: tuple[str, ...] = (
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

# A root node matcher remains useful inside nested expressions as well.
NESTED_MATCHERS = tuple(sorted(set(NESTED_MATCHERS).union(ROOT_MATCHERS)))

# Backwards-compatible alias for callers that imported the earlier catalog.
DEFAULT_MATCHERS = NESTED_MATCHERS
