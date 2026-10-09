# Limits and reporting

## Resource limits and result lifetime

Retained match values own native cursor state and semantic rows. Keep scopes short, close results promptly, and query one file or a small batch first. Iteration and indexing load rows on demand; `.rows` materializes the full tuple. Copy only the scalar or protobuf facts needed for a summary before closing the result. Multi-file work may retain a separate native snapshot per file, so a result that fits one translation unit may exceed the configured session budget across many files. Use sequential per-file contexts for scalar summaries and preserve source path with each copied fact.

Traversal, CFG, and call-graph operations have configurable node/edge/block/element and response-byte limits. Semantic child expansion has separate payload depth/node bounds. Projection depth, graph structure bounds, and retained-result memory limits are different controls. Start shallow and bounded; request more only for a specific question. Graph `main_file_only` defaults to false, so set it explicitly when the question is limited to the main file. Limit failures are errors and do not return a trustworthy complete partial graph. A depth-limited traversal reports `depth_limited`; graph responses expose completeness and availability metadata.

## Evidence and completeness

In the answer, state what was queried (file/TU scope, matcher constraints, selected compilation database/flags if known), the returned count, and any relevant availability or limit state. Attribute statements to observed protobuf values. Mark a conclusion as an inference when it combines observations. If a query returns zero rows, say only that this matcher returned zero for the selected translation unit and traversal policy; do not generalize to the whole project unless every relevant file/configuration was covered.

When an SDK call fails, include its error class/status and the attempted operation. Do not turn a matcher construction, parse, compilation, transport, or resource error into a negative code finding. Reformulate one query at a time and keep the error visible when the evidence gap remains.

Direct `CXXBaseSpecifier` bindings use `MatchBinding.base_specifier`, with immediate
type, effective access, virtualness and pack-expansion facts. They advertise no
continuation scope. Bind the related base declaration through its type to query
its members. Other unsupported native values still require an explicit coverage
report; an unavailable payload is not evidence that a construct is absent.

Public errors are importable from `clang_toolkit`: `CursorError` for parse and
retained matcher RPCs, `AnalysisError` for graph/native-script RPCs, `QueryError`
for query event streams, `MatchValueError` for invalid/expired value use, and
`ConfigurationError` for SDK configuration failures. Cursor and analysis errors
expose `.code` with the gRPC status. `QueryError` exposes `.partial_events` and
`.violations`; partial events are not a completed answer. Invalid typed matcher
construction/serialization raises `TypeError` or `ValueError`.

For current server state, use `client.server_status()` and inspect its returned
protobuf, without searching configuration files. `client.list_sessions()` lists
native sessions. Close the values created by the current script; broad cache
pruning is not required for a reasoning query.

## Static call coverage boundaries

`call_site.dispatch` classifies each matched call expression as direct, indirect, or virtual. A direct site has a statically selected non-virtual declaration (explicitly qualified virtual calls are direct). An indirect site has no selected callee. A virtual site records the statically selected virtual declaration; it does not resolve dynamic dispatch targets. Query all call sites before reporting filtered target coverage.

The native Clang call graph records native call edges and multiplicity, but performs no alias analysis, devirtualization, cross-translation-unit resolution, or runtime tracing. Unresolved function-pointer calls do not gain invented targets. Root edges represent native graph structure, not execution by an external caller. Do not claim whole-program caller coverage from a single-TU graph. When reporting caller results, state whether they are direct matches, native graph edges, or structural call-site facts, and list indirect/virtual/omitted scope separately.

Likewise, AST traversal is a native visitor rather than a matcher query; its implicit-code and template-instantiation flags are distinct from matcher traversal mode. A graph limited to main-file declarations may omit header candidates and reports that scope. Comments, macro history, cross-translation-unit references, and runtime behavior require evidence beyond these APIs.
