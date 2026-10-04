# Clang C++ semantic protobuf API

This is the versioned interface directory for clang-toolkit, shared by the server, interactive CLI, Python API and one-shot CLI. The initial operations remain `open_project`, `match` (AST matchers), `traverse`, `cfg`, `callgraph`, `run_script` and `cache_stats`. The server transport is gRPC over a Unix domain socket locally and TLS remotely. The definitions below use package `ctk.ast.v1`; this migration changes only the unreleased draft package and build integration.

The contract returns directly usable names, qualified names, types, signatures, constants, operators, arguments, initializers, bodies, members and constraints. Opaque node IDs, lookup tables, snapshot handles, source locations and TypeLoc contracts have been removed. This replaces the unreleased graph draft and is incompatible with that draft's changed field types.

| File | Contents |
| --- | --- |
| `ast/v1/common.proto` | Qualifiers, semantic flags, availability and shared enums. |
| `ast/v1/operators.proto` | Cast, binary, unary and overloaded-operator enums. |
| `ast/v1/semantic.proto` | 251 named concrete payloads, shared semantic information, exact values, names, templates and recursive value wrappers. |
| `ast/v1/node.proto` | `AstNode` union and `SemanticResult` batch, generated from the tag registry. |

Coverage is 66 declarations, 29 statements, 104 expressions and 52 types. The previous 51 TypeLoc payloads describe source occurrences and were removed. `catalog.json` retains the LLVM 22.1.8 scope/evidence inventory. Attributes and further implementation subclasses require an audit; the server and Clang serializer remain subsequent work.

## Direct values

Owned children are embedded in `DeclarationValue`, `ExpressionValue`, `StatementValue` and `TypeValue`. Call arguments contain expression payloads, function bodies contain statements, and `QualType.type` contains the type value with separate qualifiers. No node lookup is needed to read a result.

A referenced declaration is a finite `DeclarationSymbol` containing its name, qualified name, kind, type and applicable function signature. Overloaded functions and methods carry parameter/return types, qualifiers, calling convention and exception information. Symbols do not recursively expand another definition's body or members. Symbol type/signature descriptions contain normalized type names and qualifiers rather than full AST values; template arguments and constraints have finite descriptions. Named record types therefore remain finite.

Mutually recursive declarations, expressions and types share `semantic.proto` to avoid circular protobuf imports. Constants preserve widths, signedness, floating semantics and exact bits. Optional decimal strings are convenient numeric representations; raw bits remain authoritative for precision and NaN payloads. Bytes are little-endian, have length `ceil(bit_width/8)`, and unused high bits are zero.

Scalar presence distinguishes absence from false/zero. Availability uses response field paths. A serializer must bound expansion and explicitly report truncation; it must never substitute an opaque handle. `NullStmt`, `BreakStmt`, `ContinueStmt` and `SEHLeaveStmt` are unit variants whose kind supplies the control-flow meaning. Attribute arguments without typed contracts are explicitly unavailable. Semantic descriptions preserve meaning and values; they do not preserve AST object or evaluator allocation identity. Constant structures include base types and named fields rather than unlabeled value arrays.

The [function example](examples/semantic_function.json) is a validated contract fixture with parameter names/types and a returned expression; it is not a claim of Clang extraction. `check.py` refreshes this fixture from its validated protobuf message before checking the round trip, so the saved fixture retains its semantic content.

## Check and build

```sh
uv run python api/check.py
```

The checker requires `protoc` and Python's `google.protobuf`; `protobuf>=6` is included in the toolkit development dependency group. Checks cover catalog/tag/union coverage, absence of handles/source contracts, self-contained semantic values, presence, exact bits, ordering, template packs and unknown binary variants.

Build the opt-in static API library from the toolkit root:

```sh
cmake --preset dev -DCTK_BUILD_APIS=ON
cmake --build --preset dev --target ctk_ast_api
```

Generated bindings and descriptors stay in `build/dev/api/generated`. `CTK_BUILD_APIS` defaults to `OFF`; this target only builds the schema library and does not implement server operations or link it into the server.

`node_tags.json` owns protobuf payload field tags, not AST object identifiers. Surviving tags remain fixed; removed TypeLoc names/numbers are reserved. Regenerate or check the generated union with `uv run python api/generate_nodes.py` and `uv run python api/generate_nodes.py --check`.

See the [design Page](https://chatgpt.com/space/page_4b91284d97d88191a4fe1463e732cc17) and [catalog Page](https://chatgpt.com/space/page_9ad19ee5b3bc8191a754557451c0e565) for the reviewed design and node inventory. Update both alongside intentional contract changes.
