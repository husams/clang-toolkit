# Native control-flow graphs

`ctk.analysis.v1.AnalysisService.Cfg` builds Clang's native CFG for every concrete
function definition matching an exact qualified name in one validated translation
unit. Overloads are returned in native AST visitor order; dependent template
patterns require an instantiated definition. Missing definitions return NOT_FOUND;
a selection containing only dependent patterns returns FAILED_PRECONDITION.

```python
from clang_toolkit import Client, CfgOptions

result = Client(address="unix:///tmp/ctk.sock").cfg(
    "ns::function", path="example.cc", working_directory="/absolute/project",
    compile_arguments=["-std=c++23"],
    options=CfgOptions(add_implicit_dtors=True, add_rich_cxx_constructors=True),
)
for graph in result.graphs:
    print(graph.function.qualified_name, graph.entry_block, graph.exit_block)
```

The asynchronous API uses `await client.cfg("example.cc", "ns::function", ...)`.
Errors raise `AnalysisError` with the native operation's gRPC status. The formal
CLI selects a file explicitly and emits protobuf JSON:

```text
cfg ns::function in "example.cc" option add_implicit_dtors true option add_rich_cxx_constructors true blocks 10000
```

Every boolean field in `CfgOptions` is selectable with `option <field> true|false`.
`functions`, `blocks` and `elements` set response limits; duplicate options and
out-of-range values are rejected. Bare `cfg function` retains its previous client
call syntax but a real query requires an explicit file path.

Graphs contain a finite function symbol, entry/exit block indices, blocks in
ascending native block order and the native linearity property. Block indices
and predecessor/successor references describe this response's control-flow
structure. Each native edge slot is retained, including null and pruned slots;
reachable and possibly-unreachable targets are separate optional fields. Native
branch ordering is preserved. Block elements retain execution order, typed
statement values, construction contexts, initializer/destructor/scoping values,
labels, loop targets and terminator conditions. All 15 native CFG element kinds
and 11 construction-context kinds have dedicated serializers. Finite semantic
values carry the existing completeness and availability information; bounded
child expansion can be incomplete without changing graph structure.

Options preserve native defaults, including pruning trivially false edges by
default. Explicit `prune_trivially_false_edges=False` is distinct from absence.
The API exposes all boolean build options and a switch that includes all
statement kinds. `assume_reachable_default_in_switch_statements` requires Clang 22 or newer;
older servers reject it when enabled with FAILED_PRECONDITION. Internal observer
and forced-expression pointer hooks stay internal.

The default limits are 100 functions, 10,000 blocks and 100,000 elements across
all returned graphs; hard maxima are 1,000, 100,000 and 1,000,000 respectively.
A complete wire-size limit, including metadata and envelopes, also applies.
Limit failure, cancellation or unsupported CFG construction returns no partial
graph. Native CFG construction is synchronous: cancellation is checked before
and after each build and throughout collection/serialization.

CFG, traversal and retained matching share the server host's bounded operation
executor and snapshot cache. Their native execution runs under the snapshot's
lane; the graph and AST remain owned through serialization. Responses own their
semantic values. The legacy streaming-query executor remains separate.
