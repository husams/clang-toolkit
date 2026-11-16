# Compilation databases

`parse`, file matching, traversal, CFG, call graphs, query sessions and native
scripts resolve each source file's command on the server before acquiring an
AST. Clients and the server must use paths visible to the server. The
standalone `ctk-jit` runner uses the same resolver for every command that
parses project C++ (see [ctk-jit](#ctk-jit)).

With no selection, the server searches the request working directory and its
parents, then the source directory and its parents. At each directory it tries
`compile_commands.json`, `build/compile_commands.json`,
`build/dev/compile_commands.json`, `build/release/compile_commands.json` and
finally `compile_flags.txt`, which applies its flags to every file. The working
directory's database therefore wins over one next to the source. A database
found this way supplies the first command for an exact normalized source path. For headers and other files without
an entry, it first uses the first TU entry in the same source directory, in
database order. This compares the files' normalized parent directories, not
their compiler working directories, and does not include subdirectories. The
donor's options are transferred to the requested file; the donor is not parsed.
If no entry shares that directory, it uses Clang's command inference: choose a TU by
filename, language and directory similarity, then transfer its options to the
requested file. Exact header entries take precedence. Standalone files without
a usable database command retain explicit-flags/default C++ parsing behavior.

Select a JSON file, a `compile_flags.txt`, or a directory holding either
explicitly when the build directory is elsewhere:

```sh
ctk --compile-commands /workspace/project/build/compile_commands.json
```

Inside the console, selection is persisted in `.clang_tools.yaml`:

```text
set compile_commands "build"
let tree = parse "src/example.cpp"
clear compile_commands
```

`clear compile_commands` restores the inherited selection, or automatic discovery
when no layer supplies one. YAML may also set `compile_commands: build`.

Python clients accept a default selection for all operations, and `parse` also
accepts a per-call selection:

```python
from clang_toolkit import Client

with Client(compilation_database="/workspace/project/build") as client:
    with client.parse("src/example.cpp", working_directory="/workspace/project") as tree:
        with client.match_in('functionDecl().bind("f")', tree) as functions:
            print(len(functions))
```

TypeScript uses `compilationDatabase` in client or file-operation options.
The protobuf file/profile messages expose `compilation_database` for other
clients. A supplied database that is missing, malformed, or lacks the requested
source and cannot infer a command produces an error; it is never silently
replaced with default flags.

Both JSON `arguments` arrays and shell-tokenized `command` strings are loaded
with Clang's native JSON compilation database parser. The server never executes
commands (ctk-jit runs a GCC driver only as described [below](#ctk-jit)).
The command's `directory` controls relative include paths and response files.
The server strips compiler/input/output/dependency-generation arguments and
uses its own compatible Clang toolchain. The target and driver mode that the
compiler's name implies (for example `aarch64-linux-gnu-g++` or `clang-cl`)
are kept as `--target=`/`--driver-mode=` options, so the server parses with the
project's target. Request `compile_arguments` and console `extra_args` append
overrides after database flags. The existing server Clang resource-directory
default still applies. Multiple commands for a file use the first database
entry; configuration selection is not currently exposed.

Header inference preserves the TU's command directory, include paths, macros,
target and compatible language standard, while replacing its source/output
operands with the requested header. Ambiguous `.h` files inherit the donor TU's
language. The header remains the AST's main file, so `isExpansionInMainFile()`
selects declarations in that header. Inference is a filename heuristic; it does
not find every TU that includes the header, and context-dependent headers can
still require parsing their including TU.

The server runs one compiler job for the requested source. Database source
operands, including those following `--` or inside response files, are removed
before that source is supplied once. Include-file option values are retained;
request overrides remain compiler options before the database's input separator.

The server imports the database once into an indexed SQLite cache at
`$CTK_STORAGE_ROOT/compile_commands.sqlite3`, or beside the default snapshot
storage under `$XDG_CACHE_HOME/clang-toolkit/storage` or
`~/.cache/clang-toolkit/storage`. Lookups use the database path and normalized
source path. File size and modification time determine when to atomically
refresh the imported commands and Clang's inference index; a refresh failure
rejects the request instead of returning old flags.

The first donor for each normalized source directory is saved in a separate
table during the same atomic import. Missing-file lookups use its primary key,
without scanning or sorting descendant directories. Older caches reimport once
to populate these directory donors.

Exact commands expand response files for each parse on the private captured
filesystem. Inferred
commands expand them on each lookup before Clang transfers the command, using
a filesystem with private working-directory state. Effective commands
participate in AST cache identity, so
changed flags acquire a new AST while previously retained trees stay immutable.

## ctk-jit

`ctk-jit run` and `ctk-jit repl` resolve every project parse through the
server's resolver above: `parse "file"`, `match ... in "file"`, CFG, call graph
and traversal on paths, `file open`, sessions, `run X.cpp` targets and
`parse cpp`. Precedence, highest first:

1. `set compile_commands` in the current session;
2. `--compdb PATH` (alias `--compile-commands PATH`);
3. `compile_commands` in `/etc/clang_tools/config.yaml`, `~/.clang_tools.yaml`
   or `./.clang_tools.yaml`;
4. discovery as described above;
5. CTK's defaults: `-std=c++20` (`-std=c17` for `.c`) and no project flags.

Missing entries are inferred for explicit and discovered databases alike, and
several entries for one file use the first. An explicit path that does not exist
is an error. Relative explicit paths are relative to the current directory.

ctk-jit builds the AST with its embedded Clang, using the database's compiler as
the driver name so Clang infers the project's target, driver mode and
toolchain location. When that compiler is GCC (`gcc`, `g++`, versioned or
target-prefixed names, or `cc`/`c++` aliases of them) and the database was
selected explicitly (by `--compdb`, a settings file, `set compile_commands` or a
`parse cpp` option), ctk-jit first runs that GCC with `-fsyntax-only` so GCC's
own warning policy decides whether the target is accepted. A process runs the
check once per command and source size/modification time. ctk-jit never runs a
compiler from a discovered database: for discovered GCC commands Clang ignores
GCC-only warning options and keeps the project's `-Werror` for groups it knows.

`parse cpp` without `using` borrows the `--file` target's command when there is
one, else the first entry of the selected or discovered database, else CTK's
defaults. With `using`, it parses with the named file's command.

`index start` reads a directory containing `compile_commands.json`, or that
file itself. With no selection it uses the project root's
`compile_commands.json`, `build/`, `build/dev/` or `build/release/`.

Scripts themselves (`.ctk` and `.cpp` script compilation and `ctk-jit
precompile`) compile against the CTK runtime with ctk-jit's own flags. They
never use a compilation database.

## Borrow settings for temporary snippets

`parse cpp` creates a temporary `.cpp` file. `using "src/example.cpp"` borrows
the specified source file's compilation settings. With no donor, it selects the
first command in the current compilation database in database order; it does not
infer a donor from the generated temporary filename. Both forms replace the
command's source/output operands with the temporary source.

```text
let tree = parse cpp`int value = 7;` using "src/example.cpp"
let first = parse cpp`int value = 7;`
```

The options object supports `file`, `compile_arguments`, `working_directory`,
`compilation_database`, optional `includes` and `translation_unit`. Additional
arguments append after borrowed flags. Borrowing transfers compile settings,
not source declarations: include the required headers through `includes`, or
provide complete source with `translation_unit: true`. Python exposes the same
operation as `client.parse_cpp(code, file="src/example.cpp", ...)`.
See [C++ snippets](cpp-snippets.md).

When parsing fails, the SDK and console include Clang's compiler diagnostics
after the AST error, with source file, line, and column when available. This
reports missing headers, invalid compiler options, and source/preprocessor
errors directly. Each parse reports at most eight errors and bounds the
diagnostic text to about 8 KiB.
