"""Typed display trees exercised through the real workspace event loop."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from prompt_toolkit.document import Document
from prompt_toolkit.input import PipeInput

from clang_toolkit._generated.match.v1 import match_result_pb2 as results
from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit._generated.match.v1 import resources_pb2 as resources
from clang_toolkit._row_store import RowStore
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.cli.app import DispatchResult, dispatch_result
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.workspace import WorkspaceConsole
from clang_toolkit.cli.workspace_output import MAX_TRANSCRIPT_CHARS
from clang_toolkit.cli.workspace_state import (
    display_snapshot,
    outline_snapshot,
    resource_snapshot,
)
from clang_toolkit.client import Client, QueryError
from clang_toolkit.match_values import MatchValue, ParsedTree
from clang_toolkit.resources import FileSet, InputDescriptor
from test_workspace import SizedOutput, interact, wait_until


def matches(count: int = 1) -> MatchValue:
    store = RowStore()
    for index in range(count):
        row = results.MatchResult()
        decl = row.bindings["f"].node.function_decl.function.declarator.value
        decl.named.qualified_name = f"demo::run{index}"
        decl.named.name.identifier = f"run{index}"
        decl.type.description.spelling = "void ()"
        store.append(row.SerializeToString(), binding_names=row.bindings)
    return MatchValue._from_store(
        store, CursorOwner(Mock(spec=Client), "tree", 1, lambda _: None)
    )


def select_result(ui: WorkspaceConsole, identity: str) -> None:
    tree = ui.result_trees.trees[-1]
    index = next(i for i, row in enumerate(tree.entries) if row.identity == identity)
    first, _ = ui.results.buffer.document.translate_index_to_position(tree.start)
    ui.results.buffer.cursor_position = (
        ui.results.buffer.document.translate_row_col_to_index(first + index, 0)
    )
    ui.app.layout.focus(ui.results.window)


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
def test_workspace_switches_traversal_without_reparsing(tmp_path: Path, engine: str) -> None:
    from clang_toolkit.cli.runtime.config import ConfigStore
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    client = Mock(spec=Client)
    runtime = (Runtime(client, cwd=tmp_path, environment={}) if engine == "legacy"
               else PrototypeRuntime(client, cwd=tmp_path, environment={}, script_engine=engine))
    runtime.config_store = ConfigStore(tmp_path, home=tmp_path / "home", system=tmp_path / "system.yaml")
    runtime.capture_display = True
    root = ParsedTree("fixture.cc", CursorOwner(client, "parsed-tree", 1, lambda _: None))
    client.parse.return_value = root
    retained = []

    def match(query, target, **options):
        assert target is root
        assert query == 'memberExpr(hasDeclaration(fieldDecl(hasName("value"))))'
        count = 2 if options["traversal_mode"] == pb.MATCH_TRAVERSAL_MODE_AS_IS else 1
        value = matches(count)
        retained.append(value)
        return value

    client.match_in.side_effect = match
    submissions = []

    async def execute(source: str) -> DispatchResult:
        result = dispatch_result(client, source, runtime)
        submissions.append(result)
        return result

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text('let root = parse "fixture.cc"\x0a')
        await wait_until(lambda: client.parse.call_count == 1 and not ui.busy)
        assert submissions[-1].success, submissions[-1].output
        target = "$root" if engine == "legacy" else "root"
        query = f'match memberExpr(hasDeclaration(fieldDecl(hasName("value")))) in {target}'
        for mode, count in [
            ("AsIs", 2), ("IgnoreUnlessSpelledInSource", 1),
            ("AsIs", 2), ("IgnoreUnlessSpelledInSource", 1),
        ]:
            before = len(submissions)
            pipe.send_text(f"set traversal {mode}\x0a")
            await wait_until(lambda: len(submissions) > before and not ui.busy)
            assert submissions[-1].success, submissions[-1].output
            assert runtime.config_store.effective["traversal"] == mode
            before = len(submissions)
            pipe.send_text(query + "\x0a")
            await wait_until(lambda: len(submissions) > before and not ui.busy)
            assert submissions[-1].success, submissions[-1].output
            assert len(ui.result_trees.trees) == 1, ui.results.text
            latest = ui.result_trees.trees[-1]
            assert len(latest.value) == count
            assert f"MatchValue [{count}]" in latest.text
            assert ui.results.text.count("MatchValue [") == 1
            assert "traversal:" not in ui.results.text
            assert not latest.expanded and not latest.pages
            # Expanded rows from the previous traversal must disappear too.
            select_result(ui, "$Matches")
            pipe.send_text("\x1b[C")
            await wait_until(lambda: len(latest.entries) > 1)
            ui.app.layout.focus(ui.editor)
            assert ui.status == "Ready"
        before = len(submissions)
        pipe.send_text(
            f"set traversal AsIs; {query}; "
            f"set traversal IgnoreUnlessSpelledInSource; {query}\x0a"
        )
        await wait_until(lambda: len(submissions) > before and not ui.busy)
        assert submissions[-1].success, submissions[-1].output
        assert len(ui.result_trees.trees) == 1
        assert len(ui.result_trees.trees[0].value) == 1
        assert ui.results.text.count("MatchValue [") == 1
        select_result(ui, "$Matches")
        pipe.send_text("\x1b[C")
        await wait_until(lambda: len(ui.result_trees.trees[-1].entries) > 1)
        assert "traversal:" not in ui.result_trees.trees[-1].text
        client.parse.assert_called_once()
        assert [call.kwargs["traversal_mode"] for call in client.match_in.call_args_list] == [
            pb.MATCH_TRAVERSAL_MODE_AS_IS, pb.MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE,
            pb.MATCH_TRAVERSAL_MODE_AS_IS, pb.MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE,
            pb.MATCH_TRAVERSAL_MODE_AS_IS, pb.MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE,
        ]

        async def submit(source: str) -> DispatchResult:
            ui.app.layout.focus(ui.editor)
            before = len(submissions)
            pipe.send_text(source + "\x0a")
            await wait_until(lambda: len(submissions) > before and not ui.busy)
            return submissions[-1]

        # Different queries and ordinary output keep their own results.
        other = matches(3)
        retained.append(other)
        client.match_in.side_effect = None
        client.match_in.return_value = other
        assert (await submit("match fieldDecl() in $root")).success
        assert (await submit("print [42]")).success
        previous = ui.result_trees.trees[0]
        client.match_in.side_effect = QueryError("request failed")
        assert not (await submit(query)).success
        assert ui.result_trees.trees[0] is previous
        assert ui.results.text.count("MatchValue [") == 2

        # Even an empty rerun replaces the old rows; insignificant whitespace
        # and the surrounding submission do not change the matcher identity.
        empty = matches(0)
        retained.append(empty)
        client.match_in.side_effect = None
        client.match_in.return_value = empty
        assert (await submit(query.replace("match ", "match  "))).success
        assert [tree.kind for tree in ui.result_trees.trees] == ["match", "print", "match"]
        assert ui.result_trees.trees[0].value is other
        assert ui.result_trees.trees[-1].value is empty
        assert ui.results.text.count("MatchValue [") == 2
        assert "MatchValue [1]" not in ui.results.text
        assert "MatchValue [2]" not in ui.results.text
        assert "MatchValue [0]" in ui.results.text
        assert query in ui.results.text
        for tree in ui.result_trees.trees:
            assert ui.results.text.startswith(tree.text, tree.start)
        for block in ui.transcript_lexer.blocks:
            assert ui.results.text.startswith(block.text, block.start)
        select_result(ui, "$Matches")
        pipe.send_text("\x1b[C")
        await wait_until(lambda: "$Matches" in ui.result_trees.trees[-1].expanded)
        assert ui.result_trees.trees[-1].value is empty
        client.parse.assert_called_once()

    try:
        asyncio.run(interact(tmp_path, drive, execute=execute, script_engine=engine))
    finally:
        runtime.close()
        for value in retained:
            value.close()


@pytest.mark.parametrize("prefix", ["", "print "])
@pytest.mark.parametrize(
    ("literal", "root", "child"),
    [("[1,2,3]", "$List", "[2] = 3"), ("{x: 1, y: 3}", "$Dictionary", "y = 3")],
)
def test_printed_collections_expand_in_existing_results(
    tmp_path: Path, prefix: str, literal: str, root: str, child: str,
) -> None:
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    runtime.capture_display = True
    runtime.execute(f"let data = {literal}")

    async def execute(source: str) -> DispatchResult:
        with patch("clang_toolkit.cli.runtime.evaluator.render", side_effect=AssertionError("collection serialized")):
            return dispatch_result(runtime.client, source, runtime)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text(f"{prefix}$data\x0a")
        await wait_until(lambda: bool(ui.result_trees.trees) and not ui.busy)
        assert "▸ " + root[1:] in ui.results.text
        select_result(ui, root)
        pipe.send_text("\x1b[C")
        await wait_until(lambda: child in ui.results.text)
        pipe.send_text("\x1b[D")
        await wait_until(lambda: child not in ui.results.text)
        assert ui.panel_kind == "help" and not ui.files_visible

    try:
        asyncio.run(interact(tmp_path, drive, execute=execute))
    finally:
        runtime.close()


def test_nested_collections_expand_without_exposing_helpers(tmp_path: Path) -> None:
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    runtime.capture_display = True
    runtime.execute("let data = {x: [1, {y: 3}], clear: 9}")

    async def execute(source: str) -> DispatchResult:
        return dispatch_result(runtime.client, source, runtime)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("print $data\x0a")
        await wait_until(lambda: bool(ui.result_trees.trees) and not ui.busy)
        for identity, marker in (
            ("$Dictionary", "clear = 9"),
            ('$Dictionary["x"]', "[0] = 1"),
            ('$Dictionary["x"][1]', "y = 3"),
        ):
            select_result(ui, identity)
            pipe.send_text("\x1b[C")
            await wait_until(lambda: marker in ui.results.text)
        assert not any(row.identity.endswith((".keys", ".isEmpty")) for row in ui.result_trees.trees[-1].entries)
        select_result(ui, '$Dictionary["x"][1]')
        pipe.send_text("\r")
        await wait_until(lambda: "y = 3" not in ui.results.text)

    try:
        asyncio.run(interact(tmp_path, drive, execute=execute))
    finally:
        runtime.close()


@pytest.mark.parametrize("value", [[], {}, [1] * 125, {f"key{i}": i for i in range(125)}])
def test_collection_snapshots_are_paged_and_empty_values_stay_expandable(value: object) -> None:
    root = "$Dictionary" if isinstance(value, dict) else "$List"
    first = display_snapshot("print", value, frozenset({root}), {})
    assert first is not None and first[0].expandable
    if not value:
        assert len(first) == 1 and "[0]" in first[0].label
        return
    assert len([row for row in first if row.page is None and row.identity != root + ":page" and row.depth == 1]) == 50
    assert next(row for row in first if row.identity == root + ":next").page == (root, 1)
    second = display_snapshot("print", value, frozenset({root}), {root: 1})
    assert second is not None
    assert "Items 51–100 of 125" in second[1].label
    assert any(row.identity == root + ":previous" for row in second)
    assert any(row.label == ("key50 = 50" if isinstance(value, dict) else "[50] = 1") for row in second)


@pytest.mark.parametrize("literal", ["[1,2,3]", "{x: 1, y: 3}"])
def test_collection_file_and_standard_prompt_output_stays_textual(tmp_path: Path, literal: str) -> None:
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    try:
        ordinary = dispatch_result(runtime.client, f"print {literal}", runtime)
        assert ordinary.outline_value is None and ordinary.output
        runtime.capture_display = True
        redirected = dispatch_result(runtime.client, f'print {literal} to "out.txt"', runtime)
        assert redirected.success and redirected.outline_value is None
        assert (tmp_path / "out.txt").read_text().strip() == ordinary.output.strip()
        dispatch_result(runtime.client, 'set output to "sink.txt"', runtime)
        configured = dispatch_result(runtime.client, f"print {literal}", runtime)
        assert configured.success and configured.outline_value is None
        assert (tmp_path / "sink.txt").read_text().strip() == ordinary.output.strip()
    finally:
        runtime.close()


def test_match_rows_show_only_named_bindings_and_ast_properties() -> None:
    value = matches()
    try:
        rows = outline_snapshot(
            {"rows": value}, frozenset({"$rows", "$rows[0]", "$rows[0].f", "$rows[0].f.value.name"}),
        )
        assert {row.identity for row in rows if row.depth == 2} == {"$rows[0].f"}
        assert any(row.label == "qualified_name = 'demo::run0'" for row in rows)
        name = next(row for row in rows if row.identity == "$rows[0].f.value.name.identifier")
        assert name.label == "identifier = 'run0'"
        assert dict(name.commands)["p"] == "print $rows[0].f.value.name.identifier"
        assert not any(row.label == "name = 'f'" for row in rows)
        assert not any(row.identity.endswith((".parameter_name", ".record_name", ".type_name")) for row in rows)
        assert not any(
            row.identity.endswith((".bindings", ".source_match_index", ".source_file", ".keys", ".isEmpty", ".scope"))
            for row in rows
        )
    finally:
        value.close()


def test_real_binding_names_that_overlap_helpers_remain_visible() -> None:
    row = results.MatchResult()
    for name in ("bindings", "source_file", "source_match_index", "clear"):
        row.bindings[name].node.function_decl.function.declarator.value.named.qualified_name = f"demo::{name}"
    store = RowStore()
    store.append(row.SerializeToString(), binding_names=row.bindings)
    value = MatchValue._from_store(store, CursorOwner(Mock(spec=Client), "names", 1, lambda _: None))
    try:
        rows = outline_snapshot({"rows": value}, frozenset({"$rows", "$rows[0]"}))
        bindings = [row for row in rows if row.depth == 2]
        assert len(bindings) == 4
        assert all(" - demo::" in row.label for row in bindings)
        reserved = next(row for row in bindings if row.label.startswith("bindings -"))
        assert dict(reserved.commands)["p"] == 'print $rows[0].bindings["bindings"]'
    finally:
        value.close()


def test_session_list_captures_inventory_once_and_expands_in_results(tmp_path: Path) -> None:
    client = Mock(spec=Client)
    response = pb.ListSessionsResponse()
    response.sessions.add(session_id="session-1", file_path="/src/example.cpp", row_count=3)
    client.list_sessions.return_value = response
    runtime = Runtime(client, cwd=tmp_path, environment={})
    runtime.capture_display = True

    async def execute(source: str) -> DispatchResult:
        return dispatch_result(client, source, runtime)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("session list\n")
        await wait_until(lambda: bool(ui.result_trees.trees) and not ui.busy)
        assert "▸ Sessions" in ui.results.text
        select_result(ui, "$Sessions")
        pipe.send_text("\x1b[C")
        await wait_until(lambda: "session-1 · example.cpp" in ui.results.text)
        select_result(ui, "$Sessions[0]")
        pipe.send_text("\x1b[C")
        await wait_until(lambda: "row_count = 3" in ui.results.text)
        assert "session_id = 'session-1'" in ui.results.text
        assert not any(row.identity.endswith(".keys") for row in ui.result_trees.trees[-1].entries)

    try:
        asyncio.run(interact(tmp_path, drive, execute=execute))
        client.list_sessions.assert_called_once()
    finally:
        runtime.close()


def test_empty_session_list_has_expandable_zero_count() -> None:
    from clang_toolkit.cli.runtime.semantic import view

    rows = display_snapshot("session_list", view(pb.ListSessionsResponse()), frozenset({"$Sessions"}), {})
    assert rows is not None and len(rows) == 1
    assert rows[0].label == "$Sessions [0]"


def test_matches_expand_in_results_and_keep_commands_help_and_draft(
    tmp_path: Path,
) -> None:
    value = matches()

    async def execute(source: str) -> DispatchResult:
        if source == "print $rows":
            return DispatchResult("legacy JSON", True, outline_value=("print", value))
        return DispatchResult("after result", True)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("print $rows\n")
        await wait_until(lambda: bool(ui.result_trees.trees) and not ui.busy)
        assert "legacy JSON" not in ui.results.text
        before = ui.results.text
        ui.buffer.document = Document('print "draft"', 6)
        select_result(ui, "$Matches")
        content = ui.results.control.create_content(100, 20)
        assert any(
            "class:tree-selected" in fragment[0]
            for fragment in content.get_line(
                ui.results.buffer.document.cursor_position_row
            )
        )
        pipe.send_text("\x1b[C")
        await wait_until(lambda: "[0] · MatchRow" in ui.results.text)
        # Right enters the expanded root's first child; another Right expands it.
        pipe.send_text("\x1b[C")
        await wait_until(
            lambda: ui.results.buffer.document.cursor_position_row
            > before.count("\n") - 2
        )
        pipe.send_text("\x1b[C")
        await wait_until(lambda: "f - demo::run0" in ui.results.text)
        select_result(ui, "$Matches[0].f")
        pipe.send_text("\r")
        await wait_until(lambda: "qualified_name = 'demo::run0'" in ui.results.text)
        assert ui.buffer.text == 'print "draft"' and ui.buffer.cursor_position == 6
        assert "  1 │ print $rows" in ui.results.text
        assert ui.files_visible is False and ui.panel_kind == "help"
        pipe.send_text("\x1b[D")
        await wait_until(lambda: "qualified_name = 'demo::run0'" not in ui.results.text)
        select_result(ui, "$Matches[0]")
        pipe.send_text("\x1b[D")
        await wait_until(lambda: "f - demo::run0" not in ui.results.text)
        select_result(ui, "$Matches")
        pipe.send_text("\x1b[D")
        await wait_until(lambda: "[0] · MatchRow" not in ui.results.text)
        assert ui.result_trees.trees[-1].text.startswith("▸ Matches")

    try:
        asyncio.run(interact(tmp_path, drive, execute=execute))
    finally:
        value.close()


def test_result_tree_pages_and_keeps_later_styled_output_at_correct_offsets(
    tmp_path: Path,
) -> None:
    value = matches(125)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        await ui.result_trees.show("print", value)
        ui.write_markdown("## After tree\n\n```ctk\nprint 7\n```")
        later = ui.transcript_lexer.blocks[-1]
        select_result(ui, "$Matches")
        pipe.send_text("\r")
        await wait_until(lambda: "Items 1–50" in ui.results.text)
        assert ui.results.text.startswith(later.text, later.start)
        select_result(ui, "$Matches:next")
        pipe.send_text("\r")
        await wait_until(lambda: "Items 51–100" in ui.results.text)
        assert "[50]" in ui.results.text and "[0] · MatchRow" not in ui.results.text
        assert ui.results.text.startswith(later.text, later.start)
        select_result(ui, "$Matches:previous")
        pipe.send_text("\r")
        await wait_until(lambda: "Items 1–50" in ui.results.text)
        assert ui.results.text.startswith(later.text, later.start)
        assert len(ui.result_trees.trees[-1].entries) < 55

    try:
        asyncio.run(interact(tmp_path, drive))
    finally:
        value.close()


def test_result_mouse_triangle_toggles_without_executing_commands(
    tmp_path: Path,
) -> None:
    value = matches()

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        await ui.result_trees.show("print", value)
        await wait_until(lambda: ui.results.window.render_info is not None)
        # Results start on row 2; initial title is first row, tree second.
        pipe.send_text("\x1b[<0;1;3M\x1b[<0;1;3m")
        await wait_until(lambda: "[0] · MatchRow" in ui.results.text)
        pipe.send_text("\x1b[<0;1;3M\x1b[<0;1;3m")
        await wait_until(lambda: "[0] · MatchRow" not in ui.results.text)
        assert ui.buffer.text == "" and not ui.busy

    try:
        asyncio.run(interact(tmp_path, drive))
    finally:
        value.close()


def test_empty_matches_show_expandable_zero_count(tmp_path: Path) -> None:
    value = matches(0)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        await ui.result_trees.show("match", value)
        select_result(ui, "$Matches")
        pipe.send_text("\r")
        await wait_until(lambda: ui.result_trees.trees[-1].text.startswith("▾ Matches"))
        assert "[0]" in ui.results.text and len(ui.result_trees.trees[-1].entries) == 1

    try:
        asyncio.run(interact(tmp_path, drive))
    finally:
        value.close()


def test_files_group_by_directory_preserve_duplicate_profiles_and_absolute_indexes() -> (
    None
):
    manifest = FileSet(
        (
            InputDescriptor("/project/src/ui/widget.cpp", profile_id="debug"),
            InputDescriptor("/project/src/ui/widget.cpp", profile_id="release"),
            InputDescriptor("/project/include/widget.hpp"),
        )
    )
    expanded = {"$files"}
    collapsed = outline_snapshot({"files": manifest}, frozenset(expanded))
    assert any(
        row.identity == "$files:dir:/project" and row.expandable for row in collapsed
    )
    assert not any(".inputs[" in row.identity for row in collapsed)
    expanded.update(
        {
            "$files:dir:/project",
            "$files:dir:/project/src",
            "$files:dir:/project/src/ui",
            "$files:dir:/project/include",
        }
    )
    rows = outline_snapshot({"files": manifest}, frozenset(expanded))
    files = [row for row in rows if ".inputs[" in row.identity]
    assert len(files) == 3
    assert {dict(row.commands)["p"] for row in files} == {
        f"print $files.inputs[{i}]" for i in range(3)
    }


def test_resource_folders_and_details_are_collapsible_without_losing_actions() -> None:
    files = (
        resources.FileInfo(
            lease_id="lease", input=resources.InputDescriptor(file_path="/src/a.cpp")
        ),
    )
    sessions = pb.ListSessionsResponse(
        sessions=[pb.SessionInfo(session_id="cursor", row_count=4)]
    )
    roots = resource_snapshot(files, sessions, "attached1", frozenset())
    assert [row.identity for row in roots] == [":files", ":sessions"]
    entries = resource_snapshot(
        files, sessions, "attached1", frozenset({":files", ":sessions"})
    )
    assert next(row for row in entries if row.identity == "file:lease").expandable
    assert not any(row.depth == 2 for row in entries)
    details = resource_snapshot(
        files, sessions, "attached1", frozenset({":files", ":sessions", "file:lease"})
    )
    assert any(row.depth == 2 for row in details)
    session = next(row for row in details if row.identity == "session:cursor")
    assert dict(session.commands)["a"] == 'session attach "cursor" into $attached1'


def test_runtime_capture_is_opt_in_and_file_output_stays_textual(
    tmp_path: Path,
) -> None:
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    value = matches()
    runtime.bindings["rows"] = value
    try:
        plain = dispatch_result(runtime.client, "print $rows", runtime)
        assert plain.outline_value is None and "demo::run0" in plain.output
        runtime.capture_display = True
        tree = dispatch_result(runtime.client, "print $rows", runtime)
        assert tree.outline_value == ("print", value)
        redirected = dispatch_result(
            runtime.client, 'print $rows to "out.txt"', runtime
        )
        assert (
            redirected.outline_value is None
            and "demo::run0" in (tmp_path / "out.txt").read_text()
        )
        config = dispatch_result(runtime.client, 'set output to "sink.txt"', runtime)
        assert config.success
        assert (
            dispatch_result(runtime.client, "print $rows", runtime).outline_value
            is None
        )
        assert "demo::run0" in (tmp_path / "sink.txt").read_text()
    finally:
        runtime.close()


def test_bindings_command_displays_live_branches_in_results(tmp_path: Path) -> None:
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    runtime.capture_display = True
    runtime.bindings.update(
        {"config": {"count": 2}, "files": FileSet((InputDescriptor("/src/a.cpp"),))}
    )

    async def execute(source: str) -> DispatchResult:
        return await asyncio.to_thread(dispatch_result, runtime.client, source, runtime)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("bindings\n")
        await wait_until(lambda: bool(ui.result_trees.trees) and not ui.busy)
        select_result(ui, "$config")
        pipe.send_text("\r")
        await wait_until(lambda: "count = 2" in ui.results.text)
        select_result(ui, "$files")
        pipe.send_text("\r")
        await wait_until(lambda: "/src" in ui.results.text)
        select_result(ui, "$files:dir:/src")
        pipe.send_text("\r")
        await wait_until(lambda: "a.cpp" in ui.results.text)
        assert ui.panel_kind == "help" and ui.files_visible is False

    try:
        asyncio.run(interact(tmp_path, drive, execute=execute))
    finally:
        runtime.close()


def test_clear_and_trim_release_tree_previews_and_bound_large_expansions(
    tmp_path: Path,
) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        await ui.result_trees.show(
            "bindings_list", {"wide": ["x" * 4096 for _ in range(125)]}
        )
        select_result(ui, "$wide")
        pipe.send_text("\r")
        await wait_until(lambda: "[0]" in ui.results.text)
        assert len(ui.results.text) <= MAX_TRANSCRIPT_CHARS
        ui._append("x" * MAX_TRANSCRIPT_CHARS)
        assert (
            not ui.result_trees.trees and len(ui.results.text) <= MAX_TRANSCRIPT_CHARS
        )
        await ui.result_trees.show("bindings_list", {"value": [1]})
        ui.clear_results()
        assert not ui.result_trees.trees and not ui.transcript_lexer.blocks

    asyncio.run(interact(tmp_path, drive, output=SizedOutput(columns=150)))


def test_file_inventory_uses_real_paths_and_typed_properties() -> None:
    files = (
        resources.FileInfo(
            lease_id="lease", input=resources.InputDescriptor(file_path="/src/a.cpp")
        ),
    )
    entries = display_snapshot(
        "file_list", files, frozenset({"$Files", "$Files:dir:/src", "$Files[0]"}), {}
    )
    assert any("a.cpp" in row.label for row in entries)
    assert any("lease_id = 'lease'" in row.label for row in entries)
    assert display_snapshot("print", '{"bindings": {}}', frozenset(), {}) is None


def test_typed_display_reads_no_rows_until_expansion_then_only_selected_page(
    tmp_path: Path,
) -> None:
    value = matches(125)
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    runtime.capture_display = True
    runtime.bindings["rows"] = value
    try:
        with patch.object(
            RowStore, "read", autospec=True, side_effect=RowStore.read
        ) as read:
            result = dispatch_result(runtime.client, "print $rows", runtime)
            assert result.success and result.output == ""
            display_snapshot(*result.outline_value, frozenset(), {})
            assert read.call_count == 0
            display_snapshot(
                *result.outline_value, frozenset({"$Matches"}), {"$Matches": 1}
            )
            assert [call.args[1] for call in read.call_args_list] == list(
                range(50, 100)
            )
        assigned = dispatch_result(runtime.client, "let another = $rows", runtime)
        assert assigned.success and assigned.outline_value is None
    finally:
        runtime.close()


def test_file_and_binding_arrows_enter_children_and_collapse_to_parent(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "src"
    folder.mkdir()
    (folder / "file.cpp").write_text("int x;")

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("\x1bOR")
        await wait_until(lambda: bool(ui.files.entries))
        pipe.send_text("\x1b[C")
        await wait_until(lambda: len(ui.files.entries) == 2)
        pipe.send_text("\x1b[C")
        await wait_until(lambda: ui.files.current.path.name == "file.cpp")
        pipe.send_text("\x1b[D\x1b[D")
        await wait_until(lambda: len(ui.files.entries) == 1)
        assert ui.files.current.path == folder and not ui.buffer.text
        pipe.send_text("\x1bOR")
        await wait_until(lambda: not ui.files_visible)

        async def read_outline(expanded, pages):
            return outline_snapshot({"config": {"count": 2}}, expanded, pages)

        ui.read_outline = read_outline
        ui.toggle_panel("outline")
        await wait_until(lambda: bool(ui.outline.entries))
        pipe.send_text("\x1b[C")
        await wait_until(lambda: len(ui.outline.entries) == 2)
        pipe.send_text("\x1b[C")
        await wait_until(lambda: ui.outline.selected == 1)
        pipe.send_text("\x1b[D\x1b[D")
        await wait_until(lambda: len(ui.outline.entries) == 1)
        assert ui.outline.current.identity == "$config"

    asyncio.run(interact(tmp_path, drive, output=SizedOutput(columns=150)))


def test_old_result_trees_become_explicit_static_previews(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        for index in range(21):
            await ui.result_trees.show("bindings_list", {f"value{index}": [index]})
        assert len(ui.result_trees.trees) == 20
        assert "preview; print again to expand" in ui.results.text
        assert not any(
            tree.entries[0].identity == "$value0" for tree in ui.result_trees.trees
        )
        for tree in ui.result_trees.trees:
            assert ui.results.text.startswith(tree.text, tree.start)

    asyncio.run(interact(tmp_path, drive))


def test_match_rerun_replaces_an_evicted_static_preview(tmp_path: Path) -> None:
    old, new = matches(2), matches(1)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        await ui.result_trees.show("match", old, result_key="same matcher")
        for index in range(20):
            await ui.result_trees.show("print", [index])
        assert "MatchValue [2]" in ui.results.text
        assert not any(tree.value is old for tree in ui.result_trees.trees)
        await ui.result_trees.show("match", new, result_key="same matcher")
        assert "MatchValue [2]" not in ui.results.text
        assert ui.results.text.count("MatchValue [") == 1
        assert "MatchValue [1]" in ui.results.text
        for tree in ui.result_trees.trees:
            assert ui.results.text.startswith(tree.text, tree.start)
        for block in ui.transcript_lexer.blocks:
            assert ui.results.text.startswith(block.text, block.start)

    try:
        asyncio.run(interact(tmp_path, drive))
    finally:
        old.close()
        new.close()
