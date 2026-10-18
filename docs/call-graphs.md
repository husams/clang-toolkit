# Static call graphs and retained inputs

Call graphs describe represented static calls in one translation unit. Console
and Python requests use shallow semantic results by default. Recursive AST
expansion is explicit.

## Match directly from returned callgraph nodes

Assigned console graphs retain exact callable references into their pinned AST.
Both `graph.nodes[i]` and `graph.function("project::work")` are valid `match`
targets. Matching uses the callable definition when available, otherwise its
declaration; overloads retain their exact identity. It neither reparses the file
nor searches again by function name or source coordinates.

The following complete example was run in a real compiled console against the
feature client/server build on macOS on 17 October 2026. Run from the repository
root with the updated client and server:

```sh
ctk --script-engine compiled --ui prompt --script examples/callgraph_match_nodes.ctk
```

```ctk
// Run from the repository root with the updated client and server.
let source = "examples/callgraph_strict_filters/main.cc"
let filename = callgraph source exclude-system true node-filter 'functionDecl(unless(isExpansionInFileMatching("(^|/)(vendor|generated)/")))' strict-node-filter true
let tree = parse source
let entries = match functionDecl(hasName("entry"), isDefinition()).bind("f") in tree
let parsed = callgraph in tree exclude-system true node-filter 'functionDecl(unless(isExpansionInFileMatching("(^|/)(vendor|generated)/")))' strict-node-filter true
let matched = callgraph in entries[0].f depth all exclude-system true node-filter 'functionDecl(unless(isExpansionInFileMatching("(^|/)(vendor|generated)/")))' strict-node-filter true
foreach row in [{"label": "FILENAME", "graph": filename}, {"label": "PARSED", "graph": parsed}, {"label": "MATCHED", "graph": matched}] do {
    let graph = row.graph
    let work = graph.function("project::work")
    let same = match functionDecl(isDefinition()).bind("f") in graph.nodes[work.node_index] scope self
    let calls = match callExpr().bind("call") in work
    let roots = graph.call_sites | filter((site) = site.caller_node == graph.root_node)
    print "{row.label}: nodes={graph.nodes.length}, edges={graph.edges.length}, sites={graph.call_sites.length}, root_sites={roots.length}"
    print "{row.label}_MATCH: function={same[0].f.qualified_name}, calls={calls.length}, callee={calls[0].call.call_site.static_callee_name}"
    print "{row.label}_SAME_SNAPSHOT={graph.snapshot_generation == filename.snapshot_generation}"
    print "{row.label}_SHALLOW={graph.call_sites[0].call}"
}
```

Actual output (default shallow projection):

```text
FILENAME: nodes=4, edges=5, sites=2, root_sites=0
FILENAME_MATCH: function=project::work, calls=1, callee=project::leaf
FILENAME_SAME_SNAPSHOT=true
FILENAME_SHALLOW={}
PARSED: nodes=4, edges=5, sites=2, root_sites=0
PARSED_MATCH: function=project::work, calls=1, callee=project::leaf
PARSED_SAME_SNAPSHOT=true
PARSED_SHALLOW={}
MATCHED: nodes=4, edges=2, sites=2, root_sites=0
MATCHED_MATCH: function=project::work, calls=1, callee=project::leaf
MATCHED_SAME_SNAPSHOT=true
MATCHED_SHALLOW={}
```

The filename and parsed-file graphs contain the admitted TU inventory. The
matched-function graph follows all reachable admitted callees with `depth all`.
All three match inside the same retained `project::work` definition and find
its call to `project::leaf`; the native node references are independent of the
shallow `{}` expression payload. Both console engines passed this example.
Separate native and Unix/TCP acceptance tests also matched exact overloads after
closing source values and deleting both the main file and its project header.

`match ... in node` uses subtree scope by default. Add `scope self` to match
only the callable, or `scope children` for its direct AST children. For an
overload, select an exact signature, for example
`graph.function("app::leaf", "int (int)")`.
Graph filters govern graph inventory and call-site facts; a follow-up matcher
searches the complete selected callable's AST.

Each assigned graph owns an independent server cursor. Its nodes keep that
cursor alive after the graph variable is dropped. Local `callees`/`callers`
views share it and preserve native references when graph indices change.
Closing the graph's session invalidates its nodes and local views; closing the
original parsed file or matched seed does not. Normal ownership, revision,
expiry, scope and memory limits apply. The virtual root has no callable and
produces a clear error if used as a matching target. Normal console saves strip
the retained cursor and node-reference fields; loaded JSON is detached.

Python keeps the existing raw response default. Request an owned graph explicitly:

```python
from clang_toolkit import Client

with Client() as client:
    with client.callgraph("examples/callgraph_strict_filters/main.cc",
                         exclude_system_headers=True, retain_nodes=True) as graph:
        node = graph.function("project::work")
        with client.match_in('callExpr().bind("call")', node) as calls:
            print(len(calls))  # 1
```

The same `retain_nodes=True` option works with a parsed tree, a file handle or
an exact matched binding; use `max_depth="all"` with a callable seed.
`AsyncClient` supports `await client.callgraph(..., retain_nodes=True)`,
`await client.match_in(..., node)` and `await graph.aclose()`.
The raw protocol carries one `retained_nodes` completion descriptor and an
optional `native_match_index` on each real node. These are separate from
semantic AST fields and from the graph-local `node_index`.


## Practical console workflow

Run the complete example from the repository root:

```sh
ctk --script-engine compiled --script examples/callgraph_reuse.ctk
```

It analyzes [a small payment workflow](../examples/callgraph_reuse.cc):

```ctk
let tree = parse "examples/callgraph_reuse.cc"
let payments = match functionDecl(isDefinition(), hasName("demo::chargeCard")).bind("f") in tree
let incoming = callgraph in payments[0].f direction in depth 2
let api = match functionDecl(isDefinition(), hasName("demo::apiRequest")).bind("f") in tree
let reachable = callgraph in api[0].f depth all

foreach edge in incoming.edges do {
    if not edge.is_virtual_root_edge then {
        print "{incoming.nodes[edge.caller_node].function.qualified_name} -> {incoming.nodes[edge.callee_node].function.qualified_name}"
    }
}
```

The represented incoming relationships are checkout to chargeCard, retryPayment
to chargeCard, and apiRequest to checkout, with the demo:: qualification. These
are callers in this translation unit, not a whole-project inventory.
The unlimited outgoing selection from apiRequest contains five callables and
four native call records: apiRequest, checkout and its three leaves.

The full checked-in example prints eight nodes (including the synthetic root),
six call sites, three incoming ordinary edges, two route steps, six grouped
caller/callee pairs, one selected call site, one unresolved indirect site and
one CFG. `COMPLETE=true` describes its shallow semantic projection.

The existing filename form remains available:

```ctk
let all = callgraph "examples/callgraph_reuse.cc" main-file true
let same_tree = callgraph in tree main-file true
```

A standalone command consumes a stream and reports callable names, signatures,
source locations, call-site counts and unresolved-call totals. The seed
is marked and synthetic-root records are hidden. Assignment collects the graph
for field inspection and further queries. Existing ProtoJSON consumers can use
the explicit output option:

```ctk
callgraph in tree main-file true format json
```

Assigned graphs and nodes use the same bounded protobuf preview as matcher rows:
`print graph` preserves availability records, enum names and string-encoded 64-bit
integers, and `print graph | pretty()` adds readable indentation. Typed field
access still returns native values, so offsets remain integers in expressions.
`inspect graph` and `inspect graph.nodes[i]` use the same schema inspector and
default depth as matcher bindings, with graph operations and ownership metadata
alongside the schema fields. Inspection's `retained` flag reports local ownership
state; it does not check server expiry. These previews do not change the graph
or its retained matching references.
Use the existing `save graph to "graph.json" as json` for a detached export.

## System headers and custom callable boundaries

Use `exclude-system true` to keep your source and user headers while omitting
callables in Clang system headers. Unlike `main-file true`, it retains your
header implementations. Both options default to false. System classification
uses the callable's definition when available, otherwise its declaration, at
the expansion location. Clang classifies standard library headers, `-isystem`
directories and headers marked `#pragma GCC system_header` as system headers;
the filter does not guess from the `std::` namespace or angle-bracket includes.

Run [the complete example](../examples/callgraph_boundaries.ctk) from the
repository root with a server built from this branch. The private-console
launcher reproduces the verified output:

```sh
cmake --build --preset dev
mkdir -p /private/tmp/ctk-boundaries-empty-libraries
bash scripts/manual_console.sh --ui prompt --script-engine compiled \
  --lib-dir /private/tmp/ctk-boundaries-empty-libraries \
  --script "$PWD/examples/callgraph_boundaries.ctk"
```

The fixture includes a user header containing `project::check` and
`project::leaf`, a `vendor::trace` helper, and the real `<stdexcept>` header.
`entry` calls the two user-header helpers; `project::check` can throw
`std::runtime_error`. Standard library callables are omitted while the project
header remains represented.

```ctk
let filename = callgraph "examples/callgraph_boundaries.cc" exclude-system true
let tree = parse "examples/callgraph_boundaries.cc"
let parsed = callgraph in tree exclude-system true
let entries = match functionDecl(hasName("entry"), isDefinition()).bind("f") in tree
let matched = callgraph in entries[0].f exclude-system true depth all
let custom = callgraph in entries[0].f exclude-system true depth all node-filter 'functionDecl(unless(matchesName("(^|::)vendor::")))'
```

Actual shallow output from the complete example in the real compiled console:

```text
FILENAME_NODES=5
PARSED_NODES=5
MATCHED_DEFAULT_DEPTH_NODES=4
MATCHED_NODES=5
project::check -> project::leaf
entry -> project::check
entry -> vendor::trace
CUSTOM_NODES=4
project::leaf
project::check
entry
COMPLETE=true
```

Advanced `node-filter` accepts a quoted Clang declaration matcher, evaluated on
each callable's definition or fallback declaration. These are admission rules,
not seed selectors or filters applied after depth traversal:

| Desired boundary | Matcher text |
| --- | --- |
| Exclude a namespace | `functionDecl(unless(matchesName("(^\|::)vendor::")))` |
| Keep a namespace and the entry point | `functionDecl(anyOf(matchesName("(^\|::)project::"), hasName("entry")))` |
| Keep functions in a header path | `functionDecl(isExpansionInFileMatching("callgraph_boundary_helpers[.]hpp$"))` |
| Combine names and file exclusions | `functionDecl(anyOf(matchesName("(^\|::)project::"), hasName("entry")), unless(isExpansionInFileMatching("/generated/")))` |
| Exclude C++ methods | `functionDecl(unless(cxxMethodDecl()))` |

Path and name patterns are Clang regular expressions, not shell globs. Namespace
examples use `(^|::)` to account for a leading global qualifier in matcher names.
`allOf`, `anyOf`, `unless` and other compatible declaration predicates can be
composed. Invalid syntax or statement matchers such as `stmt()` return an
invalid-argument error. A filtered-out seed returns not-found.

All active scope rules combine with AND. Excluded callables stop paths: if
`entry -> excluded -> leaf` is the only route, `depth all` from `entry` does not
reach `leaf`. A whole-TU query can still contain that admitted `leaf` as a
separate node. The virtual root remains. `external_edges_omitted` counts dropped
native call records from admitted callers, including root records. Admitted
callers retain boundary call-site facts by default without a `callee_node`; the target
name can therefore still appear in a call-site fact. Excluded callers contribute
no sites and do not consume the call-site budget. `is_complete` describes the
requested scope and projection.

For call-site facts without an enclosing callable (the virtual-root caller),
`exclude-system true` also checks the call expression's expansion location.
System-header facts are omitted before consuming the call-site budget. Facts
from your own headers and main file remain, including system-defined macros
expanded there. By default, calls from an admitted function to an excluded callee still
retain their boundary facts. `node-filter` remains a callable matcher; it does
not apply a declaration matcher to root-level expressions.

Run `examples/callgraph_system_sites.ctk` against the updated server for a
complete filename, parsed-file and matched-node console check using both
`exclude-system true` and a custom matcher. It prints the virtual-root call-site
count explicitly. On Linux with the checked-in stdexcept fixture, all three
forms return `root_sites=0`; filename and parsed-file results contain 4 nodes,
5 edges and 3 call sites, while the matched `depth all` result has 4 nodes,
2 edges and 3 call sites. Both user-header functions remain.

Optional `strict-node-filter true` (Python: `strict_node_filter=True`) also
removes call-site facts whose known static callee fails the combined callable
scope filters. It requires a nonempty `node-filter` and defaults to false.
Filtering happens before the call-site limit, including calls attached to the
virtual root. This changes facts, not the admitted node set, graph edges,
`external_edges_omitted`, or depth traversal. Root expressions are not matched
as declarations: their known callee is checked. Genuine indirect calls remain
because their targets are unknown. `is_complete` still describes the requested
scope, not whole-program runtime resolution.

```ctk
let source = "examples/callgraph_strict_filters/main.cc"
let filename = callgraph source node-filter 'functionDecl(unless(isExpansionInFileMatching("(^|/)(vendor|generated)/")))' strict-node-filter true
let tree = parse source
let parsed = callgraph in tree node-filter 'functionDecl(unless(isExpansionInFileMatching("(^|/)(vendor|generated)/")))' strict-node-filter true
let entries = match functionDecl(hasName("entry"), isDefinition()).bind("f") in tree
let matched = callgraph in entries[0].f depth all node-filter 'functionDecl(unless(isExpansionInFileMatching("(^|/)(vendor|generated)/")))' strict-node-filter true
```

The complete runnable `examples/callgraph_strict_filters.ctk` also combines
`exclude-system true`, prints default versus strict call-site counts for all
three inputs, and exports the actual shallow responses. The fixture keeps
`include/myproject/logic.hpp`, excludes `vendor/trace.hpp` even though it uses
namespace `third_party`, and excludes `generated/api.hpp` even though it uses
namespace `project`. Run it from the repository root:

```sh
mkdir -p /tmp/strict-results /tmp/strict-empty-libraries
ctk --server unix:///tmp/ctk.sock --script-engine compiled \
  --lib-dir /tmp/strict-empty-libraries --script examples/callgraph_strict_filters.ctk \
  source=examples/callgraph_strict_filters/main.cc output=/tmp/strict-results
```

Actual console output from the strict-filter development build on macOS:

```text
DEFAULT: sites=4, strict=false
FILENAME: nodes=4, edges=5, sites=2, root_sites=0, strict=true, complete=true
FILENAME_CALL: project::work -> project::leaf
FILENAME_CALL: entry -> project::work
PARSED: nodes=4, edges=5, sites=2, root_sites=0, strict=true, complete=true
PARSED_CALL: project::work -> project::leaf
PARSED_CALL: entry -> project::work
MATCHED: nodes=4, edges=2, sites=2, root_sites=0, strict=true, complete=true
MATCHED_CALL: project::work -> project::leaf
MATCHED_CALL: entry -> project::work
```

The response echoes `strict_node_filter`, `exclude_system_headers` and `node_filter`; Python clients
reject servers that do not confirm these filters. Retained inputs reuse the
pinned snapshot, and graph methods that query a retained binding preserve its
boundary. Shallow results remain the default. Scope filters do not prevent
Clang from parsing included headers; they control graph membership.

Python collectors and streams use the same options:

```python
graph = client.callgraph(
    target,  # filename, parsed file, file handle or matched binding
    exclude_system_headers=True,
    node_filter='functionDecl(unless(matchesName("(^|::)vendor::")))',
    max_depth="all",  # use with a callable target
)
```

## Input and selection rules

| Input | Selection |
| --- | --- |
| Filename, path or filesystem File | Acquire the translation unit with its compilation profile. |
| ParsedTree or native FileHandle | Use the exact pinned AST generation. |
| One retained function or method binding | Seed an outgoing depth-one neighborhood by default. |
| One retained CallExpr binding | Report that exact site, its lexical caller and optional static callee. |

For callable bindings, direction out, in or both selects an outgoing, incoming
or bidirectional neighborhood. Depth zero selects only the seed. Depth is
bounded to 32 by default. Use `depth all` (or `max_depth="all"` in Python) to
follow every reachable callable in the selected direction; visited-node BFS
terminates when the graph contains cycles. The result excludes disconnected
callables and preserves every native call record. An unlimited selection is
still limited by the node, edge, site, work and byte budgets. The response marks
`selection_unlimited_depth` so clients can detect servers that do not support
the request. Unlimited depth is valid only with one callable seed; reject it for
whole-translation-unit and exact CallExpr selections.

Exact bindings preserve overload identity. Empty, multiple, unrelated-node,
dependent-function and invalid retained selections receive explicit diagnostics.
A retained query never falls back to reparsing a filename. Closing or expiring
a reference invalidates that reference; independent matched values keep their
own native ownership. On-disk edits do not change a retained AST generation.

Assigned console graphs retain a separately owned cursor of exact callable
declarations. Use `match ... in graph.nodes[i]` or `graph.function("name")`
without reparsing. Definitions are used when available, otherwise declarations.
Graph indices are local display indices; local graph selections preserve the
original native reference when they reindex. Exports and loaded JSON are detached
data and cannot recreate a cursor.

## Returned graph and projection

Assignment collects nodes, edges, call_sites, completeness, scope and
snapshot/source/profile provenance. Resolve endpoints with
`graph.nodes[edge.caller_node]` and `graph.nodes[edge.callee_node]`.

Every native call record remains a separate edge, preserving repeated calls
and native per-caller order. Synthetic-root nodes and edges are explicitly
marked; they are not runtime calls or application entry points.

Call sites are separate from target edges. An unresolved indirect call has a
site and dispatch facts, with no invented callee node. Virtual calls identify
the statically selected declaration, not a proven runtime target.
Declaration-only callees have has_definition=false.
The call-site inventory covers the supported CallExpr family; other native
call records remain available in edges.

```text
graph
  root_node: index of the synthetic root
  nodes: [node_index, function, symbol_identity, location, range, ...]
  edges: [caller_node, callee_node, call, ...]
  call_sites: [caller_node, optional callee_node, location, range, facts, ...]
  snapshot_generation, source_file, source_revision, compilation_profile_id
  optional focus_node, selection_direction, optional selection_max_depth,
  optional selection_unlimited_depth
  selection_boundary_edges, selection_boundary_call_sites
  is_complete, availability, main_file_only, external_edges_omitted
  exclude_system_headers, node_filter, strict_node_filter
```

```ctk
let graph = callgraph in tree projection shallow
let detailed = callgraph in tree projection recursive payload-depth 6 payload-nodes 1000
save graph to "/private/tmp/calls.json" as json
```

Projection changes semantic expansion, not graph relationships. Shallow results
are the default for filenames and retained inputs. Fetch detailed AST information
only where needed. Legacy raw protobuf requests that omit projection retain their
prior behavior. Completeness and availability describe the requested projection;
complete shallow results do not mean nested AST payloads were expanded.

Earlier measurements in the proposal describe the baseline response. The added
source facts, provenance and separate call-site records change export sizes;
node and edge counts alone do not predict serialized or in-memory size.

Main-file scope excludes header callable inventory. Scope omission counts and
neighborhood boundary counts describe different filters. Missing represented
edges do not prove that a function makes no calls.

## Python collectors and streams

```python
from clang_toolkit import AsyncClient

async def inspect(address, source):
    async with AsyncClient(address) as client:
        tree = await client.parse(source)
        rows = await client.match_in(
            'functionDecl(isDefinition(), hasName("demo::chargeCard")).bind("f")', tree
        )
        return await client.callgraph(rows[0].binding("f"), direction="in", max_depth=2)

async def all_reachable(address, source):
    async with AsyncClient(address) as client:
        tree = await client.parse(source)
        rows = await client.match_in(
            'functionDecl(isDefinition(), hasName("demo::apiRequest")).bind("f")', tree
        )
        return await client.callgraph(
            rows[0].binding("f"), direction="out", max_depth="all"
        )
```

Client.callgraph is the synchronous collector. Both clients return a
CallGraphResponse protobuf. Collection explicitly uses client memory.

```python
from contextlib import aclosing
from clang_toolkit import AsyncClient

async def consume(address, source):
    async with AsyncClient(address) as client:
        async with aclosing(client.callgraph_stream(source)) as events:
            async for event in events:
                if event.HasField("call_site"):
                    print(event.call_site.call_site.facts)
```

Use stream_callgraph(target, on_event=consume) for a callback; asynchronous
callbacks are awaited before reading the next event. The synchronous client
provides the callback equivalent. Early iterator close, callback failure and
cancellation cancel the RPC and release its work.

StreamCallGraph sends metadata and individual records, then final counts.
Require completion and terminal OK. Earlier records remain provisional until
both succeed. Semantic incompleteness remains separate from delivery success.
The unary CallGraph RPC remains an atomic, aggregate-byte-bounded operation.

Streaming bounds individual events instead of one aggregate serialized graph.
Clang still constructs a native graph. Slow consumers may hold its snapshot and
execution lane while applying backpressure; finish or cancel before issuing
another native query on that snapshot from a callback.

## Repeated local graph queries

```python
from clang_toolkit import CallGraph

graph = CallGraph(response)
payment = graph.function("demo::chargeCard")
incoming = graph.callers(payment, depth=2)
route = graph.shortest_path("demo::apiRequest", payment)
recursive_groups = graph.recursive_components()
grouped = graph.grouped_calls()
route_with_sites = graph.shortest_route("demo::apiRequest", payment)
```

These methods query the collected topology without an RPC or another native
graph build. Ambiguous names require an exact signature. Neighborhoods keep
repeated sites and reindex nodes and edges coherently. Paths and recursive
components exclude synthetic-root relationships and terminate on cycles.
Pass `depth="all"` to `callers` or `callees` to traverse every represented
reachable node. Queries on an already focused graph remain limited to that
graph's coverage, and carry forward inherited scope and boundary omissions;
they cannot establish reachability beyond the collected input.
Local neighborhood views omit the synthetic root and use UINT64_MAX in
root_node to mark its absence; their ordinary endpoints and focus remain array
indices. Native responses retain the explicit synthetic root.

grouped_calls groups repeated records by caller and callee and retains their
individual sites and count. shortest_path returns callable nodes;
shortest_route also supplies the call sites witnessing each step.

Native requests rebuild bounded topology from their selected snapshot; there
is no unaccounted server cache retaining snapshots after resource release.

## Native semantics and bounds

Implicit code and template instantiations default to enabled; explicit false
remains distinct from omission. Disabling instantiation visits can remove body
edges while retaining nodes introduced as callees. Empty translation units
still contain the native synthetic root.

There is no fixed callgraph node ceiling. Omit `nodes` to use the server's
configured default, initially 10,000. Set `nodes N` to override that default
with any positive count representable as uint64; `nodes all` (or `nodes 0`)
disables the node-count limit. Python accepts `max_nodes=N`,
`max_nodes="all"` or `max_nodes=0`; `None` uses the server default.

```yaml
server:
  call_graph:
    default_max_nodes: 250000  # 0 makes omitted node limits unlimited
```

The server setting is a default, not a maximum for explicit requests. It uses
the normal YAML configuration layers; invalid negative, null, boolean and
noninteger settings are rejected. Configuration counts use signed 64-bit YAML
integers; request counts use uint64. Retained inputs use the same rules without
reparsing. Shallow payloads remain the default.

```ctk
let tree = parse "examples/callgraph_reuse.cc"
let file_graph = callgraph "examples/callgraph_reuse.cc" nodes all
let tree_graph = callgraph in tree nodes 250000
let functions = match functionDecl(isDefinition(), hasName("demo::apiRequest")).bind("f") in tree
let reachable = callgraph in functions[0].f depth all nodes all
```

`depth all` removes the callable-hop limit; `nodes all` independently removes
the node-count budget. Neither disables edge, call-site, memory, byte or
cancellation controls. Edges still default to 100,000, with a maximum of
1,000,000. Synthetic-root structure counts toward finite node and edge limits.
For more than 100,000 leaf callables, raise the edge budget too because the
virtual root has an edge to each callable. A 100,001-function regression streams
100,002 nodes and 100,001 root edges using both a finite node limit above the
former ceiling and unlimited nodes, with `edges 200000`.

Call-site, work and byte bounds are independent
from semantic payload depth/node limits. Exhaustion and cancellation cannot
publish successful completion. Native function-body construction is synchronous;
cancellation is checked between traversal and serialization steps.

There is no alias analysis, runtime dispatch solver or cross-translation-unit
merge. Implicit destructor control flow belongs to CFG. The C++ Project facade
continues to return per-translation-unit graphs using normalized native
compilation database commands; it does not merge a project-wide graph.

For C++ callers, include `ctk/clang/call_graph_limits.hpp` and pass a
`CallGraphLimits` to `callgraph(project, limits)` to configure the aggregate
project budget. Set `limits.max_nodes = 0` for unlimited nodes. Finite aggregate
budgets stay exhausted when the remaining count reaches zero. The existing
one-argument `callgraph(project)` keeps its prior defaults.
