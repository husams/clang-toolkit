# Static call graphs from filenames and retained nodes

Use `callgraph` for represented static calls in one translation unit (TU).
Call-graph hop depth, graph count limits and semantic payload expansion are
independent. Keep shallow payloads unless detailed AST information is requested.

## Match directly from returned callgraph nodes

Assigned console graphs retain exact callable references into their pinned AST.
Both `graph.nodes[i]` and `graph.function("project::work")` are valid `match`
targets. Matching uses the callable definition when available, otherwise its
declaration; overloads retain their exact identity. It neither reparses the file
nor searches again by function name or source coordinates.

Run the verified bundled recipe from the repository root with the updated client and server:

```sh
ctk --script-engine compiled --ui prompt --script skills/ctk-script/scripts/callgraph_match_nodes.ctk path=skills/ctk-script/assets/callgraph_project/main.cc
```

From another working directory, resolve the installed skill root and pass absolute paths.

The complete script is [callgraph_match_nodes.ctk](../scripts/callgraph_match_nodes.ctk).
It creates filename, parsed-file and matched-function graphs and matches directly
from each returned node. The following actual compiled-console output was verified
on macOS and on Linux on 17 October 2026. The Linux run used merged main
`8c6d2c97b8a6`, including PR #50, with the rebuilt client and restarted server at
`unix:///tmp/ctk.sock`. Linux matching also succeeded after closing the original
handles and removing all fixture source/header files, as reproduced below:

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

### Linux proof after closing handles and removing source files

The verified Linux client and server both reported revision `8c6d2c97b8a6`.
This is recorded verification, not a health check of a later endpoint. Use an
authorized existing server and keep both console stages in one live session.
The filename graph creates or reuses an AST; the parsed-file and matched-node
graph requests use retained inputs. The proof then closes those original inputs
and removes the disposable source and headers before any direct node matching.

From the Linux checkout, prepare the same disposable fixture and open a console:

```sh
cd /home/husam/clang-toolkit
proof_dir=/tmp/ctk-node-match-main.8qKQpz
mkdir -p "$proof_dir/fixture" "$proof_dir/empty-libraries"
cp -R examples/callgraph_strict_filters/. "$proof_dir/fixture/"
.venv/bin/ctk --server unix:///tmp/ctk.sock --script-engine compiled --ui prompt --lib-dir "$proof_dir/empty-libraries"
```

First create filename, parsed-file and matched-function graphs. All three use the
default shallow semantic payload. `depth all` on the matched seed controls call
hops, independently of payload expansion:

```ctk
let source = "/tmp/ctk-node-match-main.8qKQpz/fixture/main.cc"
let filename = callgraph source exclude-system true node-filter 'functionDecl(unless(isExpansionInFileMatching("(^|/)(vendor|generated)/")))' strict-node-filter true
let tree = parse source
let entries = match functionDecl(hasName("entry"), isDefinition()).bind("f") in tree
let parsed = callgraph in tree exclude-system true node-filter 'functionDecl(unless(isExpansionInFileMatching("(^|/)(vendor|generated)/")))' strict-node-filter true
let matched = callgraph in entries[0].f depth all exclude-system true node-filter 'functionDecl(unless(isExpansionInFileMatching("(^|/)(vendor|generated)/")))' strict-node-filter true
print "GRAPH_READY={1}"
```

After `GRAPH_READY=1`, enter these commands separately in that console to close
the original parsed-file and matched-function handles. Keep all three graph
values alive:

```ctk
session close $tree
session close $entries
print "ORIGINAL_OWNERS_CLOSED={1}"
```

After `ORIGINAL_OWNERS_CLOSED=1`, leave this console open. In a second terminal,
remove only this disposable fixture, including the project, vendor and generated
headers; never delete the user's original source as a verification step:

```sh
rm -r -- /tmp/ctk-node-match-main.8qKQpz/fixture
test ! -e /tmp/ctk-node-match-main.8qKQpz/fixture && printf 'SOURCE_AND_HEADERS_REMOVED=true\n'
```

The recorded run confirmed `SOURCE_AND_HEADERS_REMOVED=true` before the following
queries. Back in the original console, match both the exact callable through
`graph.nodes[...]` and the calls inside `graph.function("project::work")`:

```ctk
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
print "POST_REMOVAL_MATCHES={3}"
```

This produced the twelve actual output lines above, followed by:

```text
POST_REMOVAL_MATCHES=3
```

All three graphs still matched the retained `project::work` definition and its
call to `project::leaf`, with unchanged snapshots, shallow `{}` call-site AST
payloads and zero root call-site facts. The post-removal `match` queries use only
graph nodes, with no filename lookup, `parse` call or original source handle.
The filename and parsed-file graphs include three virtual-root edges plus two
project call edges; the matched graph contains the two reachable project edges.
Graph ownership preserves the native references independently of shallow AST
fields and of the original parsed/matched owners.

Recorded evidence for this Linux run is under
`linux-dev:/tmp/ctk-node-match-main.8qKQpz/`: `console-screen.txt`, `console.raw`,
`actual-output.txt` and the real-TTY verification driver `verify.py`. The same
examples and output are on the
[callgraph Page](https://chatgpt.com/space/page_97441a03020481919a9361964dc17ff6).

### Matching scope and ownership

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


## Select the right input and coverage

| Input | Console form | Coverage |
| --- | --- | --- |
| Filename, path or filesystem File | `let graph = callgraph source` | Whole admitted TU inventory, including disconnected functions. |
| Already parsed file or native file handle | `let graph = callgraph in tree` | Same TU inventory from its pinned AST generation. |
| One retained function/method binding | `let graph = callgraph in row.f` | Outgoing depth-one neighborhood by default. |
| One retained CallExpr binding | `let graph = callgraph in row.call` | Exact call site, lexical caller and optional static callee. |

Given an existing matched node, pass that binding directly. Do not replace it
with a filename or parse again. Keep the live parsed tree/bindings in the same
console session; exported or loaded JSON cannot reconstruct native handles.
Retained queries use the exact parsed generation, even if disk files change.
Select one definition; `.one("description")` diagnoses zero or multiple matches.
Refine an overloaded-name matcher rather than choosing the first row silently.

For a callable seed, use `direction out`, `in` or `both` and `depth N` for call
hops. `depth 0` keeps the seed. `depth all` follows every reachable admitted
callable in the selected direction and terminates on cycles. It is valid only
with one callable seed, not a whole-TU or exact-call-site query. A matched seed
does not include disconnected functions and cannot merge other TUs. To get the
entire admitted TU, pass the already parsed file instead, without `depth all`.

## Independently control call depth, counts and payloads

| Intent | Console | Meaning |
| --- | --- | --- |
| All reachable call hops | `depth all` | Removes the callable-hop limit; leaves other budgets active. |
| Unlimited graph nodes | `nodes all` or `nodes 0` | Removes the node-count limit, including the virtual root. |
| Finite graph nodes | `nodes 250000` | Explicit positive uint64 request; no fixed node ceiling. |
| Compact semantic payloads | Omit `projection`, or use `projection shallow` | Default for filename and retained inputs; does not limit call-graph reachability. |
| Expanded semantic payloads | `projection recursive payload-depth 6 payload-nodes 1000` | Explicit AST payload expansion, independent of call hops. |

Omitted `nodes` uses `server.call_graph.default_max_nodes`, initially 10,000;
setting that server default to 0 makes omitted node limits unlimited. An
explicit request can override the default. `depth all nodes all` removes both
limits independently; edge, call-site, work, memory, byte and cancellation
controls remain. Raise finite `edges N` and `callsites N` only as needed. Root
edges count toward edge budgets. Require successful completion and
`graph.is_complete` before claiming a complete result for the requested scope.

## System headers and advanced custom filters

`exclude-system true` removes Clang-classified system-header callables while
keeping ordinary project headers. Classification uses the definition, falling
back to the declaration, at its expansion location; it honors `-isystem` and
`#pragma GCC system_header`. Do not infer classification from `std::` or angle
brackets. It also removes system-header call-site facts attached to the virtual
root, before charging the site budget. Project-header root facts remain.
`main-file true` excludes your own headers as well, so it is unsuitable when
the user wants to keep project headers. Graph filters do not prevent Clang from
parsing included headers: supply the real compilation profile and include paths.

`node-filter` is a quoted Clang declaration matcher, evaluated on each callable
definition or fallback declaration before topology and depth selection.
The console option requires a quoted string literal; a bare variable such as
`node-filter boundary_filter` is rejected. Customize the quoted matcher in each
query rather than claiming that a runnable matcher value is accepted here.

| Boundary | Matcher text |
| --- | --- |
| Exclude vendor/generated directory components | `functionDecl(unless(isExpansionInFileMatching("(^\|/)(vendor\|generated)/")))` |
| Exclude a namespace | `functionDecl(unless(matchesName("(^\|::)vendor::")))` |
| Keep a namespace plus the seed | `functionDecl(anyOf(matchesName("(^\|::)project::"), hasName("entry")))` |
| Keep the project namespace and seed, excluding generated files | `functionDecl(anyOf(matchesName("(^\|::)project::"), hasName("entry")), unless(isExpansionInFileMatching("(^\|/)generated/")))` |
| Keep project headers plus the seed, omitting generated files | `functionDecl(anyOf(isExpansionInFileMatching("/myproject/"), hasName("entry")), unless(isExpansionInFileMatching("/generated/")))` |

Patterns are Clang regular expressions, not shell globs. `(^|::)` handles global
qualification in matcher names. Compose compatible predicates with `allOf`,
`anyOf` and `unless`. In Markdown tables, `\|` displays a literal `|`; use the
unescaped pipe in the actual matcher. Combine scope filters with AND and retain
the seed itself. Invalid matchers/statement matchers return invalid-argument;
a filtered-out seed returns not-found. An exclusion is a traversal boundary:
`entry -> excluded -> leaf` does not reach `leaf` through that excluded function.

The default `strict-node-filter false` removes excluded callable nodes/edges
but keeps boundary call-site facts from retained callers without a `callee_node`.
For project-only known-callee facts, explicitly use `strict-node-filter true`
with a nonempty `node-filter`. It additionally removes facts whose known static
callee fails the combined scope filters, including facts attached to the virtual
root, before the site budget is charged. It does not change admitted nodes,
topology, depth selection or `external_edges_omitted`. Unknown indirect targets
remain because they cannot be classified. Filtering names alone cannot prove
that every unresolved target belongs to the project.

## Run the complete three-input recipe

[callgraph_project.ctk](../scripts/callgraph_project.ctk) explicitly opts in to
strict mode, excludes system headers, removes the node-count limit, and compares
filename, parsed-file and matched-function results. Its matched query uses
`direction out depth all`. The initial non-strict query demonstrates that strict
filtering is optional. It accepts `path`, `function` and `output`. To customize
boundaries, copy the script and edit the quoted matcher in its four graph
queries. The output directory must already exist.

The bundled fixture [main.cc](../assets/callgraph_project/main.cc) contains
`entry -> project::work -> project::leaf`, with project functions defined in
`include/myproject/logic.hpp`. `entry` also calls `third_party::trace` in
`vendor/trace.hpp` and `project::generated_call` in `generated/api.hpp`, proving
that path filtering is independent of namespace names.

Resolve `ctk_skill_dir` from the active skill's absolute path. Script and export
paths are client-side; the source must be accessible to the server. With a local
server that can read the bundled asset, run:

```sh
ctk_skill_dir=/absolute/path/to/ctk-script
mkdir -p /tmp/ctk-project-calls /tmp/ctk-empty-libraries
ctk --server unix:///tmp/ctk.sock --script-engine compiled --ui prompt \
  --lib-dir /tmp/ctk-empty-libraries \
  --script "$ctk_skill_dir/scripts/callgraph_project.ctk" \
  "path=$ctk_skill_dir/assets/callgraph_project/main.cc" \
  function=entry output=/tmp/ctk-project-calls
```

For a remote Linux server, run its console on that host or supply a server-side
source path. The checked-in equivalent is
`/home/husam/clang-toolkit/examples/callgraph_strict_filters/main.cc`; a Mac skill
asset path is not automatically uploaded. Use the supplied/configured endpoint.
For project code, pass its compilation database and refine the function matcher
and boundary matcher to the actual layout. An allowlist can be safer than a
vendor/generated denylist when dependencies live in other directories.

### Starting from an already matched function

Keep the existing `function_node` binding and run just the graph query. The
following complete console submission first creates that binding in the fixture:

```ctk
let tree = parse "examples/callgraph_strict_filters/main.cc"
let functions = match functionDecl(isDefinition(), hasName("entry")).bind("f") in tree
let function_row = functions.one("entry definition")
let function_node = function_row.f
let graph = callgraph in function_node direction out depth all nodes all exclude-system true node-filter 'functionDecl(unless(isExpansionInFileMatching("(^|/)(vendor|generated)/")))' strict-node-filter true
let roots = graph.call_sites | filter((site) = site.caller_node == graph.root_node)
print "MATCHED: nodes={graph.nodes.length}, edges={graph.edges.length}, sites={graph.call_sites.length}, root_sites={roots.length}, strict={graph.strict_node_filter}, complete={graph.is_complete}"
foreach site in graph.call_sites do {
    print "CALL: {graph.nodes[site.caller_node].function.qualified_name} -> {site.facts.static_callee_name}"
}
save graph to "/tmp/ctk-matched-project-only.json" as json
```

The graph operation reuses the binding's parsed snapshot. Adding `depth all`
does not request recursive AST payloads; the returned semantics stay shallow.

## Returned structure and evidence

Assignment collects a reusable graph; standalone `callgraph` streams a readable
summary after terminal success. Add `format json` for raw ProtoJSON. The collected
graph has:

```text
root_node: index of the synthetic root
nodes: callable identity, function, location/range and definition facts
edges: caller_node, callee_node, call and is_virtual_root_edge
call_sites: caller_node, optional callee_node, call, location/range and facts
source_file, source_revision, snapshot_generation, compilation_profile_id
focus_node, selection_direction, selection_max_depth/selection_unlimited_depth
selection_boundary_edges, selection_boundary_call_sites
is_complete, availability, main_file_only, external_edges_omitted
exclude_system_headers, node_filter, strict_node_filter
```

Resolve endpoints through `graph.nodes[index]`. An assigned live graph retains
a separate exact native reference for each callable: use that node directly as
a `match` target. Indices alone are local to one graph; exported/loaded graph
data has no native ownership. Native graphs retain a virtual root even in a focused query.
It is not an application entry point. Each native call record stays a separate
edge, including repeated calls. Call-site facts and edges have different
inventories: unresolved indirect calls have facts without an invented callee,
and some native call records are outside the supported CallExpr family. Virtual
calls describe the statically selected declaration, not proven runtime dispatch.

Use `graph.call_sites | filter((site) = site.caller_node == graph.root_node)`
to count root facts. Default shallow responses keep call-expression payloads
unexpanded (the verified exports contain `call: {}`). Counts do not determine
serialized or in-memory size; measure the current saved JSON when size matters
and identify projection, scope, revision and target instead of promising a fixed
size or reusing older baseline byte counts.

Saved ProtoJSON can omit default scalar fields: an omitted `root_node` is 0,
not an absent virtual root. It encodes uint64 graph indices as decimal strings;
convert them when indexing ordinary JSON arrays. Live CTK graph values already
support the endpoint indexing shown in the examples.

The earlier Linux project-filter verification on 17 October 2026 used merged revision
`628623311b3b` at `unix:///tmp/ctk.sock`; live evidence and the actual console
output are maintained on the [callgraph Page](https://chatgpt.com/space/page_97441a03020481919a9361964dc17ff6).
For this fixture the strict results contain 4 nodes including the virtual root,
2 call sites and 0 root facts. Filename/parsed-file graphs have 5 edges (3 root
edges plus 2 project calls); the focused matched graph has the 2 project edges.
Omitting strict mode retains 4 call-site facts. Filename and parsed-file exports
are identical. Recheck the connected client/server capabilities for new runs;
historical verification is not a health check of the current endpoint.

For the project-only recipe at that revision, the recorded Linux console output is:

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

In that run, the UTF-8 JSON exports were **14,357 bytes** each for filename and
parsed-file input, and **14,165 bytes** for matched input. These measurements
used `/home/husam/clang-toolkit/examples/callgraph_strict_filters/main.cc` and
include its source paths, provenance and shallow facts; they are not fixed size
promises for another project. All three reported `complete=true` and
`root_sites=0`.

The combined project-namespace/entry-point allowlist with a generated-path
exclusion in the matcher table was also run successfully with these same
counts. A missing function was rejected by `.one(...)` with an explicit
expected-one/got-zero error instead of selecting another function.

Do not install packages, restart services or change compilation settings solely
to make this example pass. Use an authorized existing endpoint, a real TTY-backed
console, and the final exact script. Require completion before trusting exports;
inspect `is_complete`, filter echoes, node/callee sets and root counts. Never
report old output as freshly rerun. When streaming, require terminal success as
well as completion; earlier events remain provisional if the stream fails.

## Maintained implementation sources

- `docs/call-graphs.md` and `docs/console-command-reference.md` in clang-toolkit
- `examples/callgraph_reuse.ctk`, `examples/callgraph_system_sites.ctk` and
  `examples/callgraph_strict_filters.ctk`
- `api/analysis/v1/analysis_service.proto` and the call-graph protobuf contracts
- `server/tests/test_call_graph.cpp` and `tests/unit/test_call_graph.py`

For Python SDK collectors, callbacks, streams and local graph queries, use the
SDK reasoning skill and current SDK guide. Python names include
`exclude_system_headers`, `node_filter`, `strict_node_filter`, `max_depth="all"`
and `max_nodes="all"`/0. These are the same scope controls, not a separate
whole-project graph implementation.
