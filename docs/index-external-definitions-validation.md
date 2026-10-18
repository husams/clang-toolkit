# External-definition indexing and background publication

The index now stores definitions needed across files. Function-local variables and types, file-static definitions, anonymous-namespace definitions, and declaration-only records are omitted. Externally visible functions, variables, types, aliases, class members, enumerators, concepts, templates, and friends retain their identity and definition location. The persistent schema remains the same three tables: `metadata`, `translation_unit`, and `symbol`.

The implementation is isolated on `codex/index-throughput-profile`, in commits `8d8881e8b288` and `70c198d652f9`. The managed server was rebuilt and restarted with the latter code revision; its worker bytes match the tested final external-only/pipeline worker.

## Changes

- The index action asks Clang to skip function bodies where language semantics permit it. Its visitor also skips statements, including bodies already loaded from a precompiled header (PCH). Clang can still parse bodies needed for constexpr or deduced return types. Foreground parse and match behavior is unchanged.
- Function-local declarations and internal-linkage definitions are rejected. Type signatures are no longer printed or stored; the existing signature field is empty. Names, qualified names, USRs, kinds, files, offsets, lines, and columns remain available for lookup.
- Standard/system-header symbols are excluded. Headers may still be parsed and tracked as semantic dependencies. Header reuse avoids repeated definition extraction only when compiler, arguments, environment, source identity, and observed token context match. Unsupported contexts fall back to extraction. Different macro contexts remain separate.
- At most one extraction worker runs at once. Extraction of TU N+1 overlaps validation and SQLite publication of TU N. The worker and pending thread retain background priority, foreground admission, pause/cancel handling, and existing resource bounds. The controller owns its SQLite connection.
- Unchanged TUs are skipped; affected contributions publish atomically. Lookahead is revalidated when consumed, and errors from the next TU do not discard the current result. Failed replacements retain last-good symbols.
- A redundant early publication manifest scan was removed. Fresh validation still runs after commit admission, restarts after foreground waits, and rejects changed inputs before commit. Transaction rollback keeps staged stale rows invisible. This avoids duplicate work without trusting a cached plan as a filesystem snapshot.

## What the profiles showed

Before the changes, a worker sample contained 106 of 120 stacks under Clang `ParseAST`. In a separate parent sample, 168 of 355 index-thread stacks waited for extraction, 116 performed symbol insertion, and 39 performed validation/commit work. These are sampled stacks, not wall-time fractions.

With external-only extraction and publication overlap, a later parent sample contained 97 extraction-future waits and 81 publication stacks. Repeated include-directory inventories appeared in both the early and final validation passes; this motivated removing the early duplicate. A later worker sample was dominated by dependency-buffer hashing and path/source-manager work: 110 of 325 stacks hashed buffers, 43 canonicalized paths, and 74 were under `ParseAST`, mainly end-of-TU/PCH semantic work. Only 17 appeared in the definition visitor. Definition traversal is therefore no longer the dominant sampled worker cost in that snapshot.

Artifacts: [parent before](/tmp/ctk-index-live-profile-20261018/managed-sample-before.txt), [worker before](/tmp/ctk-index-live-profile-20261018/worker-sample-before.txt), [parent after](/tmp/ctk-index-live-profile-20261018/managed-sample-after.txt), [worker after](/tmp/ctk-index-live-profile-20261018/worker-sample-after.txt).

## Timing and semantic checks

Each fixture run used the same frozen mixed 32-TU compilation database and fresh private index storage. Paired runs shared host load, but machine load varied between pairs.

| Pair | Before | After | Observation |
| --- | ---: | ---: | --- |
| Original index vs external-only/pipeline, early loaded pair | 337.620 s | 284.098 s | 15.9% less elapsed time |
| External-only/pipeline vs duplicate-validation removal | 55.998 s | 55.237 s | 1.4%; too small to establish an incremental speedup |
| Original index vs final code, lower-load repeat | 63.030 s | 41.972 s | 33.4% less elapsed time in this pair |

Earlier single runs took 201.662 s for the original, 121.857 s for external-only extraction with the original controller, and 248.983 s for the first combined build while full suites competed. Those varying-load singles do not establish a stable speedup. The paired results support an observed improvement, not a universal percentage or a full-project estimate. Result files are under `/tmp/ctk-index-live-profile-20261018/case-*/result.json`.

The normalized semantic audit expanded shared-header membership to actual TU main files. External-only and final results match exactly: 321,160 logical definition records and 80,895 physical rows. Compared with the original scope, 63,983 logical records were removed and none added. Dependency path/hash maps match. Both later controller builds also have identical definition and membership hashes. The original fixture had 96,499 physical rows. See [semantic audit](/tmp/ctk-index-live-profile-20261018/semantic-comparison.json).

## Completed managed index

The managed index completed all **623 TUs with zero failures**, then retired obsolete contexts. Its final restart reused 589 completed TU contributions and extracted the remaining 34. The completed database contains 146,512 definition rows and 1,603 shared-header groups, with exactly three tables, zero declaration-only rows, zero printed signatures, zero standard-library-header paths, and zero anonymous-namespace names. Local-scope exclusion is verified by the native scope/linkage tests rather than inferred solely from USR text.

A fresh lookup of `antlr4::ANTLRInputStream` returned definitions associated with ten TUs; `ctk::platform::current_executable_sibling` resolved to its out-of-line definition in `server/src/platform/index_worker.cpp`. Both responses reported 623 indexed TUs and no staleness. See [completed-index audit](/tmp/ctk-index-live-profile-20261018/final-audit.json).

Completion was first observed 18 min 51 s after the initial managed start. **This is not a clean final-build indexing benchmark:** it includes compilation-database corrections, concurrent tests, and a restart between the two controller revisions, with the same final extraction worker. The final restart/reconciliation took about 2 min 10 s and skipped 589 TUs; that is not the cost of freshly extracting 623 TUs.

The private compilation database retains all 623 original main-file paths and working directories. Main checkout generated API files were stale relative to current hand-written sources. Its final repair uses matching main generated headers for the two main generated API source files, and matching isolated-build API headers for 50 other commands. An initial overly broad replacement altered two source tokens; this was corrected. A second source/header version mismatch reproduced with the standalone compiler and was also corrected. Main source/configuration files and the original compilation database were preserved. The repaired input and adjustment records are in `/tmp/ctk-index-live-profile-20261018/managed-cdb/`.

## Responsiveness and validation

During final-build indexing, 14 concurrent probe bursts made 98 timed request checks (the seven types below; aggregate bundle timings excluded), with zero errors. Maximum observed times were:

| Request | Maximum |
| --- | ---: |
| Exact symbol lookup | 11.4 ms |
| Prefix lookup | 12.4 ms |
| USR lookup | 26.0 ms |
| Out-of-line definition lookup | 4.8 ms |
| Fresh parse and match | 310.9 ms |
| Server status | 82.7 ms |
| Index status | 1.8 ms |

The same 98 checks with indexing paused also had zero errors; pause and resume RPCs succeeded, and background monitoring was resumed. Host-load differences prevent treating the two windows as a controlled proof of zero overhead. Earlier heavier-load indexing probes also had zero errors: symbol lookups stayed below 167 ms and fresh parse/match below 1.1 s. See [final active samples](/tmp/ctk-index-live-profile-20261018/final/result.json) and [paused samples](/tmp/ctk-index-live-profile-20261018/idle/result.json).

- Final native suite: **472 passed**, including scope/linkage, skipped-body macro effects, context reuse, overlap, input-edit/commit races, and pause/foreground cases.
- Full Python unit rerun: **2,817 passed**. Four timed CLI/mocked-UI failures from the heavily contended first run passed serial retries and the final full rerun; no deadlines or unrelated Python code were changed.
- Full E2E suite: **207 passed** on the external-only/pipeline build; after the final validation-only change, all **four indexing-specific E2E tests passed** again.
- Formatting and diff checks passed. Tests ran on macOS arm64 with Clang 22; Linux was not run in this task.

Logs: [native](/tmp/ctk-index-live-profile-20261018/final-native.log), [Python](/tmp/ctk-index-live-profile-20261018/full-python-unit-final.log), [full E2E](/tmp/ctk-index-live-profile-20261018/full-e2e.log), [final indexing E2E](/tmp/ctk-index-live-profile-20261018/final-index-e2e.log).
