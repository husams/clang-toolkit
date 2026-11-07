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
The existing CTK parser feeds a local C++ generator by default. The runner
executes the resulting native code against the local AST.

Use `--llvm-ir` to try the direct LLVM IR backend for `.ctk` scripts.

```sh
uv run ctk-jit run query.ctk --file src/example.cpp --compdb build/ --llvm-ir
```

This path generates LLVM IR for the query and its row loop. ORC compiles it
against precompiled helpers that construct the Clang matcher, collect rows,
and print the selected declaration name. This mode compiles the query on every
run. The compilation database still supplies the flags for parsing the target.

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

Bundles contain a relocatable object and a manifest with the toolchain,
preprocessed input, and object fingerprints. A bundle freezes the script
and its included code at precompile time. Precompile again to include edits.
The original script is optional when running the bundle. Load only trusted
bundles, just as with native C++ extensions.

`run query.ctk` and `precompile query.ctk` share the object cache. Warm runs
validate the script, toolchain, used headers, and include directories before
loading the object. Parsing and preprocessing happen on a miss or when Clang
cannot produce a reusable dependency snapshot. Target file edits are picked
up when the runner builds its analysis AST. Pass `run --no-cache` to use Clang
Interpreter directly or `precompile --no-cache` to build a bundle from scratch.

The default cache is `~/.cache/ctk-jit` or `$XDG_CACHE_HOME/ctk-jit`.
Set `CTK_JIT_CACHE_DIR` to use a different private directory.
