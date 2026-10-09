"""Network BDD scenarios against the locally built C++ gRPC server."""

from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import grpc
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from clang_toolkit.client import AsyncClient, QueryError
from clang_toolkit._generated.ast.v1 import common_pb2
from clang_toolkit.cursors import CursorError
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit import (
    Matcher, callExpr, cxxBoolLiteral, equals, floatLiteral,
    functionDecl, hasName, integerLiteral,
)

pytestmark = pytest.mark.e2e
scenarios("network.feature")


@given("a C++ file with a function containing two calls", target_fixture="typed_match_source")
def typed_match_source(tmp_path: Path) -> Path:
    source = tmp_path / "typed_match.cc"
    source.write_text(
        "void leaf();\nvoid outer() { leaf(); leaf(); }\nvoid café() {}\n"
        "int integer_value() { return 42; }\n"
        "double float_value() { return 3.25; }\n"
        "bool bool_value() { return true; }\n",
        encoding="utf-8",
    )
    return source


@when("I compare typed and string matcher expressions through the async SDK",
      target_fixture="typed_match_results")
def compare_typed_and_string_matchers(server: RunningServer, typed_match_source: Path):
    from clang_toolkit import Client

    root_typed = functionDecl(hasName("outer")).bind("f")
    root_string = 'functionDecl(hasName("outer")).bind("f")'
    calls_typed = callExpr().bind("call")
    calls_string = 'callExpr().bind("call")'
    unicode_typed = functionDecl(hasName("café"))
    unicode_string = 'functionDecl(hasName("café"))'
    escaped_name = 'missing "quoted" \\ path\nnext'
    escaped_typed = functionDecl(hasName(escaped_name))
    escaped_binding = 'label "quoted" \\ path\nnext'
    escaped_binding_typed = functionDecl(hasName("café")).bind(escaped_binding)
    integer_typed = integerLiteral(equals(42))
    float_typed = floatLiteral(equals(3.25))
    bool_typed = cxxBoolLiteral(equals(True))
    assert isinstance(root_typed, Matcher)

    async def run():
        async with AsyncClient(server.endpoint) as client:
            typed = await client.match_file(typed_match_source, root_typed)
            string = await client.match_file(typed_match_source, root_string)
            typed_calls = await client.continue_match(typed.session_id, "f", calls_typed)
            string_calls = await client.continue_match(string.session_id, "f", calls_string)
            unicode_rows = await client.match_file(typed_match_source, unicode_typed)
            unicode_string_rows = await client.match_file(typed_match_source, unicode_string)
            escaped_rows = await client.match_file(typed_match_source, escaped_typed)
            labeled_rows = await client.match_file(typed_match_source, escaped_binding_typed)
            async with await client.parse(typed_match_source) as tree:
                async with await tree.match(root_typed) as tree_rows:
                    async with await tree_rows[0].binding("f").match(calls_typed) as selected_calls:
                        high_level_counts = (len(tree_rows), len(selected_calls))
                async with await client.match_in(integer_typed, tree) as integers:
                    integer_count = len(integers)
                async with await client.match_in(float_typed, tree) as floats:
                    float_count = len(floats)
                async with await client.match_in(bool_typed, tree) as booleans:
                    bool_count = len(booleans)
            try:
                return (len(typed.results), len(string.results),
                        len(typed_calls.results), len(string_calls.results),
                        len(unicode_rows.results), len(unicode_string_rows.results),
                        len(escaped_rows.results),
                        escaped_binding in labeled_rows.results[0].bindings,
                        sorted(labeled_rows.results[0].bindings), high_level_counts,
                        integer_count, float_count, bool_count)
            finally:
                await client.close_match(typed.session_id)
                await client.close_match(string.session_id)
                await client.close_match(unicode_rows.session_id)
                await client.close_match(unicode_string_rows.session_id)
                await client.close_match(escaped_rows.session_id)
                await client.close_match(labeled_rows.session_id)

    async_counts = asyncio.run(run())
    with Client(server.endpoint) as client:
        typed = client.match_file(typed_match_source, root_typed)
        string = client.match_file(typed_match_source, root_string)
        typed_calls = client.continue_match(typed.session_id, "f", calls_typed)
        string_calls = client.continue_match(string.session_id, "f", calls_string)
        unicode_rows = client.match_file(typed_match_source, unicode_typed)
        unicode_string_rows = client.match_file(typed_match_source, unicode_string)
        escaped_rows = client.match_file(typed_match_source, escaped_typed)
        labeled_rows = client.match_file(typed_match_source, escaped_binding_typed)
        with client.parse(typed_match_source) as tree:
            with tree.match(root_typed) as tree_rows:
                with tree_rows[0].binding("f").match(calls_typed) as selected_calls:
                    high_level_counts = (len(tree_rows), len(selected_calls))
            with client.match_in(integer_typed, tree) as integers:
                integer_count = len(integers)
            with client.match_in(float_typed, tree) as floats:
                float_count = len(floats)
            with client.match_in(bool_typed, tree) as booleans:
                bool_count = len(booleans)
        sync_counts = (len(typed.results), len(string.results),
                       len(typed_calls.results), len(string_calls.results),
                       len(unicode_rows.results), len(unicode_string_rows.results),
                       len(escaped_rows.results),
                       escaped_binding in labeled_rows.results[0].bindings,
                       sorted(labeled_rows.results[0].bindings), high_level_counts,
                       integer_count, float_count, bool_count)
        client.close_match(typed.session_id)
        client.close_match(string.session_id)
        client.close_match(unicode_rows.session_id)
        client.close_match(unicode_string_rows.session_id)
        client.close_match(escaped_rows.session_id)
        client.close_match(labeled_rows.session_id)
    return async_counts, sync_counts


@then("both matcher forms return equal results through retained continuation")
def verify_typed_and_string_matchers(typed_match_results) -> None:
    expected = (
        1, 1, 2, 2, 1, 1, 0, True,
        ['label "quoted" \\ path\nnext', "root"], (1, 2), 1, 1, 1,
    )
    assert typed_match_results == (expected, expected)


@when("I request versions through the CLI and SDK", target_fixture="reported_versions")
def reported_versions(server: RunningServer):
    import sys
    from clang_toolkit import Client
    from clang_toolkit.version import client_version

    def command(*arguments):
        result = subprocess.run(arguments, text=True, capture_output=True, timeout=15, check=True)
        return result.stdout.strip()

    executable = os.environ.get("CTK_SERVER", str(Path(__file__).parents[2] / "build/dev/server/ctk-server"))
    binary = command(executable, "--version", "-c", "/nonexistent/version-test.yaml")
    local = command(sys.executable, "-m", "clang_toolkit.cli.app", "--version", "-c", "/nonexistent/version-test.yaml")
    remote = command(sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint, "--server-version")
    with Client(server.endpoint) as client:
        sync = client.server_version().format("ctk-server")

    async def run():
        async with AsyncClient(server.endpoint) as client:
            return (await client.server_version()).format("ctk-server")

    return binary, local, remote, sync, asyncio.run(run()), client_version().format("ctk")


@then("the remote version matches the running binary and both revisions are printed")
def verify_reported_versions(reported_versions):
    binary, local, remote, sync, asynchronous, expected = reported_versions
    assert binary == remote == sync == asynchronous
    assert local == expected
    assert "revision " in binary and "revision " in local
    assert "revision unknown" not in local


@given("a C++ file with a missing project header", target_fixture="invalid_source")
def invalid_source(tmp_path: Path) -> Path:
    source = tmp_path / "invalid.cc"
    source.write_text('#include <ctk_missing_project_header.hpp>\nint value;\n')
    return source


@given("a C++ file including dependent vector conversions", target_fixture="vector_source")
def dependent_vector_source(tmp_path: Path) -> Path:
    (tmp_path / "conversions.hpp").write_text(
        "template<class D, class S> D convert(S value) {\n"
        "  return __builtin_convertvector(value, D);\n}\n"
        "using IntVector = int __attribute__((ext_vector_type(2)));\n"
        "using FloatVector = float __attribute__((ext_vector_type(2)));\n"
        "FloatVector concrete(IntVector value) {\n"
        "  return __builtin_convertvector(value, FloatVector);\n}\n",
        encoding="utf-8",
    )
    source = tmp_path / "vectors.cc"
    source.write_text('#include "conversions.hpp"\nint main() { return 0; }\n',
                      encoding="utf-8")
    return source


@when("I match every function through the SDK and real console", target_fixture="vector_results")
def match_vector_functions(server: RunningServer, vector_source: Path, tmp_path: Path):
    import sys

    async def run():
        async with AsyncClient(server.endpoint) as client:
            tree = await client.parse(vector_source)
            rows = await client.match_in('functionDecl().bind("x")', tree)
            assert len(rows) == 3
            assert all(row.bindings["x"].node.HasField("function_decl") for row in rows)
            assert server.process.poll() is None
            await client.server_version()
            followup = await client.match_in('functionDecl(hasName("main")).bind("x")', tree)
            assert len(followup) == 1
            return len(rows)

    count = asyncio.run(run())
    console = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint],
        input=f'let x = parse "{vector_source}"\n'
              'let m = match functionDecl().bind("x") in $x\n'
              'print $m\nprint "VECTOR_MATCH_OK"\nquit\n',
        env=dict(os.environ, XDG_STATE_HOME=str(tmp_path / "vector-state")),
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=30, check=False,
    )
    return count, console


@then("the vector functions are returned and the server remains usable")
def vector_server_remains_usable(server: RunningServer, vector_results):
    count, console = vector_results
    assert count == 3
    assert console.returncode == 0, console.stdout
    assert "VECTOR_MATCH_OK" in console.stdout
    assert "convert" in console.stdout and "concrete" in console.stdout
    assert "error:" not in console.stdout and "syntax error" not in console.stdout
    assert server.process.poll() is None


@when("I parse the invalid source through the SDK and real console", target_fixture="parse_errors")
def parse_invalid_source(server: RunningServer, invalid_source: Path):
    import sys
    from clang_toolkit import Client

    with Client(server.endpoint) as client:
        with pytest.raises(CursorError) as failure:
            client.parse(invalid_source)
    console = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint],
        input=f'let tree = parse "{invalid_source}"\nquit\n',
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
        check=False,
    )
    assert console.returncode == 1, console.stdout
    return str(failure.value), console.stdout


@then("both report the missing header and its source location")
def parse_error_diagnostics(parse_errors):
    for output in parse_errors:
        assert "ctk_missing_project_header.hpp" in output
        assert "file not found" in output
        assert "invalid.cc:1:10:" in output


@given(parsers.parse("a project with a compilation database selected by {selection}"), target_fixture="database_project")
def database_project(tmp_path: Path, selection: str):
    import json
    root = tmp_path / "database-project"
    (root / "src").mkdir(parents=True)
    (root / "build/include with spaces").mkdir(parents=True)
    (root / "build/include with spaces/profile.hpp").write_text("#define HEADER_VALUE 17\n")
    source = root / "src/profile.cc"
    source.write_text('#include <profile.hpp>\nstatic_assert(HEADER_VALUE == 17);\n'
                      '#if PROFILE == 1\nint before(){return 1;}\n#else\nint after(){return 2;}\n#endif\n')
    database = root / "build" / ("compile_commands.json" if selection == "automatic" else "selected.json")
    command = {"directory": str(root / "build"), "file": "../src/profile.cc",
               "arguments": ["clang++", "-std=c++20", "-Iinclude with spaces", "-DPROFILE=1",
                             "-c", "-o", "profile.o", "-MMD", "-MF", "profile.d", "--", "../src/profile.cc"]}
    database.write_text(json.dumps([command]))
    return root, source, database, command, selection


@when("I parse through the SDK and console and update its compilation command", target_fixture="database_results")
def parse_database_project(server: RunningServer, database_project):
    import json
    import sys
    from clang_toolkit import Client
    root, source, database, command, selection = database_project
    selected = str(database) if selection == "explicit" else None
    with Client(server.endpoint, compilation_database=selected) as client:
        with client.parse(source, working_directory=root) as tree:
            with client.match_in('functionDecl(hasName("before")).bind("f")', tree) as rows:
                assert len(rows) == 1
        script = client.run_script('let tree = parse "src/profile.cc"; let rows = match functionDecl(hasName("before")).bind("f") in $tree; emit rows;', working_directory=root)
        assert len(script.emissions[0].value.matches.rows) == 1
    arguments = [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint]
    if selected:
        arguments += ["--compile-commands", selected]
    console = subprocess.run(arguments, cwd=root,
        input='let tree = parse "src/profile.cc"\nlet rows = match functionDecl(hasName("before")).bind("f") in $tree\nprint $rows\nquit\n',
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30, check=False)
    assert console.returncode == 0, console.stdout
    assert "before" in console.stdout and "could not build" not in console.stdout

    async def run():
        async with AsyncClient(server.endpoint, compilation_database=selected) as client:
            first = await client.match_in('functionDecl(hasName("before")).bind("f")', source,
                                          working_directory=root)
            command["arguments"][3] = "-DPROFILE=22"
            database.write_text(json.dumps([command]))
            updated = await client.match_in('functionDecl(hasName("after")).bind("f")', source,
                                            working_directory=root)
            old = await client.match_in('functionDecl(hasName("before")).bind("f")', source,
                                        working_directory=root)
            pinned = await client.match_in('functionDecl(hasName("before")).bind("f")', first)
            traversal = await client.traverse(source, working_directory=root)
            events = await client.query('functionDecl(hasName("after")).bind("f")', [source],
                                        working_directory=root)
            return len(first), len(updated), len(old), len(pinned), len(traversal.nodes), sum(event.HasField("match") for event in events)
    return asyncio.run(run()), root


@then("the database include paths and changed flags produce the expected ASTs")
def database_asts(database_results):
    counts, root = database_results
    assert counts[:4] == (1, 1, 0, 1)
    assert counts[4] > 0 and counts[5] == 1
    assert not (root / "build/profile.o").exists()
    assert not (root / "build/profile.d").exists()


@given("a C++ file controlled by a client compilation profile", target_fixture="profile_source")
def client_profile_source(tmp_path: Path) -> Path:
    directory = tmp_path / "client-profile"
    directory.mkdir()
    path = directory / "profile.cc"
    path.write_text(
        "#if CLIENT_PROFILE\nint profile_function(){return 7;}\n"
        "#else\nint default_function(){return 9;}\n#endif\n",
        encoding="utf-8",
    )
    return path


@when("I run native parse blocks through the SDKs and real console without a default file", target_fixture="profile_results")
def native_client_profile(server: RunningServer, profile_source: Path, tmp_path: Path):
    import json
    import sys
    from clang_toolkit import Client

    source = '''let analysis = in parse "profile.cc" {
        let functions = match functionDecl(hasName("profile_function")).bind("f");
        yield functions;
    }; emit analysis;'''
    options = {"working_directory": profile_source.parent,
               "compile_arguments": ["-std=c++23", "-DCLIENT_PROFILE=1"]}
    with Client(config_path=server.config) as client:
        synchronous = client.run_script(source, **options)

    async def run():
        async with AsyncClient(config_path=server.config) as client:
            return await client.run_script(source, **options)

    asynchronous = asyncio.run(run())
    (profile_source.parent / ".clang_tools.yaml").write_text(
        "extra_args: ['-std=c++23', '-DCLIENT_PROFILE=1']\n", encoding="utf-8")
    console = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "-c", str(server.config)],
        input=f'script {json.dumps(source)}\nprint "PROFILE_COMPLETE"\nquit\n',
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=profile_source.parent,
        env=dict(os.environ, XDG_STATE_HOME=str(tmp_path / "profile-state")),
        timeout=30, check=False,
    )
    assert console.returncode == 0, console.stdout
    return synchronous, asynchronous, console.stdout


@then("the client working directory and compiler flags select the profile function")
def native_client_profile_matches(profile_results):
    synchronous, asynchronous, console = profile_results
    for response in (synchronous, asynchronous):
        assert len(response.emissions) == 1
        rows = response.emissions[0].value.matches.rows
        assert len(rows) == 1 and rows[0].bindings["f"].node.HasField("function_decl")
    assert "PROFILE_COMPLETE" in console and "profile_function" in console
    assert "error:" not in console and "syntax error" not in console


@when("I traverse the file and enforce a node limit", target_fixture="traversal_result")
def traverse_native_file(server: RunningServer, cursor_source: Path):
    async def run():
        async with AsyncClient(server.endpoint) as client:
            result = await client.traverse(cursor_source)
            root = await client.traverse(cursor_source, max_depth=0)
            assert root.depth_limited and len(root.nodes) == 1
            with pytest.raises(AnalysisError) as limited:
                await client.traverse(cursor_source, max_nodes=1)
            assert limited.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
            return result
    return asyncio.run(run())


@then("traversal contains the typed literal and a valid parent structure")
def valid_native_preorder(traversal_result):
    records = traversal_result.nodes
    assert records[0].value.node.HasField("translation_unit_decl")
    assert not records[0].HasField("parent_index")
    literals = []
    for index, record in enumerate(records):
        if index:
            assert record.HasField("parent_index") and record.parent_index < index
            assert record.depth == records[record.parent_index].depth + 1
        if record.value.node.HasField("integer_literal"):
            literals.append(record.value.node.integer_literal.value.unsigned_decimal)
    assert "7" in literals


@given("a C++ file containing a cursor workflow", target_fixture="cursor_source")
def cursor_source(tmp_path: Path) -> Path:
    path = tmp_path / "cursor.cc"
    path.write_text("int target(int x){return x;} int f(){return target(7);}", encoding="utf-8")
    return path


@when("I continue, restart and close the matching cursor", target_fixture="cursor_result")
def cursor_workflow(server: RunningServer, cursor_source: Path):
    async def run():
        async with AsyncClient(server.endpoint) as client:
            first = await client.match_file(cursor_source, 'functionDecl(hasName("f")).bind("f")')
            assert first.result_revision == 1 and len(first.results) == 1
            with pytest.raises(CursorError) as invalid:
                await client.restart_match(first.session_id, "invalidMatcher()", expected_result_revision=1)
            assert invalid.value.code == grpc.StatusCode.INVALID_ARGUMENT
            continuation = await client.continue_match(first.session_id, "f", 'callExpr().bind("call")',
                                                       match_index=0, expected_result_revision=1)
            assert continuation.result_revision == 2 and len(continuation.results) == 1
            assert continuation.results[0].HasField("source_match_index")
            assert continuation.results[0].source_match_index == 0
            assert continuation.results[0].bindings["call"].node.HasField("call_expr")
            with pytest.raises(CursorError) as stale:
                await client.restart_match(first.session_id, "callExpr()", expected_result_revision=1)
            assert stale.value.code == grpc.StatusCode.ABORTED
            restarted = await client.restart_match(first.session_id, 'integerLiteral().bind("n")',
                                                   expected_result_revision=2)
            assert restarted.result_revision == 3
            assert restarted.results[0].bindings["n"].node.integer_literal.value.unsigned_decimal == "7"
            await client.close_match(first.session_id)
            await client.close_match(first.session_id)
            with pytest.raises(CursorError) as closed:
                await client.restart_match(first.session_id, "callExpr()")
            assert closed.value.code == grpc.StatusCode.NOT_FOUND
            return first, continuation, restarted
    return asyncio.run(run())


@then("the cursor preserved its bindings on failure and advanced only successful revisions")
def verify_cursor_workflow(cursor_result):
    first, continued, restarted = cursor_result
    assert first.session_id == continued.session_id == restarted.session_id
    assert [first.result_revision, continued.result_revision, restarted.result_revision] == [1, 2, 3]


@dataclass
class RunningServer:
    process: subprocess.Popen[str]
    endpoint: str
    config: Path


def _launch_server(transport: str, tmp_path: Path, request, *, max_files: int = 100,
                   max_send_bytes: int | None = None) -> RunningServer:
    root = Path(__file__).parents[2]
    executable = Path(os.environ.get("CTK_SERVER", root / "build/dev/server/ctk-server"))
    if not executable.is_file():
        found = shutil.which("ctk-server")
        if found is None:
            pytest.skip(f"ctk-server binary not found at {executable}")
        executable = Path(found)

    workdir = tmp_path / "work"
    home = tmp_path / "home"
    workdir.mkdir()
    home.mkdir()
    config = tmp_path / "server.yaml"
    socket_root = Path(tempfile.mkdtemp(prefix="ctk-", dir="/tmp"))
    process: subprocess.Popen[str] | None = None

    def stop_server() -> str:
        if process is None:
            shutil.rmtree(socket_root, ignore_errors=True)
            return ""
        if process.poll() is None:
            process.terminate()
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate(timeout=5)
        shutil.rmtree(socket_root, ignore_errors=True)
        return output

    request.addfinalizer(stop_server)
    if transport == "unix":
        endpoint = f"unix://{socket_root / 'query.sock'}"
        content = f"network:\n  transport: unix\n  unix:\n    socket_path: {socket_root / 'query.sock'}\n"
    else:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        endpoint = f"127.0.0.1:{port}"
        content = f"network:\n  transport: tcp\n  tcp:\n    host: 127.0.0.1\n    port: {port}\n"
    content += f"session:\n  max_files: {max_files}\n"
    if max_send_bytes is not None:
        content += f"server:\n  grpc:\n    max_send_message_bytes: {max_send_bytes}\n"
    config.write_text(content, encoding="utf-8")
    env = dict(os.environ, HOME=str(home))
    env.pop("CLANG_TOOLKIT_HOME", None)
    process = subprocess.Popen(
        [str(executable), "-c", str(config)], cwd=workdir, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    deadline = time.monotonic() + 10
    ready = False
    while time.monotonic() < deadline and process.poll() is None:
        async def check_connection() -> bool:
            channel = grpc.aio.insecure_channel(endpoint)
            try:
                await asyncio.wait_for(channel.channel_ready(), timeout=0.25)
                return True
            except TimeoutError:
                return False
            finally:
                await channel.close()
        if asyncio.run(check_connection()):
            ready = True
            break
        time.sleep(0.05)
    if not ready:
        output = stop_server()
        pytest.fail(f"ctk-server did not become ready: {output}")
    return RunningServer(process, endpoint, config)


@given(parsers.parse("a query server using {transport}"), target_fixture="server")
def start_server(transport: str, tmp_path: Path, request) -> RunningServer:
    return _launch_server(transport, tmp_path, request)


@given(parsers.parse("an isolated resource server using {transport}"), target_fixture="server")
def start_resource_server(transport: str, tmp_path: Path, request, monkeypatch) -> RunningServer:
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "native-storage"))
    return _launch_server(transport, tmp_path, request)


@when("I inspect attach prune and close retained native sessions through the SDKs and console",
      target_fixture="managed_resources")
def manage_native_resources(server: RunningServer, source: Path, tmp_path: Path):
    from clang_toolkit import Client
    from clang_toolkit.cli.runtime import Runtime
    from clang_toolkit.match_values import MatchValueError

    with Client(server.endpoint) as client:
        rows = client.match_in('varDecl().bind("v")', source)
        identity = rows._owner.session_id
        listed = client.list_sessions()
        assert any(info.session_id == identity and "v" in info.binding_names for info in listed.sessions)
        status = client.server_status()
        assert status.active_sessions >= 1 and status.retained_memory_bytes > 0
        assert status.HasField("resident_memory_bytes") and status.resident_memory_bytes > 0
        assert status.cache.memory_available and status.cache.storage_available
        tree = client.attach_session(identity)
        assert tree._owner is rows._owner
        runtime = Runtime(client, cwd=tmp_path)
        try:
            runtime.bindings["tree"] = tree
            status_text = runtime.execute("server status")
            assert status_text.startswith("Server status\n")
            assert "Resident memory" in status_text and "Retained memory" in status_text
            assert any(unit in status_text for unit in ("KiB", "MiB", "GiB"))
            cache_text = runtime.execute("cache status")
            assert cache_text.startswith("Cache status\n") and "Storage root" in cache_text
            session_text = runtime.execute("session list")
            assert identity in session_text and str(source) in session_text
            assert "Bindings" in session_text and "Expires" in session_text
            runtime.execute("session attach $tree into $attached")
            prune_text = runtime.execute("cache prune all")
            assert prune_text.startswith("Cache prune results\n")
            assert "Before" in prune_text and "After" in prune_text
            assert client.server_status().cache.reusable_snapshots == 0
            child = client.match_in('varDecl().bind("child")', tree)
            assert len(child) == 1
            runtime.execute("session close $attached")
            with pytest.raises(MatchValueError):
                client.match_in("varDecl()", tree)
            assert len(client.match_in("varDecl()", child)) == 1
        finally:
            runtime.close()
        client.prune_caches(memory=True, disk=True)

    async def run():
        async with AsyncClient(server.endpoint) as client:
            tree = await client.parse(source)
            info = (await client.list_sessions()).sessions
            assert any(item.session_id == tree._owner.session_id for item in info)
            attached = await client.attach_session(tree._owner.session_id)
            assert attached._owner is tree._owner
            await client.prune_caches(memory=True, disk=True)
            assert (await client.server_status()).cache.reusable_snapshots == 0
            assert len(await client.match_in("varDecl()", attached)) == 1
            await client.close_match(tree._owner.session_id)
            assert tree._owner.closed
    asyncio.run(run())
    return server.process.poll()


@then("resource accounting is live and independent children survive closing their source")
def verify_managed_resources(managed_resources):
    assert managed_resources is None


@when("I export matched values through variable paths and redirect print output",
      target_fixture="exported_values")
def export_values(server: RunningServer, source: Path, tmp_path: Path):
    import sys
    commands = [
        f'let x = match varDecl().bind("v") in "{source}"',
        'let filename = "$HOME/exported"',
    ]
    for kind in ("json", "yaml", "proto"):
        commands.extend([f"save $x to $filename as {kind}",
                         f'load "$HOME/exported.{kind}" into $snapshot',
                         'print "loaded" to "$HOME/loaded.txt" mode append'])
    commands.extend(['print "old" to "$HOME/output.txt"',
                     'print "new" to "$HOME/output.txt" mode replace',
                     'print "added" to "$HOME/output.txt" mode append',
                     "bindings", "binding rename $x to $rows", "binding drop $rows", "quit"])
    result = subprocess.run([sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint],
                            input="\n".join(commands) + "\n", text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            cwd=tmp_path, env=dict(os.environ, HOME=str(tmp_path),
                                                  XDG_STATE_HOME=str(tmp_path / "state")),
                            timeout=30)
    assert result.returncode == 0 and "error:" not in result.stdout, result.stdout
    return tmp_path


@then("JSON YAML and protobuf snapshots reload and text replacement and append are correct")
def verify_exported_values(exported_values: Path):
    from clang_toolkit.cli.runtime.persistence import load
    snapshots = [load(exported_values / f"exported.{kind}") for kind in ("json", "yaml", "proto")]
    assert snapshots[0] == snapshots[1] == snapshots[2]
    assert snapshots[0].rows and "v" in snapshots[0].rows[0]["bindings"]
    assert (exported_values / "output.txt").read_text() == "new\nadded\n"
    assert (exported_values / "loaded.txt").read_text() == "loaded\n" * 3


@given("a query server with a one-file limit", target_fixture="server")
def start_limited_server(tmp_path: Path, request) -> RunningServer:
    return _launch_server("unix", tmp_path, request, max_files=1)


@given("a cursor server with a 128-byte response limit", target_fixture="server")
def start_cursor_byte_limited_server(tmp_path: Path, request) -> RunningServer:
    return _launch_server("unix", tmp_path, request, max_send_bytes=128)


@given("a cursor server with a 32-MiB response limit", target_fixture="server")
def start_large_cursor_server(tmp_path: Path, request) -> RunningServer:
    # Source ranges and USRs add copied facts to these deliberately long names.
    return _launch_server("unix", tmp_path, request, max_send_bytes=32 * 1024 * 1024)


@given(parsers.parse("a streaming cursor server using {transport} with an 8192-byte message limit"),
       target_fixture="server")
def start_streaming_cursor_server(transport: str, tmp_path: Path, request) -> RunningServer:
    return _launch_server(transport, tmp_path, request, max_send_bytes=8192)


@given("a C++ file containing many small function definitions", target_fixture="stream_source")
def small_function_definitions(tmp_path: Path) -> tuple[Path, int]:
    source = tmp_path / "stream.cc"
    count = 96
    source.write_text("\n".join(f"int streamed_{index}() {{ return {index}; }}"
                                for index in range(count)), encoding="utf-8")
    return source, count


@when("I stream retained matches through both SDKs and the real console", target_fixture="streamed_result")
def stream_retained_matches(server: RunningServer, stream_source: tuple[Path, int], tmp_path: Path):
    import sys
    from clang_toolkit import Client
    source, count = stream_source
    query = 'functionDecl().bind("f")'
    with Client(server.endpoint) as client:
        with client.parse(source, working_directory=source.parent) as tree:
            with pytest.raises(CursorError) as rejected:
                client.match_file(source, query, working_directory=source.parent)
            assert rejected.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
            received = []
            sizes = []

            def on_row(row):
                sizes.append(row.ByteSize())
                received.append(row.bindings["f"].node.function_decl.function.declarator.value.named.qualified_name)
                row.Clear()

            with client.match_in(query, tree, on_row=on_row) as functions:
                assert len(functions) == len(received) == count
                assert "f" in functions[0].bindings
                with client.match_in('integerLiteral().bind("n")', functions.binding("f")) as literals:
                    assert len(literals) == count
                    assert [row.source_match_index for row in literals] == list(range(count))
            assert functions[0].bindings["f"].node.HasField("function_decl")
            with client.match_in('functionDecl(hasName("missing"))', tree) as empty:
                assert len(empty) == 0
            with pytest.raises(RuntimeError, match="stop streamed callback"):
                client.match_in(query, tree, on_row=lambda _row: (_ for _ in ()).throw(
                    RuntimeError("stop streamed callback")))
            with client.match_in('functionDecl(hasName("streamed_0"))', tree) as after_cancel:
                assert len(after_cancel) == 1
            assert sum(sizes) > 8192 and max(sizes) < 8192

    async def run():
        async with AsyncClient(server.endpoint) as client:
            async with await client.parse(source, working_directory=source.parent) as tree:
                observed = []

                async def on_row(row):
                    observed.append(row.bindings["f"].node.function_decl.function.declarator.value.named.qualified_name)
                    await asyncio.sleep(0)

                async with await client.match_in(query, tree, on_row=on_row) as functions:
                    assert len(functions) == len(observed) == count
                    return observed

    asynchronous = asyncio.run(run())
    console = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint],
        input=f'let tree = parse "{source}"\nlet rows = match {query} in $tree\n'
              'let literals = match integerLiteral().bind("n") in $rows[0].f\n'
              'print $literals\nprint "STREAM_MATCH_OK"\nquit\n',
        env=dict(os.environ, XDG_STATE_HOME=str(tmp_path / "stream-state")),
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, check=False,
    )
    return received, asynchronous, console, count


@then("all rows arrive incrementally and remain reusable beyond the message limit")
def verify_streamed_retained_matches(server: RunningServer, streamed_result):
    synchronous, asynchronous, console, count = streamed_result
    assert len(synchronous) == len(asynchronous) == count
    assert synchronous == asynchronous
    assert console.returncode == 0, console.stdout
    assert "STREAM_MATCH_OK" in console.stdout
    assert "integer_literal" in console.stdout
    assert "error:" not in console.stdout, console.stdout
    assert server.process.poll() is None


@given("a C++ file with a large function declaration result", target_fixture="large_source")
def large_source(tmp_path: Path) -> tuple[Path, int]:
    return _included_function_source(tmp_path, 3000)


@given("a C++ file whose included matches exceed 64 MiB", target_fixture="large_source")
def very_large_source(tmp_path: Path) -> tuple[Path, int]:
    return _included_function_source(tmp_path, 15000)


def _included_function_source(tmp_path: Path, count: int) -> tuple[Path, int]:
    source = tmp_path / "large.cc"
    (tmp_path / "many.hpp").write_text("\n".join(
        f"void function_{index}_" + "x" * 1000 + "();" for index in range(count)))
    source.write_text('#include "many.hpp"\nvoid marker();\n')
    return source, count + 1


@when("I match the large result through both SDKs and the console", target_fixture="large_result")
def match_large_result(server: RunningServer, large_source: tuple[Path, int]):
    import sys
    from clang_toolkit import Client
    source, count = large_source

    with Client(server.endpoint) as client:
        with client.parse(source) as tree:
            with client.match_in('functionDecl().bind("x")', tree) as rows:
                assert len(rows) == count
                assert {"root", "x"} <= rows[0].bindings.keys()
            with client.match_in('functionDecl()', tree) as roots:
                assert len(roots) == count
                assert set(roots[0].bindings) == {"root"}
        response = client.match_file(source, 'functionDecl().bind("x")')
        assert response.ByteSize() > 4 * 1024 * 1024
        assert len(response.results) == count
        client.close_match(response.session_id)

    async def run():
        async with AsyncClient(server.endpoint) as client:
            async with await client.parse(source) as tree:
                async with await client.match_in('functionDecl().bind("x")', tree) as rows:
                    assert len(rows) == count
    asyncio.run(run())
    console = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint],
        input=f'let tree = parse "{source}"\nlet rows = match functionDecl().bind("x") in $tree\n'
              'let one = match functionDecl(hasName("marker")).bind("x") in $tree\nprint $one\nquit\n',
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90,
        check=False,
    )
    return console, response.ByteSize()


@then("every client receives all function declarations")
def verify_large_result(large_result):
    console, size = large_result
    assert console.returncode == 0, console.stdout
    assert "error:" not in console.stdout, console.stdout
    assert "marker" in console.stdout
    assert size > 4 * 1024 * 1024


@then("the complete response exceeds 64 MiB without special settings")
def verify_no_default_wire_cap(large_result):
    assert large_result[1] > 64 * 1024 * 1024


@when("I request an oversized cursor replacement", target_fixture="cursor_limited_result")
def oversized_cursor_replacement(server: RunningServer, cursor_source: Path):
    async def run():
        async with AsyncClient(server.endpoint) as client:
            first = await client.match_file(cursor_source, 'functionDecl(hasName("not_present"))')
            with pytest.raises(CursorError) as rejected:
                await client.restart_match(first.session_id, 'functionDecl().bind("f")',
                                           expected_result_revision=1)
            assert rejected.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
            assert "limit 128 bytes" in str(rejected.value)
            assert "server.grpc.max_send_message_bytes" in str(rejected.value)
            preserved = await client.restart_match(first.session_id, 'functionDecl(hasName("not_present"))',
                                                   expected_result_revision=1)
            await client.close_match(first.session_id)
            return preserved
    return asyncio.run(run())


@then("the oversized response leaves revision one available for replacement")
def cursor_wire_limit_preserves_revision(cursor_limited_result):
    assert cursor_limited_result.result_revision == 2


@given("a C++ file containing a declaration", target_fixture="source")
def create_cpp_source(tmp_path: Path) -> Path:
    source = tmp_path / "query.cpp"
    source.write_text("int network_client_marker = 1;\n", encoding="utf-8")
    return source


@when("I run the declaration query", target_fixture="events")
def run_declaration_query(server: RunningServer, source: Path):
    async def run():
        async with AsyncClient(server.endpoint) as client:
            declaration_events = await client.query(
                'varDecl(hasName("network_client_marker")).bind("decl")',
                [source], working_directory=source.parent,
            )
            child_events = await client.query(
                'integerLiteral().bind("literal")',
                [source], working_directory=source.parent,
            )
            return declaration_events, child_events
    return asyncio.run(run())


@then("the stream contains a match and successful completion")
def has_match_and_completion(events) -> None:
    for event_stream in events:
        kinds = [event.WhichOneof("event") for event in event_stream]
        assert "match" in kinds
        assert kinds[-1] == "completed"
        completed = next(
            event.completed for event in event_stream
            if event.WhichOneof("event") == "completed"
        )
        assert completed.match_count >= 1


@when("I run session commands in the console without a session option",
      target_fixture="automatic_session_console")
def run_automatic_console_session(server: RunningServer, source: Path, tmp_path: Path):
    import sys
    return subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint],
        input='session start "varDecl()"\n'
              f'session add "{source}"\n'
              'session match\nsession close\nquit\n',
        env=dict(os.environ, XDG_STATE_HOME=str(tmp_path / "console-state")),
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=30, check=False,
    )


@then("the console streams a match and completion without session errors")
def automatic_console_session_completes(automatic_session_console):
    console = automatic_session_console
    assert console.returncode == 0, console.stdout
    assert "network_client_marker" in console.stdout
    assert "completed: 1 matches" in console.stdout
    assert "error:" not in console.stdout.lower()
    assert "Task exception was never retrieved" not in console.stdout


@when("I run the query through a bidirectional session", target_fixture="session_events")
def run_bidi_query(server: RunningServer, source: Path):
    async def run():
        async with AsyncClient(server.endpoint) as client:
            session = await client.query_session()
            await session.start_query('varDecl(hasName("network_client_marker")).bind("decl")')
            await session.add_files([source], working_directory=source.parent)
            await session.match()
            await session.half_close()
            events = [event async for event in session.events()]
            await session.aclose()
            return events
    return asyncio.run(run())


@then("the session stream contains a match and completion")
def has_session_match_and_completion(session_events) -> None:
    kinds = [event.WhichOneof("event") for event in session_events]
    assert "match" in kinds
    assert "completed" in kinds


@when("I define two queries in one bidirectional session", target_fixture="rejection")
def define_two_queries(server: RunningServer):
    async def run():
        async with AsyncClient(server.endpoint) as client:
            session = await client.query_session()
            await session.start_query("varDecl()")
            await session.start_query("functionDecl()")
            await session.match()
            await session.half_close()
            events = [event async for event in session.events()]
            await session.aclose()
            return events
    return asyncio.run(run())


@then("the session reports a command rejection")
def has_command_rejection(rejection) -> None:
    assert any(event.WhichOneof("event") == "rejected" for event in rejection)
    assert any(event.WhichOneof("event") == "completed" for event in rejection)


@when("I cancel an active bidirectional session", target_fixture="cancellation")
def cancel_bidi_session(server: RunningServer):
    async def run():
        async with AsyncClient(server.endpoint) as client:
            session = await client.query_session()
            await session.start_query("varDecl()")
            await session.match()
            await session.cancel()
            try:
                [event async for event in session.events()]
            except QueryError as exc:
                return exc
            finally:
                await session.aclose()
    return asyncio.run(run())


@then("the session reports cancellation")
def has_cancellation(cancellation) -> None:
    assert isinstance(cancellation, QueryError)
    assert "CANCELLED" in str(cancellation)


@when("I match the first file and add a second file", target_fixture="limited_events")
def run_limited_batch(server: RunningServer, source: Path, tmp_path: Path):
    second = tmp_path / "second.cpp"
    second.write_text("int second_marker = 2;\n", encoding="utf-8")

    async def run():
        async with AsyncClient(server.endpoint) as client:
            session = await client.query_session()
            await session.start_query('varDecl(hasName("network_client_marker")).bind("decl")')
            await session.add_files([source], working_directory=source.parent)
            await session.pause()
            await session.resume()
            match_request_id = await session.match()
            rejected_request_id = await session.add_files([second], working_directory=second.parent)
            await session.half_close()
            events = [event async for event in session.events()]
            await session.aclose()
            return events, match_request_id, rejected_request_id
    return asyncio.run(run())


@then("the second batch is rejected while the first file completes")
def checks_limited_batch(limited_events, source: Path) -> None:
    events, match_request_id, rejected_request_id = limited_events
    rejection = next(
        event for event in events
        if event.WhichOneof("event") == "rejected" and event.request_id == rejected_request_id
    )
    assert rejection.rejected.code == "LIMIT_REACHED"
    assert len(rejection.rejected.violations) == 1
    violation = rejection.rejected.violations[0]
    assert violation.limit_name == "session.max_files"
    assert violation.current_value == 1
    assert violation.configured_limit == 1
    match = next(event for event in events if event.WhichOneof("event") == "match")
    assert match.request_id == match_request_id
    assert match.match.file == str(source.resolve())
    completed = next(event for event in events if event.WhichOneof("event") == "completed")
    assert completed.request_id == match_request_id
    assert completed.completed.match_count >= 1
    actions = [event.control.action for event in events if event.WhichOneof("event") == "control"]
    assert "paused" in actions
    assert "resumed" in actions


@then("the declaration exposes a type summary and the follow-up query exposes its literal")
def has_shallow_semantic_declaration(events) -> None:
    declaration_events, child_events = events
    match = next(event.match for event in declaration_events if event.WhichOneof("event") == "match")
    binding = match.semantic_result.bindings["decl"]
    assert binding.is_complete
    assert binding.node.WhichOneof("payload") == "var_decl"
    variable = binding.node.var_decl.variable
    assert variable.declarator.value.named.qualified_name == "network_client_marker"
    assert variable.declarator.value.type.description.spelling == "int"
    assert not variable.HasField("initializer")
    omissions = {item.field_path: item.state for item in binding.availability}
    assert omissions["VarDeclInfo.initializer"] == common_pb2.FIELD_STATE_UNREQUESTED

    literal_match = next(event.match for event in child_events if event.WhichOneof("event") == "match")
    literal = literal_match.semantic_result.bindings["literal"].node.integer_literal
    assert literal.value.unsigned_decimal == "1"


@when("I build the function CFG and reject a limited result", target_fixture="cfg_result")
def cfg_native_file(server: RunningServer, cursor_source: Path):
    async def run():
        async with AsyncClient(server.endpoint) as client:
            result = await client.cfg(cursor_source, "f", projection="recursive")
            with pytest.raises(AnalysisError) as limited:
                await client.cfg(cursor_source, "f", max_blocks=1)
            assert limited.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
            with pytest.raises(AnalysisError) as missing:
                await client.cfg(cursor_source, "unknown")
            assert missing.value.code == grpc.StatusCode.NOT_FOUND
            return result
    return asyncio.run(run())


@then("the graph contains typed statements and valid block edges")
def cfg_typed_blocks(cfg_result):
    assert len(cfg_result.graphs) == 1
    graph = cfg_result.graphs[0]
    assert graph.function.qualified_name == "f"
    indices = {block.block_index for block in graph.blocks}
    assert graph.entry_block in indices and graph.exit_block in indices
    assert any(element.HasField("statement") and element.statement.statement.expression.HasField("call_expr")
               for block in graph.blocks for element in block.elements)
    for block in graph.blocks:
        for edge in block.successors:
            if edge.HasField("reachable_block"):
                assert edge.reachable_block in indices


@when("I build the native call graph and enforce its node limit", target_fixture="call_graph_result")
def native_call_graph(server: RunningServer, cursor_source: Path):
    async def run():
        async with AsyncClient(server.endpoint) as client:
            result = await client.callgraph(cursor_source, projection="recursive")
            with pytest.raises(AnalysisError) as limited:
                await client.callgraph(cursor_source, max_nodes=1)
            assert limited.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
            return result
    return asyncio.run(run())


@then("the call graph connects the functions with a typed call")
def typed_call_graph(call_graph_result):
    result = call_graph_result
    assert result.nodes[result.root_node].is_virtual_root
    functions = {node.function.qualified_name: node.node_index for node in result.nodes if node.HasField("function")}
    calls = [edge for edge in result.edges if edge.caller_node == functions["f"] and edge.callee_node == functions["target"]]
    assert len(calls) == 1
    assert calls[0].call.call_expr.call.direct_callee.qualified_name == "target"
    assert calls[0].call.call_expr.call.arguments[0].integer_literal.value.unsigned_decimal == "7"


@when("I compose native analyses in a server script and exhaust its step budget", target_fixture="script_result")
def native_script(server: RunningServer, cursor_source: Path):
    async def run():
        async with AsyncClient(server.endpoint) as client:
            source = r'''let rows=match("functionDecl(isDefinition()).bind(\"f\")");
                emit count(rows);
                foreach item in rows {emit continue(item,"f","integerLiteral().bind(\"n\")");}
                emit cfg("f"); emit callgraph(); emit traverse(max_depth=0);'''
            result = await client.run_script(source,path=cursor_source)
            with pytest.raises(AnalysisError) as limited:
                await client.run_script(source,path=cursor_source,max_steps=1)
            assert limited.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
            with pytest.raises(AnalysisError) as malformed:
                await client.run_script("emit 7; emit missing;",path=cursor_source)
            assert malformed.value.code == grpc.StatusCode.INVALID_ARGUMENT
            return result
    return asyncio.run(run())


@then("the script contains typed query values and no native cursor handles")
def typed_script(script_result):
    assert script_result.emissions[0].value.scalar.integer >= 2
    assert any(item.value.HasField("matches") and item.value.matches.rows for item in script_result.emissions)
    assert any(item.value.HasField("cfg") and item.value.cfg.graphs[0].function.qualified_name == "f" for item in script_result.emissions)
    assert any(item.value.HasField("call_graph") and item.value.call_graph.nodes[0].is_virtual_root for item in script_result.emissions)
    assert any(item.value.HasField("traversal") and len(item.value.traversal.nodes) == 1 for item in script_result.emissions)
    assert "session_id" not in str(script_result)


@when(parsers.parse("I replace a {kind} dependency after pinning its native snapshot"),
      target_fixture="dependency_generations")
def replace_native_dependency(kind: str, server: RunningServer, tmp_path: Path):
    root = Path(__file__).parents[2]
    tool_path = root / "build/dev/ctk-clang-tool-path.txt"
    compiler = os.environ.get("CTK_TEST_CLANG")
    if compiler is None and tool_path.is_file():
        compiler = tool_path.read_text().strip()
    assert compiler is not None, "set CTK_TEST_CLANG to the server's configured Clang compiler"
    source = tmp_path / "dependency-main.cc"
    dependency = tmp_path / ("numbers.cppm" if kind == "module" else "values.hpp")
    artifact = tmp_path / ("numbers.pcm" if kind == "module" else "values.pch")
    flags = ["-std=c++20"]
    if kind == "module":
        source.write_text("import numbers; int f(){return value();}\n", encoding="utf-8")
        flags.append(f"-fmodule-file=numbers={artifact}")
    elif kind == "pch":
        source.write_text("int f(){return value();}\n", encoding="utf-8")
        flags.extend(["-include-pch", str(artifact)])
    else:
        source.write_text('#include "values.hpp"\nint f(){return value();}\n', encoding="utf-8")

    def build(value: int):
        prefix = "export module numbers; export " if kind == "module" else "inline "
        dependency.write_text(prefix + f"int value(){{return {value};}}\n", encoding="utf-8")
        if kind != "header":
            action = ["--precompile"] if kind == "module" else ["-x", "c++-header"]
            completed = subprocess.run(
                [compiler, "-std=c++20", "-Xclang", "-fvalidate-ast-input-files-content", *action,
                 str(dependency), "-o", str(artifact)], capture_output=True, text=True,
            )
            assert completed.returncode == 0, completed.stderr

    async def run():
        build(7)
        async with AsyncClient(server.endpoint) as client:
            pinned = await client.match_file(source, 'functionDecl(hasName("f")).bind("f")',
                                             working_directory=tmp_path, compile_arguments=flags)
            build(9)
            current = await client.match_file(source, 'integerLiteral().bind("n")',
                                              working_directory=tmp_path, compile_arguments=flags)
            old = await client.restart_match(pinned.session_id, 'integerLiteral().bind("n")')
            await client.close_match(pinned.session_id)
            await client.close_match(current.session_id)
            return current, old
    return asyncio.run(run())


@then("new queries see nine and the pinned snapshot still sees seven")
def verify_native_generations(dependency_generations):
    current, old = dependency_generations
    for result, expected in ((current, "9"), (old, "7")):
        literals = [row.bindings["n"].node.integer_literal.value.unsigned_decimal
                    for row in result.results]
        assert expected in literals
        assert ("7" if expected == "9" else "9") not in literals


@given("a C++ file containing multiple expression roots", target_fixture="expression_source")
def expression_source(tmp_path: Path) -> Path:
    path = tmp_path / "expressions.cc"
    path.write_text(
        "int target(int x){return x;}\n"
        "int one(){return target(7);}\n"
        "int two(){return target(9);}\n", encoding="utf-8",
    )
    return path


@when("I parse and match independent tree and binding values", target_fixture="expression_values")
def immutable_expression_values(server: RunningServer, expression_source: Path):
    from clang_toolkit.match_values import MatchValueError

    async def run():
        async with AsyncClient(server.endpoint) as client:
            tree = await client.parse(expression_source)
            functions = await client.match_in(
                'functionDecl(anyOf(hasName("one"),hasName("two"))).bind("f")', tree,
            )
            assert len(functions) == 2
            calls = await client.match_in('callExpr().bind("call")', functions.binding("f"))
            repeated = await client.match_in('callExpr().bind("call")', functions.binding("f"))
            first = await client.match_in('callExpr().bind("call")', functions[0].binding("f"))
            assert len(calls) == len(repeated) == 2 and len(first) == 1
            assert [row.source_match_index for row in calls] == [0, 1]
            tree.close()
            literals = await client.match_in('integerLiteral().bind("n")', calls.binding("call"))
            assert [row.bindings["n"].node.integer_literal.value.unsigned_decimal
                    for row in literals] == ["7", "9"]
            fresh = await client.match_in('integerLiteral().bind("n")', expression_source)
            empty = await client.match_in('functionDecl(hasName("absent")).bind("f")', expression_source)
            assert len(await client.match_in('callExpr().bind("call")', empty.binding("f"))) == 0
            with pytest.raises(MatchValueError):
                functions[2]
            with pytest.raises(MatchValueError):
                functions.binding("missing")
            with pytest.raises(CursorError) as invalid:
                await client.match_in('invalidMatcher()', functions.binding("f"))
            assert invalid.value.code == grpc.StatusCode.INVALID_ARGUMENT
            after_error = await client.match_in('callExpr().bind("call")', functions.binding("f"))
            calls.close()
            # A child owns its native tree even after its parent is closed.
            child = await client.match_in('integerLiteral().bind("n")', literals.binding("n"))
            return len(functions), len(after_error), len(fresh), len(child)

    return asyncio.run(run())


@then("every result remains selectable after continuations and tree release")
def expression_values_preserved(expression_values):
    assert expression_values == (2, 2, 2, 2)


@when("I run the approved scoped expressions in the interactive runtime", target_fixture="console_expressions")
def scoped_console_expression_values(server: RunningServer, expression_source: Path, tmp_path: Path):
    import json
    from clang_toolkit.client import Client
    from clang_toolkit.cli.runtime import Runtime

    with Client(server.endpoint) as client:
        runtime = Runtime(client, cwd=tmp_path, environment={})
        try:
            path = json.dumps(str(expression_source))
            runtime.execute(f'let tree = parse {path};')
            runtime.execute('let functions = match functionDecl(isDefinition()).bind("f") in $tree;')
            runtime.execute('let calls = match callExpr().bind("call") in $functions.f;')
            runtime.execute('let first = match callExpr().bind("call") in $functions[1].f;')
            runtime.execute(f'let literals = match integerLiteral().bind("n") in {path};')
            runtime.execute(f'''let analysis = in parse {path} {{
                let functions = match functionDecl(isDefinition()).bind("f");
                let local_calls = match callExpr().bind("call") in $functions.f;
                yield local_calls;
            }};''')
            assert "local_calls" not in runtime.bindings
            assert len(runtime.bindings["functions"]) == 3
            runtime.execute('let yielded = match integerLiteral().bind("n") in $analysis.call;')
            retained = runtime.bindings["analysis"]
            with pytest.raises(Exception):
                runtime.execute(f'''let analysis = in parse {path} {{
                    let broken = match invalidMatcher();
                    yield broken;
                }};''')
            assert runtime.bindings["analysis"] is retained
            runtime.execute('let repeated = match callExpr().bind("call") in $functions.f;')
            return tuple(len(runtime.bindings[name]) for name in
                         ("calls", "first", "literals", "analysis", "yielded", "repeated"))
        finally:
            runtime.close()


@then("the yielded value survives lexical cleanup and failed assignments")
def console_values_preserved(console_expressions):
    assert console_expressions == (2, 1, 2, 2, 2, 2)


@when("I evaluate scoped parse and match expressions in the native script", target_fixture="native_expressions")
def native_scoped_expression_values(server: RunningServer, expression_source: Path):
    import json

    async def run():
        async with AsyncClient(server.endpoint) as client:
            path = json.dumps(str(expression_source))
            source = f'''let tree = parse {path};
                let functions = match functionDecl(isDefinition()).bind("f") in $tree;
                let calls = match callExpr().bind("call") in $functions.f;
                let repeated = match callExpr().bind("call") in $functions.f;
                let first = match callExpr().bind("call") in $functions[1].f;
                let analysis = in parse {path} {{
                    let functions = match functionDecl(isDefinition()).bind("f");
                    let inner = match callExpr().bind("call") in $functions.f;
                    yield inner;
                }};
                let yielded = match integerLiteral().bind("n") in $analysis.call;
                let empty = match functionDecl(hasName("absent")).bind("f") in $tree;
                let still_empty = match callExpr().bind("call") in $empty.f;
                emit functions; emit calls; emit repeated; emit first; emit yielded; emit still_empty;'''
            result = await client.run_script(source, max_steps=1000)
            with pytest.raises(AnalysisError) as invalid:
                await client.run_script(f'''let analysis = in parse {path} {{
                    let broken = match invalidMatcher(); yield broken;
                }}; emit analysis;''')
            assert invalid.value.code == grpc.StatusCode.INVALID_ARGUMENT
            return result

    return asyncio.run(run())


@then("native continuation uses all rows and keeps yielded results usable")
def native_script_values_preserved(native_expressions):
    assert [len(item.value.matches.rows) for item in native_expressions.emissions] == [3, 2, 2, 1, 2, 0]
    assert [row.bindings["n"].node.integer_literal.value.unsigned_decimal
            for row in native_expressions.emissions[4].value.matches.rows] == ["7", "9"]


@when("I enter parse and match expressions through the real console", target_fixture="real_console_output")
def real_expression_console(server: RunningServer, expression_source: Path, tmp_path: Path):
    import json
    import sys

    path = json.dumps(str(expression_source))
    commands = f'''let tree = parse {path};
let functions = match functionDecl(isDefinition()).bind("f") in $tree;
let calls = match callExpr().bind("call") in $functions.f;
let analysis = in parse {path} {{
let functions = match functionDecl(isDefinition()).bind("f");
let calls = match callExpr().bind("call") in $functions.f;
yield calls;
}};
let numbers = match integerLiteral().bind("n") in $analysis.call;
print $numbers
print "CONSOLE_COMPLETE"
quit
'''
    env = dict(os.environ, XDG_STATE_HOME=str(tmp_path / "console-state"))
    result = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "-c", str(server.config)],
        input=commands, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=tmp_path, env=env,
        timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout
    return result.stdout


@then("the console prints both yielded literals and exits cleanly")
def real_console_completed(real_console_output):
    assert "CONSOLE_COMPLETE" in real_console_output
    assert "unsigned_decimal" in real_console_output
    assert "syntax error" not in real_console_output
    assert "error:" not in real_console_output
    assert "'7'" in real_console_output or '"7"' in real_console_output
    assert "'9'" in real_console_output or '"9"' in real_console_output


@when("I use configured synchronous and asynchronous result contexts", target_fixture="context_values")
def configured_result_contexts(server: RunningServer, expression_source: Path, tmp_path: Path, monkeypatch):
    from clang_toolkit import Client
    from clang_toolkit.match_values import MatchValueError

    config_dir = tmp_path / "client-project"
    config_dir.mkdir()
    (config_dir / ".clang-toolkit.yaml").write_text(server.config.read_text(), encoding="utf-8")
    monkeypatch.chdir(config_dir)
    monkeypatch.setenv("HOME", str(tmp_path / "client-home"))
    query = 'functionDecl(isDefinition()).bind("f")'

    with Client() as client:
        with client.match(query, file=expression_source) as functions:
            alias = functions
            with functions.binding("f").match('callExpr().bind("call")') as calls:
                sync_calls = len(calls)
                child = calls.binding("call").match('integerLiteral().bind("n")')
            with pytest.raises(MatchValueError):
                calls.binding("call").match('integerLiteral().bind("n")')
        with pytest.raises(MatchValueError):
            alias.binding("f").match('callExpr().bind("call")')
        with child:
            sync_numbers = [row.bindings["n"].node.integer_literal.value.unsigned_decimal for row in child]
        child.close()
        with pytest.raises(RuntimeError, match="context body"):
            with client.parse(expression_source) as tree:
                raise RuntimeError("context body")
        with pytest.raises(MatchValueError):
            tree.match(query)

    async def run():
        async with AsyncClient(config_path=server.config) as client:
            async with await client.match(query, file=expression_source) as functions:
                async with await functions.binding("f").match('callExpr().bind("call")') as calls:
                    async_calls = len(calls)
                    child = await calls.binding("call").match('integerLiteral().bind("n")')
            async with child:
                async_numbers = [row.bindings["n"].node.integer_literal.value.unsigned_decimal for row in child]
            await child.aclose()
            with pytest.raises(MatchValueError):
                await functions.binding("f").match('callExpr().bind("call")')
            return async_calls, async_numbers

    return (sync_calls, sync_numbers), asyncio.run(run())


@then("context cleanup preserves children and invalidates closed aliases")
def result_contexts_preserved(context_values):
    assert context_values == ((2, ["7", "9"]), (2, ["7", "9"]))


@when("I parse with a configured 16-byte receive limit", target_fixture="configured_receive_error")
def configured_receive_limit(server: RunningServer, expression_source: Path, tmp_path: Path, monkeypatch):
    selected = tmp_path / "limited-client.yaml"
    selected.write_text(server.config.read_text() + "client:\n  grpc:\n    max_receive_message_bytes: 16\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path / "client-home"))

    async def run():
        async with AsyncClient(config_path=selected) as client:
            with pytest.raises(CursorError) as rejected:
                await client.parse(expression_source)
            return rejected.value.code

    return asyncio.run(run())


@then("the configured client rejects the oversized response")
def configured_response_rejected(configured_receive_error):
    assert configured_receive_error == grpc.StatusCode.RESOURCE_EXHAUSTED
