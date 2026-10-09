# Console command reference

Use `help COMMAND` or `COMMAND?` in the console. Multiword topics work too:
`help cursor open` and `cursor open?` are equivalent. Help is local and remains
visible when command output is redirected. Bare `help` lists all forms.

Uppercase words are placeholders; brackets denote optional syntax. Examples
use the checked-in `examples/parse_match.cc` fixture. Run them from the repository
root with a native server for analysis operations. Use returned cursor IDs in
place of `CURSOR_ID`; the console opens its query session automatically.

## help

Explain console syntax locally; no server is required.

```text
help [command [subcommand]]
command [subcommand]?
```

- No topic: list commands. A topic: purpose, usage, arguments and examples.
- Help and errors always appear in the console, regardless of output routing.
- Every syntax error explains the expected input and marks its location with a caret; unknown commands suggest help.

```text
help match
parse?
help cursor open
cursor open?
```

## parse

Parse a file and retain its native tree as a value.

```text
parse PATH
let tree = parse PATH
```

- PATH: quoted file path or a reference to a path/File; relative to the session directory.
- Automatically loads compile_commands.json; extra_args append compiler overrides.
- Select a database with ctk --compile-commands PATH or set compile_commands PATH.
- Use the result with match ... in $tree or a scoped in $tree block.

```text
parse "examples/parse_match.cc"
let tree = parse "examples/parse_match.cc"
```

## match

Match native nodes and optionally retain the resulting rows.

```text
match MATCHER [in TARGET]
let rows = match MATCHER [in TARGET]
match MATCHER in TARGET do { STATEMENT; ... }
```

- Use `match` after `=` to assign query results; a bare matcher assignment constructs a matcher and accepts no `in` target.
- MATCHER: root matcher call or $matcher; .bind("name") names a selected node.
- TARGET: quoted file path, directory or glob; File, Directory, file list, parsed tree, match value or binding selection.
- Directories recurse over C/C++/Objective-C source files; globs support absolute paths and **. Expansion uses the client's filesystem. Empty selections return an empty collection.
- Target variables must already exist; bind labels name bindings in the new results.
- With do { ... }, run ordinary statements as each streamed row arrives. Every bind label becomes a local variable: .bind("func") exposes $func.value.node. Newlines or semicolons separate statements; # starts a comment.
- Each row gets a fresh local scope; outer variables are restored afterwards. Streamed bindings provide copied semantic fields; native continuation requires a completed retained result. Row work is serialized across concurrent file streams; row order follows arrival order. Limits: 10000 rows and 1000000 bytes of collected output.
- A missing `match` in this assignment form shows its insertion point and a corrected command.
- Without in: use the enclosing block tree, otherwise configured files (default []).
- Rows use zero-based indices: $rows[0].f; $rows.f selects bind label f across rows.
- Collections expose length, isEmpty, rows, zero-based indexing, and unique(field), sort(field), filter(field, expected). Selectors accept dotted paths; unique preserves the first row and sort orders numbers numerically, strings lexically, and other values deterministically by type and text.
- A directory, glob or file-list query returns one typed collection with per-row source_file provenance. Files run in parallel up to pool.size, retaining input order. Continue from one binding with match ... in $rows[0].f, or from every row with match ... in $rows.f.
- Continuation rows expose source_match_index (the zero-based parent row) and source_file, so multi-file and parent-row provenance remain inspectable.
- Semantic fields continue from the bound node, for example $rows[0].f.value.node.
- Declaration conveniences include node.name (typed DeclarationName), node.qualified_name (string), node.declared_type, and binding shortcuts such as decl_name, parameter_name, record_name, type_name and decl_type.
- Bindings expose symbol_identity (Clang USR for named declarations), raw documentation, location and range. Location file/line/column is valid only when location.valid is true; coordinates are one-based and include macro status. Ranges retain expansion and spelling endpoints.
- Call-expression bindings expose call_site with caller identity/name, static callee identity/name and CALL_DISPATCH_DIRECT, CALL_DISPATCH_INDIRECT or CALL_DISPATCH_VIRTUAL. VIRTUAL records the statically selected declaration, not a runtime target.
- Completion labels active payloads, fields and methods, and offers inherited fields such as name, qualified_name and return_type.
- Match values contain immediate fields; bodies, parameters, operands and other child AST values are unrequested. Retrieve child nodes with a follow-up match.
- Read type text through return_type.description.spelling; return_type.type is unrequested.
- fieldState("field") reports PRESENT, ABSENT, SEMANTICALLY_ABSENT, INAPPLICABLE, UNREQUESTED, UNAVAILABLE, TRUNCATED or UNSPECIFIED.
- hasField("field") checks presence only when the field has presence information; it raises for UNREQUESTED fields. fieldOr("field", default) supplies a default for ABSENT, SEMANTICALLY_ABSENT or INAPPLICABLE fields and raises for UNREQUESTED, UNAVAILABLE, TRUNCATED or UNSPECIFIED fields.
- Tab inside hasField, fieldState or fieldOr arguments offers quoted field names.
- Uses extra_args (default []) and traversal (default AsIs); server validates matcher types.

```text
match functionDecl().bind("f") in "examples/parse_match.cc"
let rows = match functionDecl().bind("f") in "examples/parse_match.cc"
let m = match functionDecl(isExpansionInMainFile()).bind("f") in $f
match callExpr() in $rows.f
$rows[0].f.value.node.qualified_name
$rows[0].f.value.node.name.identifier
$rows[0].f.value.node.function_decl.function.declarator.value.named.qualified_name
$rows[0].f.value.node.cxx_method_decl.method.function.declarator.value.named.qualified_name
let calls = match callExpr().bind("c") in $rows[0].f
$calls[0].source_file
$calls[0].source_match_index
$rows[0].f.symbol_identity
$rows[0].f.location.line
$rows[0].f.range.expansion_begin.column
$rows[0].f.documentation
$calls[0].c.call_site.static_callee_name
let unique = $rows.unique("f.symbol_identity")
let filtered = $unique.filter("f.decl_name", "demo::run")
$rows[0].f.value.node.hasField("body")
$rows[0].f.value.node.fieldState("parameters")
$rows[0].f.value.node.name.fieldOr("identifier", "anonymous")
```

## let

Bind a typed expression without printing it.

```text
let NAME = VALUE
let NAME(PARAM, ...) = MATCHER
```

- NAME: identifier without $. References use $name, fields and zero-based [index].
- VALUE: matcher, literal, list, reference, glob, parse, match, foreach or scoped block. match do is a statement loop and does not produce an assignable collection.
- Matcher construction is local; parse/match require a server. Failed evaluation preserves the prior binding.
- Parameterized matchers use let named(name) = functionDecl(hasName($name)). Parameters are declared without $ and referenced with $ inside the routine. Calls use named("value") and may be nested or followed by .bind("label").
- A routine body must return a matcher. Arguments may be strings, numbers, booleans, matcher values or references. Parameters are local to each call; other references and routines use their current values at call time. Argument counts must match, parameter names must be unique, built-in matcher names are reserved, and call depth is limited to 64.
- let silently retains typed query and graph results. Read counts with .length, rows with [index], and select bind label f across rows with $rows.f.
- Use unique(field), sort(field) and filter(field, expected) on supported collections; field selectors may be dotted paths.

```text
let predicate = hasName("main")
let named(name) = functionDecl(hasName($name))
let rows = match named("main").bind("f") in "examples/parse_match.cc"
let matcher = functionDecl($predicate)
let files = glob("examples/*.cc")
let rows = match $matcher in $files
let continued = match callExpr().bind("call") in $rows.f
let unique = $rows.unique("f.symbol_identity").sort("f.decl_name")
let graph = traverse "examples/parse_match.cc" depth 1 projection shallow main-file true
```

## inspect

Inspect a value's bounded shape, fields, methods and availability locally.

```text
inspect $REFERENCE
```

- Accepts runtime bindings and indexed/field selections; no server request is made.
- Output is bounded to a preview of the value. Use fieldState on semantic values to distinguish UNREQUESTED from absent fields.

```text
inspect $rows[0].f
```

## in

Evaluate a declarative block with a default parsed tree and local bindings.

```text
in parse PATH { let NAME = VALUE; ... yield VALUE; }
in $tree { let NAME = VALUE; ... yield VALUE; }
```

- The target must be a parsed tree; assignment statements require semicolons.
- Unqualified match uses this tree. Nested blocks restore the enclosing tree on exit.
- One terminal yield is required; its final semicolon is optional. Locals disappear on exit.
- Yielded native values retain the tree resources they need.

```text
let result = in parse "examples/parse_match.cc" { let rows = match functionDecl().bind("f"); yield rows; }
```

## yield

Return one value from a scoped in block.

```text
in $tree { ... yield VALUE; }
```

- Only supported as the terminal expression of an in block, not a standalone command.
- VALUE: expression, $reference or bare local name; no default value.

```text
in parse "examples/parse_match.cc" { let rows = match functionDecl(); yield rows; }
```

## print

Render a value through the configured output destination.

```text
print VALUE [to PATH [mode replace|append]]
$reference
QUOTED_STRING
```

- VALUE: any value expression. Output defaults to stdout; let is silent.
- to PATH writes only this print: replaces by default; mode append adds to an existing file.
- PATH accepts a quoted/interpolated string or $variable; relative to the session directory.
- Double quotes interpolate $name/${reference}; single quotes are literal.
- Escape a dollar as \$ in double quotes. Lists expose length, isEmpty and joinWith(separator).

```text
let values = [1, 2, 3]
print $values
$values.length
"count=${values.length}"
```

## foreach

Map a list expression using a scoped iterator.

```text
foreach $NAME in LIST do VALUE [done]
let results = foreach $NAME in LIST do VALUE done
```

- LIST must evaluate to a list (at most 10000 elements); the body is one value expression.
- The iterator shadows outer names only during the body. A multiline do requires done.
- Returns a new ordinary list of body results; let captures it silently. Errors report the element index.
- Iterate query rows directly; each row exposes its bound values plus source_match_index and source_file. Iterate $rows.f to visit a named binding from every row.
- Lists and query collections support .length and indexing; use unique(field), sort(field) or filter(field, expected) before iterating when needed.

```text
let files = glob("examples/*.cc")
foreach $file in $files do "${file.basename}" done
```

## glob

Create sorted File and Directory values from a relative pattern.

```text
let files = glob(QUOTED_PATTERN)
```

- Patterns are relative to the session directory; ** recurses. Absolute patterns are rejected.
- No matches returns []; maximum 10000 entries. File/Directory metadata is a snapshot.
- Properties: size, modified, basename, dirname, absolute, parts. Match accepts directory targets; file lists must contain only files.

```text
let files = glob("examples/*.cc")
match varDecl() in $files
```

## background

Start a legacy streaming query while the prompt remains active.

```text
background MATCHER [in FILE_LIST]
```

- Requires an active asynchronous console client. Unlike match, in accepts only a file list.
- Omitted files use configured files (default []); uses configured extra_args.
- This streams query events; use declarative match/let for retained analysis values.

```text
background functionDecl() in ["examples/parse_match.cc"]
```

## set

Persist a project or user configuration override.

```text
set [user] traversal MODE
set [user] extra_args STRING_LIST
set [user] compile_commands PATH
set [user] cache_dir to DIRECTORY
set [user] files to FILE_LIST
set [user] output to PATH_OR_STDOUT [mode replace|append]
```

- Default scope: ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.
- Precedence: project > user > /etc/clang_tools/config.yaml > built-in defaults.
- traversal: AsIs (default) or IgnoreUnlessSpelledInSource. extra_args: [] by default.
- cache_dir: quoted directory, default null. files: list of paths/Files, default [].
- output: quoted/interpolated path, $variable or stdout (default). Files append; mode replace truncates.
- cache_dir is a persisted console setting; these console operations do not forward it as an RPC option.

```text
set extra_args ["-std=c++20"]
set files to glob("examples/*.cc")
set output to "results.txt"
set output to stdout
```

## clear

Remove an override, revealing the lower configuration layers.

```text
clear [user] KEY
```

- KEY: traversal, extra_args, compile_commands, cache_dir, files, output or vars.
- Default scope is project; user selects the home layer. Does not erase runtime let bindings.

```text
clear output
clear traversal
clear user extra_args
```

## add

Append one compiler argument to the project configuration.

```text
add extra_arg QUOTED_ARGUMENT
```

- Only extra_arg is supported. extra_args defaults to []; order is preserved.

```text
add extra_arg "-Iinclude"
add extra_arg "-std=c++20"
```

## save

Persist an evaluated variable as detached data.

```text
save $REFERENCE to PATH [as FORMAT]
```

- PATH: quoted/interpolated output file or $variable, relative to the session directory; ~/ uses HOME.
- FORMAT: yaml, json, proto or csv; inferred from suffix, yaml when no suffix (adds .yaml).
- YAML/JSON preserve typed values. CSV supports flat primitive/record lists.
- proto is binary SavedValue protobuf (api/match/v1/saved_value.proto), with a versioned typed envelope.
- Exported native rows are detached and cannot be reused as live match targets.

```text
let values = [1, 2, 3]
save $values to "values"
save $values to "values.json" as json
let filename = "$HOME/results.proto"
save $values to $filename as proto
```

## read

Read an ordinary JSON or YAML file as a console value.

```text
read PATH
let data = read PATH
```

- PATH: quoted/interpolated file path, string variable or File; .json, .yaml and .yml are supported.
- Files are read on the client computer; relative paths use the session directory and ~/ uses HOME.
- Objects expose fields and string-key indexing; lists support zero-based indexing and foreach. Scalar and null roots are also supported; empty YAML returns null.
- YAML uses safe loading; recursive aliases are rejected. Errors preserve the previous assignment value.
- read returns the document as written, including any schema_version/type/value keys. Use load to restore CTK save snapshots.

```text
let data = read "config.json"
let data = read "config.yaml"
print $data.project.name
print $data.sources[0]
let filename = "$HOME/config.yml"
let data = read $filename
```

## load

Load persisted data into a simple variable.

```text
load PATH into $NAME
```

- PATH: quoted/interpolated existing file or $variable; formats .yaml/.yml, .json, .proto and .csv.
- Without suffix: probe those extensions and require a unique match.
- NAME must be a simple variable. Failed loading preserves its prior value.

```text
let values = [1, 2, 3]
save $values to "values.yaml"
load "values.yaml" into $restored
print $restored
```

## history

Export or clear recorded command history.

```text
history save PATH
history clear
```

- The console records timestamped commands with a session UUID and optional label.
- Up/Down recall submitted commands across console restarts; Ctrl+R searches saved command history.
- Multiline commands remain one history entry. Syntax errors are recorded too; cancelled edits are not submitted.
- Default store: $XDG_STATE_HOME/clang_tools/history.jsonl, or ~/.local/state/clang_tools/history.jsonl.
- See help history save / help history clear.

```text
history save "commands.jsonl"
```

## history save

Export command history to a file.

```text
history save PATH
```

- PATH: quoted destination relative to the session directory; history must be enabled.

```text
history save "commands.jsonl"
```

## history clear

Clear saved commands and interactive recall history.

```text
history clear
```

- No arguments or options; history must be enabled.

```text
history clear
```

## session

List, attach or close retained native sessions, label history or control a query.

```text
session label STRING
session start QUERY_STRING
session add PATH
session match
session pause
session resume
session close
session list
session attach ID into $tree
session close ID_OR_VALUE
```

- list/attach/close ID operate native retained cursors; label is local.
- The console opens a query session automatically; start defines its matcher and add supplies files.
- See help session <subcommand>. Use parse/match/in/yield for declarative analysis.

```text
session label "study functions"
```

## session list

List retained native sessions owned by this caller.

```text
session list
```

- Shows labeled IDs, files, revisions, row counts, native binding names and idle expiry.

```text
session list
```

## session attach

Attach a retained session as a reusable tree and renew its idle expiry.

```text
session attach ID_OR_VALUE into $tree
```

- ID_OR_VALUE: quoted UUID, UUID variable or retained tree/match value.
- Only sessions owned by this caller are available; match in $tree creates independent results.
- Attached handles share this cursor; closing it invalidates attachments in other clients.
- Use session list to find IDs. Attaching does not restore result rows into a variable.

```text
session attach "00000000-0000-4000-8000-000000000001" into $tree
```

## server

Inspect the running server.

```text
server status
```

- See help server status for memory and cache accounting.

```text
server status
```

## server status

Show live server memory and retained resource usage.

```text
server status
```

- Reports uptime, current process RSS when available, session count and configured limits.
- Sizes use KiB below 1 MiB, MiB below 1 GiB, and GiB otherwise.
- Retained/native memory counters are estimates; cache and cursor bytes can overlap.
- Unavailable disk or memory cache accounting is explicitly flagged.

```text
server status
```

## cache

Inspect and prune native caches.

```text
cache status
cache prune [memory|disk|all]
```

- Active session trees and disk leases survive pruning.

```text
cache status
cache prune memory
```

## cache status

Show reusable memory snapshots and persistent native artifacts.

```text
cache status
```

- Sizes use KiB below 1 MiB, MiB below 1 GiB, and GiB otherwise.
- Disk bytes count native artifacts, excluding SQLite metadata and directory overhead.

```text
cache status
```

## cache prune

Release reusable memory entries and retire unused disk snapshots.

```text
cache prune [memory|disk|all]
```

- Default: memory. all releases memory reuse before disk cleanup.
- Pinned native sessions remain valid; their leased artifacts cannot be deleted.
- Returns before/after counters. Concurrent work may publish new entries during cleanup.

```text
cache prune memory
cache prune disk
cache prune all
```

## bindings

List local variable bindings and their retained session IDs.

```text
bindings
bindings list
```

- Lists names and types without printing bound values or environment variables.
- Native matcher binding names appear in session list; local variables use binding drop/rename.

```text
bindings
```

## binding

Drop or rename local variables.

```text
binding drop $name
binding rename $name to $new_name
```

- Targets must be simple variables. Rename rejects an occupied destination.
- Dropping a final reference releases its cursor; aliases keep it alive.

```text
binding rename $rows to $functions
binding drop $functions
```

## binding drop

Remove one local variable.

```text
binding drop $name
```

- Aliases remain valid; dropping the last retained owner releases resources.

```text
binding drop $rows
```

## binding rename

Rename a local variable without closing its resources.

```text
binding rename $name to $new_name
```

- The destination must not already exist; a same-name rename is a no-op.

```text
binding rename $rows to $functions
```

## session label

Set the local history label without changing its UUID.

```text
session label STRING
```

- STRING: quoted label; default is no label.

```text
session label "study functions"
```

## session start

Define the query for the console's session.

```text
session start QUERY_STRING
```

- QUERY_STRING is a quoted matcher expression, not a path. The session opens automatically.
- Uses configured extra_args and the session working directory.

```text
session start "functionDecl()"
```

## session add

Add a source file to the console's query session.

```text
session add PATH
```

- Define a query with session start first. PATH: quoted file path; uses configured extra_args and the session directory.

```text
session start "functionDecl()"
session add "examples/parse_match.cc"
session match
```

## session match

Run the query over files added to a bidirectional session.

```text
session match
```

- Requires session start and files supplied with session add; no arguments or options.
- An ordinary match expression executes immediately and does not define this session's query.

```text
session start "functionDecl()"
session add "examples/parse_match.cc"
session match
```

## session pause

Pause the session's query feedback.

```text
session pause
```

- Requires a started query; no arguments or options.

```text
session pause
```

## session resume

Resume the session's query feedback.

```text
session resume
```

- Requires a started query; no arguments or options.

```text
session resume
```

## session close

Close a retained native cursor or the console's query session.

```text
session close ID_OR_VALUE
session close
```

- With a quoted UUID, UUID variable, tree, match value or binding: release that retained cursor.
- A valid unavailable UUID is an idempotent close; derived independent cursors survive.
- Without an argument: close the query session's input. The console remains open.

```text
session close $tree
session close
```

## cursor

Operate explicit mutable legacy result cursors.

```text
cursor open PATH MATCHER
cursor continue ID BIND MATCHER [OPTIONS]
cursor restart ID MATCHER [revision NUMBER]
cursor close ID
```

- Paths, cursor IDs and binding names are quoted. IDs come from cursor open responses.
- See help cursor <subcommand>. Declarative match values manage their own retained handles.

```text
cursor open "examples/parse_match.cc" functionDecl().bind("f")
```

## cursor open

Match a file and return an explicit cursor identifier and revision.

```text
cursor open PATH MATCHER
```

- PATH: quoted source file; MATCHER: root call or matcher reference.
- Uses extra_args [] and traversal AsIs unless configured. row/scope/revision are rejected here.

```text
cursor open "examples/parse_match.cc" functionDecl().bind("f")
```

## cursor continue

Replace a cursor result by matching a selected binding.

```text
cursor continue ID BIND MATCHER [row INDEX] [scope MODE] [revision NUMBER]
```

- ID/BIND: quoted response cursor ID and existing binding name.
- row: zero-based unsigned index; omitted selects all rows. scope: subtree (default) or root_only.
- revision: positive expected result revision; omitted sends no guard. Options may occur once.

```text
cursor continue "CURSOR_ID" "f" callExpr().bind("call") row 0 scope subtree revision 1
```

## cursor restart

Replace a cursor result with a query over its entire retained tree.

```text
cursor restart ID MATCHER [revision NUMBER]
```

- ID: quoted response cursor ID. revision: positive expected revision; omitted sends no guard.
- row/scope are rejected; uses the configured traversal mode.

```text
cursor restart "CURSOR_ID" varDecl().bind("v") revision 2
```

## cursor close

Release an explicit retained cursor.

```text
cursor close ID
```

- ID: quoted response cursor ID; no options.

```text
cursor close "CURSOR_ID"
```

## traverse

Visit a file's AST and return a typed traversal value.

```text
traverse PATH [depth NUMBER] [nodes NUMBER] [implicit BOOL] [instantiations BOOL] [projection shallow|recursive] [main-file BOOL] [payload-depth NUMBER] [payload-nodes NUMBER]
```

- PATH: quoted source file or path/File reference. BOOL: true or false.
- depth: 0..256, default 64. nodes: 1..100000, default 10000.
- implicit/instantiations: false by default. Each option may occur once.
- projection: shallow by default; recursive includes nested semantic payloads. payload-depth: 1..64 (default 24); payload-nodes: 1..100000 (default 10000 per node payload). These limits are independent of traversal depth/nodes.
- main-file true restricts traversal to the main source file; default false includes header declarations.
- Assign to a variable to use nodes and depth_limited as typed fields. A standalone command continues to print ProtoJSON.
- Uses configured extra_args and the session directory.

```text
traverse "examples/parse_match.cc" depth 12 nodes 10000 projection shallow main-file true payload-depth 2 payload-nodes 1000
let graph = traverse "examples/parse_match.cc" depth 1 projection shallow main-file true
print $graph.nodes.length
```

## cfg

Build control-flow graphs for an exact qualified function name in a file.

```text
cfg FUNCTION in PATH [option NAME BOOL] [functions NUMBER] [blocks NUMBER] [elements NUMBER] [projection shallow|recursive] [main-file BOOL] [payload-depth NUMBER] [payload-nodes NUMBER]
```

- FUNCTION: bare, qualified or quoted exact name. PATH: quoted file or path/File reference.
- option NAME BOOL: a CfgOptions boolean field. prune_trivially_false_edges defaults to true; others to false.
- Option names: prune_trivially_false_edges, add_eh_edges, add_initializers, add_implicit_dtors, add_temporary_dtors, add_lifetime, add_scopes, add_loop_exit, add_static_init_branches, add_cxx_new_allocator, add_cxx_default_init_expr_in_ctors, add_cxx_default_init_expr_in_aggregates, add_rich_cxx_constructors, mark_elided_cxx_constructors, add_virtual_base_branches, omit_implicit_value_initializers, assume_reachable_default_in_switch_statements, always_add_statements
- functions: 1..1000 (default 100); blocks: 1..100000 (default 10000); elements: 1..1000000 (default 100000).
- projection: shallow by default; recursive expands nested semantic payloads. payload-depth: 1..64 (default 24); payload-nodes: 1..100000 (default 10000 per payload). These limits are independent of function/block/element limits.
- main-file true restricts graph construction to the main source file; default false includes headers.
- Assign a graph expression such as let flow = cfg FUNCTION in PATH to navigate graphs/blocks/elements. A standalone cfg command retains ProtoJSON output.
- Options may occur once. Uses configured extra_args. Legacy cfg FUNCTION is recognized but reports a local error requiring in PATH.

```text
cfg one in "examples/parse_match.cc" option add_implicit_dtors true blocks 10000 projection shallow main-file true payload-depth 2 payload-nodes 1000
let flow = cfg one in "examples/parse_match.cc" projection shallow main-file true
print $flow.graphs.length
```

## callgraph

Build the static native AST call graph for a file and return a typed value.

```text
callgraph PATH [nodes NUMBER] [edges NUMBER] [implicit BOOL] [instantiations BOOL] [projection shallow|recursive] [main-file BOOL] [payload-depth NUMBER] [payload-nodes NUMBER]
```

- PATH: quoted file or path/File reference. nodes: 1..100000 (default 10000).
- edges: 1..1000000 (default 100000). Options may occur once.
- Omitted implicit/instantiations use Clang CallGraph defaults (both true).
- projection: shallow by default; recursive expands nested semantic payloads. payload-depth: 1..64 (default 24); payload-nodes: 1..100000 (default 10000 per payload). These limits are independent of graph node/edge limits.
- main-file true scopes the graph to main-file declarations; default false includes headers. is_complete and external_edges_omitted expose graph coverage.
- The graph is static: indirect calls do not establish target edges, and virtual entries identify the statically selected declaration rather than runtime targets.
- Assign a graph expression to navigate nodes and edges. A standalone callgraph command continues to print ProtoJSON.
- Uses configured extra_args. Bare legacy callgraph is recognized but reports a local error requiring a path.

```text
callgraph "examples/parse_match.cc" nodes 10000 edges 100000 projection shallow main-file true payload-depth 2 payload-nodes 1000
let calls = callgraph "examples/parse_match.cc" nodes 100 projection shallow main-file true
print $calls.nodes.length
```

## script

Execute the bounded server DSL and display its typed response.

```text
script SOURCE [in PATH]
```

- SOURCE: quoted DSL source or string reference, not a script filename.
- PATH: optional quoted source file or path/File reference used as the DSL's default file.
- Uses configured extra_args and the session directory. Step budget defaults to 100; it is not a console option.

```text
script "emit 7;"
script 'let rows = match functionDecl() in "examples/parse_match.cc"; emit rows;'
```

## quit

Exit the console and clean up its client resources.

```text
quit
exit
```

- No arguments/options; Ctrl+D also exits. Ctrl+C cancels current input.

```text
quit
```

## exit

Exit the console (alias of quit).

```text
exit
```

- No arguments or options; closes the client and runtime resources.

```text
exit
```

## add extra_arg

Append one compiler argument to the project configuration.

```text
add extra_arg QUOTED_ARGUMENT
```

- Only extra_arg is supported. extra_args defaults to []; order is preserved.

```text
add extra_arg "-Iinclude"
add extra_arg "-std=c++20"
```

## set traversal

Set the traversal configuration override.

```text
set [user] traversal MODE
```

- MODE: AsIs (default) or IgnoreUnlessSpelledInSource.
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set traversal IgnoreUnlessSpelledInSource
```

## set user traversal

Set the traversal configuration override.

```text
set [user] traversal MODE
```

- MODE: AsIs (default) or IgnoreUnlessSpelledInSource.
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user traversal IgnoreUnlessSpelledInSource
```

## set extra_args

Set the extra_args configuration override.

```text
set [user] extra_args STRING_LIST
```

- STRING_LIST: ordered compiler arguments; default [].
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set extra_args ["-std=c++20"]
```

## set user extra_args

Set the extra_args configuration override.

```text
set [user] extra_args STRING_LIST
```

- STRING_LIST: ordered compiler arguments; default [].
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user extra_args ["-std=c++20"]
```

## set compile_commands

Set the compile_commands configuration override.

```text
set [user] compile_commands PATH
```

- PATH: server-side JSON file or directory; default null enables automatic discovery.
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set compile_commands "build"
```

## set user compile_commands

Set the compile_commands configuration override.

```text
set [user] compile_commands PATH
```

- PATH: server-side JSON file or directory; default null enables automatic discovery.
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user compile_commands "build"
```

## set cache_dir

Set the cache_dir configuration override.

```text
set [user] cache_dir to DIRECTORY
```

- DIRECTORY: quoted directory; default null. Stored setting; not forwarded by current console RPCs.
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set cache_dir to ".ctk-cache"
```

## set user cache_dir

Set the cache_dir configuration override.

```text
set [user] cache_dir to DIRECTORY
```

- DIRECTORY: quoted directory; default null. Stored setting; not forwarded by current console RPCs.
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user cache_dir to ".ctk-cache"
```

## set files

Set the files configuration override.

```text
set [user] files to FILE_LIST
```

- FILE_LIST: list of paths or File values, including glob results; directories are rejected. Default [].
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set files to glob("examples/*.cc")
```

## set user files

Set the files configuration override.

```text
set [user] files to FILE_LIST
```

- FILE_LIST: list of paths or File values, including glob results; directories are rejected. Default [].
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user files to glob("examples/*.cc")
```

## set output

Set the output configuration override.

```text
set [user] output to PATH_OR_STDOUT [mode replace]
```

- Default stdout. File output appends unless mode replace explicitly truncates it. Help and errors remain visible.
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set output to "results.txt"
```

## set user output

Set the output configuration override.

```text
set [user] output to PATH_OR_STDOUT [mode replace]
```

- Default stdout. File output appends unless mode replace explicitly truncates it. Help and errors remain visible.
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user output to "results.txt"
```

## clear user

Remove an override, revealing the lower configuration layers.

```text
clear user KEY
```

- KEY: traversal, extra_args, compile_commands, cache_dir, files, output or vars.
- Removes the home-layer override; project overrides still take precedence. Runtime let bindings remain.

```text
clear user output
clear user traversal
clear user extra_args
```

## set user

Persist a project or user configuration override.

```text
set user traversal MODE
set user extra_args STRING_LIST
set user compile_commands PATH
set user cache_dir to DIRECTORY
set user files to FILE_LIST
set user output to PATH_OR_STDOUT [mode replace|append]
```

- Writes ~/.clang_tools.yaml; project overrides still take precedence.
- Precedence: project > user > /etc/clang_tools/config.yaml > built-in defaults.
- traversal: AsIs (default) or IgnoreUnlessSpelledInSource. extra_args: [] by default.
- cache_dir: quoted directory, default null. files: list of paths/Files, default [].
- output: quoted/interpolated path, $variable or stdout (default). Files append; mode replace truncates.
- cache_dir is a persisted console setting; these console operations do not forward it as an RPC option.

```text
set user extra_args ["-std=c++20"]
set user files to glob("examples/*.cc")
set user output to "results.txt"
set user output to stdout
```
