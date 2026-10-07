# Server scripting

`AnalysisService.RunScript` evaluates a bounded ANTLR 4.13.2 DSL on the server.
A request may supply one file target and compiler flags. Every native operation
pins the same translation-unit snapshot, including when the source changes while
the script runs. Pure scripts need no file and work with Clang disabled.

```text
let functions = match("functionDecl(isDefinition()).bind(\"f\")");
emit count(functions);
foreach function in functions {
  emit continue(function, "f", "integerLiteral().bind(\"n\")");
}
emit cfg("f", always_add_statements=true, add_implicit_dtors=true);
emit callgraph(visit_template_instantiations=false);
emit traverse(max_depth=2);
```

`let` binds an immutable value in the current lexical scope. Duplicate local
bindings and undefined references fail; loop locals expire after each iteration.
`emit` appends an owned typed value (and its variable name when applicable).
`foreach` visits independent matched rows in order, preserving multiplicity.
String literals use JSON escapes. Numbers retain int64 or finite double values;
bools retain their protobuf kind. Comments start with `//`.

| Function | Arguments | Named options |
| --- | --- | --- |
| `match` | matcher string | `traversal="as_is"` or `"spelled"` |
| `continue` | matched rows, binding name, matcher string | traversal; `scope="subtree"` or `"root"` |
| `restart` | matched rows, matcher string | traversal |
| `row` | matched rows, zero-based integer index | none |
| `count` | matched rows, traversal, CFG, or call graph | none |
| `traverse` | none | fields from TraverseRequest except file |
| `cfg` | exact qualified function name | CfgOptions booleans and max_functions/max_blocks/max_elements |
| `callgraph` | none | CallGraphRequest fields except file |

Continuations branch from captured native bindings without consuming a cursor
revision. `row` and loop variables select one original row. Restart covers the
whole pinned AST. Empty matches remain an explicit empty collection. Native
analysis limitations and bounds are the same as their standalone operations;
call graphs remain per translation unit, with static dispatch and finite symbols.
Count measures rows, traversal nodes, CFG graphs, or call graph nodes including
its virtual root. Native bindings and snapshot ownership are released at request
completion; responses contain semantic values without session handles.

All syntax is parsed before evaluation. Defaults: 100 execution steps (statements,
function calls, loop iterations), 1 MiB source, 100,000 tokens, nesting 64, 16 MiB
retained values/bindings, and at most 64 MiB response by default (following a
positive `server.grpc.max_send_message_bytes`). `max_steps` accepts 1..10,000. Snapshot memory uses the server's
configured memory bound. Errors, cancellation, and any limit return no partial
emissions. A script occupies one shared worker; native calls run directly within
that worker, avoiding nested worker-queue waits. The DSL provides no shell,
network, filesystem-writing, or dynamic code execution functions.

Python:

```python
result = client.run_script(source, path="file.cc", max_steps=100)
# AsyncClient exposes the same operation with await.
```

CLI (formal Lark outer grammar):

```text
script "emit 7;"
script "emit cfg(\"f\");" in "file.cc"
```

The C++ `ctk::script::Engine::eval` now returns JSON of evaluated pure emissions;
it no longer echoes source. `Engine::run` supports an explicit operation
Environment. Building with `CTK_BUILD_SCRIPT=OFF` preserves the interface and
returns FAILED_PRECONDITION. Generated C++ parser sources are checked in;
ordinary builds need the pinned C++ runtime, not Java. Regeneration uses the
matching 4.13.2 tool and `scripts/generate_script_parser.sh`.
