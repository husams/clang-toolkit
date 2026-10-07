# Compilation databases

`parse`, file matching, traversal, CFG, call graphs, query sessions and native
scripts resolve each source file's command on the server before acquiring an
AST. Clients and the server must use paths visible to the server.

With no selection, the server searches the request working directory and its
parents for `compile_commands.json` or `build/compile_commands.json`, then the
source directory and its parents. A database found this way supplies the first
command for an exact normalized source path. Standalone files without a matching
entry retain the existing explicit-flags/default C++ parsing behavior.

Select a JSON file or its directory explicitly when the build directory is
elsewhere:

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
source produces an error; it is never silently replaced with default flags.

Both JSON `arguments` arrays and shell-tokenized `command` strings are loaded
with Clang's native JSON compilation database parser. Commands are not executed.
The command's `directory` controls relative include paths and response files.
The server strips compiler/input/output/dependency-generation arguments and
uses its own compatible Clang toolchain. Request `compile_arguments` and console
`extra_args` append overrides after database flags. The existing server Clang
resource-directory default still applies. Multiple commands for a file use the
first database entry; configuration selection and header-command inference are
not currently exposed.

The server imports the database once into an indexed SQLite cache at
`$CTK_STORAGE_ROOT/compile_commands.sqlite3`, or beside the default snapshot
storage under `$XDG_CACHE_HOME/clang-toolkit/storage` or
`~/.cache/clang-toolkit/storage`. Lookups use the database path and normalized
source path. File size and modification time determine when to atomically
refresh the imported commands; a refresh failure rejects the request instead of
returning old flags. Response files are expanded for each parse on the private
captured filesystem. Effective commands participate in AST cache identity, so
changed flags acquire a new AST while previously retained trees stay immutable.
