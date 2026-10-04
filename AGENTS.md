# AGENTS.md — clang-toolkit

C++ tools built on the Clang C++ APIs (AST matchers, AST traversal, CFG, call graph),
exposed through a server with a single well-defined interface. Consumers: an interactive
Python CLI (prompt_toolkit), a Python API for users and AI agents, and one-shot command-line use.

## Architecture

```
 ctk (interactive CLI)   Python API / AI agents   one-shot CLI
            \                    |                   /
             +------ api/ (gRPC: UDS + HTTPS) ------+
                                 |
                        server/ (ctk-server, C++20)
   net/      transport front-end, request dispatch
   script/   scripting engine composing queries (custom DSL, ANTLR4 grammar)
   cache/    in-memory LRU (hash table; radix tree for prefix lookups)
   storage/  persistent cache (filesystem blobs + SQLite index)
   clang/    Clang API layer: matchers, traversal, CFG, call graph
```

- `api/` is the contract. Change it first, then server and Python client together.
- Transport: gRPC/protobuf over a Unix domain socket (`unix://<path>`, local) and HTTPS (TLS, remote).
- `server/include/ctk/<module>/` holds public headers; `server/src/<module>/` the implementation.
- Only `server/src/clang/` includes Clang/LLVM headers. Everything else stays Clang-free.
- `python/clang_toolkit/` — `client.py` (Python API) and `cli/` (interactive console).
- REPL commands are parsed with Lark (`python/clang_toolkit/cli/grammar.lark`); no hand-written parser.

## Layout

```
api/                 interface definition (protobuf .proto, gRPC services)
server/              C++ server (CMake target ctk-server, lib ctk_core, ctk_clang)
server/tests/        GoogleTest unit tests
python/clang_toolkit Python package (API + CLI, entry point `ctk`)
tests/unit/          pytest unit tests
tests/e2e/           pytest-bdd E2E tests (features/*.feature + step modules)
```

## Supported platforms

| Platform | Clang/LLVM | Install |
|---|---|---|
| macOS (arm64/x86_64) | Homebrew LLVM (`/opt/homebrew/opt/llvm`, `/usr/local/opt/llvm`) | `brew install llvm cmake ninja uv` |
| RHEL 9 (and Rocky/Alma 9) | system `clang`, `clang-devel`, `llvm-devel` (`/usr`) | `dnf install clang clang-devel llvm-devel cmake ninja-build` + uv |

- `cmake/Platform.cmake` auto-detects the toolchain before `project()`; override with
  `-DCTK_LLVM_ROOT=<prefix>` or `-DCMAKE_CXX_COMPILER=...`.
- RHEL ships Clang/LLVM as shared libs only: link via `clang-cpp` + `LLVM` targets (fallback: component libs).
- Keep code portable: no platform APIs outside a dedicated `platform/` shim; use `std::filesystem`.
- RHEL validation: `podman build -f packaging/rhel9.Containerfile -t ctk-rhel9 . && podman run --rm ctk-rhel9`.

## Tooling

- Compiler: Clang, C++20.
- Build: CMake (>= 3.24) + Ninja via presets (`dev`, `release`, `dev-noclang`).
- Python: `uv` for env and deps; Python >= 3.14 (pinned in `.python-version`).
- Tests: GoogleTest/CTest (C++), pytest (Python unit), pytest-bdd (E2E BDD).

## Commands

```bash
# C++
cmake --preset dev && cmake --build --preset dev && ctest --preset dev
cmake --preset dev-noclang   # build without the Clang layer

# Python
uv sync
uv run pytest tests/unit
uv run pytest tests/e2e -m e2e
uv run ctk --server unix:///tmp/ctk.sock
```

## Conventions

- C++: namespace `ctk::<module>`, `snake_case` files, `PascalCase` types, headers `.hpp`.
- Python: type hints everywhere, `from __future__ import annotations`.
- Every new server operation needs: API entry, server handler, Python client method,
  CLI command, unit test, and a BDD scenario.
- Run all C++ and Python tests before declaring work done; all must be green.
- Worktrees go under `~/.claude/worktrees/clang-toolkit/<branch>`.
