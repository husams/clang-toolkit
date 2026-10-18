# Clean 623-TU indexing measurement

All **623 TU variants completed from scratch in 891.129 seconds (14 minutes 51.129 seconds)**, with **zero failed or skipped TUs**. Foreground operations remained responsive: 411 timed checks during indexing and 98 after completion had zero errors or timeouts.

The measured job ran continuously from **04:38:40.327 to 04:53:31.466 on 18 October 2026, Europe/London**. The monotonic completion bracket is 890.625–891.129 seconds; polling uncertainty is 0.504 seconds. Startup, unrelated foreground warmup, and post-completion checks are outside the index elapsed time.

## Run isolation

- Worktree: `/Users/husam/.claude/worktrees/clang-toolkit/index-definitions-context-reuse`, source revision `90bae180e0e0977a4d19e2aab1ec8a85dfef1eb3`; server code revision `70c198d652f9`.
- Tested server and worker binaries were copied and pinned in a new private run directory. The temporary server used a separate socket, storage root, SQLite database, and header-extraction cache. No symbol database existed before the single Start request.
- Exactly one `StartProjectIndex` was issued; there were no Pause, Resume, Cancel, restart, or input-repair operations during the job. All progress states were queued, indexing, or complete. A launchd snapshot recorded one process launch, and server uptime samples never decreased. The private server stopped only after indexing and the final checks completed.
- All 1,978 pinned input hashes and both binary hashes were rechecked unchanged. No build or source changes were made during the run.
- This is a fresh **index**, using the existing valid worktree build/PCH. OS filesystem caches were not flushed. Normal background scheduling and foreground admission remained enabled, and the elapsed time includes the foreground probe workload.

The frozen compilation database selects the original requested **623 command variants / 622 unique files** from the current worktree release build. The current build has two additional commands (`directory_watch.cpp` and `test_index_definition_reuse.cpp`) outside that original cohort; they were excluded to keep the requested set exact. All selected commands were preserved without source/header path repairs. The 141 source files outside the worktree are its existing fetched dependencies: 136 ANTLR, four GoogleTest/Mock, and one SQLite TU. Generated API files and the PCH belong to the matching worktree build.

## Foreground responsiveness

Concurrent bursts ran every 15 seconds with two-second request deadlines. Parse/match checks used unique source files outside the indexed inputs, preventing AST-cache hits from substituting for fresh parsing. The completion poll ran independently of probe work. Only checks finished before the last known nonterminal poll are counted as indexing-time samples.

| Operation | During-index samples | During-index p95 | During-index maximum | Idle-after maximum |
| --- | ---: | ---: | ---: | ---: |
| Exact lookup | 59 | 25.244 ms | 38.854 ms | 13.529 ms |
| Prefix lookup | 58 | 21.231 ms | 33.573 ms | 10.044 ms |
| USR lookup | 58 | 10.424 ms | 13.188 ms | 6.340 ms |
| Out-of-line lookup | 59 | 7.857 ms | 13.382 ms | 5.535 ms |
| Fresh parse and native match | 59 | 59.172 ms | 89.001 ms | 61.204 ms |
| Server status | 59 | 13.999 ms | 18.515 ms | 16.057 ms |
| Index status | 59 | 2.711 ms | 3.542 ms | 2.748 ms |

Exact, prefix, and USR checks made **174 genuine cross-TU queries**, using definitions contributed by multiple source TUs. Initial queries were allowed to be empty until their definitions were published. The out-of-line definition `ctk::platform::current_executable_sibling` was successfully checked 23 times while other TUs were still indexing; those positive checks had a maximum of **6.491 ms** and resolved to `server/src/platform/index_worker.cpp`. The table's full out-of-line series also includes the earlier empty results before that TU was indexed.

The post-completion window contained 14 checks of each operation, all successful. Lookup targets and result sizes varied as indexing progressed, so these windows establish observed fast responses rather than a controlled claim of zero latency overhead.

## Completed-index audit

The fresh database has exactly three tables (`metadata`, `translation_unit`, `symbol`), **623 TU variants**, **1,601 shared-header groups**, and **145,259 definition rows**. It contains zero declaration-only rows, nonempty signatures, anonymous-namespace names, or rows located in standard C++/Clang resource-header paths. Eligible ANTLR/LLVM headers contribute 19 namespace `std` records and 39 `std::...` member records; standard-header exclusion preserves explicit definitions supplied by those headers. Local-variable exclusion remains the previously tested external-definition policy; it is not inferred solely from symbol names in this database audit.

## Pre-start lookup issue retained in the evidence

Before Start, eight symbol lookups against the intentionally nonexistent database returned `unable to open database file`. Consequently the raw harness's final **all-phases** assertion exited with status 1. The raw result remains unchanged with `success: false`; it is not presented as a globally passing harness run. These errors occurred before the timed job. All 411 indexing-time checks, all 98 post-completion checks, status polling, completion assertions, and input-integrity checks passed. An independent audit therefore marked the requested clean indexing and responsiveness measurement **PASS** while preserving this separate pre-index behavior.

## Evidence

The run directory is `/tmp/ctk623-clean-20261018-edojhyc1`.

- [Independent audit](/tmp/ctk623-clean-20261018-edojhyc1/independent-audit.json)
- [Raw result, including pre-start errors](/tmp/ctk623-clean-20261018-edojhyc1/result.json)
- [Terminal timing and status](/tmp/ctk623-clean-20261018-edojhyc1/index-complete.json)
- [Timestamped request samples](/tmp/ctk623-clean-20261018-edojhyc1/request-samples-final.json)
- [Continuous progress](/tmp/ctk623-clean-20261018-edojhyc1/progress.jsonl)
- [Frozen 623-command database](/tmp/ctk623-clean-20261018-edojhyc1/cdb/compile_commands.json)
- [Pinned inputs](/tmp/ctk623-clean-20261018-edojhyc1/input-manifest-before.json)
