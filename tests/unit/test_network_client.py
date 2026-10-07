import asyncio
from pathlib import Path

import pytest

from clang_toolkit import client as client_module
from clang_toolkit._generated.query.v1 import query_pb2
from clang_toolkit.client import AsyncClient, Client, QueryError, _format_violation
from clang_toolkit.configuration import ConfigurationError, load_network_config
from clang_toolkit._generated.match.v1 import match_service_pb2, parse_response_pb2


class Stream:
    def __init__(self, events):
        self.events = events
        self.cancelled = False

    def __aiter__(self):
        self.iterator = iter(self.events)
        return self

    async def __anext__(self):
        try:
            return next(self.iterator)
        except StopIteration:
            raise StopAsyncIteration from None

    def done(self):
        return False

    def cancel(self):
        self.cancelled = True
        return True


class Stub:
    def __init__(self, events):
        self.events = events
        self.request = None

    def Query(self, request, timeout=None):
        self.request = request
        self.timeout = timeout
        self.stream = Stream(self.events)
        return self.stream


class Channel:
    async def close(self):
        return None


def patch_transport(monkeypatch, events):
    stub = Stub(events)
    monkeypatch.setattr(client_module.grpc.aio, "insecure_channel", lambda *_args, **_kwargs: Channel())
    monkeypatch.setattr(client_module.query_pb2_grpc, "QueryServiceStub", lambda _channel: stub)
    return stub


def test_async_query_collects_completed_and_preserves_request(monkeypatch, tmp_path):
    events = [query_pb2.QueryEvent(started=query_pb2.Started()),
              query_pb2.QueryEvent(completed=query_pb2.Completed(match_count=0))]
    stub = patch_transport(monkeypatch, events)
    source = tmp_path / "sample.cpp"
    source.write_text("int value;", encoding="utf-8")

    async def run():
        client = AsyncClient(address="unix:///tmp/test.sock")
        got = await client.query(
            "varDecl()", [Path("sample.cpp")], working_directory=tmp_path,
            compile_arguments=["-std=c++20"],
        )
        await client.aclose()
        return got

    got = asyncio.run(run())
    assert [event.WhichOneof("event") for event in got] == ["started", "completed"]
    assert stub.request.files[0].path == str(source.resolve())
    assert list(stub.request.files[0].compile_arguments) == ["-std=c++20"]


def test_stream_without_completed_raises_with_partial_events(monkeypatch):
    partial = query_pb2.QueryEvent(started=query_pb2.Started())
    patch_transport(monkeypatch, [partial])

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            return await client.query("varDecl()")

    with pytest.raises(QueryError, match="without Completed") as error:
        asyncio.run(run())
    assert error.value.partial_events == (partial,)


def test_background_query_retains_task_until_stream_consumed(monkeypatch):
    patch_transport(monkeypatch, [
        query_pb2.QueryEvent(started=query_pb2.Started()),
        query_pb2.QueryEvent(completed=query_pb2.Completed()),
    ])

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            background = client.start_background_query("varDecl()")
            return await background.result()

    assert len(asyncio.run(run())) == 2


def test_sync_facade_rejects_use_inside_running_loop():
    async def run():
        with pytest.raises(RuntimeError, match="active event loop"):
            Client("unix:///tmp/test.sock").match("varDecl()")

    asyncio.run(run())


def test_limit_violation_format_includes_bytes_and_gibibytes():
    violation = query_pb2.LimitViolation(
        limit_name="session.overhead_memory_bytes",
        current_value=1_073_741_824,
        configured_limit=2_147_483_648,
        requested_increment=1_073_741_824,
        projected_value=3_221_225_472,
    )
    rendered = _format_violation(violation)
    assert "current 1073741824" in rendered
    assert "requested +1073741824" in rendered
    assert "projected 3221225472" in rendered
    assert "limit 2147483648" in rendered
    assert "3.00 GiB" in rendered
    assert "2.00 GiB" in rendered


def test_callback_failure_closes_and_cancels_partial_stream(monkeypatch):
    partial = query_pb2.QueryEvent(started=query_pb2.Started())
    stub = patch_transport(monkeypatch, [partial])

    async def run():
        client = AsyncClient(address="unix:///tmp/test.sock")
        def fail(_event):
            raise ValueError("callback failed")
        with pytest.raises(ValueError, match="callback failed"):
            await client.query("varDecl()", on_event=fail)
        stream = stub.stream
        await client.aclose()
        return stream

    stream = asyncio.run(run())
    assert stream.cancelled


def patch_native_transport(monkeypatch):
    created, requests = [], []
    count = 0

    def channel(target, *, options=()):
        created.append((target, options))
        return Channel()

    class NativeStub:
        def __init__(self, _channel):
            pass

        async def Parse(self, request, *, timeout=None):
            nonlocal count
            count += 1
            return parse_response_pb2.ParseResponse(session_id=f"native-{count}", result_revision=1)

        async def Match(self, request, *, timeout=None):
            nonlocal count
            count += 1
            requests.append(request)
            return match_service_pb2.MatchResponse(session_id=f"native-{count}", result_revision=1)

        async def CloseSession(self, request, *, timeout=None):
            return match_service_pb2.CloseSessionResponse()

    monkeypatch.setattr(client_module.grpc.aio, "insecure_channel", channel)
    monkeypatch.setattr(client_module.query_pb2_grpc, "QueryServiceStub", lambda _channel: Stub([]))
    monkeypatch.setattr(client_module.match_service_pb2_grpc, "MatchServiceStub", NativeStub)
    return created, requests


def test_no_address_sync_client_discovers_once_and_caches_winning_configuration(monkeypatch, tmp_path):
    cwd = tmp_path / "project"
    cwd.mkdir()
    path = cwd / ".clang-toolkit.yaml"
    path.write_text("network:\n  unix:\n    socket_path: run/first.sock\n")
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(client_module, "load_network_config", lambda selected=None:
        load_network_config(selected, cwd=cwd, home=tmp_path / "home", system_dir=tmp_path / "etc"))
    created, requests = patch_native_transport(monkeypatch)
    with Client() as client:
        assert client.address is None
        assert client.config.provenance["network.unix.socket_path"] == str(path)
        with client.match('functionDecl().bind("f")', file="example.cc") as functions:
            path.write_text("network:\n  unix:\n    socket_path: run/second.sock\n")
            with functions.binding("f").match("callExpr()"):
                pass
        assert requests[1].preserve_source
    assert all(target == f"unix://{cwd / 'run/first.sock'}" for target, _ in created)
    with Client() as restarted:
        assert restarted.config.target == f"unix://{cwd / 'run/second.sock'}"


def test_no_address_async_contexts_use_discovered_yaml(monkeypatch, tmp_path):
    cwd = tmp_path / "project"
    cwd.mkdir()
    path = cwd / ".clang-toolkit.yaml"
    path.write_text("network:\n  unix:\n    socket_path: run/async.sock\nclient:\n  grpc:\n    max_receive_message_bytes: 4096\n")
    monkeypatch.setattr(client_module, "load_network_config", lambda selected=None:
        load_network_config(selected, cwd=cwd, home=tmp_path / "home", system_dir=tmp_path / "etc"))
    created, _ = patch_native_transport(monkeypatch)

    async def run():
        async with AsyncClient() as client:
            assert client.address is None
            async with await client.match('functionDecl().bind("f")', file="example.cc") as functions:
                child = await functions.binding("f").match("callExpr()")
            async with child:
                assert not child._owner.closed
            assert not client._value_cleanup and not client._pending_value_cleanup

    asyncio.run(run())
    assert created == [(f"unix://{cwd / 'run/async.sock'}", (("grpc.max_receive_message_length", 4096),))]


def test_explicit_endpoint_and_injected_config_do_not_bypass_selected_file_errors(monkeypatch, tmp_path):
    selected = tmp_path / "bad.yaml"
    selected.write_text("pool:\n  size: false\n")
    defaults = load_network_config(cwd=tmp_path, home=tmp_path / "home", system_dir=tmp_path / "etc")
    created, _ = patch_native_transport(monkeypatch)
    with pytest.raises(ConfigurationError) as failure:
        with Client("unix:///override.sock", config_path=selected, config=defaults):
            pass
    assert str(selected) in str(failure.value) and "pool.size" in str(failure.value)

    async def run():
        with pytest.raises(ConfigurationError) as failure:
            async with AsyncClient("unix:///override.sock", config_path=selected, config=defaults):
                pass
        assert str(selected) in str(failure.value) and "pool.size" in str(failure.value)

    asyncio.run(run())
    assert not created
