"""Catalog fetches never block keystrokes or fan out into repeated RPCs."""

from __future__ import annotations

import asyncio

from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from clang_toolkit.cli.project_completion import (
    ProjectCompletionCache,
    refresh_project_menu,
)
from clang_toolkit.cli.prompt import create_session


def test_refresh_is_nonblocking_coalesced_and_notified():
    async def drive():
        release = asyncio.Event()
        updated = asyncio.Event()
        calls = 0

        async def load():
            nonlocal calls
            calls += 1
            await release.wait()
            return ("/projects/ctk-lab",)

        cache = ProjectCompletionCache()
        cache.bind(load, updated.set)
        try:
            for _ in range(100):
                assert cache.get() == ()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert calls == 1
            assert not updated.is_set()
            release.set()
            await asyncio.wait_for(updated.wait(), 1)
            assert cache.get() == ("/projects/ctk-lab",)
            assert calls == 1
        finally:
            await cache.aclose()

    asyncio.run(drive())


def test_refresh_keeps_last_good_snapshot_and_observes_added_projects():
    async def drive():
        release = asyncio.Event()
        updated = asyncio.Event()
        calls = 0

        async def load():
            nonlocal calls
            calls += 1
            if calls > 1:
                await release.wait()
                return ("/projects/ctk-lab", "/projects/another")
            return ("/projects/ctk-lab",)

        cache = ProjectCompletionCache(ttl=0)
        cache.bind(load, updated.set)
        try:
            assert cache.get() == ()
            await asyncio.wait_for(updated.wait(), 1)
            updated.clear()
            for _ in range(100):
                assert cache.get() == ("/projects/ctk-lab",)
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert calls == 2
            release.set()
            await asyncio.wait_for(updated.wait(), 1)
            assert cache.get() == ("/projects/another", "/projects/ctk-lab")
        finally:
            await cache.aclose()

    asyncio.run(drive())


def test_worker_refresh_uses_owner_loop_and_coalesces_requests():
    async def drive():
        loop = asyncio.get_running_loop()
        started = asyncio.Event()
        release = asyncio.Event()
        updated = asyncio.Event()
        calls = 0

        async def load():
            nonlocal calls
            assert asyncio.get_running_loop() is loop
            calls += 1
            started.set()
            await release.wait()
            return ("/projects/ctk-lab",)

        def notify():
            assert asyncio.get_running_loop() is loop
            updated.set()

        cache = ProjectCompletionCache()
        cache.bind(load, notify)
        try:
            snapshots = await asyncio.to_thread(lambda: [cache.get() for _ in range(100)])
            assert snapshots == [()] * 100
            await asyncio.wait_for(started.wait(), 1)
            assert calls == 1
            release.set()
            await asyncio.wait_for(updated.wait(), 1)
            assert await asyncio.to_thread(cache.get) == ("/projects/ctk-lab",)
        finally:
            await cache.aclose()

    asyncio.run(drive())


def test_close_prevents_already_queued_worker_refresh():
    async def drive():
        from concurrent.futures import ThreadPoolExecutor

        async def load():
            raise AssertionError("closed cache must not start a queued fetch")

        cache = ProjectCompletionCache()
        cache.bind(load, lambda: None)
        # Keep this loop paused while the worker queues its refresh callback.
        with ThreadPoolExecutor(max_workers=1) as executor:
            assert executor.submit(cache.get).result(timeout=1) == ()
        await cache.aclose()
        await asyncio.sleep(0)
        assert cache._task is None
        assert await asyncio.to_thread(cache.get) == ()

    asyncio.run(drive())


def test_failed_and_timed_out_refreshes_preserve_the_snapshot():
    async def drive():
        completed = asyncio.Event()
        calls = 0

        async def load():
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("offline")
            if calls > 2:
                await asyncio.Event().wait()
            return ("/projects/ctk-lab",)

        cache = ProjectCompletionCache(ttl=0, timeout=0.01)
        cache.bind(load, completed.set)
        try:
            cache.get()
            await asyncio.wait_for(completed.wait(), 1)
            completed.clear()
            assert cache.get() == ("/projects/ctk-lab",)
            await asyncio.sleep(0.02)
            assert calls == 2
            assert cache.get() == ("/projects/ctk-lab",)
            await asyncio.sleep(0.03)
            assert calls == 3
            assert not completed.is_set()
            assert cache.get() == ("/projects/ctk-lab",)
        finally:
            await cache.aclose()

    asyncio.run(drive())


def test_close_cancels_inflight_fetch_and_prevents_later_requests():
    async def drive():
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def load():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        cache = ProjectCompletionCache()
        cache.bind(load, lambda: None)
        cache.get()
        await asyncio.wait_for(started.wait(), 1)
        await cache.aclose()
        assert cancelled.is_set()
        assert cache.get() == ()

    asyncio.run(drive())


def test_typing_stays_responsive_and_late_catalog_reopens_the_project_menu():
    async def drive():
        started = asyncio.Event()
        release = asyncio.Event()

        async def load():
            started.set()
            await release.wait()
            return ("/projects/ctk-lab",)

        async def until(predicate):
            async with asyncio.timeout(3):
                while not predicate():
                    await asyncio.sleep(0.01)

        cache = ProjectCompletionCache()
        with create_pipe_input() as pipe:
            session = create_session(
                input=pipe,
                output=DummyOutput(),
                script_engine="compiled",
                indexed_projects=cache.get,
            )
            cache.bind(
                load, lambda: refresh_project_menu(session.default_buffer, session.app)
            )
            prompt = asyncio.create_task(session.prompt_async("ctk> "))
            try:
                source = 'index find "flow" in '
                pipe.send_text(source)
                await until(lambda: session.default_buffer.text == source)
                await asyncio.wait_for(started.wait(), 3)
                pipe.send_text('"ct')
                await until(lambda: session.default_buffer.text == source + '"ct')
                release.set()
                await until(
                    lambda: session.default_buffer.complete_state is not None
                    and bool(session.default_buffer.complete_state.completions)
                )
                state = session.default_buffer.complete_state
                (item,) = state.completions
                assert item.display_text == "ctk-lab"
                session.default_buffer.apply_completion(item)
                pipe.send_text("\r")
                assert await asyncio.wait_for(prompt, 3) == source + '"ctk-lab"'
            finally:
                await cache.aclose()
                if not prompt.done():
                    prompt.cancel()
                    await asyncio.gather(prompt, return_exceptions=True)

    asyncio.run(drive())
