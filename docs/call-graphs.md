# Static call graphs and retained inputs

Call graphs describe represented static calls in one translation unit. Console
and Python requests use shallow semantic results by default. Recursive AST
expansion is explicit.

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

Exports are detached data. Response-local graph indices do not identify native
AST objects. Keep the original retained bindings when continuing with match,
traverse or CFG.

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

Default limits are 10,000 nodes and 100,000 edges; hard maxima are 100,000 and
1,000,000 respectively, subject to server settings. Synthetic-root structure
counts toward these limits. Call-site, work and byte bounds are independent
from semantic payload depth/node limits. Exhaustion and cancellation cannot
publish successful completion. Native function-body construction is synchronous;
cancellation is checked between traversal and serialization steps.

There is no alias analysis, runtime dispatch solver or cross-translation-unit
merge. Implicit destructor control flow belongs to CFG. The C++ Project facade
continues to return per-translation-unit graphs using normalized native
compilation database commands; it does not merge a project-wide graph.
