"""Grammar token styles shared by single-line and multiline REPL input."""

from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import lex, parser as parser

KEYWORDS = {
    "PARSE",
    "YIELD",
    "LET",
    "MATCH",
    "CFG",
    "CALLGRAPH",
    "HELP",
    "QUIT",
    "EXIT",
    "TRAVERSE",
    "OPTION",
    "FUNCTIONS",
    "BLOCKS",
    "ELEMENTS",
    "EDGES",
    "DEPTH",
    "NODES",
    "IMPLICIT",
    "INSTANTIATIONS",
    "SCRIPT",
    "PRINT",
    "FOREACH",
    "IN",
    "DO",
    "DONE",
    "GLOB",
    "SET",
    "CLEAR",
    "ADD",
    "EXTRA_ARG",
    "EXTRA_ARGS",
    "TRAVERSAL",
    "CACHE_DIR",
    "FILES",
    "OUTPUT",
    "STDOUT",
    "SAVE",
    "LOAD",
    "TO",
    "AS",
    "INTO",
    "USER",
    "HISTORY",
    "SESSION",
    "LIST",
    "ATTACH",
    "SERVER",
    "STATUS",
    "CACHE",
    "PRUNE",
    "BINDINGS",
    "BINDING",
    "DROP",
    "RENAME",
    "APPEND",
    "CURSOR",
    "OPEN",
    "CONTINUE",
    "RESTART",
    "ROW",
    "CURSOR_SCOPE",
    "REVISION",
    "LABEL",
    "MODE",
    "REPLACE",
    "JOIN_WITH",
}
TOKEN_STYLES = {
    **{kind: "keyword" for kind in KEYWORDS},
    "FILES_EXPR": "keyword",
    "ROOT_MATCHER_NAME": "matcher",
    "MATCHER_NAME": "matcher",
    "STRING": "string",
    "FILE_STRING": "string",
    "DIRECTORY_STRING": "string",
    "PATH_STRING": "string",
    "HELP_SHORT_TOPIC": "keyword",
    "HELP_WORD": "keyword",
    "QUESTION": "punctuation",
    "OPEN_STRING": "string",
    "NUMBER": "number",
    "TRUE": "value",
    "FALSE": "value",
    "BIND": "bind",
    "ERROR": "error",
    "EQUAL": "operator",
    **{
        kind: "punctuation"
        for kind in (
            "LPAR",
            "RPAR",
            "LSQB",
            "RSQB",
            "LBRACE",
            "RBRACE",
            "COMMA",
            "DOT",
            "SEMICOLON",
        )
    },
}
STYLE = Style.from_dict(
    {
        "keyword": "bold ansiblue",
        "matcher": "ansicyan",
        "bind": "ansimagenta",
        "reference": "ansiyellow",
        "variable": "ansiyellow",
        "string": "ansigreen",
        "number": "ansibrightmagenta",
        "value": "ansiyellow",
        "punctuation": "ansibrightblack",
        "operator": "bold ansiwhite",
        "error": "bg:ansired ansiwhite",
    }
)


# Workspace-only syntax palette; chrome and the standard prompt keep their styles.
WORKSPACE_SYNTAX = {
    "keyword": "bold #ff7896",
    "matcher": "#b8a1ef",
    "matcher-root": "#82adff",
    "matcher-predicate": "#a3d36b",
    "reference": "#79c6bc",
    "variable": "#79c6bc",
    "string": "#e6c47d",
    "number": "#f1a875",
    "value": "#ffd580",
    "boolean": "italic #f1a875",
    "operator": "bold #c7d5ee",
    "punctuation": "#90a4b4",
    "comment": "italic #748999",
    "bind": "#b8a1ef",
}


def matcher_style(name: str, *, root: bool) -> str:
    """Differentiate node matchers, predicates and traversal/combinator calls."""
    traversal = {
        "hasDeclaration",
        "hasType",
        "hasObjectExpression",
        "hasReceiverType",
        "hasReturnType",
        "hasArgument",
        "hasAnyArgument",
        "hasDescendant",
        "hasAncestor",
        "hasParent",
        "has",
        "to",
        "member",
        "callee",
        "forEach",
        "forEachDescendant",
        "forEachAncestor",
        "forEachArgumentWithParam",
    }
    if name in traversal or name in {
        "anyOf",
        "allOf",
        "eachOf",
        "unless",
        "optionally",
    }:
        return "matcher"
    if name.startswith(("has", "is", "matches", "equals", "contains")):
        return "matcher-predicate"
    if root or name.endswith(("Decl", "Expr", "Stmt", "Type", "TypeLoc")):
        return "matcher-root"
    return "matcher"


def highlight(
    text: str, *, semantic_matchers: bool = False, batch: bool = False
) -> StyleAndTextTuples:
    """Preserve every character while assigning styles from grammar tokens."""
    tokens = lex(text, batch=batch)
    next_types = [""] * len(tokens)
    next_type = ""
    for index in range(len(tokens) - 1, -1, -1):
        next_types[index] = next_type
        if tokens[index].type != "WS":
            next_type = tokens[index].type
    fragments: StyleAndTextTuples = []
    in_reference = False
    previous = ""
    for index, token in enumerate(tokens):
        kind = token.type
        if kind != "WS":
            in_reference = kind == "DOLLAR" or (
                in_reference and kind in {"NAME", "DOT"}
            )
        style = TOKEN_STYLES.get(kind, "")
        if kind != "WS" and in_reference:
            style = "reference"
        elif kind == "NAME":
            if previous == "LET":
                style = "variable"
            elif next_types[index] == "LPAR":
                style = "matcher"
            else:
                style = "value"
        if semantic_matchers:
            if style == "matcher":
                style = matcher_style(str(token), root=kind == "ROOT_MATCHER_NAME")
            elif kind in {"TRUE", "FALSE"}:
                style = "boolean"
            elif kind == "COMMENT":
                style = "comment"
        fragments.append((f"class:{style}" if style else "", str(token)))
        if kind != "WS":
            previous = kind
    return fragments


class ReplLexer(Lexer):
    def __init__(self, *, semantic_matchers: bool = False) -> None:
        self.semantic_matchers = semantic_matchers

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        # Lex once for the whole document so strings/references retain context.
        lines: list[StyleAndTextTuples] = [[]]
        try:
            parser().parse(document.text)
            batch = False
        except UnexpectedInput:
            batch = True
        for fragment in highlight(
            document.text, semantic_matchers=self.semantic_matchers, batch=batch
        ):
            style, text = fragment[0], fragment[1]
            for index, part in enumerate(text.split("\n")):
                if index:
                    lines.append([])
                if part:
                    lines[-1].append((style, part))
        return lambda lineno: lines[lineno] if 0 <= lineno < len(lines) else []
