# Native semantic serialization

The implementation owns 251 dedicated source/header pairs under
`server/src/clang/serialization/{decl,stmt,expr,type}/`: 66 declarations,
29 statements, 104 expressions and 52 types. Dispatch and catalog registration
are separate from concrete field extraction. Shared helpers cover inheritance
metadata, finite symbols, names/templates, qualifiers and exact constants.

The strict AST contract uses concrete typed recursive oneofs. Dedicated proto
source files are assembled for compilation to avoid import cycles; public-import
facades retain existing C++ include and Python module paths. See
[the draft migration](../api/README.md#draft-contract-migration-6-october-2026)
for reserved Any fields, descriptor ownership and necessary draft migrations.

`check_node_serializer_coverage.py` checks catalog/payload mapping, dedicated
classes/source definitions and 923 direct payload field extraction or explicit
availability paths. This is source evidence. It does not assert that every rare
node or every field combination has been produced by a runtime fixture.

Native fixture evidence is kept in the test suites:

| Family / behavior | Evidence |
| --- | --- |
| Declarations | `server/tests/test_declaration_semantics.cpp`: definitions, parameters/defaults/bodies, bases/members, constructors/initializers, templates/specializations, concepts, namespaces/aliases, blocks, labels and attributes. |
| Expressions | `server/tests/test_expression_semantics.cpp`: derived calls, operators, exact signed constants/floats/strings, casts/construction, lambda captures, constraints, type traits and child presence. |
| Types | `server/tests/test_type_semantics.cpp`: bound qualified types, exact qualifiers, arrays, function/member-pointer signatures, template arguments/substitution, vectors, bit widths, decltype and dependent arrays. |
| Statements and ownership | `server/tests/test_statement_semantics.cpp`: branches/loops/cases/handlers, finite goto symbols, owned wire round trips, duplicate/empty rows, truncation and structural constant field indexing. |
| Auxiliary base specifications | `server/tests/test_base_specifier_semantics.cpp`: directly bound typed bases, effective/default access, virtualness, pack expansion and shallow completeness. |
| Explicit availability | `server/tests/test_availability_states.cpp`: native function definition/body states, template-alias applicability and expansion-budget precedence. |
| Transport | `tests/e2e/features/network.feature`: complete typed initializer and exact type survive a native server/Python client round trip. |

The caller pins the native AST and holds its execution lane during all getters
and serialization. Results copy protobuf data and survive destruction of the
query engine. Exact native dispatch preserves derived expressions and canonical
dependent type subclasses. Bound `QualType` values retain their qualifiers.

Owned expansion defaults to 24 levels and 10,000 semantic values. Repeated
children are checked before allocating protobuf slots. Exceeding a limit records
`FIELD_STATE_TRUNCATED`; the result and containing owned values become incomplete.
Each root binding starts independent completeness/accounting. Symbols describe
referenced declarations without expanding their bodies or members.

Selected top-level fields have explicit positive and semantic-absence metadata:
function definition flags are PRESENT (including false), an unowned function
body is SEMANTICALLY_ABSENT, and non-alias template-specialization `aliased_type`
is INAPPLICABLE. Returned recursive function bodies are PRESENT even when their
descendants are unavailable or truncated; shallow bodies remain UNREQUESTED.
Presence and `is_complete` are independent. These states come from native getters,
not protobuf absence.
Field paths identify message fields rather than individual recursive occurrences;
query nested values directly to establish their own semantic state.

Some draft fields cannot be obtained from the native object or represented by the
current typed schema. They have explicit field paths/reasons and remain absent;
results that require them report `is_complete=false`. Examples:

- Attribute arguments have no typed attribute-specific contract. Identification
  is retained, with unavailable argument semantics explicitly reported.
- ReturnStmt has no separate coroutine return-object initializer or noreturn
  property; LabelStmt has no GNU asm-label flag.
- RecoveryExpr does not retain candidate declarations/overload state; inherited
  constructor initialization does not expose the constructing constructor.
- Runtime coroutine readiness, `this` capture origin, unconditional dynamic-cast
  success, and a temporary binding rank are not retained as these draft fields.
- Dependent or unevaluated values preserve absent evaluation results rather than
  fabricating constants. Descriptions retain dependence and available children.
- LLVM 21 retains ElaboratedType outside the LLVM 22 catalog, and lacks some newer
  qualified type node APIs. These native/version limitations are explicit.

Unsupported native values report UnsupportedValue and advertise no continuation
scope. Declaration/statement bindings advertise root/subtree scopes; types and
qualified types advertise root scope. No AST pointers, opaque node identifiers or
source-location payloads cross the public boundary.

Directly bound `CXXBaseSpecifier` values use `MatchBinding.base_specifier`, outside
the core `AstNode` catalog. Their copied type description, effective access,
virtualness and pack-expansion flags are available without expanding the base
record. They advertise no continuation scope; match through the base's type to
bind its declaration when a follow-up declaration query is needed.

Native API evidence comes from the installed LLVM 22.1.8 headers and the tested
LLVM 21 compiler. Structural/lvalue constant indexing follows the official
[APValue implementation](https://github.com/llvm/llvm-project/blob/llvmorg-22.1.8/clang/lib/AST/APValue.cpp)
and [constant evaluator](https://github.com/llvm/llvm-project/blob/llvmorg-22.1.8/clang/lib/AST/ExprConstant.cpp).

Current validation results and unresolved work are tracked in
[query-engine-progress.md](../query-engine-progress.md).
