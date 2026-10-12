# Native AST traversal

`traverse` walks native AST syntax in preorder. Its target can be a source path,
opened file, pinned `ParsedTree`, or any retained `BindingSelection`; it does not
run a matcher, reparse retained targets, or replace their bindings. `current` is
unnecessary: the selected reference is already the root. This operation descends
through native visitor edges; parent lookup and inheritance navigation remain
separate proposal operations.

```text
let tree = parse "example.cc"
let rows = match cxxRecordDecl(hasName("Leaf"), isDefinition()).bind("record") in $tree
traverse $rows[0].record depth 4 nodes 10000 projection shallow
traverse $tree depth 2
```

Standalone console commands emit one `TraversalNode` ProtoJSON object as each
visit arrives, then `TraverseCompleted` metadata. This is a sequence of JSON
objects, not one aggregate JSON document. Errors can follow provisional visits;
only completion plus terminal RPC success establishes a successful traversal.
`let graph = traverse ...` explicitly collects an inspectable compatibility
value with `nodes` and `depth_limited`.

```python
from clang_toolkit import Client

with Client(address="unix:///tmp/ctk.sock") as client:
    with client.parse("example.cc") as tree:
        completed = client.stream_traverse(
            tree, on_node=lambda node: print(node.index, node.native_kind),
            max_depth=4, main_file_only=True,
        )
        print(completed.node_count, completed.depth_limited)
```

`AsyncClient.stream_traverse` accepts a synchronous or asynchronous callback;
`AsyncClient.traverse_stream` is an async event iterator. Use `contextlib.aclosing`
when stopping the iterator early. Each callback is awaited before consuming the
next event. Callback failure, early close, transport failure, cancellation and
limits cancel or reject the stream. Clients verify ordinal, parent/depth
structure, completion count and terminal status. No visit payloads are retained
by the streaming APIs. `Client.traverse` and `AsyncClient.traverse` are explicit
compatibility collectors over this same streaming RPC; unary `Traverse` remains
available for old protocol clients and returns no partial tree on failure.

Each record carries an ordinal `index`, `native_kind`, depth and optional parent
index. A binding spanning several rows produces a forest in row order: every
root has depth zero and no parent, while indices continue across roots. Repeated
occurrences are preserved. Depth and node limits apply across the whole visit.

The visitor accepts all `DynTypedNode` families: declarations, statements,
raw/qualified types, type locations, attributes, base specifiers, constructor
initializers, template arguments and locations, template names, nested name
specifiers and locations, OpenMP clauses, and supported-version concept or
Objective-C protocol references. Native auxiliary values that require enclosing
context (such as a lambda capture initializer) are explicitly emitted as
`leaf=true`; they are not silently discarded. A native kind whose owned semantic
schema is deferred carries `value.unsupported`. This does not prevent traversal
of its available native children. A type's declaration and a base's referenced
record are semantic relations, not visitor children.

`visit_implicit_code` and `visit_template_instantiations` map to the native
visitor options, independently of matcher traversal policies. An explicitly
selected root is emitted even when implicit or outside the main file; these
filters apply to descendants. Type locations without a supported semantic schema
remain explicitly unsupported. Main-file filtering uses declaration/statement
expansion locations; it is not a universal source-location predicate on types.

Root depth is zero. Default maximum depth is 64 (range 0..256); zero emits roots
only and reports `depth_limited` when descendants were pruned. Default maximum
nodes is 10,000 (range 1..100,000). Limits and cancellation can terminate a stream
after visits, without completion. Semantic projection expansion has its own
payload depth/node bounds and completeness metadata. Shallow projection is the
Python/console default. The streaming byte budget applies per node event, while
the compatibility unary response retains an aggregate byte budget.

The server writes visits synchronously to gRPC, so transport backpressure slows
the native visitor rather than filling a response vector. It shares the bounded
operation executor and snapshot execution lane with matching. Caller ownership,
expiry and expected revision are validated before retaining the native state;
source cursor results and revision stay unchanged. Resource work pins the native
snapshot through stream completion, including during source-cursor closure.
