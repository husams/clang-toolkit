# Background project symbol index

The server maintains a persistent cross-TU symbol index independently of retained
AST sessions. Indexing reads the compilation database, extracts declarations and
definitions in a separate `ctk-index-worker` process, and replaces each affected
TU's rows in one SQLite transaction. Unchanged compile entries are skipped.

## Console

```ctk
index list
index start "/server/path/project"
index status "/server/path/project"
index pause "/server/path/project"
index resume "/server/path/project"
index find "demo::Widget" in "/server/path/project"
index lookup "USR_FROM_A_RESULT" in "/server/path/project"
index cancel "/server/path/project"
```

List, status and lookup commands return reusable values:

```ctk
let projects = index list
print $projects.total_count
print $projects.projects
let progress = index status "/server/path/project"
print $progress.state
let symbols = index find "demo::Widget" in "/server/path/project"
print $symbols.symbols
```

Paths refer to the server filesystem. Relative console project paths use the
console working directory. No VS Code extension code is needed to use the wire
contract; an extension can call the same service directly.

`index list` lists all saved project indexes in this server's storage plus its
current monitors, sorted by project path, with the folder name and full path in
separate columns, state, indexed/total translation units
and a total project count. It includes paused, failed and cancelled jobs. Saved
indexes without a current monitor (including after restart) show `IDLE`; start them
again to revalidate their coverage. Listing never parses project sources.
`server status` and the live Server status pane show the same project inventory,
the number of projects in progress (queued or indexing), indexed and pending
translation-unit counts, and the current translation unit when available.

Freshness reconciliation shows `CHECKING`; `INDEXING` means extraction is in
flight. Saved indexed coverage is separate from this pass's reused entries,
newly indexed entries, and currently indexing entries. Pending entries may only
need freshness checks; they do not imply that saved entries will be extracted
again. Reused and newly indexed counts reset at the start of each pass.

## Python and UI gRPC clients

```python
from clang_toolkit import Client

with Client("unix:///tmp/ctk.sock") as client:
    projects = client.list_project_indexes()
    print(projects.total_count)
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
`ListProjectIndexes(ListProjectIndexesRequest)` returns `projects` and
`total_count`; `ServerStatus` includes the same data in `project_indexes`.

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

## Reusing indexes across updates

The extractor identity hashes extraction sources, the selected compiler/resource
directory, and the worker request/result messages (including `Symbol`). Inventory
RPCs, status messages, protocol comments and formatting do not invalidate saved
translation units. A compatibility anchor preserves the deployed v1 identity for
the unchanged worker contract; changing worker fields still invalidates it.

On macOS, a fresh build caches its native architecture; subsequent configurations
preserve the selected value, including explicit empty and universal settings.
Deploy a built `ctk-server`/`ctk-index-worker` pair without reconfiguring the indexed
project or regenerating its compilation database. Compiler arguments remain part
of the context because changing target architecture can change extracted symbols.

`scripts/server.sh` manages a persistent launchd job on macOS and a detached
process on Linux. The macOS job label is recorded beside `server.pid`, scoped to
the state directory, and removed before stopping the child process. Restarts
therefore cannot resurrect an older build through its supervisor. Compiler-input
environment variables (including empty values) are forwarded explicitly; unrelated
environment values are not copied into launch arguments. The lifecycle
helper does not configure builds, rewrite compilation databases, or delete saved
indexes; restart the desired project monitors through the indexing API afterward.

`index status "ctk-lab"` resolves the Project name shown by `index list`.
Duplicate names report all matching paths; use the full path to select one.
Unknown names report an error. Explicit paths (including `./ctk-lab`) retain path semantics.
