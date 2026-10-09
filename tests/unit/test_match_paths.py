"""Directory and glob targets preserve retained match semantics."""

import pytest
from threading import Barrier, Event

from clang_toolkit.cli.runtime.evaluator import EvaluationError
from clang_toolkit.cli.runtime.filesystem import Directory, from_path
from clang_toolkit.match_values import NativeMatchCollection
from test_reasoning_values import _match_value, _runtime


@pytest.mark.parametrize("absolute", [False, True])
@pytest.mark.parametrize("target_kind", ["directory", "glob", "recursive_glob"])
def test_directory_and_glob_targets_are_sorted_typed_collections(tmp_path, absolute, target_kind):
    source = tmp_path / "source files"
    source.mkdir()
    nested = source / "nested"
    nested.mkdir()
    for name in ("b.cpp", "a.cpp", "ignored.h", "notes.txt"):
        (source / name).write_text("")
    (nested / "c.cpp").write_text("")
    (source / "directory.cpp").mkdir()
    base = str(source) if absolute else source.name
    target = base + {"directory": "", "glob": "/*.cpp", "recursive_glob": "/**/*.cpp"}[target_kind]
    client, runtime = _runtime(tmp_path)
    client.match_in.side_effect = lambda *args, **kwargs: _match_value()

    result = runtime.evaluate(f"let rows = match functionDecl().bind('f') in '{target}'")

    expected = [str(source / "a.cpp"), str(source / "b.cpp")]
    if target_kind != "glob":
        expected.append(str(nested / "c.cpp"))
    assert isinstance(result, NativeMatchCollection)
    assert result.files == tuple(expected)
    assert len(result) == len(expected)
    assert [row.source_file for row in result] == expected
    assert runtime.evaluate("$rows[0].source_file") == expected[0]
    runtime.evaluate("match parmVarDecl() in $rows[0].f")
    assert client.match_in.call_args.args[1].source_file == expected[0]


def test_directory_value_and_string_variable_expand(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "a.cc").write_text("")
    client, runtime = _runtime(tmp_path)
    client.match_in.side_effect = lambda *args, **kwargs: _match_value()
    runtime.bindings["directory"] = from_path(source, tmp_path)
    assert isinstance(runtime.bindings["directory"], Directory)
    assert len(runtime.evaluate("match functionDecl() in $directory")) == 1
    runtime.evaluate('let pattern = "src/*.cc"')
    assert len(runtime.evaluate("match functionDecl() in $pattern")) == 1


@pytest.mark.parametrize("target", ["empty", "missing/*.cpp"])
def test_empty_directory_and_unmatched_glob_return_empty_collection(tmp_path, target):
    (tmp_path / "empty").mkdir()
    client, runtime = _runtime(tmp_path)
    result = runtime.evaluate(f'match functionDecl() in "{target}"')
    assert isinstance(result, NativeMatchCollection)
    assert result.files == ()
    assert len(result) == 0
    client.match_in.assert_not_called()


@pytest.mark.parametrize("target", ["src", "src/*.cpp"])
def test_expansion_limit_preserves_assignment_without_requests(tmp_path, target):
    source = tmp_path / "src"
    source.mkdir()
    for index in range(5):
        (source / f"{index}.cpp").write_text("")
    client, runtime = _runtime(tmp_path)
    runtime.bindings["rows"] = "previous"
    with pytest.raises(EvaluationError, match="configured limit of 4"):
        runtime.evaluate(f'let rows = match functionDecl() in "{target}"')
    assert runtime.bindings["rows"] == "previous"
    client.match_in.assert_not_called()


def test_single_file_and_file_variable_keep_existing_value(tmp_path):
    file = tmp_path / "a.cpp"
    file.write_text("")
    client, runtime = _runtime(tmp_path)
    match = _match_value()
    client.match_in.return_value = match
    assert runtime.evaluate('match functionDecl() in "a.cpp"') is match
    runtime.bindings["file"] = from_path(file, tmp_path)
    assert runtime.evaluate("match functionDecl() in $file") is match


def test_glob_deduplicates_resolved_files(tmp_path):
    file = tmp_path / "a.cpp"
    file.write_text("")
    (tmp_path / "alias.cpp").symlink_to(file)
    client, runtime = _runtime(tmp_path)
    client.match_in.return_value = _match_value()
    result = runtime.evaluate('match functionDecl() in "*.cpp"')
    assert result.files == (str(file),)
    client.match_in.assert_called_once()


def test_parallel_matches_keep_input_order_and_compiler_settings(tmp_path):
    client, runtime = _runtime(tmp_path)
    started = Barrier(2)
    second_finished = Event()
    first, second = _match_value(), _match_value()
    runtime.config_store.effective["extra_args"] = ["-std=c++20"]
    runtime.config_store.effective["traversal"] = "IgnoreUnlessSpelledInSource"

    def matching(query, target, **options):
        started.wait(timeout=5)
        if target.endswith("a.cpp"):
            assert second_finished.wait(timeout=5)
            return first
        second_finished.set()
        return second

    client.match_in.side_effect = matching
    result = runtime.evaluate('match functionDecl() in ["a.cpp", "b.cpp"]')

    assert result.matches == (first, second)
    assert result.files == (str(tmp_path / "a.cpp"), str(tmp_path / "b.cpp"))
    assert all(call.kwargs["compile_arguments"] == ["-std=c++20"]
               and call.kwargs["traversal_mode"] != 0
               for call in client.match_in.call_args_list)


def test_parallel_failure_cleans_later_success_and_preserves_assignment(tmp_path):
    client, runtime = _runtime(tmp_path)
    started = Barrier(2)
    failed = Event()
    successful = _match_value()
    runtime.bindings["rows"] = "previous"

    def matching(query, target, **options):
        started.wait(timeout=5)
        if target.endswith("a.cpp"):
            failed.set()
            raise RuntimeError("first file failed")
        assert failed.wait(timeout=5)
        return successful

    client.match_in.side_effect = matching
    with pytest.raises(RuntimeError, match="first file failed"):
        runtime.evaluate('let rows = match functionDecl() in ["a.cpp", "b.cpp"]')
    assert successful._owner.closed
    assert runtime.bindings["rows"] == "previous"


def test_async_expression_cancel_cancels_every_parallel_request(monkeypatch, tmp_path):
    import asyncio
    from clang_toolkit import AsyncClient

    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        entered = asyncio.Event()
        requests = []
        cancelled = []

        async def matching(request, **options):
            requests.append(request.file.file_path)
            if len(requests) == 2:
                entered.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.append(request.file.file_path)

        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_stream_cursor_match", matching)
        operation = asyncio.create_task(client.execute(
            'let rows = match functionDecl() in ["a.cpp", "b.cpp"]',
            working_directory=tmp_path,
        ))
        try:
            await asyncio.wait_for(entered.wait(), timeout=5)
        finally:
            operation.cancel()
        with pytest.raises(asyncio.CancelledError):
            await operation
        assert len(cancelled) == 2
        assert sorted(cancelled) == sorted(requests)
        assert client._value_operation_count == 0
        assert "rows" not in client._expression_runtime.bindings
        await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("target", ['"*.cpp"', '["a.cpp", "b.cpp"]'])
def test_async_expression_uses_configured_file_limit(monkeypatch, tmp_path, target):
    import asyncio
    from dataclasses import replace
    from unittest.mock import AsyncMock
    from clang_toolkit import AsyncClient

    for name in ("a.cpp", "b.cpp"):
        (tmp_path / name).write_text("")
    mock_client, _ = _runtime(tmp_path)
    config = replace(mock_client._configuration(), max_files=1)

    async def run():
        client = AsyncClient(config=config)
        client._loop = asyncio.get_running_loop()
        matching = AsyncMock()
        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_stream_cursor_match", matching)
        with pytest.raises(EvaluationError, match="configured limit of 1"):
            await client.execute(f'match functionDecl() in {target}', working_directory=tmp_path)
        matching.assert_not_called()
        await client.aclose()

    asyncio.run(run())
