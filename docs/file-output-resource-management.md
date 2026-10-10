# File output and resource management

These commands run in the `ctk` console and in console input piped to `ctk`.
`save`, `load`, `read`, and print destinations use the client computer's
filesystem. Source paths used by `files`, `file`, `match`, and analysis commands
are resolved on the serving machine; remote clients must pass paths visible to
the server.

## Save query results

```text
let x = match functionDecl().bind("f") in "example.cc"
save $x to "functions.json" as json
save $x to "functions.yaml" as yaml
save $x[0].f to "binding.yaml" as yaml
save $x[0].f.node to "node.json" as json
save $x[0].f.node.qualified_name to "name.json" as json
let filename = "$HOME/functions.proto"
save $x to $filename as proto
load $filename into $snapshot
```

Save replaces the destination atomically. Without a suffix, the format's suffix
is added; without `as`, the suffix determines the format, defaulting to YAML.
An explicit format and an existing suffix must agree. CSV remains supported for
flat lists. JSON and YAML contain ordinary records, lists and scalar values;
for example, a boolean field is written as `is_implicit: true`. A saved binding
contains its AST payload directly, such as `cxx_record_decl: {...}`, without
runtime `value` or binding `node` carriers. Binary
protobuf preserves a versioned typed envelope.
The protobuf schema is `api/match/v1/saved_value.proto` (`ctk.match.v1.SavedValue`),
including decimal text for arbitrary-size integers. `.proto` here contains binary
snapshot data, not protobuf source text. Loads return detached snapshots: printed
and exported match rows keep their semantic values but cannot select live trees.

Read binding properties with `$x[0].f.node`, `$x[0].f.is_complete` and
`$x[0].f.keys`; existing `.value` paths remain supported. Typing `$x[0].f` or
`print $x[0].f` displays the copied bound value directly. Save an indexed binding
such as `$x[0].f` to export that binding's AST properties, or save an individual
field. Rows export a `bindings` dictionary of named AST payloads; collections
export an ordered list of rows. JSON/YAML omit binding availability, serializer
completeness flags, continuation scopes and row provenance. Unrequested fields
remain omitted. Actual AST properties, including source locations and
`is_complete_definition`, retain their schema names. User dictionary keys such
as `availability` or `is_complete` and explicitly selected scalar fields remain
ordinary data. Binding exports also retain copied source coordinates, ranges,
symbol identity, documentation and call-site facts when present; saving `.node`
alone exports only the AST payload. Protobuf snapshots retain availability and restore exact byte/enum
values and semantic views; ordinary JSON/YAML reload as records, lists and
scalars. For example, load an exported function binding and read
`$saved.function_decl.function.declarator.value.named.qualified_name` using the exported
schema structure. Older typed JSON/YAML snapshots remain loadable.

These navigation and display changes run in the `ctk` console. Restart that
console and repeat the match to use an updated version.

JSON/YAML byte fields become text when their contents are valid UTF-8;
otherwise they become `base64:` followed by the encoded bytes. Known enum
values use their symbolic names; unknown enum values use their numeric value.
Use protobuf when exact typed restoration is needed.

Destinations accept string variables, `$name` and `${reference}` interpolation
inside double quotes, and `~/` using `HOME`. Lookup uses runtime bindings, then
environment variables, then configuration values. Single quotes remain literal.
Undefined variables and non-string destinations fail before file creation.
Relative paths use the console working directory. Loading a missing, malformed
or unsupported snapshot preserves the destination binding.

## Discover and process serving-machine files

```text
let inputs = files "src/**/*.cpp"
file list discovered in $inputs
file open $inputs.inputs[0] into $source
match functionDecl().bind("f") in $source
file info $source
file refresh $source into $fresh
file close $source
resource status
batch part in $inputs size 20 jobs 4 memory "768MiB" do {
  let rows = match functionDecl().bind("f") in $part.inputs
  save $rows to "group-${part.index}.json" as json
}
```

`files` discovers paths on the serving machine and returns an immutable
metadata-only `FileSet` with frozen compilation profiles and diagnostics. It
does not parse sources or retain ASTs. `file open` creates a caller-owned lease;
`file refresh` creates a handle to the current snapshot while older handles and
their result cursors remain independent. `file close all` releases explicit
leases owned by the caller. Resource status includes file leases and transient
scopes alongside cursor, cache, and admission accounting.

`batch` accepts only a `FileSet`; choose exactly one of `size` or balanced
`count`. Groups run in the foreground and are admitted atomically before any
body work. Each group has a fresh local scope and a transient server resource
scope that is cancelled on failure and released before the next group begins.
`jobs` is the maximum concurrency within that group and may exceed its size.
When omitted, it uses the effective configured `pool_size` from direct
multi-file matching; an explicit value overrides it for this batch only. The
default error policy is `stop`; `continue` runs later groups after
acknowledged cleanup but the final command still reports failure. Unconfirmed
cleanup always stops later work. Live handles, trees, match results, or wrappers
containing them cannot escape a group through outer variables, lists, dictionaries
or closures; save detached data or scalar summaries instead.

Output is emitted as statements run and is limited to 1,000,000 characters per
group. The final JSON report is capped at 4,000 characters and includes a fixed
sample of at most eight groups with unknown cleanup. It reports file outcomes
only for inputs actually targeted by scoped operations; untouched admitted files
are counted as unattempted. The report also includes accepted inputs, skipped
and cancelled files, successful `save` exports, output characters, peak
accounted/reserved bytes, remaining
external pins, and cleanup acknowledgment.

## Read JSON and YAML documents

```text
let data = read "config.json"
let settings = read "config.yaml"
print $data.project.name
print $settings.sources[0]
let sources = foreach $source in $settings.sources do $source done
let filename = "$HOME/config.yml"
let settings = read $filename
```

`read` accepts ordinary `.json`, `.yaml` and `.yml` files on the client computer.
Objects become records with dot access and string-key indexing, lists support
indexing and `foreach`, and scalar/null roots are preserved. Empty YAML returns
null. YAML uses safe loading and rejects recursive aliases. Paths accept literals,
string variables, File values and double-quoted interpolation; relative paths use
the console working directory and `~/` expands through HOME. Failed reads preserve
the existing assignment value. `read` preserves document keys as written.
`load` also recognizes the exact legacy `schema_version`, `type`, `value`
snapshot envelope; use `read` when an ordinary document intentionally has
that same shape.

## Print text to a file

```text
let filename = "$HOME/functions.txt"
print "Functions:" to $filename
print $x to $filename mode append
print "Replacement" to $filename mode replace
```

Each print writes rendered text followed by a newline. The default is replacement;
`mode append` preserves existing contents. This affects only that print. The
persistent sink defaults to append and accepts the same destination variables:

```text
set output to $filename mode append
print $x
set output to $filename mode replace
print "Fresh output"
set output to stdout
```

Help and diagnostics remain on the console. One-print replacement is atomic;
persistent replacement truncates immediately when the output setting is applied.

## Inspect and release resources

```text
server status
cache status
session list
bindings
binding rename $x to $functions
binding drop $functions
session attach "SESSION-UUID" into $tree
match functionDecl() in $tree
session close $tree
cache prune memory
cache prune disk
cache prune all
```

Resource commands display labeled text and tables in the console. Byte sizes use
KiB below 1 MiB, MiB below 1 GiB, and GiB otherwise, with two decimal places.
Session IDs and local binding names remain visible for reuse in commands.

`server status` reports uptime, current process RSS when available, active native
cursor count, estimated retained memory and configured cursor limits. Cache
accounting includes reusable snapshots, estimated reusable native memory, pending
builds, native artifact disk bytes, ready/stale/leased snapshots and the server's
storage root. Unavailable caches are flagged explicitly. Cursor and reusable-cache
memory overlap when they pin the same AST; these counters must not be added to
estimate process RSS. Artifact bytes exclude SQLite metadata and directory overhead.

`session list` reports only retained parse/match cursors owned by the caller,
including ID, file, revision, row count, native binding names and idle expiry.
Expired sessions are excluded. Attach renews the lease and returns a tree handle
at the current revision without rerunning a query or restoring serialized rows.
The ID argument can also be a UUID string variable, tree, match value or binding
selection. Attached handles share the cursor: explicit close or final owner cleanup
in any client can invalidate other clients' attachments. A new match in an attached
tree creates independent result ownership. Insecure local transports share the
local-user owner; authenticated transports use verified peer identity.

`bindings` lists local variable names/types and retained session IDs without
displaying their values. Drop removes one variable; aliases keep resources alive.
Rename preserves the value and rejects an occupied destination. These are lexical
variable controls; native matcher binding names are listed by `session list`.

`session close ID_OR_VALUE` releases one cursor and invalidates its local aliases;
independent derived cursors remain usable. Closing a valid unavailable UUID is
idempotent. The console opens its query session automatically; bare `session close`
closes that query's input. Define its matcher with `session start`, add files with
`session add`, then execute `session match`. Ordinary parse/match expressions run
immediately and create retained cursors independently of this query stream.

Memory pruning (the default) drops reuse entries, retaining active cursor pins.
Disk pruning retires unused snapshots while preserving leased artifact closures.
`all` drops memory reuse before disk cleanup. Pruning returns before/after counters;
concurrent queries may publish new entries during the operation. Native trees
remain usable even if their reusable disk copy is retired.

## Python API

Both `Client` and `AsyncClient` expose `discover_files()`, `open_file()`,
`list_files()`, `file_info()`, `close_file()`, `close_all_files()`,
`refresh_file()`, `open_resource_scope()` and `resource_status()`; async methods
must be awaited. The frozen `InputDescriptor` and `FileSet` values carry serving
paths and compilation-profile metadata without retaining native resources.
`FileHandle` is an opaque caller-owned lease. A `ResourceScope` atomically admits
its `inputs` and optional memory/job limits, and supports acknowledged
`describe()`, `cancel()`, and `release()` plus sync and async context-manager
use. Pass `scope=scope` to `parse`, `match_in`, `traverse`, `cfg`, call-graph,
and script operations to keep their native resources inside that scope.
`FileBatch` and `partition_inputs(files, size=... xor count=...)` provide
bounded, immutable manifest slices. Async API methods must be awaited. The
server must be running a build that implements the file and resource-scope RPCs.
