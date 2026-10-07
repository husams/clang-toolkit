# Query network component

The server uses native gRPC callback reactors over one Unix socket or one loopback
TCP listener. Configuration discovery and endpoint resolution are shared with the
Python client. Parsing and matching run on application workers; gRPC owns sockets
and transport threads.

## Build and run

macOS dependencies: `brew install llvm cmake ninja grpc protobuf libyaml uv`.
Rocky/RHEL dependencies are recorded in `packaging/rhel9.Containerfile`.

```sh
cmake --preset dev
cmake --build --preset dev
uv sync
build/dev/server/ctk-server -c /absolute/path/settings.yaml
uv run ctk -c /absolute/path/settings.yaml --query 'functionDecl().bind("function")' --file /absolute/path/source.cpp
```

Both executables retain the agreed `-c` / `--cofing` spelling. `--print-config`
prints the resolved endpoint. Omitting a file discovers and merges system, home
and working-directory files. At home/working-directory level, the hidden file
overrides the plain file; an explicitly selected file has highest precedence.

```yaml
version: 1
network:
  transport: unix
  unix:
    socket_path: null
pool:
  size: 3
queue:
  size: 100
session:
  max_files: 100
  max_memory_bytes: 2147483648
server:
  grpc:
    max_send_message_bytes: -1
client:
  grpc:
    max_receive_message_bytes: -1
```

The Unix default is `<platform-temporary-directory>/ctk.sock`. A relative override
uses its supplying file's directory. TCP requires an explicit loopback host and
port; there is no default TCP port. IPv6 targets use brackets. Missing discovered
files are normal; explicit missing files and invalid supplied fields are errors,
even if a higher layer would override them. Server send and client receive limits
default to `-1` (no configured wire cap). Other gRPC fields use the library
defaults unless configured;
null clears an inherited setting, including these response defaults.

Complete cursor results remain bounded by `session.max_memory_bytes`, including
the retained snapshot and binding state. A positive server send limit adds a
response byte cap for parse/match cursors and native analysis operations.
For example, the following settings impose an explicit 128 MiB wire limit:

```yaml
server:
  grpc:
    max_send_message_bytes: 134217728
client:
  grpc:
    max_receive_message_bytes: 134217728
```

A server send value of `null` or `-1` leaves the application memory budget in
effect. Explicit byte-cap failures report their limit and preserve existing
cursor revisions. Header declarations are included by default; no source-file
exclusion is needed to retrieve a large result.

## Python API

The [protobuf command contract](../api/query/v1/README.md) defines both RPCs,
incremental commands, streamed events and structured rejection details.

```python
from clang_toolkit.client import AsyncClient

async with AsyncClient(config_path="/absolute/path/settings.yaml") as client:
    async for event in client.iter_events('varDecl().bind("decl")', ["source.cpp"]):
        print(event)

    task = client.start_background_query('functionDecl().bind("function")', ["source.cpp"])
    # Other event-loop tasks can run while the stream is consumed.
    events = await task.result()

    session = await client.query_session()
    await session.start_query('varDecl().bind("decl")')
    await session.add_files(["source.cpp"])
    await session.match()
    await session.half_close()
    events = [event async for event in session.events()]
```

The collector requires the final `Completed` event and successful terminal gRPC
status. Failed calls expose partial events through `QueryError`; those events do
not represent a complete successful result. The synchronous `Client.match` facade
is available outside an active event loop. The bidirectional sender and receiver
run concurrently and serialize each direction independently.
The server reads the next session command after the application has consumed the
previous one, bounding command retention without pausing accepted matching work.

## Interactive commands

```text
background functionDecl().bind("function") in ["source.cpp"]
session start "varDecl().bind(\"decl\")"
session add "source.cpp"
session match
session pause
session resume
session close
```

Start the CLI with `--session` to enable bidirectional commands. A fixed-file query
can also start with `--query ... --file ... --background`, leaving the prompt active.
Closing input means no further commands; accepted work and outgoing writes still
finish before the call completes. Only explicit Pause changes production pacing.
Resume a paused session before closing input, or cancel the call with `aclose()`.
Server shutdown closes input and resumes paused work to drain accepted requests.

## Resource and delivery policy

Foreground, background and bidirectional calls share a 100-file/profile and 2 GiB
retained/admission budget, plus a shared 2 GiB parsing/overhead allowance. Atomic
batch rejection includes every violated limit and its current, configured,
requested and projected values. A rejected bidirectional command leaves the
stream and previously accepted work running. Native memory estimates can be
exceeded without pausing or cancelling accepted work.

The memory output queue holds 64 events, each at most 512 KiB, and spills overflow
to an ordered temporary spool. Spooling runs off gRPC reaction threads. Slow clients
do not pause native parsing/matching. Matches arrive as callbacks occur, and events
from different files may interleave. The write pump owns each payload until
`OnWriteDone`; it calls `Finish` once after application completion and the last
write. Transport cleanup detaches producers before deleting a reactor.

## Scope

`ctk.query.v1.QueryService` adds transport-ready semantic summaries. The complete
recursive AST payload serializer and the legacy `ctk.match.v1.MatchService` cursor
contract remain separate work. Native ASTs currently stay within the Clang facade.
Simple main-only profiles reuse ASTs after exact consumed-byte checks. Inputs
using preprocessing, headers, modules or PCH rebuild conservatively to avoid
stale lookup results.
Production `SnapshotLoader` and native Store reload/publication adapters are not
provided by the existing Cache/Storage interfaces. This network implementation
does not claim persistent AST reuse, disk-cache orchestration, CFG or callgraph RPCs.

Design: [Clang Toolkit Network Layer Design](https://chatgpt.com/space/page_561b779557cc8191a5aace9bf6273191).
Implementation and validation: [network-implementation-progress.md](network-implementation-progress.md).
