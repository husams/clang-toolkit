# Python SDK reasoning skill validation

Validated on 2026-10-09 with macOS/Homebrew LLVM against isolated native servers.
The independent tester used the installed skill's launcher, bundled references
and public Python APIs. It did not read target C++, SDK source, configuration,
environment files or filesystem source inventories. Every requested regression
passed, with zero unexpected SDK or semantic failures.

The positive fixture contained documented declarations, class-template
specializations and aliases, public virtual/private/dependent-pack bases, an
automatic destructor and functions with ordinary and nested lambda bodies.
Queries supplied that fixture's path and `compile_arguments=['-std=c++20']`.
No compilation database was supplied or read for these fixture checks.

| Check | Observed result |
|---|---|
| Direct base specifications | Three typed `base_specifier` rows preserve effective access, virtualness, pack expansion, type descriptions and valid source metadata; completeness is true and continuation scopes are empty. |
| Related base declaration | Bind the record through the base type; retained member queries survive parent-result closure. |
| Attached documentation | The documented declaration returns its nonempty attached raw documentation. |
| Class-template relationships | Both concrete specializations identify the primary template and preserve typed recursive arguments. |
| Alias spelling | Written `Count &` and canonical `const int &` are distinct and preserved. |
| Template-type applicability | Non-alias types have a present false `has_alias` flag and INAPPLICABLE alias child; an alias has a PRESENT child. |
| Implicit destructors | Enabling the option adds exactly one automatic-object destructor for the fixture variable; disabling it removes that element. |
| Definition flags | A declaration's false definition flag is physically present and explicitly PRESENT. |
| Function body states | Non-owning declarations are SEMANTICALLY_ABSENT; shallow owning bodies are UNREQUESTED; returned recursive typed bodies are PRESENT. |
| Presence versus completeness | Bodies with unavailable descendants remain PRESENT and incomplete; complete control fixtures remain PRESENT and complete. |
| Payload budgets | Small depth/node budgets leave body stubs without a typed payload, report TRUNCATED and preserve incomplete results. |
| Streaming callbacks | Detached protobufs match returned semantic rows, survive cleanup and preserve continuation provenance. |
| Type/QualType continuations | Explicit root-only selection works through both public entry points and after parent-result cleanup; default subtree selection returns the expected rejection. |
| Sync/async parity | Copied bindings, continuations and CFG responses agree. |
| Cleanup | Public session listing reports zero retained native sessions after all validator contexts close. |

The tester also verified the final branch-specific reference wording: QualType
facts use `qualified_type.description`; native Type values use their selected
`node` payload. The direct template-specialization matcher recipe resolved an
initial instruction gap.

Additional pack instantiations, differing macro coordinates, written-access
syntax and runtime/cross-translation-unit/whole-project coverage were outside
this fixture's tested scope. Auxiliary bases have no independent continuation;
Type/QualType subtree continuation is unsupported. Two ReturnStmt properties
remain explicitly UNAVAILABLE because Clang exposes neither a separate
coroutine return-object initializer on ReturnStmt nor a ReturnStmt noreturn flag.
PRESENT describes a returned typed field and does not imply complete descendants.

Automated evidence lives in the repository:

- [Positive SDK BDD fixture](../../tests/e2e/test_sdk_reasoning_coverage.py).
- [Executable skill reference examples](../../tests/e2e/test_sdk_skill_examples.py).
- [Native base semantics](../../server/tests/test_base_specifier_semantics.cpp).
- [Native availability states](../../server/tests/test_availability_states.cpp).
- [Current gates and deployment checks](../sdk-agent-progress.md).

Final gates: 296 native tests, 654 Python unit tests and 81 E2E tests pass;
52 TypeScript unit tests pass with 24 opt-in integration tests skipped. SDK typing,
API/schema and serializer checks, skill validation and whitespace checks pass.
The separate RHEL packaging run was not performed for this change.
