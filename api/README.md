# Clang C++ semantic protobuf API

This is the versioned interface directory for clang-toolkit, shared by the server, interactive CLI, Python API and one-shot CLI. The initial operations remain `open_project`, `match` (AST matchers), `traverse`, `cfg`, `callgraph`, `run_script` and `cache_stats`. The server transport is gRPC over a Unix domain socket locally and TLS remotely. The definitions below use package `ctk.ast.v1`; this migration changes only the unreleased draft package and build integration.

`ctk.match.v1.MatchService` now implements retained file queries, guarded
whole-tree restarts, binding continuations and idempotent `CloseSession`; see
[result cursor semantics](../docs/result-cursors.md). Its existing v1 field
numbers and typed matcher-result contract are preserved.

`ctk.analysis.v1.AnalysisService.Traverse` returns owned declaration/statement
occurrences with preorder parent structure and native visitor options; see
[standalone traversal](../docs/ast-traversal.md). Each traversal message has
its own source schema under `analysis/v1/`.

The contract returns directly usable names, qualified names, types, signatures, constants, operators, arguments, initializers, bodies, members and constraints. Opaque node IDs, lookup tables, snapshot handles, source locations and TypeLoc contracts have been removed. This replaces the unreleased graph draft and is incompatible with that draft's changed field types.

| File | Contents |
| --- | --- |
| `ast/v1/common.proto` | Qualifiers, semantic flags, availability and shared enums. |
| `ast/v1/operators.proto` | Cast, binary, unary and overloaded-operator enums. |
| `ast/v1/<node>.proto` | One source schema for each of the 251 named concrete payloads. |
| `ast/v1/semantic_types.proto` | Shared semantic information, exact values, names, templates and typed recursive wrappers. |
| `ast/v1/semantic.proto` | Source-schema umbrella; replaced by the assembled recursive compilation unit during generation. |
| `ast/v1/node.proto` | `AstNode` union and `SemanticResult` batch, generated from the tag registry. |

Coverage is 66 declarations, 29 statements, 104 expressions and 52 types. Each catalog node now has a dedicated native serializer header/source under `server/src/clang/serialization/<family>/`; dispatch and shared semantic helpers remain separate. `scripts/check_node_serializer_coverage.py` checks the concrete mappings and field extraction/availability paths; native declaration, expression, statement and type fixtures validate semantic values through the query engine. The source gate alone does not establish runtime completeness. The previous 51 TypeLoc payloads describe source occurrences and were removed. `catalog.json` retains the LLVM 22.1.8 scope/evidence inventory. Attribute arguments lack a typed contract and are reported unavailable; types introduced after the installed Clang version and older native type qualifiers can also be explicitly unavailable. Expansion limits produce explicit truncation. Further implementation subclasses remain outside the catalog pending an audit.

## Direct values

Match results serialize each bound node's immediate fields and inherited same-node metadata. They do not expand function bodies, parameter declarations, initializers, operands, record members or nested type nodes. These child fields carry `FIELD_STATE_UNREQUESTED`; an intentionally omitted child does not make `MatchBinding.is_complete` false. Native binding continuation remains available to match those nodes separately. Explicitly binding a child in the original matcher also returns that child's immediate fields.

A `QualType` carries `description` with spelling, canonical spelling, qualifiers and dependence, plus its direct qualifiers. Its recursive `type` value is unrequested in shallow results. Referenced declarations retain concise symbols with their names, kinds and type descriptions; referenced signatures and template expansions are omitted. The recursive wrappers remain in the schema for compatibility and internal serializer fixtures, but public matching uses the shallow projection.

Each concrete node stays maintained in its dedicated source schema. `assemble_ast.py` places the mutually recursive definitions and helpers in the generated `semantic.proto` compilation unit, then emits public-import facades at the original paths. This permits typed recursion without cyclic imports. C++ include paths and Python module imports remain available; reflection descriptors for the concrete messages now report `ast/v1/semantic.proto`. `catalog.json` records the dedicated source paths, and the checker verifies that every source defines exactly its one catalog node. [Protobuf public imports](https://protobuf.dev/programming-guides/proto3/#importing-definitions) provide the forwarding mechanism.

Constants preserve widths, signedness, floating semantics and exact bits. Optional decimal strings are convenient numeric representations; raw bits remain authoritative for precision and NaN payloads. Bytes are little-endian, have length `ceil(bit_width/8)`, and unused high bits are zero.

## Draft contract migration (6 October 2026)

The intermediate split used `google.protobuf.Any node = 2` for owned children and reserved the original typed discriminators. That draft failed the semantic contract checker. The four owned-value wrappers now expose concrete `payload` oneof cases with the stable tags from `node_tags.json`; `is_complete = 1` and `StatementValue.expression = 10` remain. Removed `node = 2` is reserved. Typed draft consumers can again read `value.integer_literal` or `qualified.type.pointer_type` directly. Any-draft consumers must regenerate server and Python bindings together; their packed tag-2 values are not interpreted as typed children. Persisted Any-draft result payloads require recomputation. Native AST cache artifacts do not contain these protobuf rows.

`BindingDecl.binding = 3` now contains its actual bound expression (`ExpressionValue`) rather than a declaration symbol. This correction is incompatible with that field's draft message encoding; old BindingDecl result payloads require recomputation. `FriendTemplateDecl.template_parameters = 2` is repeated so nested template parameter lists survive; older singular consumers merge repeated messages and cannot preserve every list. `friend_type = 5` is additive. Offset components gain typed base, dependent identifier-name and index-expression alternatives; signed shuffle masks, typed substituted template arguments and type-form generic selections use new tags. Language address spaces use named `AddressSpace.language_space = 3`. Existing tags and legacy fields otherwise remain. Query operation envelopes, RPC names and streaming directions remain covered by the published contract fixture.

Scalar presence distinguishes absence from false/zero. Availability uses response field paths. A serializer must bound expansion and explicitly report truncation; it must never substitute an opaque handle. `NullStmt`, `BreakStmt`, `ContinueStmt` and `SEHLeaveStmt` are unit variants whose kind supplies the control-flow meaning. Attribute arguments without typed contracts are explicitly unavailable. Semantic descriptions preserve meaning and values; they do not preserve AST object or evaluator allocation identity. Constant structures include base types and named fields rather than unlabeled value arrays.

Direct `CXXBaseSpecifier` bindings use the additive `MatchBinding.base_specifier = 12` value branch and the existing typed base schema. They carry immediate type, effective access, virtualness and pack-expansion facts. They are auxiliary values outside the 251-node `AstNode` catalog and advertise no continuation scope.

The [function example](examples/semantic_function.json) is a validated contract fixture with parameter names/types and a returned expression; it is not a claim of Clang extraction. `check.py` refreshes this fixture from its validated protobuf message before checking the round trip, so the saved fixture retains its semantic content.

## Check and build

```sh
uv run python api/check.py
```

The checker requires `protoc` and Python's `google.protobuf`; `protobuf>=6` is included in the toolkit development dependency group. It assembles the dedicated schemas in a temporary directory before compiling. Checks cover source ownership, catalog/tag/union coverage, absence of handles/source contracts, the unchanged Any/Struct prohibition, self-contained semantic values, presence, exact bits, ordering, template packs and unknown binary variants.

Build the opt-in static API library from the toolkit root:

```sh
cmake --preset dev -DCTK_BUILD_APIS=ON
cmake --build --preset dev --target ctk_ast_api
```

Generated bindings and descriptors stay in `build/dev/api/generated`; assembled compiler inputs stay in `build/dev/api/schema`. `CTK_BUILD_APIS` defaults to `OFF`; Clang or network builds also generate and link their required contract libraries. The schema target itself implements no server operations.

`node_tags.json` owns protobuf payload field tags, not AST object identifiers. Surviving tags remain fixed; removed TypeLoc names/numbers are reserved. Regenerate or check the generated union with `uv run python api/generate_nodes.py` and `uv run python api/generate_nodes.py --check`.

See the [design Page](https://chatgpt.com/space/page_4b91284d97d88191a4fe1463e732cc17) and [catalog Page](https://chatgpt.com/space/page_9ad19ee5b3bc8191a754557451c0e565) for the reviewed design and node inventory. Update both alongside intentional contract changes.

Native CFG: `analysis/v1/AnalysisService.Cfg`, with dedicated graph/block/element
and construction-context messages; see [control-flow](../docs/control-flow.md).

Native call graphs: `analysis/v1/AnalysisService.CallGraph`; see
[call graph semantics and limits](../docs/call-graphs.md).

Server query composition: see [server scripting](../docs/server-scripting.md).

Parsed-tree and immutable result expressions: `MatchService.Parse` acquires a
zero-row tree cursor; `MatchRequest.preserve_source` creates independent results
from retained trees or bindings. See [syntax and ownership](../docs/parse-match-expressions.md),
the existing [Python API](../python/clang_toolkit/client.py), and the packaged
[TypeScript SDK](../typescript/README.md). Existing cursor replacement defaults
and streaming query commands retain their behavior.

`MatchService.StreamMatch(MatchRequest)` is an additive server-streaming RPC.
`match/v1/match_stream.proto` defines ordered row events and a single completion
with cursor identity, revision, expiry and row count. Clients require terminal OK
as well as completion before publishing a reusable value. Wire limits apply per
event. Python retained matches, TypeScript retained matches and console expressions
use this RPC; legacy unary `Match` and script responses remain compatible.

`AnalysisService.RunScript` accepts an independent `ScriptCompilationProfile`
(`ScriptRequest.profile = 4`) for explicit parse/file expressions. SDKs populate
the caller's working directory and compiler flags without requiring a default
file. Omitting this additive field preserves the legacy file-profile behavior.
Python generation includes `.pyi` message stubs so nested semantic values keep
their concrete types in installed SDK consumers.
