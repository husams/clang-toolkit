# Reasoning gap improvements — 2026-10-09

Baseline: clean `60180b798ce2e1f49d055fed7e57c231bfde041e`.
Plan: `/Users/husam/workspace/wiki/pages/planning/clang-toolkit-reasoning-gap-improvements.md`.

| Story | Status | Verification |
|---|---|---|
| S1 Selected lambda roots | Complete | Native regressions and independent lambda-root/whole-function probes. |
| S2 Match provenance, identity, documentation and static call facts | Complete | Native/BDD metadata, overload identity, macro coordinates and lexical caller extraction. |
| S3 Native aggregate and detached collections | Complete | Path/list/tree provenance, two-file continuation, mixed bindings, cleanup and snapshots. |
| S4 Safe fields and parent joins | Complete | Availability states/defaults and dynamic source-file/local-parent-index joins. |
| S5 Collection reshaping | Complete | Stable unique, numeric/lexical sort, filter and grouped expression counts. |
| S6 Batch execution and completion safeguards | Complete | Nonterminal/-e/script execution, local-only batches, correlated session completion, bounded tracking and EOF/error status. |
| S7 Composable shallow graphs and scope | Complete | Native/Python/BDD graphs, projection validation and header-boundary probes. |
| S8 Recipes, coverage and full gates | Complete | All full suites and schema/serializer gates pass; 45 documented statements parse. |

## Final validation

| Gate | Verified result |
|---|---|
| Native configure/build | dev preset succeeds; generated API and native server rebuilt. |
| Full C++ suite | 289 tests from 33 suites pass in one process with isolated storage; same 289 tests as the CTest inventory. |
| Full Python unit suite | 584 pass. |
| Full E2E BDD suite | 74 pass, including four new reasoning scenarios. The final tracker refinement is additionally verified by the real session BDD. |
| API schema | 256 protos compile; typed payload, presence, stable-tag and no-native-handle gates pass. |
| Serializer coverage | 251 concrete serializers and 923 extraction paths validated. |
| Recipes and whitespace | 45 console statements parse, generated reference is synchronized, git diff --check passes. |

The native full suite ran through `build/dev/server/tests/ctk_tests`; a duplicate
CTest per-test run was stopped after the complete native suite passed. Validation
used macOS/Homebrew LLVM and private servers/storage. RHEL packaging was not run.
The final small streaming-tracker refinement was tested with the full Python
suite and a real session BDD after the successful full BDD run.

## Verified independent observations

- Selected lambda call-operator continuation finds one call, attributed to the
  lambda; whole-function matching does not duplicate it.
- Path and singleton-list counts agree: 15 in AsIs mode and 7 source-spelled.
- The fixture traversal preserves eight nodes while reducing protobuf payload
  from 146,990 bytes recursive to 4,270 bytes shallow. The call graph preserves
  nine nodes/14 edges while reducing 11,787 bytes to 2,479 bytes.
- Main-file call graphs expose four omitted external edges; header CFG lookup
  is excluded only when main-file scope is requested.
- A 4,200-character local batch completes in 0.557 seconds; an invalid variable
  exits 1, and successful text beginning `error:` exits 0.
- Twelve repository application files yield scalar summaries under the default
  2 GiB budget through per-file scoped blocks. A retained 12-file aggregate
  exceeds that budget; an explicit private 8 GiB configuration yields 116
  functions and 116 distinct USRs. This remains a configured resource boundary.
- A 101-file list is rejected at the configured 100-file limit; a subsequent
  single-file query succeeds in the same continue-on-error batch.

Recipes and explicit boundaries for every Claude G1-G12 are documented in
[reasoning-gaps.md](reasoning-gaps.md).

## Boundaries

The implementation does not add arbitrary field masks/predicates, a materialization-free
count API, implicit parent binding copies, partial publication on resource
exhaustion, a persistent whole-program reference index, exhaustive includes/macro
history or resolved dynamic dispatch. The coverage matrix records the working
alternative or explicit boundary for each historical gap. Default graph builders
are shallow; old raw protobuf requests without projection remain recursive.

No commits, publication or shared-server restart performed.
