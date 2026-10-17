"""Source diagnostics and display mappings used by the result code blocks."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import Mock

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text.utils import fragment_list_to_text
from prompt_toolkit.input import PipeInput
from prompt_toolkit.layout.processors import TransformationInput
from prompt_toolkit.utils import get_cwidth

from clang_toolkit.cli.app import DispatchResult, dispatch_result
from clang_toolkit.cli.highlight import highlight
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.prototype.repl_editor import PrototypeReplLexer
from clang_toolkit.cli.workspace import WorkspaceConsole
from clang_toolkit.cli.workspace_transcript import (
    CodeRows,
    ErrorSpan,
    StyledBlock,
    TranscriptLexer,
    command_block,
    error_span,
)
from clang_toolkit.client import Client
from test_workspace import interact, wait_until


@pytest.mark.parametrize(
    "output,success,expected",
    [
        ('{"nested":{"count":3}}', True, '"count": 3'),
        ("Server status\nActive sessions  2", True, "Active sessions  2"),
        ("## literal\n```\n<source>\n```", True, "## literal"),
        ("error: command failed", False, "error: command failed"),
    ],
)
def test_other_command_results_are_formatted_literal_markdown(
    tmp_path: Path, output: str, success: bool, expected: str,
) -> None:
    async def execute(source: str) -> DispatchResult:
        return DispatchResult(output, success)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("print 7\n")
        await wait_until(lambda: not ui.busy and expected in ui.results.text)
        assert ui.transcript_lexer.blocks
        block = ui.transcript_lexer.blocks[-1]
        assert expected in block.text
        assert any("bg:" in fragment[0] for line in block.lines for fragment in line)

    asyncio.run(interact(tmp_path, drive, execute=execute))


@pytest.mark.parametrize(
    ("source", "message", "expected"),
    [
        (
            ";et x = 1",
            "syntax error at line 1, column 1: unexpected `;`",
            ErrorSpan(1, 1),
        ),
        (
            "let x = [\n  $missing\n]",
            "error: unknown variable: missing",
            ErrorSpan(2, 3, 8),
        ),
        (
            "print $xs[0]",
            "error: value does not support indexing at [0] (line 1, column 10)",
            ErrorSpan(1, 10),
        ),
        (
            "let x = [",
            "syntax error at line 1, column 10: unexpected end of input",
            ErrorSpan(1, 10),
        ),
        ("print [$a, $a]", "error: unknown variable: a", None),
        ("match foo()", "error: 1:7: Matcher not found: foo", None),
        ("print 1", "error: /source.cpp:1:2: header not found", None),
        ("print 1", "error: failure (line 30, column 90)", None),
    ],
)
def test_mark_only_unambiguous_script_locations(
    source: str, message: str, expected: ErrorSpan | None
) -> None:
    assert error_span(source, message) == expected


def test_marked_block_retains_multiline_context_and_underlines_the_token() -> None:
    source = "let x = [\n  $missing\n]"
    block = command_block(source, ErrorSpan(2, 3, 8))
    document = Document(block)
    render = TranscriptLexer().lex_document(document)
    marker = next(i for i, line in enumerate(document.lines) if "^" in line)
    assert document.lines[marker].index("^") == document.lines[marker - 1].index("$")
    marked = [
        (style, text) for style, text in render(marker - 1) if "underline" in style
    ]
    assert "".join(text for _, text in marked) == "$missing"
    assert all("class:diagnostic" in style for style, _ in marked)
    assert "CTK command" not in block and "ctk>" not in block
    assert "  3 │ ]" in block


@pytest.mark.parametrize("width", [18, 27, 60])
def test_code_rows_wrap_and_fill_without_changing_search_source(width: int) -> None:
    document = Document(command_block('print "' + "界" * 20 + 'TAIL"'))
    fragments = TranscriptLexer().lex_document(document)(0)
    ti = TransformationInput(Mock(), document, 0, lambda i: i, fragments, width, 20)
    transformed = CodeRows(lambda: True).apply_transformation(ti)
    text = fragment_list_to_text(transformed.fragments)
    assert "TAIL" in text
    assert get_cwidth(text) % width == 0
    assert "     │ " in text if width < 60 else True
    assert all("class:code" in fragment[0] for fragment in transformed.fragments)
    for index in range(len(document.lines[0]) + 1):
        assert (
            transformed.display_to_source(transformed.source_to_display(index)) == index
        )
    assert "     │ " not in document.text


def test_transcript_uses_active_compiled_lexer_for_completed_code() -> None:
    source = "let x = 1\nlet y = if $x > 0 then $x * 10 + 1 else 1"
    text = command_block(source)
    lexer = TranscriptLexer(PrototypeReplLexer()).lex_document(Document(text))

    operator_styles = {
        token: style for style, token in lexer(1) if token in {">", "*", "+"}
    }
    assert set(operator_styles) == {">", "*", "+"}
    assert all("class:operator" in style for style in operator_styles.values())
    assert all("class:error" not in style for style in operator_styles.values())
    assert any(
        style.endswith("class:keyword")
        for style, token in lexer(1)
        if token == "then"
    )

    legacy = TranscriptLexer().lex_document(Document(command_block("let y = 1 + 2")))
    assert any("class:error" in style for style, token in legacy(0) if token == "+")


def test_stored_transcript_styles_override_active_lexer_across_lines() -> None:
    text = command_block("let y = 1 +\n2")
    styled = [
        [("class:code class:stored", line)]
        for line in text.splitlines()
    ]
    transcript = TranscriptLexer(PrototypeReplLexer())
    transcript.blocks.append(StyledBlock(0, text, styled))

    lines = transcript.lex_document(Document(text))
    assert all("class:stored" in style for style, _ in lines(0))
    assert all("class:stored" in style for style, _ in lines(1))


def test_workspace_syntax_roles_distinguish_commands_matchers_and_literals() -> None:
    fragments = highlight(
        'match memberExpr(member(hasName("first")))', semantic_matchers=True
    )
    styles = {text: style for style, text in fragments if text.strip()}
    assert (
        len(
            {
                styles["match"],
                styles["memberExpr"],
                styles["hasName"],
                styles['"first"'],
            }
        )
        == 4
    )
    assert (
        dict((text, style) for style, text in highlight('let list = files "*.cpp"'))[
            "files"
        ]
        == "class:keyword"
    )
    assert ("class:boolean", "true") in highlight("print true", semantic_matchers=True)


def test_actual_parser_and_runtime_errors_mark_the_submitted_block(
    tmp_path: Path,
) -> None:
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path)

    async def execute(source: str):
        return dispatch_result(runtime.client, source, runtime)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        for source, expected in [(";et x = 1", ";"), ("print $missing", "$missing")]:
            ui.clear_results()
            pipe.send_text(source + "\n")
            await wait_until(
                lambda: ui.status == "Command failed" and "^" in ui.results.text
            )
            assert ui.results.text.count(source) == 1
            document = ui.results.buffer.document
            rendered = TranscriptLexer().lex_document(document)
            assert any(
                expected
                in "".join(
                    text for style, text in rendered(index) if "underline" in style
                )
                for index in range(len(document.lines))
            )
            assert ui.buffer.text == ""
            ui.status = "Ready"

    try:
        asyncio.run(interact(tmp_path, drive, execute=execute))
    finally:
        runtime.close()


def test_error_marker_keeps_a_readers_cursor_on_the_same_source_character(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        release = asyncio.Event()

        async def execute(source: str):
            await release.wait()
            from clang_toolkit.cli.app import DispatchResult

            return DispatchResult("error: unknown variable: missing", False)

        async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
            source = "let x = [\n  $missing\n]"
            pipe.send_text("\x1b[200~" + source + "\x1b[201~\n")
            await wait_until(lambda: ui.busy and "  3 │ ]" in ui.results.text)
            ui.follow = False
            ui.results.buffer.cursor_position = ui.results.text.rindex("]")
            assert ui.results.buffer.document.current_char == "]"
            release.set()
            await wait_until(lambda: not ui.busy and "^" in ui.results.text)
            assert ui.results.buffer.document.current_char == "]"
            assert not ui.follow

        await interact(tmp_path, drive, execute=execute)

    asyncio.run(run())


def test_all_workspace_syntax_roles_have_distinct_colors_and_match_rich() -> None:
    from clang_toolkit.cli.highlight import WORKSPACE_SYNTAX
    from clang_toolkit.cli.workspace_markdown import CtkLexer, CtkSyntaxTheme

    source = 'let x = addrLabelExpr(hasDeclaration(labelDecl(hasName("done"))))'
    styled = {text: style for style, text in highlight(source, semantic_matchers=True)}
    assert styled["addrLabelExpr"] == styled["labelDecl"] == "class:matcher-root"
    assert styled["hasDeclaration"] == "class:matcher"
    assert styled["hasName"] == "class:matcher-predicate"
    roles = [
        "let",
        "x",
        "=",
        "addrLabelExpr",
        "hasDeclaration",
        "hasName",
        '"done"',
        "(",
    ]
    assert len(
        {WORKSPACE_SYNTAX[styled[text].removeprefix("class:")] for text in roles}
    ) == len(roles)
    rich_tokens = list(CtkLexer().get_tokens_unprocessed(source))
    theme = CtkSyntaxTheme()
    for _, token, text in rich_tokens:
        if text in roles:
            assert theme.get_style_for_token(token).color is not None
    assert len(
        {
            theme.get_style_for_token(token).color
            for _, token, text in rich_tokens
            if text in roles
        }
    ) == len(roles)


def test_rendered_help_survives_append_error_markers_trim_and_clear(
    tmp_path: Path,
) -> None:
    from clang_toolkit.cli.workspace_output import MAX_TRANSCRIPT_CHARS

    runtime = Runtime(Mock(spec=Client), cwd=tmp_path)

    async def execute(source: str):
        return dispatch_result(runtime.client, source, runtime)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.clear_results()
        # A near-full transcript exercises both offset shifting and eviction.
        ui.write("old output\n" * (MAX_TRANSCRIPT_CHARS // 11))
        for command in ["help parse", "parse?", "help match"]:
            pipe.send_text(command + "\n")
            await wait_until(
                lambda: not ui.busy and not ui.buffer.text and ui.last_source == command
            )
        assert "Usage:" not in ui.results.text
        assert "###" not in ui.results.text and "```" not in ui.results.text
        assert "`" not in ui.results.text
        assert "Examples" in ui.results.text
        assert "\x1b" not in ui.results.text
        assert ui.transcript_lexer.blocks
        blocks = list(ui.transcript_lexer.blocks)
        pipe.send_text("print $missing\n")
        await wait_until(lambda: "unknown variable" in ui.results.text)
        lines = ui.transcript_lexer.lex_document(ui.results.buffer.document)
        for block in blocks:
            assert ui.results.text.startswith(block.text, block.start)
            first, _ = ui.results.buffer.document.translate_index_to_position(
                block.start
            )
            assert any("bold" in style for style, _ in lines(first))
            assert any(
                len({style for style, text in fragments if text.strip()}) >= 3
                for fragments in block.lines
            )
        ui.clear_results()
        assert not ui.transcript_lexer.blocks and not ui.results.text

    asyncio.run(interact(tmp_path, drive, execute=execute))


def test_help_examples_retain_keyword_colors_across_commands() -> None:
    from pygments.token import Token
    from clang_toolkit.cli.workspace_markdown import CtkLexer

    source = 'parse "first.cpp"\nlet tree = parse "second.cpp"'
    tokens = list(CtkLexer().get_tokens_unprocessed(source))
    assert [value for _, kind, value in tokens if kind == Token.Keyword] == [
        "parse",
        "let",
        "parse",
    ]
    assert any(
        kind == Token.Name.Variable and value == "tree" for _, kind, value in tokens
    )
    assert "".join(value for _, _, value in tokens) == source
