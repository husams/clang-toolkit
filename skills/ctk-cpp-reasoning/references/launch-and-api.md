# Launch and public API

## Run the SDK

The skill includes a setup helper for operators and a Python launcher for reasoning
agents. With `uv` installed, run setup with the desired destination;
the default destination is `$HOME/.codex/skills/ctk-cpp-reasoning`:

```sh
bash /path/to/skill/scripts/setup.sh "$HOME/.codex/skills/ctk-cpp-reasoning"
```

For a custom destination, replace the destination argument with its chosen path.

Setup copies the packaged skill, prepares Python 3.14 and runs `uv sync --frozen`
for the bundled SDK wheel and locked dependencies. Omitting the destination uses
the default. Setup can be rerun to update the packaged files and synchronize the
SDK environment; unrelated skill files are preserved. A
reasoning agent uses the installed environment and does not run setup unless asked.

The Python helper computes its own skill directory and selects that directory's
preinstalled SDK project by default. A missing or empty `CTK_SDK_PROJECT` keeps the
default; a nonempty value overrides it with another uv project that already has
the SDK installed. Keep the selected project path opaque. Use the absolute path of
the loaded skill directory supplied by the skill catalog; do not search for it.
For the standard installation, that path is `$HOME/.codex/skills/ctk-cpp-reasoning`.
Start every standalone SDK probe with:

```sh
bash "/absolute/path/to/loaded-skill-directory/scripts/python.sh" - <<'PY'
from clang_toolkit import Client

with Client() as client:
    ...
PY
```

For the standard installation, the launcher command is:

```sh
bash "$HOME/.codex/skills/ctk-cpp-reasoning/scripts/python.sh" - <<'PY'
from clang_toolkit import Client
...
PY
```

For a custom destination, use that destination's `scripts/python.sh`. The selected
project is expected to contain the installed SDK; do not run setup, install
packages, bootstrap the project, or search for SDK source at runtime unless the
user asks for setup. Do not echo `CTK_SDK_PROJECT`, inspect its value, open
configuration files, or locate/read installed SDK files. `Client()` is the default.
When the user gives a compilation database location, pass it as
`compilation_database=...`; otherwise rely on configured/default server selection
and state that selection if it affects the conclusion. Paths and compiler arguments
are interpreted by the server, which must see the source tree.

## Core calls

The synchronous public entry points used by this skill are:

```text
Client(address=None, config_path=None, config=None, compilation_database=None)
client.parse(path)
client.match_in(matcher, target)
client.traverse(path)
client.cfg("ns::function", path=source)
client.callgraph(path)
```

`parse` also accepts `working_directory`, `compile_arguments`, and `compilation_database`. `match_in` accepts `working_directory`, `compile_arguments`, `traversal_mode`, and `on_row`; set its compilation database on the client. `target` can be a source path, a `ParsedTree`, a retained `MatchValue`, or a binding selection. `parse` returns a retained tree; `match_in` returns a retained `MatchValue`. `ParsedTree`, `MatchValue`, and client objects are context managers. Their asynchronous counterparts are `AsyncClient`, awaited calls, and `async with` cleanup.

### Graph options

All three graph methods accept `working_directory`, `compile_arguments`,
`projection="shallow"` or `"recursive"`, `main_file_only=False`,
`payload_depth=24`, and `payload_nodes=10000`. These are keyword arguments.

| Method | Structural controls |
|---|---|
| `traverse(path, ...)` | `max_depth` (0..256), `max_nodes` (1..100000), `visit_implicit_code=False`, `visit_template_instantiations=False` |
| `cfg(function, path=path, ...)` | `options=CfgOptions(...)`, `max_functions` (1..1000), `max_blocks` (1..100000), `max_elements` (1..1000000) |
| `callgraph(path, ...)` | `max_nodes` (1..100000), `max_edges` (1..1000000), optional `visit_implicit_code`, `visit_template_instantiations` |

Omit a structural bound to use server defaults. Async CFG uses the different
argument order `await client.cfg(path, function, ...)`; other async graph calls
use the same argument order as their synchronous equivalents. Response fields
and graph recipes appear in [recipes.md](recipes.md).

For all three graph methods, `payload_depth` accepts 1..64 and `payload_nodes`
accepts 1..100000; values outside those inclusive ranges raise `ValueError` in
the SDK.

### Asynchronous retained values

```python
import asyncio
from clang_toolkit import AsyncClient
from clang_toolkit.matchers import functionDecl, isDefinition, callExpr

async def analyze(source):
    async with AsyncClient() as client:
        async with await client.parse(source) as tree:
            async with await tree.match(functionDecl(isDefinition()).bind("fn")) as functions:
                for row in functions:
                    async with await row.binding("fn").match(callExpr().bind("call")) as calls:
                        print(row.binding("fn").decl_name, len(calls))

asyncio.run(analyze(source))
```

Create and use an `AsyncClient` in one event loop. For normal scripts, choose
the synchronous client when concurrent work is unnecessary.

For a known project compilation database, supply its path or directory as the client's `compilation_database`, or pass it to `parse`. The server uses that database to select compiler flags for each file. Without a supplied database, server discovery checks the working directory and parents and then the source directory and parents for `compile_commands.json` or `build/compile_commands.json`. Missing/malformed explicit databases and databases without the requested source fail; they are not silently replaced by default flags. `compile_arguments` append overrides. Do not claim a TU was parsed with project flags unless that is the selected configuration.

## Results and cleanup

Iterate or index a result without materializing all rows:

```python
from clang_toolkit import Client
from clang_toolkit.matchers import functionDecl, isDefinition

with Client() as client:
    with client.match_in(functionDecl(isDefinition()).bind("f"), source) as functions:
        print(len(functions))
        for row in functions:
            selection = row.binding("f")
            proto = row.bindings["f"]  # copied MatchBinding protobuf
            print(row.source_file, selection.decl_name, proto.symbol_identity)
```

`row.bindings` is a mapping of labels to copied `MatchBinding` protobuf values. Read raw metadata such as `symbol_identity`, `location`, or `call_site` from that protobuf. Its `value` oneof includes `node`, `qualified_type`, `unsupported`, and `base_specifier`; check `proto.WhichOneof("value")` before reading one. Only the `node` branch contains an `AstNode`, whose separate oneof is `proto.node.WhichOneof("payload")`. For the `qualified_type` branch, read immediate facts from `proto.qualified_type.description` and its `qualifiers`. Native Type values in the `node` branch use their selected AST payload; inspect its returned fields with `ListFields()`. Inspect `proto.unsupported` for unsupported bindings and `proto.base_specifier` for its typed auxiliary value. `row.binding("f")` returns a `BindingSelection` with convenience properties such as `.decl_name` and `.decl_type`; on a specific row its `.value` is a detached `MatchBinding` protobuf copy, so apply the same oneof check before accessing `.value.node`. The selection's `.match(...)` continues natively against the retained tree. A copied protobuf is safe to inspect after its parent closes, but continued matching requires a live owner. Close retained values promptly or use `with` blocks. A child result owns independent state and remains usable after its parent result closes.

`MatchValue.rows` materializes all rows as a tuple. Prefer iteration/indexing for large results.

### Streaming callback payload

`on_row` receives a detached `ctk.match.v1.MatchResult` protobuf. Its
`.bindings` is a map of labels to `MatchBinding` protobufs, and
`.source_match_index` carries native continuation provenance when present.
Check each binding's `WhichOneof("value")` before reading its semantic value:
`node` holds an `AstNode` with its own `payload` oneof, `qualified_type` holds
immediate type facts in `.qualified_type.description`, `unsupported` holds the
unsupported-value details, and `base_specifier` holds its typed auxiliary value.
Read it with protobuf APIs or
`google.protobuf.json_format.MessageToDict`.
The semantic helpers `.binding(...)`, `.to_dict()` and `.source_file` belong
to rows obtained by iterating the returned `MatchValue`. Preserve the supplied
source path alongside callback data when needed. Callbacks run before the complete
retained result is returned; start continuation queries from that returned result.

```python
from clang_toolkit import Client
from clang_toolkit.matchers import functionDecl, isDefinition, isExpansionInMainFile

streamed_symbols = []
def collect(proto):
    streamed_symbols.append({
        label: binding.symbol_identity
        for label, binding in proto.bindings.items()
    })

with Client() as client:
    with client.match_in(
        functionDecl(isDefinition(), isExpansionInMainFile()).bind("fn"),
        source, on_row=collect,
    ) as functions:
        assert len(streamed_symbols) == len(functions)
        print("streamed:", len(streamed_symbols))
```

`Client.match(matcher, file=...)` returns a retained value. `Client.match(matcher, files=...)` is the legacy query path and returns reduced JSON strings; use `match_in` for typed semantic results. The Python SDK also exposes `Client.execute`, but it runs the console expression language; this skill uses direct Python APIs and typed matchers instead.
