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
separate columns, state, saved indexed files, current-pass checked/total,
active extractions, and last completed pass reused/newly indexed/failed counts
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
again. Current-pass counters reset at the start of each pass; last completed
pass counts stay visible throughout checking, pausing, or cancellation. The
completed summary is persisted atomically in existing index metadata and survives
server restarts. Older indexes show a dash (not zero) until a full pass finishes.
`index status` includes the completed pass timestamp and detailed current progress.
A completed pass may include failures; an interrupted pass never replaces the summary.

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
Python API lookup remains exact by default; pass `prefix=True` for prefix search. The console `index find` now defaults to case-insensitive prefix matching; add `exact` for case-sensitive literal matching. A symbol result includes
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

After initial reconciliation, monitors wait for filesystem notifications for
source/header contents, compilation databases, the worker executable, and
include-directory entries. macOS uses path-based FSEvents streams; Linux uses
inotify directory events. Idle monitoring does not retain a descriptor for each
file or impose a 1,024-file coverage limit. Temporary-file-and-rename saves,
deletions, and recreation are detected by path, including successive replacements.
Independent projects retain independent event queues, and idle notifications do
not compete with cached readers for the index descriptor allowance.

The poll interval controls notification sampling, capped at two seconds; it does
not request a full scan every tick. Unchanged projects keep their completed
status and last-pass counts. A five-minute safety reconciliation covers missed
or dropped events and unavailable OS notifications. Newly discovered dependencies
receive one additional guarded validation pass. Pause/resume and cancellation
remain interruptible. Include-inventory cache validation still uses synchronous,
inode-validated directory guards; asynchronous idle notifications do not decide
publication freshness, and dependency contents are freshly validated as before.

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
Set an optional name when starting, or rename any saved project:

```ctk
index start "." as "My library"
index rename "My library" to "Core library"
index status "Core library"
```

Without `as`, start preserves a saved name or defaults to the directory name.
Names persist across restarts. Renaming changes metadata only, preserving the
project path, indexed symbols, revision and monitoring state. Status, controls,
search and autocomplete use the saved name. A full path can always identify a
project, including when renaming it. Names must be 1–255 bytes and cannot contain
slashes, control characters or leading/trailing spaces, or be path-like (`.`,
`..`, or starting with `~`). The wildcard scope `*` is also reserved. The Python APIs accept
`start_project_index(root, project_name="My library")` and
`rename_project_index(root, "Core library")`.

Duplicate names report all matching paths; use the full path to select one.
Unknown names report an error. Explicit paths (including `./ctk-lab`) retain path semantics.

`index find "flow::clamp" in "ctk-lab"` uses the same project-name resolution and ambiguity checks as `index status`; explicit paths remain supported.

### Partial and global console search

```ctk
index find "cla" in "ctk-lab"
index find "flow::cl*" in "ctk-lab"
index find "flow::clamp" exact in "ctk-lab"
index find "flow::cl*"
index find "flow::cl*" in "*"
let hits = index find "flow::cl*"
print $hits[0].project_root
print $hits[0].result.symbols
```

Omitting `in` (or using `in "*"`) searches every project returned by `index list`.
Results are grouped by full project path, with per-project revision, stale and
truncated indicators; a failed project is reported without hiding other results.
Global values are a list of `{project_root, result, error}` records; `result` is
null for a failed project. Scoped searches keep their existing response shape.

Prefixes use the server's existing indexed name/qualified-name searches and
retain its 100-result limit per project. A trailing `*` is shorthand for the
same prefix lookup, not a scan. Empty prefixes, leading/internal `*`, `?`, and
character classes are rejected. Strings are literal prefixes, not regular
expressions; unrestricted glob/regex searches would require scanning and are
not provided. Use `exact` to search literal operator names containing `*`, `?`,
or brackets. Global searches perform one bounded lookup per listed project,
so their cost grows with the number of projects.

### Optional symbol kind filter

```ctk
index find "flow::cl*" kind function in "ctk-lab"
index find "Widget" kind class
index find "counter" exact kind variable
index find "flow::clamp" exact in "ctk-lab"
let hits = index find "flow::clamp" exact kind function in "ctk-lab"
print $hits.symbols[0].kind
```

Omit `kind` to search every kind, including namespaces, aliases, and enums.
Functions include free functions, methods, constructors, destructors, conversion
functions and deduction guides. Classes include named records (class, struct,
union) and class-template specializations. Variables include indexed variables,
fields, bindings and variable-template specializations; local variables are not
part of the project definition index. The filter works with prefixes, trailing
`*`, exact matching and global searches, and runs on the server before limiting
results. Every result retains its raw Clang `kind` (such as `Function`,
`CXXMethod`, `CXXRecord`, or `Var`), also shown beside its name in console output.

Python clients accept `find_symbols(project, query, kind="function")`, with an
empty kind (the default) meaning unfiltered. Both server and client must be
updated to use filtering. Stored symbols and worker extraction are unchanged;
existing indexes do not need reindexing for this search filter.

### Aliases and unique per-project results

```ctk
index find "Alias" kind alias in "ctk-lab"
index find "ctk::" kind alias
```

`kind alias` includes `using` type aliases and `typedef` declarations; their raw
kinds are `TypeAlias` and `Typedef`. Alias templates are represented by their
defining `TypeAlias` declaration, not a separate template wrapper. Namespace
aliases remain separate kinds and are available in unfiltered searches.

Console `index find` returns each definition once per project, even when a header
is indexed through several translation units or compile variants. Definitions
are identified by USR, file path, byte offset and definition status; distinct
overloads and locations remain separate. Global searches deduplicate within each
project and retain matching definitions from different projects. Each returned
symbol retains one deterministic representative translation unit and compile
context. Grouping happens before result limits, so duplicates do not consume the
100-symbol budget or incorrectly mark a complete set as truncated.

The Python API keeps per-TU provenance by default. Opt into the console behavior
with `find_symbols(project, query, kind="alias", unique_symbols=True)`.
`index lookup` remains a provenance lookup and can still return per-TU entries.
No stored index schema or worker extraction change is required.

## Keeping status changes out of the native PCH

`ctk/clang/tooling.hpp` includes the stable `cache_resources.pb.h` cache-inventory
contract, not the match-service RPC header. `CacheResources` lives in
`match/v1/cache_resources.proto`; the match service imports that schema publicly so
existing Python `match_service_pb2.CacheResources` constructors and protobuf
fully qualified names/field numbers stay compatible.

The CMake match-schema generator emits each module independently, so editing an
RPC schema does not rewrite unchanged resource/parse headers. This keeps
`ProjectIndexStatus` and `ServerStatusResponse` out of the shared
native precompiled header. Status-only API changes may still rebuild the small
set of files that directly consume those RPC contracts, but must not rebuild the
native PCH or all serializers. Cache-resource or native input changes remain
real dependencies. Moving to this layout requires one PCH rebuild and normal
revalidation of affected indexed files; later status changes use the separated
layout. The extractor fingerprint and existing compilation arguments are unchanged;
the leaf schema adds one generated cache-inventory translation unit.

`tests/unit/test_index_build_identity.py` checks the cache contract's dependency
closure, legacy Python constructor compatibility, and the actual Ninja PCH
dependency list when a native build is available. Incremental validation also
adds temporary fields to project, server, and resource status messages, rebuilds, checks the PCH and
serializer objects remain unchanged, then restores the schemas and rebuilds.

A controlled rebuild with temporary fields in all three status responses rebuilt
21 of 323 native objects: the shared PCH (including its timestamp), all serializer
objects, existing compile arguments, and extractor identity remained unchanged.
Restoring the schemas and rebuilding also left the PCH unchanged. These counts
measure dependency isolation, not a claim that every RPC consumer avoids rebuilds.
