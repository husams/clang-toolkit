# Background project symbol index

The server maintains a persistent cross-TU symbol index independently of retained
AST sessions. Indexing reads the compilation database, extracts declarations and
definitions in a separate `ctk-index-worker` process, and replaces each affected
TU's rows in one SQLite transaction. Unchanged compile entries are skipped.

## Console

```ctk
index start "/server/path/project"
index status "/server/path/project"
index pause "/server/path/project"
index resume "/server/path/project"
index find "demo::Widget" in "/server/path/project"
index lookup "USR_FROM_A_RESULT" in "/server/path/project"
index cancel "/server/path/project"
```

Status and lookup commands return reusable values:

```ctk
let progress = index status "/server/path/project"
print $progress.state
let symbols = index find "demo::Widget" in "/server/path/project"
print $symbols.symbols
```

Paths refer to the server filesystem. Relative console project paths use the
console working directory. No VS Code extension code is needed to use the wire
contract; an extension can call the same service directly.

## Python and UI gRPC clients

```python
from clang_toolkit import Client

with Client("unix:///tmp/ctk.sock") as client:
    client.start_project_index(
        "/server/path/project", compile_commands="/server/path/project/build",
        poll_interval_seconds=2,
    )
    progress = client.project_index_status("/server/path/project")
    client.pause_project_index("/server/path/project")
    matches = client.find_symbols("/server/path/project", "demo::Wid", prefix=True)
    client.resume_project_index("/server/path/project")
```

`AsyncClient` exposes the same methods as awaitables. Results are protobuf values.
Exact lookup is the default; prefix search is explicit. A symbol result includes
its USR, declaration or definition location, owning TU, and compilation context.
It is detached index data, not a native AST pointer.

The service is `ctk.index.v1.IndexService`, defined in
`api/index/v1/index_service.proto`. UI clients can poll
`GetProjectIndexStatus(ProjectIndexRequest)` and call `PauseProjectIndex` or
`ResumeProjectIndex` with the same project identity. `StartProjectIndex` returns
queued work rather than waiting for extraction. `CancelProjectIndex` preserves
already committed TU contributions. `FindSymbols` and `LookupSymbol` query the
committed index without parsing source files.

## Persistence and change detection

The symbol database has three tables: `metadata`, `translation_unit`, and
`symbol`. TU rows retain compile context and a JSON dependency manifest with file
digests. A source edit invalidates its compile entries; a header edit invalidates
the entries whose manifests include that header. Reconciliation checks command
changes and removed entries as well as file changes. Shared header declarations
may appear under several TUs so their compilation context is preserved.

The server monitors multiple projects independently. Start each project with
`index start`; pause, resume, and cancel affect only the named project. All
projects share the server's extraction worker limit (at most four processes),
and yield to foreground requests. Starting an already monitored project returns
its current status. Persisted indexes remain queryable. After a
server restart, call start again to revalidate a project's saved manifests;
unchanged TUs are skipped. Paused, cancelled, or unrevalidated indexes are marked
stale. Response files are expanded when reading compilation commands so changing
their effective arguments invalidates the relevant compile entries.

Precompiled headers and explicit module inputs are tracked along with the source
buffers they load. Compiler environment settings participate in the compile
context. Extraction uses CTK's configured compiler driver so its defaults match
the native parser and compatible precompiled headers; C source files retain C
language mode.

Dependency manifests also record filename inventories for the source directory
and explicit include roots. New or removed files under those roots conservatively
invalidate their TUs, covering newly created headers that change include lookup.
Inventories are bounded to 500,000 paths and 32 MiB of names per root. Changes to
implicit system search roots require a toolchain or command refresh. Keep index
storage outside project/include roots. Reference search, macros as searchable
symbols, and project wide atomic snapshots are outside this implementation.

An update stages facts outside the live index, then commits the TU symbols and
its dependency manifest together. Failed or cancelled extraction leaves committed
rows available. Consumers must inspect freshness and coverage; an empty partial
result does not establish that a symbol does not exist.

## Request isolation

The worker has separate Clang objects and never uses the foreground native
executor. One background writer and short read transactions use a dedicated
SQLite database. Worker priority and resource budgets restrict extraction, and
foreground activity takes priority over background admission. Status and control
calls do not perform project scans or parse source files.

CPU, memory bandwidth, and storage are still shared physical resources. The
implementation prevents waiting for extraction; it does not promise zero latency
change under every machine load. Test latency with representative projects before
choosing operational budgets. Install `ctk-index-worker` alongside `ctk-server`.
