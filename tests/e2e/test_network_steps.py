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

pytestmark = pytest.mark.e2e
scenarios("network.feature")


@dataclass
class RunningServer:
    process: subprocess.Popen[str]
    endpoint: str
    config: Path


def _launch_server(transport: str, tmp_path: Path, request, *, max_files: int = 100) -> RunningServer:
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


@given("a query server with a one-file limit", target_fixture="server")
def start_limited_server(tmp_path: Path, request) -> RunningServer:
    return _launch_server("unix", tmp_path, request, max_files=1)


@given("a C++ file containing a declaration", target_fixture="source")
def create_cpp_source(tmp_path: Path) -> Path:
    source = tmp_path / "query.cpp"
    source.write_text("int network_client_marker = 1;\n", encoding="utf-8")
    return source


@when("I run the declaration query", target_fixture="events")
def run_declaration_query(server: RunningServer, source: Path):
    async def run():
        async with AsyncClient(server.endpoint) as client:
            return await client.query(
                'varDecl(hasName("network_client_marker")).bind("decl")',
                [source], working_directory=source.parent,
            )
    return asyncio.run(run())


@then("the stream contains a match and successful completion")
def has_match_and_completion(events) -> None:
    kinds = [event.WhichOneof("event") for event in events]
    assert "match" in kinds
    assert kinds[-1] == "completed"
    completed = next(event.completed for event in events if event.WhichOneof("event") == "completed")
    assert completed.match_count >= 1


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


@then("the declaration contains a complete typed initializer and exact type")
def has_typed_semantic_declaration(events) -> None:
    match = next(event.match for event in events if event.WhichOneof("event") == "match")
    binding = match.semantic_result.bindings["decl"]
    assert binding.is_complete
    assert not binding.availability
    assert binding.node.WhichOneof("payload") == "var_decl"
    variable = binding.node.var_decl.variable
    assert variable.declarator.value.named.qualified_name == "network_client_marker"
    assert variable.declarator.value.type.type.WhichOneof("payload") == "builtin_type"
    assert variable.initializer.WhichOneof("payload") == "integer_literal"
    assert variable.initializer.is_complete
    assert variable.initializer.integer_literal.value.unsigned_decimal == "1"
    assert variable.initializer.integer_literal.info.type.type.builtin_type.info.spelling == "int"
