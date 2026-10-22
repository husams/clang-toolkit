"""Source links and batch progress exercised through the actual workspace."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable
from pathlib import Path
from threading import Lock, Thread
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.input import PipeInput
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType, MouseButton
from prompt_toolkit.data_structures import Point, Size

from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit._generated.match.v1 import match_result_pb2 as results
from clang_toolkit._generated.analysis.v1 import batch_pb2
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.batches import batch_run
from clang_toolkit.client import Client
from clang_toolkit.match_values import MatchValue
from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.batch_execution import BatchInterrupted
from clang_toolkit.cli.runtime.progress import BatchProgress, durable_progress
from clang_toolkit.cli.workspace import WorkspaceConsole
from clang_toolkit.cli.workspace_source_data import (
    MAX_SOURCE_BYTES, SourceSnapshot, SourceMatch, SourceTarget, source_snapshot, source_target,
)
from clang_toolkit.cli.workspace_source_render import SourcePresentation
from clang_toolkit.cli.workspace_state import display_snapshot, outline_snapshot
from clang_toolkit.cli.runtime.semantic import view
from clang_toolkit.cli.runtime.values import MatchSet
from test_workspace import interact, wait_until, SizedOutput
from test_workspace_result_tree import select_result
from test_console_file_batch_runtime import _runtime
from clang_toolkit.resources import FileSet, InputDescriptor


def source_matches(path: Path, count: int = 2) -> MatchValue:
    response = pb.MatchResponse()
    for index in range(count):
        row = response.results.add()
        for name, begin, end in (("root", 5 + index, 5 + index), ("callee", 1, 3)):
            binding = row.bindings[name]
            binding.location.CopyFrom(results.MatchSourcePoint(file=str(path), valid=True, line=begin, column=1))
            binding.range.expansion_begin.CopyFrom(binding.location)
            binding.range.expansion_end.CopyFrom(results.MatchSourcePoint(file=str(path), valid=True, line=end, column=2))
    return MatchValue._from_response(response, CursorOwner(Mock(spec=Client), "source", 1, lambda _: None), source_file=str(path))


def test_match_binding_and_location_links_use_own_valid_ast_coordinates(tmp_path: Path) -> None:
    path = tmp_path / "demo.cpp"
    matches = source_matches(path)
    entries = display_snapshot("match", matches, frozenset({"$Matches", "$Matches[0]", "$Matches[0].callee"}), {})
    assert entries is not None
    assert next(row.source for row in entries if row.identity == "$Matches[0]").line == 5
    callee = next(row.source for row in entries if row.identity == "$Matches[0].callee")
    assert callee.line == 1 and callee.end_line == 3
    assert next(row.source for row in entries if row.identity == "$Matches[0].callee.location").line == 1
    assert source_target(results.MatchBinding()) is None
    point = results.MatchSourcePoint(file=str(path), valid=False, line=5)
    assert source_target(point) is None


def test_source_links_preserve_exclusive_end_columns_for_mid_line_expressions(tmp_path: Path) -> None:
    binding = results.MatchBinding()
    binding.range.expansion_begin.CopyFrom(results.MatchSourcePoint(file=str(tmp_path / "expression.cc"), valid=True, line=3, column=24))
    binding.range.expansion_end_exclusive.CopyFrom(results.MatchSourcePoint(file=str(tmp_path / "expression.cc"), valid=True, line=3, column=37))
    target = source_target(binding)
    assert (target.line, target.column, target.end_line, target.end_column) == (3, 24, 3, 37)


def test_source_region_keeps_cpp_colors_and_numbers_without_extra_rows() -> None:
    text = "class Calculator {\npublic:\n    int value() const {\n        return 42;\n    }\n};\n"
    presentation = SourcePresentation(text, SourceTarget("demo.cc", 1, 1, 6, end_column=2))
    assert presentation.document.line_count == Document(text).line_count
    assert presentation.document.text == text
    for original in range(6):
        display_row = presentation.code_rows[original]
        fragments = presentation.lex_document(presentation.document)(display_row)
        assert not any("source-range" in style or "bg:" in style for style, _ in fragments)
        assert str(original + 1) in "".join(text for _, text in presentation.gutter(display_row, 0))
        gutter = presentation.gutter(display_row, 0)
        assert gutter[0] == ("class:source-marker", "▶")
        assert len("".join(text for _, text in gutter)) == 4
    assert any("pygments.keyword" in style for style, text in presentation.lex_document(presentation.document)(0) if "class" in text)
    presentation = SourcePresentation("int f() {\n\n    return 1;\n}\n", SourceTarget("demo.cc", 1, 1, 4, end_column=2))
    assert presentation.gutter(1, 0)[0][1] == "▶"  # Blank lines remain inside the region.


def test_expression_rule_uses_utf8_byte_columns_tabs_and_exclusive_boundary() -> None:
    text = '\tconst char *label = "é"; int answer = 7 + twice(3) * 2;'
    expression = "twice(3) * 2"
    begin = text.index(expression)
    start = len(text[:begin].encode("utf-8")) + 1
    end = start + len(expression)
    presentation = SourcePresentation(text, SourceTarget("demo.cc", 1, start, 1, end_column=end))
    fragments = presentation.lex_document(presentation.document)(0)
    assert "".join(text for style, text in fragments if " underline" in style) == expression
    assert presentation.gutter(0, 0)[0][1] == "▶"
    # An exclusive endpoint at the next line's first column does not mark it.
    presentation = SourcePresentation("int x;\nint y;", SourceTarget("demo.cc", 1, 1, 2, end_column=1))
    assert presentation.document.line_count == 2
    assert presentation.gutter(1, 0)[0][1] == " "


def test_source_snapshot_contains_only_the_clicked_match(tmp_path: Path) -> None:
    path = tmp_path / "demo.cpp"
    path.write_text("int target() {\n  return 1;\n}\n\nint a = target();\nint b = target();\n")
    matches = source_matches(path, 75)
    target = source_target(matches[1])
    snapshot = source_snapshot(target, tmp_path)
    assert snapshot.matches == (SourceMatch(target.label, target, ()),)
    assert snapshot.text == path.read_text()
    assert snapshot.display_path == "demo.cpp"


def test_all_match_ranges_keep_gaps_and_selected_marker_without_extra_rows() -> None:
    text = "int first = a + b;\n\nint second = c + d;\nint untouched;\n"
    selected = SourceTarget("demo.cc", 1, 13, 1, end_column=14)
    other = SourceTarget("demo.cc", 1, 17, 1, end_column=18)
    region = SourceTarget("demo.cc", 2, 1, 3, end_column=20)
    nested = SourceTarget("demo.cc", 3, 14, 3, end_column=15)
    presentation = SourcePresentation(text, selected, (other, region, nested, region, selected))
    assert presentation.document.text == text
    assert [presentation.gutter(row, 0)[0][1] for row in range(4)] == ["▶", "▷", "▷", " "]
    lexer = presentation.lex_document(presentation.document)
    assert "".join(value for style, value in lexer(0) if " underline" in style) == "ab"
    assert "".join(value for style, value in lexer(2) if " underline" in style) == "int second = c + d;"
    assert presentation.spans[2] == [(0, 19)]
    moved = SourcePresentation(text, nested, (selected, other, region))
    assert moved.gutter(0, 0)[0][1] == "▷" and moved.gutter(2, 0)[0][1] == "▶"
    assert moved.spans == presentation.spans


def test_source_header_uses_relative_paths_only_beneath_current_directory(tmp_path: Path) -> None:
    cwd = tmp_path / "project"
    child = cwd / "src" / "demo.cc"
    child.parent.mkdir(parents=True)
    child.write_text("int value;\n")
    snapshot = source_snapshot(SourceTarget(str(child), 1, 1, 1), cwd)
    assert snapshot.path == child and snapshot.display_path == "src/demo.cc"
    relative = source_snapshot(SourceTarget("src/demo.cc", 1, 1, 1), cwd)
    assert relative.display_path == snapshot.display_path
    sibling = tmp_path / "project-other.cc"
    sibling.write_text("int outside;\n")
    outside = source_snapshot(SourceTarget(str(sibling), 1, 1, 1), cwd)
    assert outside.display_path == str(sibling)


@pytest.mark.parametrize("columns", [48, 100])
def test_click_binding_opens_only_its_range_without_changing_draft(tmp_path: Path, columns: int) -> None:
    path = tmp_path / "demo.cpp"
    path.write_text("int target() {\n  return 1;\n}\n\nint a = target();\nint b = target();\n")
    matches = source_matches(path)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.buffer.set_document(Document('print "draft"', 7))
        await ui.result_trees.show("match", source_matches(path, 75))
        await ui.result_trees.show("match", matches)
        select_result(ui, "$Matches")
        pipe.send_text("\x1b[C")
        await wait_until(lambda: any(row.identity == "$Matches[0]" for row in ui.result_trees.trees[-1].entries))
        select_result(ui, "$Matches[0]")
        pipe.send_text("\x1b[C")
        await wait_until(lambda: any(row.identity == "$Matches[0].callee" for row in ui.result_trees.trees[-1].entries))
        select_result(ui, "$Matches[0].callee")
        row = ui.results.buffer.document.cursor_position_row
        ui.results_mouse(MouseEvent(Point(8, row), MouseEventType.MOUSE_UP, MouseButton.LEFT, frozenset()))
        await wait_until(lambda: ui.source.snapshot is not None)
        assert ui.source.visible and ui.app.layout.has_focus(ui.source.code.window)
        await wait_until(lambda: ui.source.code.window.render_info is not None and ui.source.code.window.render_info.window_height >= 18)
        assert ui.source.target.line == 1 and ui.source.target.end_line == 3
        assert ui.source.snapshot.display_path == "demo.cpp"
        assert len(ui.source.snapshot.matches) == 1
        assert ui.source.snapshot.matches[0].target == ui.source.target
        assert ui.source.code.lexer.gutter(4, 0)[0][1] == " "
        assert ui.source.code.lexer.gutter(5, 0)[0][1] == " "
        syntax = ui.source.code.lexer.lex_document(ui.source.code.buffer.document)(0)
        assert any("pygments.keyword" in style for style, text in syntax if "int" in text)
        pipe.send_text("\t")
        await wait_until(lambda: ui.app.layout.has_focus(ui.source.tree.window))
        assert len(ui.source.tree.entries) == 2  # Count and the selected link only.
        pipe.send_text("n")
        pipe.send_text("p")
        await asyncio.sleep(0.05)
        assert ui.source.target.line == 1
        pipe.send_text("\x1b")
        await wait_until(lambda: not ui.source.visible)
        assert ui.app.layout.has_focus(ui.results.window)
        assert ui.buffer.text == 'print "draft"' and ui.buffer.cursor_position == 7
        assert not ui.files_visible and ui.panel_kind == "help"
        # Opening a different row replaces the earlier binding's range.
        select_result(ui, "$Matches[1]")
        pipe.send_text("o")
        await wait_until(lambda: ui.source.visible and ui.source.target is not None and ui.source.target.line == 6)
        assert ui.source.target.line == 6
        assert len(ui.source.snapshot.matches) == 1
        assert ui.source.code.lexer.gutter(0, 0)[0][1] == " "
        assert ui.source.code.lexer.gutter(4, 0)[0][1] == " "
        assert ui.source.code.lexer.gutter(5, 0)[0][1] == "▶"
        pipe.send_text("\x1b")
        await wait_until(lambda: not ui.source.visible)
        assert ui.buffer.text == 'print "draft"' and ui.buffer.cursor_position == 7

    asyncio.run(interact(tmp_path, drive, output=SizedOutput(columns=columns)))


def test_selected_expression_is_not_broadened_by_an_overlapping_function(tmp_path: Path) -> None:
    path = tmp_path / "overlap.cpp"
    expression = "value * 3"
    path.write_text("int f() {\n    return 6 + " + expression + ";\n}\n")
    line = path.read_text().splitlines()[1]
    start = line.index(expression) + 1
    target = SourceTarget(str(path), 2, start, 2, end_column=start + len(expression))

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        await ui.result_trees.show("match", source_matches(path))
        reads: list[SourceTarget] = []

        async def read(selected: SourceTarget) -> SourceSnapshot:
            reads.append(selected)
            return source_snapshot(selected, tmp_path)

        ui.read_source = read
        ui.open_source(target)
        await wait_until(lambda: ui.source.snapshot is not None)
        assert reads == [target]
        assert len(ui.source.snapshot.matches) == 1
        presentation = ui.source.code.lexer
        fragments = presentation.lex_document(ui.source.code.buffer.document)(1)
        assert "".join(text for style, text in fragments if " underline" in style) == expression
        assert presentation.gutter(0, 0)[0][1] == " "
        assert presentation.gutter(1, 0)[0][1] == "▶"
        assert presentation.gutter(2, 0)[0][1] == " "
        ui.close_source()

    asyncio.run(interact(tmp_path, drive))


def test_keyboard_source_open_and_missing_file_error_are_recoverable(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        await ui.result_trees.show("match", source_matches(tmp_path / "missing.cpp"))
        select_result(ui, "$Matches")
        pipe.send_text("\x1b[C")
        await wait_until(lambda: any(row.identity == "$Matches[0]" for row in ui.result_trees.trees[-1].entries))
        select_result(ui, "$Matches[0]")
        pipe.send_text("o")
        await wait_until(lambda: "Cannot open source" in ui.source.notice)
        assert ui.source.visible
        pipe.send_text("\x1b")
        await wait_until(lambda: not ui.source.visible)
        assert ui.app.layout.has_focus(ui.results.window)
    asyncio.run(interact(tmp_path, drive))


@pytest.mark.parametrize("columns", [48, 100])
def test_source_scrollbar_pans_long_lines_keeps_gutter_and_handles_short_cursor_line(tmp_path: Path, columns: int) -> None:
    path = tmp_path / "long.cpp"
    text = 'int short_line;\nconst char *text = "' + "é界" * 80 + 'END_OF_LONG_LINE";\n'
    path.write_text(text)
    output = SizedOutput(columns=columns)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.buffer.set_document(Document('print "draft"', 7))
        ui.open_source(SourceTarget(str(path), 1, 1, 1))
        await wait_until(lambda: ui.source.snapshot is not None)
        bar = ui.source.scrollbar
        await wait_until(lambda: bar.window.render_info is not None)
        assert bar.maximum_offset > 100
        original_cursor = ui.source.code.buffer.cursor_position
        pipe.send_text("\x1b[1;5C")
        await wait_until(lambda: ui.source.code.window.horizontal_scroll == 8)
        assert ui.source.code.buffer.cursor_position == original_cursor
        pipe.send_text("\x1b[B")
        await wait_until(lambda: ui.source.code.buffer.document.cursor_position_row == 1)
        assert bar.manual_offset == 8
        pipe.send_text("\x1b[A")
        await wait_until(lambda: ui.source.code.buffer.cursor_position == original_cursor)
        assert bar.manual_offset == 8
        assert ui.source.code.lexer.gutter(0, 0)[0][1] == "▶"
        bar.mouse(MouseEvent(Point(bar.gutter_width + bar.viewport_width - 1, 0), MouseEventType.MOUSE_UP, MouseButton.LEFT, frozenset()))
        await wait_until(lambda: ui.source.code.window.horizontal_scroll == 16)
        assert ui.app.layout.has_focus(ui.source.code.window)
        bar.mouse(MouseEvent(Point(bar.gutter_width + bar.viewport_width - 2, 0), MouseEventType.MOUSE_UP, MouseButton.LEFT, frozenset()))
        await wait_until(lambda: ui.source.code.window.horizontal_scroll == bar.maximum_offset)
        assert ui.source.code.buffer.cursor_position == original_cursor
        old_maximum = bar.maximum_offset
        output.size = Size(rows=24, columns=columns + 40)
        ui.app.invalidate()
        await wait_until(lambda: bar.maximum_offset < old_maximum and ui.source.code.window.horizontal_scroll == bar.maximum_offset)
        pipe.send_text("\x1b[1;5D")
        await wait_until(lambda: ui.source.code.window.horizontal_scroll == bar.maximum_offset - 8)
        ui.source.jump(SourceTarget(str(path), 1, 1, 1))
        await wait_until(lambda: ui.source.code.window.horizontal_scroll == 0)
        pipe.send_text("\x1b")
        await wait_until(lambda: not ui.source.visible)
        ui.open_source(SourceTarget(str(tmp_path / "missing.cpp"), 1, 1, 1))
        await wait_until(lambda: "Cannot open source" in ui.source.notice)
        assert bar.maximum_offset == 0 and bar.manual_offset is None
        ui.source.show(SourceSnapshot(path, "int fits;\n", ()), SourceTarget(str(path), 1, 1, 1))
        await wait_until(lambda: bar.maximum_offset == 0 and bar.manual_offset is None)
        assert bar.code.window.get_line_prefix(0, 0)[0][1] == "▶"
        pipe.send_text("\x1b")
        await wait_until(lambda: not ui.source.visible)
        assert ui.buffer.text == 'print "draft"' and ui.buffer.cursor_position == 7

    asyncio.run(interact(tmp_path, drive, output=output))


def test_source_window_keeps_foreground_cancellation_and_quit_keys(tmp_path: Path) -> None:
    path = tmp_path / "demo.cpp"
    path.write_text("int value;\n")
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        cancelled = []
        async def cancel():
            cancelled.append(True)
            ui.busy = False
            return "Cancellation acknowledged"
        ui.cancel = cancel
        ui.open_source(SourceTarget(str(path), 1, 1, 1))
        await wait_until(lambda: ui.source.snapshot is not None)
        ui.busy = True
        pipe.send_text("\x03")
        await wait_until(lambda: bool(cancelled))
        assert ui.source.visible
        pipe.send_text("\x1b[21~")
        await wait_until(lambda: not ui.app.is_running)
        assert ui.closing
    asyncio.run(interact(tmp_path, drive))


def test_source_outline_pages_all_matches_and_next_previous_cross_pages(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        links = tuple(SourceMatch(f"row {i}", SourceTarget("demo.cpp", i + 1, 1, i + 1), ()) for i in range(125))
        ui.source.visible = True
        ui.source.show(SourceSnapshot(tmp_path / "demo.cpp", "int value;\n" * 125, links), links[49].target)
        ui.source.next_match(1)
        assert ui.source.target.line == 51 and ui.source.page == 1
        assert ui.source.code.lexer.gutter(124, 0)[0][1] == "▷"  # Off-page matches are also marked.
        assert "Matches [125]" in ui.source.tree.entries[0].label
        ui.source.next_match(-1)
        assert ui.source.target.line == 50 and ui.source.page == 0
        ui.source.close()
    asyncio.run(interact(tmp_path, drive))


def test_source_reader_bounds_file_size_and_sanitizes_terminal_controls(tmp_path: Path) -> None:
    path = tmp_path / "controls.cpp"
    path.write_bytes(b"int x;\x1b[31m\x00\r\n")
    target = SourceTarget(str(path), 1, 1, 1)
    assert "\x1b" not in source_snapshot(target, tmp_path).text
    path.write_bytes(b"x" * (MAX_SOURCE_BYTES + 1))
    with pytest.raises(ValueError, match="8 MB"):
        source_snapshot(target, tmp_path)


def test_source_view_does_not_read_or_depend_on_session_matches(tmp_path: Path) -> None:
    path = tmp_path / "demo.cpp"
    path.write_text("int value;\n" * 6)
    matches = source_matches(path)
    target = source_target(matches[0])
    with patch.object(MatchValue, "iter_rows", side_effect=AssertionError("must not scan matches")):
        snapshot = source_snapshot(target, tmp_path)
    assert snapshot.matches == (SourceMatch(target.label, target, ()),)
    assert snapshot.notice == ""


def batch_runtime(tmp_path):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(tuple(InputDescriptor.from_path(f"{i}.cc", working_directory=tmp_path) for i in range(3)))
    return runtime, client


def test_live_foreground_progress_replaces_text_and_counts_files_once(tmp_path: Path, capsys) -> None:
    runtime, client = batch_runtime(tmp_path)
    runtime.capture_display = True
    events = []
    runtime.batch_progress = events.append
    try:
        outcome = dispatch_result(client, 'batch part in $inputs size 2 do { match functionDecl() in $part; }', runtime)
        assert outcome.success and outcome.outline_value[0] == "batch_statement"
        assert events[0].done == 0 and events[-1].done == 3 and events[-1].total == 3
        assert events[-1].state == "completed"
        assert any(event.done == 1 and event.state == "running" for event in events)
        assert "group" not in capsys.readouterr().out
        assert runtime._batch_file_progress is None and all(scope.released for scope in client.scopes)
    finally:
        runtime.close()


def test_failed_and_cancelled_progress_excludes_skipped_files(tmp_path: Path) -> None:
    runtime, client = batch_runtime(tmp_path)
    events = []
    runtime.batch_progress = events.append
    original = client.match_in
    def fail(*args, **kwargs):
        raise ValueError("broken input")
    client.match_in = fail
    outcome = dispatch_result(client, 'batch part in $inputs size 1 do { match functionDecl() in $part; }', runtime)
    assert not outcome.success
    assert events[-1].done == 1 and events[-1].failed == 1 and events[-1].skipped == 2 and events[-1].state == "failed"
    client.match_in = original
    events.clear()
    def cancel_after_first(event):
        events.append(event)
        if event.done == 1:
            runtime.request_batch_cancel()
    runtime.batch_progress = cancel_after_first
    with pytest.raises(BatchInterrupted):
        runtime.execute('batch part in $inputs size 1 do { match functionDecl() in $part; }')
    assert events[-1].done == 1 and events[-1].state == "cancelled"
    assert runtime._batch_file_progress is None
    runtime.close()


def test_progress_off_and_file_redirection_keep_existing_output(tmp_path: Path, capsys) -> None:
    runtime, _ = batch_runtime(tmp_path)
    events = []
    runtime.batch_progress = events.append
    runtime.execute('batch part in $inputs size 1 progress off do { print $part.index; }')
    assert events == [] and capsys.readouterr().out.splitlines() == ["1", "2", "3"]
    runtime.execute('set output to "batch.log"')
    runtime.execute('batch part in $inputs size 1 do { match functionDecl() in $part; }')
    assert events == [] and "completed_files" in (tmp_path / "batch.log").read_text()
    runtime.close()


def test_durable_progress_uses_frozen_inputs_and_preserves_cancelled_fraction() -> None:
    run = batch_pb2.BatchRun(run_id="run", state="cancelled")
    for state in ("completed", "failed", "cancelled", "pending"):
        group = run.groups.add(state=state)
        group.inputs.add(file_path="a.cc")
    progress = durable_progress(batch_run(run))
    assert (progress.done, progress.total, progress.failed, progress.skipped) == (2, 4, 1, 1)
    assert "2/4 files" in progress.label() and "[Cancel]" not in progress.label()


def test_progress_updates_in_place_and_durable_polling_stops_on_completion(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.show_batch_progress(BatchProgress("many", 1000))
        await wait_until(lambda: "0/1000 files" in ui.results.text)
        await asyncio.to_thread(lambda: [ui.show_batch_progress(BatchProgress("many", 1000, i, i)) for i in range(1, 1001)])
        await wait_until(lambda: "1000/1000 files" in ui.results.text)
        assert ui.results.text.count("Batch many") == 1
        ui._append("x" * 210_000)
        assert not ui.result_trees.trees
        assert "1000/1000 files" in ui.footer()
        ui.show_batch_progress(BatchProgress("many", 1000, 1000, 1000, state="completed"))
        await wait_until(lambda: "State: completed" in ui.results.text)
        reads = []
        async def read(run_id):
            reads.append(run_id)
            return BatchProgress(run_id, 2, 2, 2, state="completed", durable=True)
        ui.read_batch_status = read
        ui.show_batch_progress(BatchProgress("durable", 2, durable=True))
        await wait_until(lambda: "2/2 files" in ui.results.text)
        await wait_until(lambda: not ui.batch_monitors)
        assert reads == ["durable"]
    asyncio.run(interact(tmp_path, drive))


def test_terminal_progress_renders_after_queued_batch_output() -> None:
    class QueuedLoop:
        def __init__(self) -> None:
            self.callbacks: deque[tuple[Callable[..., None], tuple]] = deque()

        def call_soon_threadsafe(self, callback: Callable[..., None], *args: object) -> None:
            self.callbacks.append((callback, args))

        def drain(self) -> None:
            while self.callbacks:
                callback, args = self.callbacks.popleft()
                callback(*args)

    class ProgressTree:
        def __init__(self) -> None:
            self.rows: dict[str, BatchProgress] = {}

        def progress(self, progress: BatchProgress) -> None:
            self.rows[progress.run_id] = progress
            events.append(progress.state)

    events: list[str | tuple[str, str]] = []
    loop = QueuedLoop()
    ui = WorkspaceConsole.__new__(WorkspaceConsole)
    ui.loop = loop
    ui.app = SimpleNamespace(is_running=True, invalidate=lambda: None)
    ui.progress_lock = Lock()
    ui.pending_progress = {}
    ui.progress_states = {}
    ui.result_trees = ProgressTree()
    ui.write_markdown = lambda markdown: events.append(("body", markdown))

    def publish() -> None:
        ui.show_batch_progress(BatchProgress("quick", 1))
        ui.write_output("BODY_LINE\n" * 30 + "BODY_LAST")
        ui.show_batch_progress(BatchProgress("quick", 1, 1, 1, state="completed"))

    worker = Thread(target=publish)
    worker.start()
    worker.join()
    loop.drain()

    assert events[0] == "running"
    assert events[1][0] == "body" and "BODY_LAST" in events[1][1]
    assert events[2] == "completed"
    assert len(ui.result_trees.rows) == 1


def test_outline_panel_bindings_also_carry_source_links(tmp_path: Path) -> None:
    matches = source_matches(tmp_path / "demo.cpp")
    entries = outline_snapshot({"rows": matches}, frozenset({"$rows", "$rows[0]"}), {})
    assert next(row for row in entries if row.identity == "$rows[0].callee").source.line == 1


def test_detached_batch_match_rows_keep_named_binding_links_without_carrier_metadata(tmp_path: Path) -> None:
    value = MatchSet((view(source_matches(tmp_path / "demo.cpp")[0]._message()),))
    entries = display_snapshot("print", value, frozenset({"$Matches", "$Matches[0]"}), {})
    children = [row for row in entries if row.depth == 2]
    assert len(children) == 2
    assert {row.source.line for row in children} == {1, 5}
    assert not any(row.label.startswith(("bindings ·", "source_match_index")) for row in children)


def test_durable_cancel_and_unavailable_status_keep_console_recoverable(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        cancelled = []
        async def cancel(run_id):
            cancelled.append(run_id)
            return BatchProgress(run_id, 4, 2, 2, state="cancelled", durable=True, revision=2)
        ui.cancel_batch = cancel
        ui.show_batch_progress(BatchProgress("cancel", 4, 2, 2, durable=True, revision=1))
        await wait_until(lambda: "[Cancel]" in ui.results.text)
        ui.app.layout.focus(ui.results.window)
        tree = ui.result_trees.trees[-1]
        ui.results.buffer.cursor_position = tree.start
        pipe.send_text("c")
        await wait_until(lambda: "State: cancelled" in ui.results.text)
        assert cancelled == ["cancel"] and ui.results.text.count("Batch cancel") == 1
        # An older poll cannot overwrite a revision-checked cancellation.
        ui.show_batch_progress(BatchProgress("cancel", 4, durable=True, revision=1))
        await asyncio.sleep(0.01)
        assert "2/4 files" in ui.results.text and "State: cancelled" in ui.results.text
        async def fail(_run_id):
            raise OSError("disconnected")
        ui.read_batch_status = fail
        ui.show_batch_progress(BatchProgress("unavailable", 4, durable=True))
        await wait_until(lambda: "status unavailable" in ui.results.text)
        assert "Batch [" not in ui.footer()
        assert not ui.batch_monitors
    asyncio.run(interact(tmp_path, drive))


def test_batch_progress_has_separate_state_row_and_cancel_click(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        cancelled = []
        async def cancel(run_id):
            cancelled.append(run_id)
            return BatchProgress(run_id, 24, 3, 2, 1, state="cancelled", durable=True, revision=2)
        ui.cancel_batch = cancel
        ui.show_batch_progress(BatchProgress("run", 24, 3, 2, 1, durable=True, revision=1))
        await wait_until(lambda: "[Cancel]" in ui.results.text)
        tree = ui.result_trees.trees[-1]
        rows = tree.text.splitlines()
        assert len(rows) == 2 and "3/24 files" in rows[0] and "State:" not in rows[0]
        assert "State: running" in rows[1] and "1 failed" in rows[1]
        first, _ = ui.results.buffer.document.translate_index_to_position(tree.start)
        # Only the second row's Cancel label responds; bar clicks do not cancel.
        ui.results_mouse(MouseEvent(Point(rows[1].index("[Cancel]"), first), MouseEventType.MOUSE_UP, MouseButton.LEFT, frozenset()))
        assert not cancelled
        ui.results_mouse(MouseEvent(Point(rows[1].index("[Cancel]"), first + 1), MouseEventType.MOUSE_UP, MouseButton.LEFT, frozenset()))
        await wait_until(lambda: "State: cancelled" in ui.results.text)
        assert cancelled == ["run"]
    asyncio.run(interact(tmp_path, drive))
