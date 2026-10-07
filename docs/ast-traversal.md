# Standalone AST traversal

`ctk.analysis.v1.AnalysisService.Traverse` runs Clang's `RecursiveASTVisitor`
over a validated file snapshot. It returns declaration and statement occurrences
in preorder, each with an owned typed `MatchBinding` value. Type information
is embedded in the existing semantic payloads; this operation does not emit
TypeLoc, source locations or native lookup handles.

The translation-unit record has depth zero and no parent index. Other records
refer to an earlier record in the same response and have their parent's depth
plus one. These indices describe visitor structure, not identities that can
be looked up in a later request. Native visitor occurrences are retained,
including revisits enabled by template instantiation traversal.

```python
from clang_toolkit import Client

result = Client(address="unix:///tmp/ctk.sock").traverse(
    "example.cc", working_directory="/absolute/project",
    compile_arguments=["-std=c++23"], max_depth=12,
    visit_template_instantiations=True,
)
for item in result.nodes:
    print(item.depth, item.value)
```

`AsyncClient.traverse` provides the equivalent asynchronous API. Failures raise
`AnalysisError` with the gRPC status. The formal CLI command is:

```text
traverse "example.cc" depth 12 nodes 10000 implicit false instantiations true
```

It uses the session working directory and compiler arguments and emits protobuf
JSON. A string reference or a file from `glob` can also select the file.

`visit_implicit_code` and `visit_template_instantiations` map directly to the
native visitor's options. They are distinct from AST matcher's `AS_IS` and
`IGNORE_UNLESS_SPELLED_IN_SOURCE` policies; implicit expression wrappers can
still be visited with the default visitor policy. No matcher policy equivalence
is claimed.

The default visitor depth is 64; explicit zero returns the translation-unit
record alone. The response's `depth_limited` flag identifies deliberate pruning.
The maximum configurable depth is 256. The default node count is 10,000, and
the hard maximum is 100,000. Node limits, cancellation and complete wire-size
limits return an error with no partial tree. Semantic child expansion inside
each record retains the serializer's own completeness and expansion rules;
the visitor depth limit controls the record structure.

Traversal uses the snapshot's native execution lane and the same cache engine
as retained matching in the server host. It shares a bounded operation executor with
retained matching and CFG; the streaming-query executor remains separate. The existing transport send limit
also bounds traversal responses before publication. A native snapshot stays
owned until traversal and serialization finish; the returned protobuf values
remain usable afterward.
