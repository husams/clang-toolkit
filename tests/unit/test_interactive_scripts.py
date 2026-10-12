"""Whole-script dispatch and real workspace editing/rendering regressions."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.input import PipeInput

from clang_toolkit.cli.app import DispatchResult, dispatch_result
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.highlight import ReplLexer
from clang_toolkit.cli.input_state import input_state
from clang_toolkit.cli.prompt import PersistentPromptHistory
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.history import HistoryStore
from clang_toolkit.cli.workspace import WorkspaceConsole
from clang_toolkit.client import Client
from test_workspace import interact, wait_until


@pytest.fixture
def runtime(tmp_path: Path) -> Iterator[Runtime]:
    value = Runtime(
        Mock(spec=Client), cwd=tmp_path, environment={},
        history=HistoryStore(tmp_path / "history.jsonl"),
    )
    try:
        yield value
    finally:
        value.close()


def test_script_shares_bindings_and_preserves_nested_syntax(runtime: Runtime, tmp_path: Path) -> None:
    (tmp_path / "names.txt").write_text(" a \n b \n", encoding="utf-8")
    source = '''# Paste the whole script, including multiline expressions.
let lines = read "names.txt"
let clean = foreach line in $lines do {
    print $line.strip();
}
print $clean; print "length=${lines.length}"
'''
    result = dispatch_result(runtime.client, source, runtime)
    assert result.success
    assert result.output.splitlines() == ["a", "b", "length=2"]
    assert runtime.history.read_commands() == [source]


def test_script_retains_each_outline_and_help_result(runtime: Runtime) -> None:
    runtime.capture_display = True
    result = dispatch_result(runtime.client, 'help read\nprint [1, 2]\nprint [3, 4]', runtime)
    assert result.success
    assert result.parts[0].markdown is not None
    assert [part.outline_value for part in result.parts[1:]] == [
        ("print", [1, 2]), ("print", [3, 4])
    ]
    assert runtime.display_value is None


def test_script_results_preserve_collections_before_later_mutation(runtime: Runtime) -> None:
    runtime.capture_display = True
    result = dispatch_result(runtime.client, 'let xs = {items: [1]}\nprint $xs\n$xs.items.push(2)\nprint $xs', runtime)
    assert result.success
    assert result.parts[1].outline_value == ("print", {"items": [1]})
    assert result.parts[-1].outline_value == ("print", {"items": [1, 2]})


def test_script_stops_at_error_and_retains_earlier_effects_and_output(runtime: Runtime) -> None:
    source = 'let first = 7\nprint "before"\nprint $missing\nlet skipped = 9'
    result = dispatch_result(runtime.client, source, runtime)
    assert not result.success
    assert result.output == "before\nerror: unknown variable: missing"
    assert runtime.evaluate("$first") == 7
    assert not dispatch_result(runtime.client, "$skipped", runtime).success
    assert dispatch_result(runtime.client, 'print "recovered"', runtime).success
    assert runtime.history.read_commands()[0] == source


def test_script_validates_all_syntax_before_any_effects(runtime: Runtime) -> None:
    source = 'let first = 7\nprint "before"\nlet broken = [1, @]'
    result = dispatch_result(runtime.client, source, runtime)
    assert not result.success
    assert "line 3, column" in result.output
    assert not runtime.bindings
    assert runtime.history.read_commands() == [source]


@pytest.mark.parametrize("exit_command", ["quit", "exit"])
def test_script_exit_retains_output_and_skips_later_statements(runtime: Runtime, exit_command: str) -> None:
    result = dispatch_result(runtime.client, f'print "before"; {exit_command}; let skipped = 9', runtime)
    assert result.success and result.exit_requested
    assert result.output == "before"
    assert not runtime.bindings


def test_script_reference_errors_keep_original_source_coordinates(runtime: Runtime) -> None:
    result = dispatch_result(runtime.client, 'let values = [1]\nprint "before"\nprint $values[3]', runtime)
    assert not result.success
    assert "line 3, column" in result.output


@pytest.mark.parametrize("separator", ["\n", "; "])
def test_completion_and_highlighting_after_first_statement(separator: str) -> None:
    source = "let n = 1" + separator + "match fun"
    suggestions = list(ReplCompleter().get_completions(Document(source), None))
    assert "functionDecl(" in {item.text for item in suggestions}
    lines = ReplLexer().lex_document(Document("let n = 1" + separator + 'print "later"'))
    assert ("class:keyword", "print") in lines(1 if separator == "\n" else 0)
    assert not input_state("let n = 1\nforeach x in [1] do\nprint $x\ndone").needs_more
    assert input_state("let n = 1\nforeach x in [1] do\nprint $x").needs_more


def test_read_format_completion_uses_current_statement() -> None:
    source = 'save [1] to "old.json" as json\nread "names.txt" as '
    suggestions = {item.text for item in ReplCompleter().get_completions(Document(source), None)}
    assert "text" in suggestions and "proto" not in suggestions


@pytest.mark.parametrize("sequence", ["\x1b\r", "\x1b[13;2u", "\x1b[27;2;13~"])
def test_newline_key_builds_a_script_without_executing(tmp_path: Path, sequence: str) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.buffer.document = Document('print "first"', len('print "first"'))
        pipe.send_text(sequence)
        await wait_until(lambda: ui.buffer.text == 'print "first"\n')
        assert not ui.busy and "OK" not in ui.results.text
        pipe.send_text('print "second"\x1b[27;5;13~')
        await wait_until(lambda: not ui.busy and "OK" in ui.results.text)
        assert 'print "second"' in ui.results.text

    asyncio.run(interact(tmp_path, drive))


def test_pasted_script_executes_with_rich_results_and_single_history_entry(runtime: Runtime, tmp_path: Path) -> None:
    runtime.capture_display = True
    source = 'let n = 7\nprint [1, 2]\nprint [3, 4]\nprint "DONE=${n}"'

    async def execute(text: str) -> DispatchResult:
        return await asyncio.to_thread(dispatch_result, runtime.client, text, runtime)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("\x1b[200~" + source + "\x1b[201~\x1b[27;5;13~")
        await wait_until(lambda: not ui.busy and "DONE=7" in ui.results.text)
        assert ui.results.text.count("▸ List · list [2]") == 2
        assert runtime.history.read_commands() == [source]
        assert not ui.buffer.text

    asyncio.run(interact(tmp_path, drive, execute=execute, history=PersistentPromptHistory(runtime.history)))
