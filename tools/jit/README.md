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
The existing CTK parser feeds a local C++ generator. The runner executes the
resulting native code against the local AST.

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

`run query.ctk` and `precompile query.ctk` share the object cache. A source run
checks the toolchain and preprocessed inputs, builds a bundle on a miss, and
loads the cached object on a hit. Target file edits are picked up when the
runner builds its analysis AST. Pass `run --no-cache` to use Clang Interpreter
directly or `precompile --no-cache` to build a bundle from scratch.

The default cache is `~/.cache/ctk-jit` or `$XDG_CACHE_HOME/ctk-jit`.
Set `CTK_JIT_CACHE_DIR` to use a different private directory.
