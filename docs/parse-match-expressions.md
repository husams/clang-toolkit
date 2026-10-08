# Parse and match expressions

Run a local server and interactive console with `scripts/manual_console.sh`.
From the repository directory, these commands use the supplied two-function
fixture (each command is one console input):

```text
let tree = parse "examples/parse_match.cc";
let functions = match functionDecl(isDefinition()).bind("f") in $tree;
let calls = match callExpr().bind("call") in $functions.f;
let first = match callExpr().bind("call") in $functions[0].f;
let literals = match integerLiteral().bind("n") in "examples/parse_match.cc";
print $calls
```

`parse` acquires and pins an immutable tree without running a matcher. A file
target acquires its tree and matches it; a parsed-tree target matches the whole
tree. `functions`, `calls`, `first` and `literals` are independent retained
values. Continuing from `functions` again preserves its earlier bindings.
The compiler settings come from the console configuration or explicit SDK
options. Paths, include paths and compilation flags refer to the server's
filesystem; the server must be able to read the source.

`$functions.f` selects `f` from every result row containing it.
`$functions[0].f` selects `f` from zero-based row zero. The fixture above returns
two functions, two calls, one call in the first row and the literals 7 and 9.
There are no UUIDs or revision numbers to manage in this flow.

The name in `.bind("f")` is the binding label: `$functions[0].f.name` returns
`"f"`. A row's `$functions[0].name` instead asks for a binding labeled
`"name"`. To reach fields on the bound protobuf node, continue through
`.value.node`; for example:

```text
$functions[0].f.value.node.qualified_name
$functions[0].f.value.node.name.identifier
```

Completion follows each live value through nested fields and zero-based row
indices. Optional protobuf fields that are absent raise a field-unavailable error;
check them with `.hasField("field")` before reading them. `foreach` evaluates
its body for each input value and returns a new list of those results.

`node` contains one active concrete payload. For function declarations, including
C++ methods, constructors, destructors, conversions and deduction guides, its
concrete and inherited declaration fields are also available directly. Tab after
`$m[0].f.value.node.` offers fields such as `name`, `qualified_name`, `return_type`,
the active payload, and the `hasField(` method. Child fields such as `parameters`
and `body` are intentionally unrequested in match results.
Exact schema paths remain available. For example:

```text
$m[0].f.value.node.cxx_method_decl.method.function.declarator.value.named.qualified_name
$m[0].f.value.node.qualified_name
$m[0].f.value.node.return_type.description.spelling
```

The first two paths read the same qualified name. The third reads the return
type's spelling. `name` is a typed `DeclarationName`: an ordinary function
has `name.identifier`; operators, constructors and other special names retain
their own typed variants. `return_type` is a `QualType`; use
`return_type.description.spelling` for its type text and `return_type.qualifiers`
for qualifiers. Its recursive `type` field is unrequested.
`spelling` belongs to type information and is not a universal
field of `node`. Direct fields come only from the matched declaration and its
explicit base metadata chain, never its parameters or parent record.

Each binding contains only its matched node's immediate fields. Function bodies,
parameter declarations, initializers and expression operands require a follow-up
match rather than serialized subtree expansion. Omitted children are marked
`UNREQUESTED`; `is_complete` describes the immediate projection. For example:

```text
let parameters = match parmVarDecl().bind("p") in $functions.f
let returns = match returnStmt().bind("r") in $functions[0].f
$functions[0].f.value.node.return_type.description.spelling
```

`hasField("field")` checks whether a field supporting protobuf presence is
present; it does not retrieve the value. Tab after `.hasField(` or an unfinished
quoted argument suggests valid field names with quotes. An empty argument reports
the missing field name and its position. Repeated fields use `.length` or
`.isEmpty` rather than `hasField`.

Enter a scoped expression as one console input, using multiline entry when
available:

```text
let analysis = in parse "examples/parse_match.cc" {
    let functions = match functionDecl(isDefinition()).bind("f");
    let calls = match callExpr().bind("call") in $functions.f;
    yield calls;
};
let numbers = match integerLiteral().bind("n") in $analysis.call;
print $numbers
```

An omitted `in` target inside the block uses its parsed tree. A nested block
uses its own tree and restores the surrounding default on exit. Local variables
may shadow outer names; local names disappear on exit. The terminal `yield`
returns one value whose native tree and bindings survive local cleanup. A block
requires a parsed tree and one terminal yield. Missing yields, wrong target
types, unknown variables, invalid matchers and out-of-range rows fail without
assigning the block result. The console keeps any earlier assignment intact.

Continuation visits each selected row independently, inclusively matching the
root and its descendants. Overlapping roots or duplicate input rows can produce
the same native match more than once; results retain that multiplicity. A
continuation's `source_match_index` identifies the immediate input row.
Relationship predicates can inspect the whole AST, even while candidate roots
are scoped. Subtree continuation requires Decl/Stmt bindings and matchers;
explicit root-only selection additionally supports native Type/QualType roots.

An empty match collection continues to an empty collection. For a nonempty
collection, a binding missing from every row is an error; rows without that
binding are skipped. An explicitly missing row is always an error. A successful
zero-row match remains a valid value. Saved/exported semantic rows are detached
and cannot reconstruct native bindings.

Each new value has an internal cursor, optimistic revision guard and shared
immutable tree ownership. The server retains process-local cursors under count,
memory, result-size and idle limits. Expiry, explicit close or server restart
makes a handle unavailable; a stale revision errors rather than selecting newer
rows. Existing values keep their original tree if the file later changes.
A new file parse/match validates dependencies and acquires the current generation.
Query failures and limits preserve prior variables and publish no partial value.
A lost network response can leave an unobserved cursor, which expires normally.

The existing `match`, `query`, `cursor open/continue/restart/close`, traversal,
CFG and call-graph commands remain available. Cursor commands retain their
explicit mutable latest-result behavior. The expression API requests an
independent result instead.

## Python SDK

The synchronous `Client` and asynchronous `AsyncClient` automatically discover
the shared YAML network configuration. `Client()` needs no address;
`Client(config_path="network.yaml")` adds an explicit highest-priority layer.
The TypeScript equivalent is `await Client.connect()` or
`await Client.connect({ configPath: "network.yaml" })`. Existing explicit
endpoint arguments remain supported. Server and interactive console use the
same configuration rules and accept `--config` / `-c`.

Merge order is defaults, `/etc/clang-toolkit/clang-toolkit.yaml`, home
`clang-toolkit.yaml`, home `.clang-toolkit.yaml`, current-directory
`clang-toolkit.yaml`, current-directory `.clang-toolkit.yaml`, then explicit
file. Mappings merge recursively; supplied scalar values replace earlier
ones. Omitted keys inherit and permitted `null` values clear optional tuning
or select the automatic Unix socket. A relative socket is resolved from the
file that supplied its winning value. The automatic endpoint uses the
platform temporary directory and `ctk.sock`. TCP requires a supplied loopback
host and port; there is no TCP fallback address. Every supplied file is
validated before merging, including overridden lower layers and inactive
transport branches. Missing discovered files are harmless; invalid or missing
explicit files fail. Effective settings and dotted-key winning provenance
are available through each SDK's configuration object; built-in origins are
marked `<defaults>`. The approved
[shared network configuration design](https://chatgpt.com/space/page_561b779557cc8191a5aace9bf6273191)
defines the common schema.

`parse`, `match(query, file=...)`, `match_in`, and binding-selection `match`
return retained values. A binding selection carries its owner's identity and revision.
Rows expose typed semantic protobuf values with copy-on-read bindings.

Retained matching uses `StreamMatch`: rows arrive during matching and collectors
spool large results to temporary storage. The result becomes reusable only after
successful stream completion. Normal iteration and indexing read rows on demand;
the `.rows` property deliberately creates a complete snapshot. Use `on_row` on
Python `match_in` to process each provisional protobuf row as it arrives; async
callbacks are awaited. Callback failure cancels collection and publishes no value.

```python
with Client() as client:
    with client.match_in('functionDecl().bind("f")', "example.cc",
                         on_row=lambda row: print(row.bindings["f"])) as functions:
        print(len(functions))
```

```python
from clang_toolkit import Client

with Client() as client:
    with client.match('functionDecl(isDefinition()).bind("f")',
                      file="examples/parse_match.cc") as functions:
        with functions.binding("f").match('callExpr().bind("call")') as calls:
            for row in calls:
                print(row.bindings["call"])
```

Python references, row selections and aliases share cursor ownership. Explicit
`close()` invalidates aliases of that same value; closing a parent leaves its
independent children usable. Client/context cleanup closes its owned cursors.
Parsed trees and result values support synchronous and asynchronous contexts;
asynchronous construction is awaited before entering `async with`:

```python
from clang_toolkit import AsyncClient

async with AsyncClient() as client:
    async with await client.parse("examples/parse_match.cc") as tree:
        async with await tree.match('functionDecl(isDefinition()).bind("f")') as functions:
            async with await functions.binding("f").match('callExpr().bind("call")') as calls:
                for row in calls:
                    print(row.bindings["call"])
```

Context exit cleans up on exceptions. Async result context exit awaits that
result's cleanup. Subsequent requests retry failed cleanup in the background;
client shutdown awaits remaining cleanup and reports failures. Explicit close is
idempotent. Aliases share ownership, while independently created children
retain their native snapshot after their parent's context exits.
See the runnable [Python example](../examples/parse_match.py).

`client.execute(source)` evaluates one Lark console expression or assignment
and returns its evaluated value, which can be a tree, result, scalar or collection.
Its return annotation is dynamic; parse/match methods retain their concrete
sync/async types. Named variables persist across execute calls until
client cleanup; a yielded `MatchValue` remains a live target for `match_in`.
`AsyncClient` provides the same operations with `await`. The expression helper
uses the existing client and retains its lexical runtime rather than opening a
second client.

## Native block execution and TypeScript

`run_script` in Python and `runScript` in TypeScript execute the ANTLR server
language. Use the same parse/match/block syntax above and `emit analysis;` to
return a typed `ScriptResponse`. Yielded native values remain selectable after
block exit within the script. Emissions returned to the client contain detached
semantic values; native script locals are released when the request ends.
`run_script`/`runScript` propagate the SDK's working directory and compilation
flags to explicit parse/file expressions, including when no default `path`/`file`
is supplied. The console's `script` command uses its current directory and
configured `extra_args` in the same way. Existing default-file scripts remain
supported. Python ships generated protobuf type stubs for nested semantic fields.

Native scripts reject duplicate declarations in one lexical scope and allow
inner shadowing. This extends the existing `match("...")`, `continue`, `row`,
`foreach` and `emit` language without arbitrary code execution.

The packaged TypeScript SDK provides retained parse/match values, typed binding
and row selection, automatic client cleanup and scoped tree callbacks. Its
generated protobuf/gRPC bindings cover the actual server contract. It targets
Node.js 22 or later, with Unix domain sockets and plaintext TCP; browsers and
gRPC-Web require an additional gateway and are not supported by this package.
The current server uses insecure gRPC transports. See the
[TypeScript SDK](../typescript/README.md) for installation, connection options,
native block execution and the runnable example.

## Wire contract

`MatchService.Parse(ParseRequest)` returns a caller-owned zero-row tree cursor.
`MatchRequest.preserve_source=true` publishes a fresh result cursor from a
retained whole-tree or binding target while keeping the source identity,
revision, expiry and native bindings unchanged. `CloseSession` also closes
tree cursors. Existing Match requests default to replacement behavior.
The high-level SDKs supply opaque identifiers, guards and cleanup internally.
