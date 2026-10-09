# Python SDK parity, typed matchers and reasoning skill

Baseline: clean `main` at `84e4627` on 2026-10-09. Existing wiki console guidance is the historical checklist; current APIs and executed tests determine coverage.

| Story | Status | Verification |
|---|---|---|
| S1 Console-to-SDK feature audit | Complete | [Coverage matrix](python-sdk-console-coverage.md) distinguishes direct APIs, single-expression bridge, gaps and terminal features. |
| S2 Immutable typed matcher composition | Complete | String compatibility; sync/async query, cursor and retained APIs; native Unicode/string-label and scalar semantics; typing contract. |
| S3 Self-contained Python reasoning skill | Complete | All executable reference examples pass on a private native server; schema validation passes; installed in `$HOME/.codex/skills/ctk-cpp-reasoning/`. |
| S4 Portable uv skill deployment | Complete | Default, custom, nested and repeated setup pass; shipped SDK imports and native queries pass; independent SDK-only validation confirms the revised workflows. |
| S5 Address demonstrated semantic and coverage limits | Complete | Typed base-specifier bindings, explicit native availability, positive SDK fixtures and revised references pass; all 1,031 native/unit/E2E tests and the independent skill-only retest pass. |

## Acceptance

- Report console coverage and actual public SDK gaps explicitly.
- Compose matcher objects, serialize safely, and pass them directly to public SDK APIs.
- Skill users use the bundled installed uv project by default, with an optional opaque `CTK_SDK_PROJECT` override; use public APIs and bundled references without source/configuration discovery.
- Run all C++ tests, Python unit tests and E2E scenarios before completion, with isolated native storage.

## Initial verification

| Gate | Result |
|---|---|
| Native configure/build | dev preset succeeds, including serializer coverage gate. |
| Complete C++ GoogleTest suite | 289/289 pass with private storage and local socket access. Initial sandbox-only run blocked six socket binds; unrestricted local run passes. |
| Complete Python unit suite | 654/654 pass after literal-encoding corrections. |
| Complete E2E suite | 80/80 pass in 293.24 seconds, including typed matcher BDD and all executable skill references; isolated native servers and local socket access. |
| SDK typing consumer | Pyright: 0 errors, 0 warnings. |
| New native typed matcher BDD | Passes sync/async string parity, retained continuation, parsed tree and selected binding APIs, Unicode, exact quote/backslash/newline labels, and integer/float/bool predicates. |
| Skill schema validator | Passes. |
| Native SDK recipe execution | Every runnable Python fence in the recipe, semantic-value and API references executes against a private server, including async ownership and graph/base/call-site queries. |
| Whitespace | `git diff --check` passes. |

Native matcher string tokens preserve contents literally. The builder selects
an absent single/double quote delimiter and rejects strings containing both
delimiters, rather than silently introducing JSON escape characters. Native
semantic validation remains authoritative for matcher names, argument arity,
and AST category compatibility. Those initial matcher changes did not alter the
wire contract or server operations.

The initial reference tests used the local SDK with a private endpoint; the
configured installed project was intentionally not inspected or searched. No
shared-server restart or publication was involved.

Independent final review found no remaining actionable issue. The installed
skill also passes the skill schema validator. All 1,023 native/unit/E2E tests
pass; E2E reports existing pytest-bdd fixture deprecation warnings. Validation
is macOS/Homebrew LLVM, without a separate RHEL packaging run.

## Portable skill deployment

The independent tester's initial launcher failed before Python because the
required `--project` argument had no usable value. The updated skill instead
includes a bundled SDK wheel, a portable uv project and a dependency lock.
`scripts/setup.sh [destination]` deploys the packaged skill files, installs
managed Python 3.14 through uv and prepares the destination's SDK environment.
The reasoning agent launches `scripts/python.sh` from its loaded skill directory.
Missing and empty `CTK_SDK_PROJECT` values use that directory's project; a
nonempty override stays opaque. Runtime probes do not install packages.

| Deployment check | Result |
|---|---|
| Default deployment | Setup installs the packaged skill and SDK into `$HOME/.codex/skills/ctk-cpp-reasoning/`; public sync/async clients and typed matcher imports pass. |
| Custom destination | Fresh deployment into a temporary directory containing a space succeeds; the launcher selects its own SDK environment from a different working directory. |
| Project selection | Missing and empty overrides use the bundled project; an explicit installed-project override uses the expected environment. All four launcher probes pass. |
| Repeated setup | In-place setup and redeployment succeed; an unrelated destination file is preserved, and setup validates its destination even when the runtime override points elsewhere. |
| Nested destination | Review caught recursion when deploying within a copied source directory; pruning the canonical destination fixes it. Real setup and SDK launch in a nested directory pass. |
| Deployed SDK native query | The default installed wheel queries 41 main-file function definitions in `server/src/application/match_controller.cpp` through typed public APIs and the project's compilation database. |
| Streaming callback documentation | Tester exposed ambiguity about callback rows. The references now specify detached `ctk.match.v1.MatchResult` protobufs, label-map binding access and semantic result-row helpers separately; the new executable callback example passes natively. |
| Type continuation documentation | Tester reproduced default subtree scope rejection for QualType. The existing public `binding(..., scope=1)` option selects native root-only scope; a real QualType continuation and the new reference example pass. No SDK or server change is needed. |
| Updated reference examples | Both `uv run python -m pytest` and `uv run pytest` pass the skill example test against a private native server. Its test-module import was corrected for standalone pytest collection. |
| Packaging and schema | Source and installed skill schema validation pass; shell syntax and whitespace checks pass. |

Deployment-script review confirms the nested-directory fix and finds no remaining
actionable installer or launcher defect.

The independent tester completed its SDK-only C++ reasoning matrix against the
installed default environment and a supplied isolated server/compilation database.
The [validation summary](validation/sdk-reasoning-skill.md) confirms the
revised callback and root-scope workflows, retained lifetimes, sync/async behavior,
provenance, CFG selection and graph bounds. No SDK implementation bug was
demonstrated in those workflows. That initial validation identified direct `CXXBaseSpecifier`
semantic payloads as a native limitation and left positive documentation,
template/availability examples untested. Whole-program/runtime-target claims
remain outside the static APIs. The original private server was stopped after
validation.

## Addressing the demonstrated limits

`MatchBinding.base_specifier = 12` adds a typed auxiliary value without changing
core `AstNode` tags or introducing an RPC. The dedicated serializer copies type,
effective access, virtualness and pack-expansion facts. Base specifications have
no native continuation scope; bind their related record declaration for member
queries. Source/range metadata survives the real MatchService transport.

Selected top-level native fields now produce PRESENT, SEMANTICALLY_ABSENT and
INAPPLICABLE metadata. A declaration without its own body differs from a shallow,
unrequested definition body; returned recursive typed bodies are PRESENT while
descendant unavailability and truncation remain explicit. PRESENT does not imply
complete descendants. Producer classifications are limited to the top-level
binding because aggregate descriptor paths do not identify individual nested
instances. Existing unavailability and budget reporting retains precedence.

The positive SDK BDD scenario passes against a private native server with both
clients: attached documentation, template primary/arguments, written/canonical
alias types, direct base facts and metadata, implicit-destructor option effects,
explicit availability and budget truncation. The updated installed SDK also
passes a retained typed-base query. TypeScript regeneration exposed a stale
boundary schema; the decoder now retains copied metadata and the new value, with
a real protobuf round-trip test. Its build, type checks, lint and 52 unit tests
pass; 24 opt-in integration tests remain skipped.

All 296 native tests pass in four GoogleTest shards with independent storage
roots; all 654 Python unit tests and SDK consumer typing checks pass. The complete
E2E suite passes 81/81 in 344.11 seconds, including all runnable skill examples
and the new positive scenario. It reports existing pytest-bdd fixture warnings.
The updated API contract check, source serializer gate, source/installed skill
schema validation and whitespace checks pass. All 12 packaged skill files match
the installed copies. The [independent skill-only retest](validation/sdk-reasoning-skill.md)
passes every requested regression with zero unexpected SDK/semantic failures.
It verifies effective public/private and pack bases, documentation, template and
alias facts, destructor effects, body presence versus completeness, budget
truncation, detached callbacks and both native Type/QualType continuation paths.
The tester's final Type-branch wording clarification was applied, deployed and
independently verified. Static runtime/cross-TU boundaries and intentionally
unsupported continuation scopes remain explicit. The private validation server
was stopped after testing.
The full E2E suite uses `uv run python -m pytest`: the standalone pytest
entry point cannot resolve several existing `tests.e2e` namespace imports.
