# Standalone CTK JIT prototype

Build the local runner with LLVM and Clang 21 or newer, including their shared
development libraries. Then run the CLI from the repository's Python environment.

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

Save this as `query.ctk` to print each explicit function definition in the
target source file.

```text
let tree = parse arg.file
let rows = match functionDecl(isDefinition(), isExpansionInMainFile(), unless(isImplicit())).bind("f") in tree
foreach row in rows do {
    print row.f.decl_name
}
```

The prototype supports one parse of `arg.file`, one bound `functionDecl` or
`cxxMethodDecl` match, and one projection of `decl_name` or `qualified_name`
per row. Supported predicates are `isDefinition`, `isExpansionInMainFile`,
`isImplicit`, `isConst` (methods), `hasName` with a literal, and `unless`.
By default, `ctk-jit` lowers `.ctk` queries and their row loops directly to LLVM
IR. The runner uses precompiled helpers to construct the matcher, collect rows,
and print the selected declaration name. Repeated runs reuse a native object
keyed by the script, front end, and toolchain. Use `--no-cache` for cold IR JIT.
The compilation database still supplies the flags for parsing the target.

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
build input, and object fingerprints. A bundle freezes the script
and its included code at precompile time. Precompile again to include edits.
The original script is optional when running the bundle. Load only trusted
bundles, just as with native C++ extensions.

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
Bindings can also hold scalar literals such as `true` and records such as
`{c:1, n:3}`. Use `print g` to display a value binding or `print g.n` to
display one of its fields.

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

Submit one statement at a time. The continuation prompt accepts an open
`foreach` block across lines. Each session keeps up to 128 compiled commands,
keyed by exact input text, and evicts the oldest entry when full. Repeating a
command reuses its compiled code. Matches still traverse the retained AST
and refresh their result bindings. Printing reads the current saved rows.

A failed command leaves earlier bindings available. Use `:quit` or EOF to exit,
and start a new session to pick up changes to the target. Piped input uses
the same syntax.
