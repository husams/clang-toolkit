# Native AST call graphs

`ctk.analysis.v1.AnalysisService.CallGraph` runs Clang's AST call-graph builder
on one validated translation unit. It returns owned finite declaration symbols,
a virtual root, declaration-order node indices and native call records. Every
call record remains a separate edge; repeated calls to the same callee retain
their multiplicity and native per-caller ordering. Call expressions are typed
semantic values. Root edges have no call expression and are explicitly marked.
Anonymous block declarations use their existing typed declaration payload.

```python
from clang_toolkit import Client

result = Client(address="unix:///tmp/ctk.sock").callgraph(
    "example.cc", working_directory="/absolute/project",
    compile_arguments=["-std=c++23"],
    visit_template_instantiations=True,
)
for edge in result.edges:
    print(result.nodes[edge.caller_node].function.qualified_name,
          result.nodes[edge.callee_node].function.qualified_name)
```

`await AsyncClient.callgraph(path, ...)` provides the equivalent asynchronous
API. The formal CLI emits protobuf JSON and uses current compiler arguments:

```text
callgraph "example.cc" nodes 10000 edges 100000 implicit true instantiations true
```

The request's two optional visitor flags preserve absence separately from
explicit false; native defaults visit implicit code and template instantiations.
Disabling template instantiations can remove body edges while leaving a node
introduced as a callee. Nodes with declarations but no definitions remain in
the graph. Empty translation units still return the native virtual root.

Node indices refer only to the current response's graph structure and cannot
be used to look up AST objects. Ordering uses a complete native declaration
visitor, including implicit declarations and instantiated templates, rather
than pointer-map order. Responses carry semantic completeness and availability;
existing bounded child expansion rules apply to typed calls/declarations.

This is the native AST call graph. A virtual call points to its statically
selected declaration; function-pointer calls that the native builder cannot
resolve do not produce invented targets. The operation performs no alias
analysis, devirtualization or cross-translation-unit resolution. Root edges
retain Clang's native fan-out; they do not assert which functions an external
caller will execute. Implicit destructor control flow belongs to CFG operations.

The default limits are 10,000 nodes and 100,000 edges; hard maxima are 100,000
and 1,000,000. Both counts include virtual-root structure. Byte limits include
the complete wire envelope. Limit failures and cancellation publish no partial
graph. Native building checks cancellation between declarations; a native
function-body build is synchronous. Collection and serialization also check
cancellation. Call graphs share the native execution lane, snapshot engine and
bounded operation executor with matching, traversal and CFG.

The C++ `Project` facade now executes matching, CFG and call-graph queries.
Compilation-database inputs use the first native command for each selected
file, stripping inputs, outputs and dependency-file generation flags. With no
explicit files, database files are selected in sorted order. Without a database,
explicit files use native default compiler arguments. Invalid projects and
failed matcher construction raise errors. Matching returns JSON callback rows;
CFG returns aggregate `CfgResponse` JSON; call graphs return a JSON array of
per-translation-unit responses. No cross-TU graph merging is claimed. Facade
result bounds apply across the selected project; no object/dependency files are
created by the database commands.
