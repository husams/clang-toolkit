"""Serve shared-parser compilation requests from the native LLVM runner."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
from threading import Thread
from typing import Any

from lark.exceptions import LarkError

LowerRequest = Callable[[str, Path | None, bool], str]


@contextmanager
def compiler_channel(lower: LowerRequest | None) -> Iterator[dict[str, Any]]:
    if lower is None:
        yield {}
        return

    frontend, native = socket.socketpair()
    with frontend, native:

        def serve() -> None:
            with frontend.makefile("rwb") as stream:
                try:
                    for line in stream:
                        try:
                            request = json.loads(line)
                            source = request["source"]
                            path = Path(request["path"]) if request["path"] else None
                            response = {"ir": lower(source, path, request["library"])}
                        except (LarkError, OSError, SyntaxError, ValueError) as error:
                            response = {"error": str(error)}
                        stream.write(json.dumps(response).encode("utf-8") + b"\n")
                        stream.flush()
                except OSError:
                    return

        thread = Thread(target=serve, name="ctk-jit-compiler")
        thread.start()
        try:
            yield {
                "env": {**os.environ, "CTK_JIT_COMPILER_FD": str(native.fileno())},
                "pass_fds": (native.fileno(),),
            }
        finally:
            frontend.shutdown(socket.SHUT_RDWR)
            thread.join()
