"""Grammar token styles shared by single-line and multiline REPL input."""

from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style

from clang_toolkit.cli.language import lex, parser as parser

KEYWORDS = {
    "LET",
    "MATCH",
    "CFG",
    "CALLGRAPH",
    "HELP",
    "QUIT",
    "EXIT",
    "TRAVERSE",
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
    "LABEL",
    "MODE",
    "REPLACE",
    "JOIN_WITH",
}
TOKEN_STYLES = {
    **{kind: "keyword" for kind in KEYWORDS},
    "ROOT_MATCHER_NAME": "matcher",
    "MATCHER_NAME": "matcher",
    "STRING": "string",
    "OPEN_STRING": "string",
    "NUMBER": "number",
    "TRUE": "value",
    "FALSE": "value",
    "BIND": "bind",
    "ERROR": "error",
    "EQUAL": "operator",
    **{
        kind: "punctuation"
        for kind in ("LPAR", "RPAR", "LSQB", "RSQB", "LBRACE", "RBRACE", "COMMA", "DOT")
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


def highlight(text: str) -> StyleAndTextTuples:
    """Preserve every character while assigning styles from grammar tokens."""
    tokens = lex(text)
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
        fragments.append((f"class:{style}" if style else "", str(token)))
        if kind != "WS":
            previous = kind
    return fragments


class ReplLexer(Lexer):
    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        # Lex once for the whole document so strings/references retain context.
        lines: list[StyleAndTextTuples] = [[]]
        for style, text in highlight(document.text):
            for index, part in enumerate(text.split("\n")):
                if index:
                    lines.append([])
                if part:
                    lines[-1].append((style, part))
        return lambda lineno: lines[lineno] if 0 <= lineno < len(lines) else []
