# SDK review and fixes

Approved scope: declarative Python/TypeScript SDK usage, shared configuration,
typed semantic values, safe result contexts, and verified native DSL semantics.
Implementation chat completed and released all edit ownership before repairs.
The review baseline was `706740f6f86bf1a62c7e8ab6ccd6153daeed33c8`; unrelated
project source matched the initial baseline. The review phase made no Git
publication changes. The scoped integration evidence below supersedes its
historical delivery status.
Baseline manifest: `/tmp/ctk-sdk-review-baseline-hk3m40if/manifest.json`.

Wiki checked first: network-yaml-configuration, result-cursors,
match-service-sessions, query-engine and interactive-runtime; these predate the
new SDK/DSL, so findings use current source and executable evidence.

## Confirmed findings

| ID | Defect | Status |
| --- | --- | --- |
| F1 | Cancelling a request cancels shared cursor cleanup and poisons later requests. | Fixed |
| F2 | A result's async context exit waits for unrelated sibling cleanup. | Fixed |
| F3 | Cross-loop context exit mutates ownership before failing. | Fixed |
| F4 | Shutdown rejects nested work belonging to an already accepted execute. | Fixed |
| F5 | Sync/async convenience return types erase owner mode; kwargs hide invalid options. | Fixed |
| F6 | Python semantic protobuf payloads become Unknown to static consumers. | Fixed |
| F7 | Settled TypeScript scope failures disappear before finish sees them. | Fixed |
| F8 | Native scripts lose SDK compilation profiles without a redundant default file. | Fixed |
| F9 | Native script root continuation accepts unsupported binding scopes as empty success. | Fixed |
| F10 | Finished TypeScript scopes retain settled promises and detached semantic row copies. | Fixed |
| F11 | Async expression return annotation excludes actual tree and scalar results. | Fixed |
| F12 | Settled Python cleanup failures produce unhandled exceptions and stop retrying on later operations. | Fixed |

Configuration lifetime and gRPC channel-option naming were corrected during
implementation and independently rechecked. Native approved-flow probes passed
all-row/index-zero selection, overlap multiplicity, empty chaining, preserved
earlier bindings, concurrent independent matches and post-block continuation.

Regression evidence is preserved under `/tmp/ctk_python_review.py`,
`/tmp/ctk_loop_review.py`, `/tmp/ctk_sdk_types_review.py`,
`/tmp/ctk_semantic_types_review.py`, `/tmp/ctk-native-review.py` and the
`ctk-ts-review-6R9YOz` temporary review directory. Sandbox socket binding was
denied; approved local-socket runs distinguish that restriction from defects.

## Verification

- [x] Focused meaningful regressions and static SDK consumer checks.
- [x] Full macOS native/Python/live console suites and Clang variants.
- [x] Rocky 9 native/Python/live suites with current source parity.
- [x] TypeScript strict/unit/integration/build and packaged consumer checks.
- [x] Runnable SDK examples, schema/serializer/boundary and diff checks.

## Current evidence

- Python focused lifecycle/profile regressions: 41 passed; valid Pyright source
  consumer: zero errors. Invalid consumer rejects misspelled keywords, invalid
  traversal types and non-string compiler arguments.
- TypeScript: 41 unit tests, strict checking, lint and build passed; 20 live Unix
  and TCP integration tests passed before the final promise-retention change,
  whose success/failure regressions are covered by the unit suite.
- macOS native: 248 passed (149 individual CTest cases plus the remaining 99 in
  one CTest-managed suite against the same rebuilt binary). The first runner
  was stopped only to avoid repeated process startup; no completed test failed.
  Coverage: `/tmp/ctk-sdk-review-native-remaining/coverage.json`; logs:
  `/tmp/ctk-sdk-review-macos-native.log` and
  `/tmp/ctk-sdk-review-macos-native-remaining.log`.
- Rocky native: 248 passed (`/tmp/ctk-sdk-review-rhel-native.log`).
- Final macOS and Rocky Python/BDD: 258 passed on each platform
  (`/tmp/ctk-sdk-review-macos-python-final.log`,
  `/tmp/ctk-sdk-review-rhel-python-final.log`). Final native/Python source parity
  verified for 1,787 files (`/tmp/ctk-sdk-review-rhel-parity-final.log`).
- No-Clang: 104 tests passed initially; five socket tests passed after rerunning
  with local socket access (109 total). Clang-only: 144 passed initially; six
  persistent-cache tests passed with a writable isolated cache (150 total).
  These initial failures reflect sandbox access, not product defects.
- Schema/serializer gates passed: 256 protobufs, 251 payloads/serializers and
  923 extraction paths. Clang/LLVM include boundary and diff checks passed.
- Native original probes preserve approved, overlapping, empty and yielded
  matching behavior; unsupported scopes now fail consistently in script and
  unary services (`/tmp/ctk-sdk-review-native-repro.log`).
- Actual TypeScript tarball passed external strict compilation and native
  declarative/profile/context cleanup under Node 24.19; Node 22 runtime was
  unavailable. Cached dependency tarballs were incomplete, so its isolated
  consumer linked existing dependencies. Details:
  `/tmp/ctk-sdk-packaged-consumer/evidence.md`.
- Actual shipped TypeScript example ran with automatically discovered YAML and
  a separate server working directory, returning two call rows; evidence:
  `/tmp/ctk-ts-example-client/evidence.md`.
- Final Python wheel was built by Hatchling, installed offline into a separate
  environment and passed valid/invalid strict consumers, real sync/async native
  scripts, profiles without a default file, binding continuations and nested
  result contexts. The shipped Python example also passed automatic YAML
  discovery. The wheel matches all 641 source-package files exactly, includes
  295 protobuf stubs and `py.typed`, and has SHA-256
  `60dd3b1e33c71deaf8b1310309227b592f2cd0aab41c41c24e874394da9f0cc1`.
  Artifact: `/tmp/ctk-sdk-consumer-validation/dist-final/clang_toolkit-0.1.0-py3-none-any.whl`;
  parity: `/tmp/ctk-sdk-review-python-wheel-parity.json`.

## Verification limits

macOS Python/runtime consumers used the project's Python 3.14.0rc2; Rocky used
stable Python 3.14.8. The separate macOS 3.14.6 installation has an existing
`pyexpat`/libexpat symbol error. Python consumer dependencies were linked from
the existing environment, while the SDK came from the actual installed wheel.
TypeScript runtime consumers used Node 24.19; unit/live tests used Node 25.9,
with Node 22 declarations for type checking. Actual Node 22 and native TLS/browser
runtimes remain unverified. No package was published.

## Final review and preservation

Independent final Python/native audits found no unresolved actionable defects.
Async value contexts await only their own cleanup; ordinary operations retry
settled failed cleanup in the background, and shutdown awaits/reports remaining
failures. Documentation describes this policy and the dynamic expression return
type accurately.

An isolated Python package helper mistakenly replaced the repository's editable
installation with an equivalent scratch wheel. The source-backed editable
installation was restored using the actual build backend; repository source and
dependencies were unchanged. Final wheel checks use a separate environment.

Source-preservation evidence:
`/tmp/ctk-sdk-review-source-preservation.json`. No unexpected source changes or
source deletions were found. A pre-existing Vim swap file,
`server/src/cache/.snapshot_cache.cpp.swp`, is now absent; its associated source
remains unchanged. The task-created pnpm cache was moved to
`/tmp/ctk-sdk-review-pnpm-store`.

## Scoped main integration (7 October 2026)

The clean integration snapshot builds on serializer commit `706740f` and includes
Parse, immutable matching forks, typed Python and TypeScript values, shared YAML
configuration, native scoped matching and the required cursor/scripting foundation.
Standalone native traversal, CFG, call graph, project facade and enhanced snapshot
cache implementations remain in the shared working tree. Their wire DTOs are
retained because ScriptValue and generated service bindings import them; the lean
service inherits generated defaults for those three standalone analysis RPCs.

Validation used the isolated candidate rather than the broader dirty checkout:

- macOS native: 219 tests passed, including the original serializers and SDK
  ownership/profile/scoped-binding regressions. Rocky 9: the same 219 passed.
- Full Python unit and live BDD suites: 230 passed on each platform (206 unit
  and 24 BDD); no skipped tests.
- Clang disabled: 108 passed. Clang-only/network disabled: 138 passed.
- TypeScript: 41 unit and 20 real Unix/TCP integration tests passed; strict
  compilation, lint and package build passed.
- Source and extracted-wheel strict Python consumers: zero errors. The invalid
  fixture reported the expected five errors. The final Hatchling wheel matches
  all 635 package files and includes py.typed and generated semantic stubs.
  SHA-256: `139fcbdf3d1efd8b3f1d518066f24ab5939862a0ae7adbde526aebab177983fc`.
- Schema/serializer gates: 256 protobufs, 251 concrete payloads/serializers and
  923 extraction paths. Clang/LLVM include boundary passed.
- Rocky parity: 2,423 source hashes matched the frozen candidate.
- Exact publication audit covered 2,051 changed files across the pending
  serializer commit and SDK candidate; secret-pattern and private-artifact
  scans found no matches. Authored Git diff whitespace checks passed; generated
  ANTLR/TypeScript bindings and copied schemas retain generator formatting.

The live checkout's 2,564 recorded source paths were unchanged before integration;
only these two owned progress reports were subsequently updated. Indexed shared
files use scoped temporary variants so unrelated implementations and the existing
swap-file deletion remain unstaged. The snapshot preparation incident altered
only temporary files; the lean candidate was restored, its final builds/tests
rerun, and the temporary Node dependency link repaired before final validation.

Evidence: `/tmp/ctk-sdk-integration-plan.json`,
`/tmp/ctk-sdk-integration-frozen-manifest.json`,
`/tmp/ctk-sdk-integration-rhel-report.md`,
`/tmp/ctk-sdk-integration-macos-native.log`,
`/tmp/ctk-sdk-integration-macos-python.log`,
`/tmp/ctk-sdk-integration-noclang.log`,
`/tmp/ctk-sdk-integration-clang-only.log`,
`/tmp/ctk-sdk-integration-ts-live-final.log`,
`/tmp/ctk-sdk-integration-publication-audit.json` and
`/tmp/ctk-sdk-integration-precommit-preservation.json`. These are local validation
artifacts. The human explicitly authorized local main integration and its
non-force publication to the existing GitHub repository.
