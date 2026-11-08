# Standalone CTK JIT prototype

Build the local runner with LLVM and Clang 21 or newer, plus the ICU and libyaml
development libraries, Protobuf and OpenSSL. Run the CLI from the repository's
Python environment. The build uses the repository's native Clang libraries
and turns off the server and its gRPC transport.

```sh
cmake -S tools/jit -B build/jit -G Ninja
cmake --build build/jit
uv sync --locked
uv run ctk-jit run query.ctk --file src/example.cpp --compdb build/
```

Use a compilation database with one entry for the target file. Prefer a
compilation database produced by a toolchain compatible with the linked Clang.
On macOS, use the matching Homebrew Clang when generating an entry with
`clang++ -MJ` so the entry uses flags understood by the runner.
The CLI accepts a database directory or the JSON file itself. Use `--runner`
for a native runner built outside `build/jit`.
LLVM scripts can omit `--file` and `--compdb` when they supply their own input
or operate on ordinary values. Use `--arg name=value` to supply a script value
as `arg.name`.

Save this as `query.ctk` to print each explicit function definition in the
target source file.

```text
let tree = parse arg.file
let rows = match functionDecl(isDefinition(), isExpansionInMainFile(), unless(isImplicit())).bind("f") in tree
foreach row in rows do {
    print row.f.decl_name
}
```

The default backend uses the existing CTK parser and lowers its syntax tree
directly to LLVM IR. The native runner evaluates values and control flow,
loads project ASTs with the compilation database, and evaluates matchers
through Clang's dynamic matcher registry. Repeated runs reuse a native object
keyed by the script, front end, and toolchain. Use `--no-cache` for cold IR JIT.

The native language covers values, collections, destructuring, arithmetic,
conditionals, loops, runnables, pipelines, error handlers, and the console's
built-in pipeline filters. Matchers can use saved arguments and bindings,
file lists, and retained nodes with `scope self`, `scope subtree`, or
`scope children`.
The runner can parse inline C++ and retains the ASTs referenced by saved
results. It supports text reads, JSON, YAML and CSV reads and writes, output
routing, and definitions-only imports. The existing
frontend compiles imported definitions and dynamic `ctk()` commands on demand.

CFG, call graph, variable flow, traversal, `peek`, and `step` use the
existing native analysis code and the retained AST. File discovery, file
leases, cursors, and the secondary `script` DSL execute in the runner process.
Typed `.proto` files support detached scalar, list, record, enum, matcher,
and semantic values, including copied AST bindings, match results, repeated
and map fields, and call graph records.

The REPL also embeds the managed query controller, project index controller,
resource scopes, and durable batch registry. `session start`, `session add`,
`session match`, `session pause`, `session resume`, and `session close` stream
query events back to the terminal. The index controller uses the existing
`ctk-index-worker` built alongside the runner for isolated extraction. Foreground
batch bodies compile to LLVM IR. Durable batches use the shared native script
engine and persist their reports for status and promotion after restart.

Indexes and durable batch state default to `~/.local/state/ctk-jit` or
`$XDG_STATE_HOME/ctk-jit`. Set `CTK_JIT_STATE_DIR` to select a different state
directory. One runner at a time owns that directory. Closing the runner stops
its background work. Use `index start` to restart reconciliation of a saved
index and `batch status` to inspect a saved run.

The runner reads the existing layered console settings and saves updates to
the user or project settings file. Graph values support local neighborhoods,
shortest paths and routes, grouped calls, and recursive components.
Pass a retained function binding to `graph.callers()` or `graph.callees()`
to build a new neighborhood from that binding's AST.

`glob` returns typed file and directory snapshots with metadata. A match
can take the resulting file list. Each `match ... do` row runs its block in
a fresh scope with the named bindings and `root`. Assign the command to a
binding to collect its text output.

```text
let sources = glob("src/**/*.cpp")
match functionDecl(isDefinition(), isExpansionInMainFile()).bind("f") in $sources do {
    print $f.value.node.qualified_name;
}
```

The prompt recalls persistent history with Up/Down and Ctrl+R. `session label`
tags subsequent commands, `history save "history.jsonl"` exports the records,
and `history clear` clears them. The log is shared with the existing console
at `$XDG_STATE_HOME/clang_tools/history.jsonl`, or
`~/.local/state/clang_tools/history.jsonl` by default. Use `ctk-jit repl
--ui workspace` for the full-screen editor, transcript, and source viewer.

The workspace shows the native session's bindings (F7), file leases and
retained cursors (F8), and local runtime status (F9). Expand match and
collection previews to page through results or open source locations. Batch
progress and cancellation use the local runner, and help uses the shared
console's Markdown presentation. Panels read native state between commands.
Batch progress updates while a command runs.

Use `--cpp-jit` to select the C++ backend or `--llvm-ir` to select IR explicitly.

```sh
uv run ctk-jit run query.ctk --cpp-jit --no-cache --file src/example.cpp --compdb build/
```

To exercise a custom matcher, pass a trusted `.cpp` file to `run`. Include
`<ctk/jit/runtime.hpp>` and define `void run(ctk::jit::RunContext &ctx)`.
Use `ctx.match(matcher, callback)` to traverse the target and
`ctx.emit_text(text)` to emit a line. The extension executes with the invoking
user's permissions.

## Precompile and run a bundle

Precompile the script without a target file. Load its native object with the
same runner and toolchain. Each invocation reads the target's current AST.

```sh
uv run ctk-jit precompile query.ctk --output query.ctk-bundle
uv run ctk-jit run --bundle query.ctk-bundle --file src/example.cpp --compdb build/
```

Add `--cpp-jit` to precompile a C++ bundle.
`run --bundle` selects the backend from the manifest.

Bundles contain a relocatable object and a manifest with the toolchain,
build input, and object fingerprints. A bundle freezes the script and any
C++ includes at precompile time. CTK `import` reads the library at execution
time, including when a bundle runs. The original script is optional when
running the bundle. Load only trusted bundles and native C++ extensions.

`run query.ctk` and `precompile query.ctk` share an object cache per backend.
For C++ objects, warm runs validate the script, toolchain, used headers, and
include directories. Parsing and preprocessing happen on a miss or when
Clang cannot produce a reusable dependency snapshot. Both backends pick up
target edits when the runner builds its analysis AST. Pass `run --no-cache`
for cold JIT or `precompile --no-cache` to build a bundle from scratch.

The default cache is `~/.cache/ctk-jit` or `$XDG_CACHE_HOME/ctk-jit`.
Set `CTK_JIT_CACHE_DIR` to use a different private directory.

## Stateful LLVM IR session

`repl` opens the target AST once and keeps named bindings in the native
runner. `let tree = parse arg.file` binds that AST. A match saves its rows
for later commands, and `foreach` can print the same rows more than once.
Bindings can hold ordinary CTK values and native runnables. Use `print g`
to display a value binding or `print g.n` to display one of its fields.

```text
$ uv run ctk-jit repl --file src/example.cpp --compdb build/
ctk-jit> let tree = parse arg.file
ctk-jit> let rows = match functionDecl(isDefinition()).bind("f") in tree
ctk-jit> foreach row in rows do { print row.f.decl_name }
add
square
ctk-jit> let selected = match functionDecl(hasName("square")).bind("f") in tree
ctk-jit> foreach row in selected do { print row.f.decl_name }
square
ctk-jit> foreach row in rows do { print row.f.qualified_name }
add
square
ctk-jit> :quit
```

Submit one statement or a semicolon-separated group. The continuation prompt
accepts open blocks across lines. Each session keeps up to 128 compiled commands,
keyed by exact input text, and evicts the oldest entry when full. Repeating a
command reuses its compiled code. Saved runnables retain their code even when
the command that defined them leaves the cache. Matches traverse the retained
AST and refresh their result bindings. Printing reads the current saved rows.

A failed command leaves earlier bindings available. Use `:quit` or EOF to exit,
and start a new session to pick up changes to the target. Piped input uses
the same syntax.
