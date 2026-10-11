"""Rich Markdown rendered into prompt_toolkit's scrollable, styled text buffer."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import ANSI, StyleAndTextTuples, to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_to_text, split_lines
from prompt_toolkit.lexers import Lexer as PromptLexer
from prompt_toolkit.widgets import TextArea
from pygments.lexer import Lexer
from pygments.token import Token
from rich.console import Console, ConsoleOptions, RenderResult
from rich.markdown import CodeBlock, Markdown
from rich.style import Style as RichStyle
from rich.syntax import Syntax, SyntaxTheme
from rich.theme import Theme

from clang_toolkit.cli.highlight import WORKSPACE_SYNTAX, highlight


class CtkLexer(Lexer):
    kinds = {
        "class:keyword": Token.Keyword,
        "class:matcher": Token.Name.Function,
        "class:matcher-root": Token.Name.Class,
        "class:matcher-predicate": Token.Name.Decorator,
        "class:boolean": Token.Keyword.Constant,
        "class:comment": Token.Comment,
        "class:bind": Token.Name.Tag,
        "class:reference": Token.Name.Variable,
        "class:variable": Token.Name.Variable,
        "class:string": Token.Literal.String,
        "class:number": Token.Literal.Number,
        "class:value": Token.Literal,
        "class:punctuation": Token.Punctuation,
        "class:operator": Token.Operator,
    }

    def get_tokens_unprocessed(self, text: str) -> Iterator[tuple[int, Any, str]]:
        offset = 0
        for fragment in highlight(text, semantic_matchers=True, batch=True):
            style, value = fragment[0], fragment[1]
            yield offset, self.kinds.get(style, Token.Text), value
            offset += len(value)


class CtkSyntaxTheme(SyntaxTheme):
    """Use the editor's syntax palette in rendered Markdown examples as well."""

    def get_style_for_token(self, token_type: Any) -> RichStyle:
        for kind, token in CtkLexer.kinds.items():
            if token_type == token:
                return RichStyle.parse(WORKSPACE_SYNTAX[kind.removeprefix("class:")])
        return RichStyle(color="#d8dee9")

    def get_background_style(self) -> RichStyle:
        return RichStyle(bgcolor="#182a38")


class CtkCodeBlock(CodeBlock):
    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        if self.lexer_name in {"ctk", "ctk-numbered"}:
            yield Syntax(
                str(self.text).rstrip(),
                CtkLexer(),
                theme=CtkSyntaxTheme(),
                background_color="#182a38",
                word_wrap=self.lexer_name != "ctk-numbered",
                line_numbers=self.lexer_name == "ctk-numbered",
                padding=0 if self.lexer_name == "ctk-numbered" else 1,
            )
        else:
            yield from super().__rich_console__(console, options)


class WorkspaceMarkdown(Markdown):
    elements = {**Markdown.elements, "fence": CtkCodeBlock, "code_block": CtkCodeBlock}


class RenderedMarkdownLexer(PromptLexer):
    def __init__(self) -> None:
        self.lines: list[StyleAndTextTuples] = []

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        lines = self.lines
        return lambda number: lines[number] if 0 <= number < len(lines) else []


class MarkdownPanel(TextArea):
    def __init__(self) -> None:
        self.markdown_lexer = RenderedMarkdownLexer()
        self.render_key: tuple[str, int] | None = None
        super().__init__(
            read_only=True,
            focus_on_click=True,
            scrollbar=True,
            lexer=self.markdown_lexer,
            wrap_lines=False,
        )

    def set_markdown(self, markdown: str, width: int = 32) -> None:
        key = (markdown, width)
        if key == self.render_key:
            return
        text, lines = render_markdown(markdown, width)
        self.markdown_lexer.lines = lines
        self.buffer.set_document(
            Document(text, min(self.buffer.cursor_position, len(text))),
            bypass_readonly=True,
        )
        self.render_key = key


def render_markdown(markdown: str, width: int) -> tuple[str, list[StyleAndTextTuples]]:
    """Render Rich markup to searchable plain text and matching style fragments."""
    console = Console(
        force_terminal=True,
        no_color=False,
        color_system="256",
        width=max(12, width),
        height=10000,
        highlight=False,
        theme=Theme(
            {
                "markdown.h1": "bold #62b3ff",
                "markdown.h2": "bold #62b3ff",
                "markdown.code": "#ffd580 on #182a38",
                "markdown.item.bullet": "#8adf87",
            }
        ),
    )
    with console.capture() as capture:
        console.print(WorkspaceMarkdown(markdown, hyperlinks=False))
    fragments = to_formatted_text(ANSI(capture.get()))
    text = fragment_list_to_text(fragments)
    return text, list(split_lines(fragments))
