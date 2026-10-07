# Retained matcher results

The registered `ctk.match.v1.MatchService` exposes unary `Match` and
`CloseSession` alongside the existing streaming query service. The v1
`session_id` identifies one result cursor, not a project or transport channel.
A file query acquires an independent cursor and an immutable cached AST
generation. Whole-tree restarts and binding continuations reuse that generation.
Changing source or compiler flags requires another file query.

Each successful replacement, including zero matches, increments
`result_revision`. An optional positive `expected_result_revision` rejects
stale work with `ABORTED`. Invalid queries, cancellation before commit and
resource failures preserve both the previous semantic rows and native bindings.
Results own their typed protobuf values and remain readable after closure.

Continuation selects the named binding from all latest result rows, or the
optional zero-based `match_index` (presence matters for row zero). Each selected
row runs independently; overlaps retain multiplicity and each emitted row
carries `source_match_index`. Previous bindings are not implicitly inherited.
Missing bindings and rows return `NOT_FOUND`. The default `SUBTREE` supports
Decl/Stmt roots and Decl/Stmt matchers, including cross-category searches.
`ROOT_ONLY` matches one selected candidate; native Type/QualType bindings also
support that scope. Unsupported scope combinations return `FAILED_PRECONDITION`.
Successful native callbacks without explicit bindings remain empty result rows.

Both traversal policies use Clang's native matcher traversal. Subtree filters
restrict candidate ancestry while relationship predicates see the full AST.
The current implementation traverses the pinned tree once per selected source
row, so workloads with many selected roots can be expensive.

```python
from clang_toolkit import Client

client = Client(address="unix:///tmp/ctk.sock")
first = client.match_file("example.cc", 'functionDecl().bind("f")',
                          working_directory="/absolute/project",
                          compile_arguments=["-std=c++23"])
calls = client.continue_match(first.session_id, "f", 'callExpr().bind("call")',
                               expected_result_revision=first.result_revision)
client.close_match(calls.session_id)
```

The same methods are available asynchronously on `AsyncClient`. RPC failures
raise `CursorError` with the gRPC status name and message.

```text
cursor open "example.cc" functionDecl().bind("f")
cursor continue "<uuid>" "f" callExpr().bind("call") row 0 scope subtree revision 1
cursor restart "<uuid>" integerLiteral().bind("value") revision 2
cursor close "<uuid>"
```

The formal Lark commands use the session working directory, configured
`extra_args` and traversal mode, and print the typed response as protobuf JSON.

Cursors are scoped to a verified transport identity when present; the current
insecure server serves one local user. Caller-supplied request metadata cannot
select another owner. Closing an unknown valid UUID is idempotent. Successful
queries refresh a five-minute idle deadline; expired cursors are rejected and
reclaimed on subsequent requests. Closing waits for the cursor's active
operation and releases retained state.

The bounded executor and registry enforce cursor count, estimated retained
memory, row count and the complete serialized response size. Snapshot estimates
are counted once per unique snapshot within this registry. Defaults are 100
cursors, 2 GiB estimated retained memory, 100,000 rows, and 64 MiB per response.
The response budget follows a positive `server.grpc.max_send_message_bytes`;
configure `client.grpc.max_receive_message_bytes` to receive responses of that size.
These cursor budgets are independent of the streaming
query controller's existing analysis-session budgets; they do not constitute
one combined process-memory cap. Native parsing/traversal cancellation is
cooperative, and publication has a final cancellation checkpoint.

Native and application tests cover owned results, cross-category scope,
overlap, empty rows, row zero, atomic revisions, stale guards, final-boundary
cancellation, count/memory/wire limits, concurrent updates, closure, expiry,
pinned generations and native traversal parity. Python and BDD tests exercise
the API and formal CLI over Unix and TCP transports.
