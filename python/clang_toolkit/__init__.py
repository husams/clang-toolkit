"""Python API for the clang-toolkit server."""

from clang_toolkit.client import AsyncClient, Client, QueryError, QuerySession
from clang_toolkit.configuration import ConfigurationError, NetworkConfig, load_network_config
from clang_toolkit.cursors import CursorError
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit.control_flow import CfgOptions
from clang_toolkit.matchers import (
    Matcher, MatcherArg, MatcherInput, MatcherLiteral, allOf, anyOf, binaryOperator, callExpr, cxxBoolLiteral, cxxConstructExpr,
    cxxConstructorDecl, cxxMemberCallExpr, cxxMethodDecl, cxxRecordDecl,
    decl, declRefExpr, equals, expr, fieldDecl, floatLiteral, forEachDescendant, functionDecl, hasAncestor,
    hasAnyArgument, hasAnyBase, hasArgument, hasDeclaration, hasDescendant, hasName,
    hasParameter, hasParent, hasType, integerLiteral, isDefinition,
    isExpansionInMainFile, isImplicit, memberExpr, parmVarDecl, pointerType,
    qualType, recordDecl, recordType, referenceType, returns, stmt, stringLiteral,
    to, unless, varDecl, callee, cxxBaseSpecifier,
)
from clang_toolkit.match_values import (
    BindingSelection, MatchRow, MatchValue, MatchValueError, NativeBindingCollection,
    NativeMatchCollection, ParsedTree,
)

__all__ = [
    "AnalysisError",
    "AsyncClient",
    "Client",
    "CfgOptions",
    "BindingSelection",
    "MatchRow",
    "MatchValue",
    "NativeMatchCollection",
    "MatchValueError",
    "NativeBindingCollection",
    "ParsedTree",
    "ConfigurationError",
    "CursorError",
    "NetworkConfig",
    "QueryError",
    "QuerySession",
    "load_network_config",
    "Matcher", "MatcherArg", "MatcherInput", "MatcherLiteral",
    "functionDecl", "cxxMethodDecl", "cxxConstructorDecl",
    "cxxRecordDecl", "recordDecl", "varDecl", "parmVarDecl", "fieldDecl",
    "decl", "declRefExpr", "callExpr", "cxxMemberCallExpr", "memberExpr", "cxxConstructExpr",
    "binaryOperator", "integerLiteral", "floatLiteral", "cxxBoolLiteral", "equals",
    "stringLiteral", "stmt", "expr",
    "hasName", "hasType", "returns", "qualType", "pointerType", "referenceType",
    "hasDeclaration", "hasArgument", "hasParameter", "hasAnyArgument",
    "hasDescendant", "hasAncestor", "hasParent", "callee", "to", "hasAnyBase",
    "cxxBaseSpecifier", "recordType", "isDefinition", "isExpansionInMainFile",
    "isImplicit", "forEachDescendant",
    "allOf", "anyOf", "unless",
]
__version__ = "0.1.0"
