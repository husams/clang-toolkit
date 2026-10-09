# File output and resource management

These commands run in the `ctk` console and in console input piped to `ctk`.
Paths are on the client computer. Native files, sessions and caches are on the server.

## Save query results

```text
let x = match functionDecl().bind("f") in "example.cc"
save $x to "functions.json" as json
save $x to "functions.yaml" as yaml
let filename = "$HOME/functions.proto"
save $x to $filename as proto
load $filename into $snapshot
```

Save replaces the destination atomically. Without a suffix, the format's suffix
is added; without `as`, the suffix determines the format, defaulting to YAML.
An explicit format and an existing suffix must agree. CSV remains supported for
flat lists. JSON, YAML and binary protobuf preserve a versioned typed envelope.
The protobuf schema is `api/match/v1/saved_value.proto` (`ctk.match.v1.SavedValue`),
including decimal text for arbitrary-size integers. `.proto` here contains binary
snapshot data, not protobuf source text. Loads return detached snapshots: printed
and exported match rows keep their semantic values but cannot select live trees.

Destinations accept string variables, `$name` and `${reference}` interpolation
inside double quotes, and `~/` using `HOME`. Lookup uses runtime bindings, then
environment variables, then configuration values. Single quotes remain literal.
Undefined variables and non-string destinations fail before file creation.
Relative paths use the console working directory. Loading a missing, malformed
or unsupported snapshot preserves the destination binding.

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
idempotent. The existing bare `session close` still closes the opted-in legacy
bidirectional query (`ctk --session`). Its stream lifecycle remains separate from
native cursor listing and attachment.

Memory pruning (the default) drops reuse entries, retaining active cursor pins.
Disk pruning retires unused snapshots while preserving leased artifact closures.
`all` drops memory reuse before disk cleanup. Pruning returns before/after counters;
concurrent queries may publish new entries during the operation. Native trees
remain usable even if their reusable disk copy is retired.

## Python API

Both `Client` and `AsyncClient` expose `server_status()`, `list_sessions()`,
`attach_session(id)`, `close_match(id)` and
`prune_caches(memory=True, disk=False)`. Async methods must be awaited.
The four added RPCs are in `MatchService`; an older server returns `UNIMPLEMENTED`
for them and needs to be restarted with the new binary.
