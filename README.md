# clang-toolkit

C++ source analysis built on the Clang APIs, with a native gRPC server,
an interactive console, and typed Python and TypeScript clients. Parse source
files, run AST matchers, continue queries from retained bindings, traverse ASTs,
build control-flow and call graphs, and compose analyses with the server
scripting language.

The current server supports local Unix domain sockets and plaintext loopback
TCP. Source paths and compilation arguments refer to the server's filesystem.

## Requirements

- Clang/LLVM development libraries and a compiler supporting C++23.
- CMake 3.25 or later (for the supplied presets) and Ninja.
- gRPC, protobuf, libyaml, SQLite, and OpenSSL development libraries.
- Python 3.14 or later and [uv](https://docs.astral.sh/uv/).
- Internet access on the first build to fetch the ANTLR4 runtime and GoogleTest.

On macOS, install the dependencies with Homebrew:

```sh
brew install llvm cmake ninja grpc protobuf libyaml sqlite openssl@3 uv
```

For Rocky Linux / RHEL 9, use the dependency list and container validation
instructions in [packaging/rhel9.Containerfile](packaging/rhel9.Containerfile).
The build discovers Homebrew LLVM on macOS and system LLVM on RHEL; use
`-DCTK_LLVM_ROOT=/path/to/llvm` to select another installation.

## Quick start

```sh
git clone https://github.com/husams/clang-toolkit.git
cd clang-toolkit
cmake --preset dev
cmake --build --preset dev
uv sync
```

Start the server from the repository root:

```sh
build/dev/server/ctk-server
```

In another terminal, from the same directory, run a query against the included
fixture:

```sh
uv run ctk --query 'functionDecl(isDefinition()).bind("f")' --file examples/parse_match.cc
```

Or start the interactive console:

```sh
uv run ctk
```

Enter each expression as a separate console input:

```text
let tree = parse "examples/parse_match.cc";
let functions = match functionDecl(isDefinition()).bind("f") in $tree;
let calls = match callExpr().bind("call") in $functions.f;
print $calls
```

The default endpoint is `ctk.sock` in the platform temporary directory. Server
and clients discover shared `clang-toolkit.yaml` configuration files; `-c`
selects an explicit file for the server or console. See
[network configuration](docs/network.md) for the schema and merge order.

## Python API

```python
from clang_toolkit import Client

with Client() as client:
    with client.match('functionDecl(isDefinition()).bind("f")',
                      file="examples/parse_match.cc") as functions:
        with functions.binding("f").match('callExpr().bind("call")') as calls:
            for row in calls:
                print(row.bindings["call"])
```

Context managers release retained server values. `AsyncClient` provides the
asynchronous API. See [parse and match expressions](docs/parse-match-expressions.md)
and the runnable [Python example](examples/parse_match.py).

For Node.js 22 or later, see the [TypeScript SDK](typescript/README.md).

## Development

Run the C++ and Python suites after building the server:

```sh
ctest --preset dev
uv run python -m pytest tests/unit
uv run python -m pytest tests/e2e -m e2e
```

The E2E suite launches the native server from `build/dev/server/ctk-server`;
set `CTK_SERVER` to use another build. The `release` preset builds an optimized
server, and `dev-noclang` builds without the Clang layer.

To validate in the Rocky Linux 9 container:

```sh
podman build -f packaging/rhel9.Containerfile -t ctk-rhel9 .
podman run --rm ctk-rhel9
```

## Project layout

| Directory | Purpose |
| --- | --- |
| `api/` | Versioned protobuf and gRPC contracts, generated semantic AST schemas. |
| `server/` | Native server, application coordination, Clang analysis, cache, storage, and scripting. |
| `python/clang_toolkit/` | Python API and Lark-based interactive console. |
| `typescript/` | Typed Node.js gRPC SDK. |
| `server/tests/` | C++ GoogleTest suites. |
| `tests/` | Python unit and pytest-bdd E2E suites. |
| `examples/` | Small C++ fixtures and runnable client examples. |
| `docs/` | Contracts, design notes, and feature documentation. |

Public API changes start in `api/` and update the server and clients together.
Clang/LLVM dependencies stay in the native analysis layer. Project conventions
and platform details are recorded in [AGENTS.md](AGENTS.md).

## Documentation

- [API contract](api/README.md)
- [Parse and match expressions](docs/parse-match-expressions.md)
- [Interactive console](docs/repl.md)
- [Console command reference](docs/console-command-reference.md)
- [AST traversal](docs/ast-traversal.md)
- [Control-flow graphs](docs/control-flow.md)
- [Call graphs](docs/call-graphs.md)
- [Server scripting](docs/server-scripting.md)
- [Semantic serialization](docs/semantic-serialization.md)
- [Result cursors](docs/result-cursors.md)
- [Network configuration](docs/network.md)
- [Cache](docs/cache.md)

## License

Licensed under the [MIT License](LICENSE).
