"""Panel behavior, bounded resource snapshots and Rich-to-toolkit rendering."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import Mock

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.input import PipeInput

from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit._generated.match.v1 import resources_pb2 as resources
from clang_toolkit.cli.app import DispatchResult
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.prompt import create_session
from clang_toolkit.cli.workspace import WorkspaceConsole
from clang_toolkit.cli.workspace_context import CommandContext
from clang_toolkit.cli.workspace_state import (
    MAX_OUTLINE_ROWS,
    outline_snapshot,
    resource_snapshot,
)
from clang_toolkit.cli.workspace_tree import WorkspaceTree
from test_workspace import SizedOutput, interact, wait_until


def test_rich_help_wraps_and_colors_headings_and_ctk_examples() -> None:
    panel = CommandContext()
    panel.update("match", ".")
    assert "Usage" in panel.text and "Examples" in panel.text
    assert max(map(len, panel.text.splitlines())) <= 32
    lines = panel.markdown_lexer.lex_document(panel.buffer.document)
    heading = lines(0)
    assert any("bold" in style and "#" in style for style, _ in heading)
    example = next(
        i
        for i, line in enumerate(panel.text.splitlines())
        if "match functionDecl" in line
    )
    styles = {style for style, text in lines(example) if text.strip()}
    assert len(styles) >= 2
    original = panel.render_key
    panel.update("match", ".")
    assert panel.render_key == original


def test_completion_descriptions_cover_commands_matchers_and_help() -> None:
    completer = ReplCompleter()
    for source, display, expected in [
        ("ma", "match", "Match native"),
        ("match functionD", "functionDecl(", "node matcher"),
        ("help mat", "match", "Match native"),
    ]:
        results = list(
            completer.get_completions(
                Document(source), CompleteEvent(completion_requested=True)
            )
        )
        choice = next(item for item in results if item.display_text == display)
        assert expected in choice.display_meta_text


def test_outline_scrolls_long_properties_and_pages_without_losing_selection(
    tmp_path: Path,
) -> None:
    bindings = {"rows": ["x" * 250 + str(index) for index in range(125)]}

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        async def read_outline(expanded: frozenset[str], pages: dict[str, int]):
            return outline_snapshot(bindings, expanded, pages)

        ui.read_outline = read_outline
        ui.toggle_panel("outline")
        await wait_until(lambda: bool(ui.outline.entries))
        pipe.send_text("\r")
        await wait_until(
            lambda: any(item.identity == "$rows:next" for item in ui.outline.entries)
        )
        assert any("Page 1/3" in item.label for item in ui.outline.entries)
        assert any(len(item.label) > 250 for item in ui.outline.entries)
        # Ctrl+Right pans; plain arrows navigate branches.
        pipe.send_text("\x1b[1;5C")
        await wait_until(lambda: ui.outline.horizontal_offset == 8)
        await wait_until(lambda: ui.outline.window.horizontal_scroll == 8)
        assert ui.outline.expanded == {"$rows"}
        pipe.send_text("\x1b[1;5C" * 10)
        await wait_until(lambda: ui.outline.horizontal_offset == 88)
        await wait_until(lambda: ui.outline.window.horizontal_scroll == 88)
        assert ui.outline.current.identity == "$rows"
        pipe.send_text("\x1b[1;5D" * 10)
        await wait_until(lambda: ui.outline.horizontal_offset == 8)
        pipe.send_text("\x1b[1;5D")
        await wait_until(lambda: ui.outline.horizontal_offset == 0)
        assert ui.outline.expanded == {"$rows"}
        pipe.send_text("\x1b[F\r")  # End selects Next page, Enter loads it.
        await wait_until(
            lambda: any("Page 2/3" in item.label for item in ui.outline.entries)
        )
        assert any(item.identity == "$rows[50]" for item in ui.outline.entries)
        assert not any(item.identity == "$rows[0]" for item in ui.outline.entries)
        pipe.send_text("\x1b[F\r")
        await wait_until(
            lambda: any("Page 3/3" in item.label for item in ui.outline.entries)
        )
        assert any(item.identity == "$rows[124]" for item in ui.outline.entries)
        assert not any(item.identity == "$rows:next" for item in ui.outline.entries)
        ui.outline.selected = next(
            i
            for i, item in enumerate(ui.outline.entries)
            if item.identity == "$rows:previous"
        )
        pipe.send_text("\r")
        await wait_until(
            lambda: any("Page 2/3" in item.label for item in ui.outline.entries)
        )
        assert ui.outline.current.identity == "$rows:previous"

    asyncio.run(interact(tmp_path, drive, output=SizedOutput(columns=150)))


def test_outline_expands_only_selected_branches_and_keeps_dictionary_keys() -> None:
    bindings = {
        "rows": [{"name": "f", "type": {"spelling": "int"}}],
        "other": [1] * 1000,
    }
    roots = outline_snapshot(bindings, frozenset())
    assert len(roots) == 2
    expanded = outline_snapshot(
        bindings, frozenset({"$rows", "$rows[0]", '$rows[0]["type"]'})
    )
    selected = next(
        item for item in expanded if item.identity == '$rows[0]["type"]["spelling"]'
    )
    assert "int" in selected.label
    assert dict(selected.commands)["p"] == 'print $rows[0]["type"]["spelling"]'
    assert not any(item.identity.startswith("$other[") for item in expanded)
    assert (
        len(outline_snapshot({"wide": list(range(100000))}, frozenset({"$wide"}))) <= 53
    )
    assert (
        len(
            outline_snapshot(
                {str(i): [1] * 100 for i in range(1000)},
                frozenset("$" + str(i) for i in range(1000)),
            )
        )
        <= MAX_OUTLINE_ROWS
    )


def test_resource_commands_select_one_lease_or_cursor_and_preserve_identity() -> None:
    file = resources.FileInfo(
        lease_id="lease-id",
        input=resources.InputDescriptor(file_path="/source.cpp"),
        explicit_leases=1,
    )
    sessions = pb.ListSessionsResponse(
        sessions=[
            pb.SessionInfo(session_id="cursor-id", file_path="/source.cpp", row_count=3)
        ]
    )
    entries = resource_snapshot((file,), sessions, "attached2")
    file_row = next(item for item in entries if item.identity == "file:lease-id")
    session_row = next(item for item in entries if item.identity == "session:cursor-id")
    assert dict(file_row.commands)["c"] == 'file close "lease-id"'
    assert (
        dict(session_row.commands)["a"] == 'session attach "cursor-id" into $attached2'
    )
    assert dict(session_row.commands)["c"] == 'session close "cursor-id"'
    prepare = Mock()
    tree = WorkspaceTree(Mock(), prepare)
    tree.update(entries)
    tree.selected = entries.index(session_row)
    tree.command("a")
    prepare.assert_called_once_with('session attach "cursor-id" into $attached2')


def test_panel_keys_preserve_draft_and_status_refreshes_then_marks_stale(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        calls = 0

        async def read_status() -> pb.ServerStatusResponse:
            from clang_toolkit._generated.index.v1 import index_service_pb2 as index_pb
            nonlocal calls
            calls += 1
            if calls > 1:
                raise RuntimeError("offline")
            return pb.ServerStatusResponse(
                resident_memory_bytes=12 * 1024**2,
                active_sessions=2,
                retained_memory_bytes=4 * 1024**2,
                max_sessions=100,
                project_indexes=index_pb.ListProjectIndexesResponse(
                    total_count=1, projects=[index_pb.ProjectIndexStatus(
                        project_root="/active-project", state=index_pb.INDEX_STATE_INDEXING,
                        translation_units_indexed=2, translation_units_total=7,
                        translation_units_pending=5)]),
            )

        async def execute(source: str) -> DispatchResult:
            return DispatchResult("done", True)

        async def read_outline(expanded: frozenset[str], pages: dict[str, int]):
            return outline_snapshot({"value": {"name": "f"}}, expanded, pages)

        with create_pipe_input() as pipe:
            output = SizedOutput(columns=150)
            ui = WorkspaceConsole(
                create_session(input=pipe, output=output),
                tmp_path,
                execute,
                server_status=read_status,
                outline=read_outline,
                input=pipe,
                output=output,
            )
            task = asyncio.create_task(ui.run())
            try:
                await wait_until(
                    lambda: ui.app.is_running and ui.server_snapshot is not None
                )
                assert "RSS 12M" in ui.footer()
                pipe.send_text('print "kept"\x1bOS')  # F4 closes help.
                await wait_until(lambda: not ui.context_visible)
                pipe.send_text("\x1bOS")
                await wait_until(lambda: ui.show_context)
                pipe.send_text("\x1b[18~")  # F7 outline.
                await wait_until(
                    lambda: ui.panel_kind == "outline" and bool(ui.outline.entries)
                )
                pipe.send_text("\r")
                await wait_until(lambda: len(ui.outline.entries) == 2)
                pipe.send_text("\x1b[20~")  # F9 server.
                await wait_until(lambda: ui.panel_kind == "server")
                assert "Resident memory" in ui.server_panel.text
                assert "Projects in progress" in ui.server_panel.text
                assert "/active-project" in ui.server_panel.text
                assert "2/7 indexed" in ui.server_panel.text
                await wait_until(lambda: calls >= 2 and "stale" in ui.footer())
                assert "Refresh failed" in ui.server_panel.text
                assert ui.buffer.text == 'print "kept"'
            finally:
                ui.request_exit()
                await asyncio.wait_for(task, 3)
            assert ui.monitor_task is not None and ui.monitor_task.done()

    asyncio.run(run())


def test_fileset_outline_lists_paths_directly_with_lazy_pages() -> None:
    from clang_toolkit.resources import FileSet, InputDescriptor

    manifest = FileSet(tuple(InputDescriptor(f'/src/{index}.cpp') for index in range(125)))
    entries = outline_snapshot({'files': manifest}, frozenset({'$files', '$files:dir:/src'}), {'$files': 1})
    assert entries[0].label == '$files · FileSet [125]'
    assert any('Page 2/3' in item.label for item in entries)
    files = [item for item in entries if item.identity.startswith('$files.inputs[')]
    assert len(files) == 50
    assert files[0].label == '[50] · 50.cpp · /src/50.cpp'
    assert files[-1].label == '[99] · 99.cpp · /src/99.cpp'
    assert dict(files[0].commands)['p'] == 'print $files.inputs[50]'
    assert not any(item.identity == '$files.inputs' for item in entries)


def test_outline_binding_label_uses_semantic_name_and_type() -> None:
    from clang_toolkit._generated.match.v1 import match_result_pb2
    from clang_toolkit._row_store import RowStore
    from clang_toolkit._value_lifecycle import CursorOwner
    from clang_toolkit.match_values import MatchValue

    result = match_result_pb2.MatchResult()
    declaration = result.bindings['root'].node.function_decl.function.declarator.value
    declaration.named.qualified_name = 'demo::run'
    declaration.type.description.spelling = 'int (int)'
    store = RowStore()
    store.append(result.SerializeToString(), binding_names=result.bindings)
    value = MatchValue._from_store(store, CursorOwner(object(), 'outline', 1, lambda _: None))
    entries = outline_snapshot({'m': value}, frozenset({'$m', '$m[0]'}))
    assert next(item.label for item in entries if item.identity == '$m[0].root') == 'root - demo::run · int (int)'
    declaration.named.ClearField('qualified_name')
    declaration.named.name.identifier = 'run'
    store2 = RowStore()
    store2.append(result.SerializeToString(), binding_names=result.bindings)
    value2 = MatchValue._from_store(store2, CursorOwner(object(), 'fallback', 1, lambda _: None))
    entries = outline_snapshot({'m': value2}, frozenset({'$m', '$m[0]'}))
    assert next(item.label for item in entries if item.identity == '$m[0].root') == 'root - run · int (int)'
