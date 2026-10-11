from __future__ import annotations

import asyncio
from pathlib import Path
import os
import select
import time

from pytest_bdd import given, scenarios, then, when

from clang_toolkit import AsyncClient, Client
from clang_toolkit.cli.runtime.values import MatchSet
from test_network_steps import _launch_server

scenarios("durable_batches.feature")


@given(
    "an isolated durable batch server with a source file",
    target_fixture="durable_fixture",
)
def durable_fixture(tmp_path: Path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "durable-storage"))
    server = _launch_server("unix", tmp_path, request, max_files=2)
    source = tmp_path / "durable.cc"
    source.write_text("int durable_target() { return 7; }\n", encoding="utf-8")
    return server, source, tmp_path


@when(
    "I start and wait for a durable batch through the async SDK",
    target_fixture="durable_run_id",
)
def start_durable_run(durable_fixture) -> str:
    server, source, root = durable_fixture

    async def run() -> str:
        async with AsyncClient(server.endpoint) as client:
            last_run_id = ""
            for start_number, (cwd_mode, jobs) in enumerate(
                (("omitted", 2), ("omitted", 2)), start=1
            ):
                discover_kwargs = (
                    {"working_directory": root} if cwd_mode == "explicit" else {}
                )
                manifest = await client.discover_files([source], **discover_kwargs)
                run_kwargs = {} if jobs is None else {"jobs": jobs}
                started = await client.start_batch(
                    manifest,
                    'let rows = match functionDecl().bind("f") in $part.inputs; $rows;',
                    size=1,
                    request_id=f"durable-sdk-{cwd_mode}-{jobs}-{start_number}",
                    **run_kwargs,
                )
                current = started
                deadline = time.monotonic() + 40
                while time.monotonic() < deadline:
                    try:
                        current = await client.batch_status(started.run_id)
                    except Exception as error:
                        output = ""
                        if server.process.stdout is not None:
                            ready, _, _ = select.select(
                                [server.process.stdout], [], [], 0
                            )
                            if ready:
                                output = os.read(
                                    server.process.stdout.fileno(), 4096
                                ).decode(errors="replace")
                        raise AssertionError(
                            f"batch status failed; server exit={server.process.poll()}, "
                            f"output={output!r}"
                        ) from error
                    if current.status in {
                        "completed",
                        "failed",
                        "cancelled",
                        "interrupted",
                    }:
                        break
                    await asyncio.sleep(0.025)
                resource_status = await client.resource_status()
                assert current.status == "completed", (
                    f"run ({cwd_mode=}, {jobs=}) stayed {current.status} after "
                    f"40s: {current.to_proto()}; resources={resource_status}"
                )
                assert current.result_group_indices == (1,)
                last_run_id = started.run_id
            return last_run_id

    return asyncio.run(run())


@then("a new sync client can read its final detached group values")
def read_durable_run_after_reconnect(durable_fixture, durable_run_id: str) -> None:
    server, _source, _root = durable_fixture
    with Client(server.endpoint) as client:
        run = client.batch_status(durable_run_id)
    assert run.status == "completed"
    assert run.result_group_indices == (1,)
    results = run.promote()
    assert len(results) == 1
    assert isinstance(results[0], MatchSet)
    assert results[0].rows[0].bindings["f"].symbol_identity
