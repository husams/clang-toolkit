# Full 623-TU isolated indexing measurement

All **623/623 TUs completed in 43m 43.467s (2623.467 seconds)**, with zero failed TUs. Indexing began at 2026-10-17T18:34:38+01:00 and reached COMPLETE at 2026-10-17T19:18:21+01:00.

**Responsiveness passed for the sampled workload; the desired indexing speed remains unmet.** The run exceeds the earlier 26-minute result. There is no matched old-extractor 623-TU run under these exact build and foreground-load conditions, so this is not a controlled regression percentage.

## Workload and isolation

The recovered worktree is `/Users/husam/.claude/worktrees/clang-toolkit/index-definitions-context-reuse`, branch `codex/definitions-header-reuse`, based on `ac0e7a6`. Its extractor and header-cache source hashes match the interrupted run exactly; the rebuilt worker binary hash also matches. The server and worker were built with Release flags `-O1 -DNDEBUG -g0`, then copied into the private run directory so another worktree cleanup could not remove them.

A frozen copy of the original main-checkout compile database supplied all 623 TUs, including dependencies and generated sources; source paths and working directories were unchanged. The index and header cache were initially empty. Native foreground parsing was warmed before the timer; the timer includes worker startup, extraction, cache I/O, SQLite publication, foreground yields/retries and status-poll granularity. Build and test time are excluded. The managed server was untouched.

## Requests during indexing

1965 validated active-phase requests were sampled in concurrent bursts approximately every minute, alongside one-second progress polling. There were zero RPC failures or timeouts. This demonstrates sampled responsiveness, rather than continuous saturation or a guarantee of zero latency impact.

| Request | Active samples | Active mean ms | Active p95 ms | Active max ms | After-index max ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| exact | 320 | 5.105 | 8.968 | 33.304 | 4.88 |
| fresh_parse_and_match | 129 | 52.678 | 90.296 | 133.681 | 44.608 |
| index_status | 430 | 1.167 | 5.897 | 18.645 | 0.6 |
| out_of_line_definition | 16 | 3.227 | 4.61 | 4.61 | 2.407 |
| prefix | 320 | 8.827 | 17.648 | 41.815 | 8.024 |
| server_status | 430 | 7.42 | 21.144 | 71.296 | 17.974 |
| usr | 320 | 4.756 | 8.809 | 19.205 | 5.369 |

Exact, prefix and USR probes assert populated definition results contributed by multiple distinct TUs, using `antlr4::ANTLRInputStream` and `ctk::ast::v1::APArrayValue`. The out-of-line probe locates `ctk::platform::current_executable_sibling` in `server/src/platform/index_worker.cpp`, separate from its call in `server/src/net/index_service.cpp`. Each foreground parse uses a different new source file, then matches its native function declaration.

Some active latencies are higher than the idle samples; zero slowdown is not established. All observed active requests completed within 134 ms. Cross-TU exact/prefix/USR lookups stayed within 42 ms; the out-of-line definition lookup stayed within 5 ms.

## Index contents

SQLite has exactly three tables: metadata, translation_unit and symbol. It contains 623 indexed main TUs and 202,257 physical symbol rows, with zero non-definition rows and zero rows from the checked libc++, Clang builtin or SDK include paths.

There are 77 std-named rows defined in non-standard ANTLR, GoogleTest and LLVM/Clang headers. These include project/library specializations and overloads such as `std::hash<antlr4::atn::ATNConfig>::operator()`; standard-library includes remain excluded. The full audit is saved beside the raw measurements.

The progress snapshots show 2 resets of the per-pass completed counter while cumulative indexed coverage remains intact. Foreground interruption can restart reconciliation and recheck already indexed TUs. The final pass skipped 618 already published TUs; this was still a fresh all-623 run, with cumulative revision 623. This behavior adds background work and is a remaining performance finding, not a measured attribution of all elapsed time.

## Recovery and verification

The earlier run was interrupted at 275/623 when an external cleanup removed the worktree and build/cache files. Cleanup had saved the changes in Git stash b85a7f2; applying that backup restored the exact implementation and tests. The interrupted timing is excluded.

Recovery checks: 447/454 C++ cases passed in the parallel invocation; seven persistent-cache cases failed with shared private storage and then all seven passed when rerun serially. Thus all 454 cases have successful results. All 2,500 Python unit tests passed. The previously completed E2E validation was not rerun for this measurement; no product implementation changes were made after recovery.

## Observer corrections

The first observer incorrectly rejected the expected stale flag while the project was incomplete. Its 12 assertion samples are archived in initial-observer-samples.jsonl and initial-observer-assertions.json and excluded from validated lookup statistics; no RPC failed. The observer was replaced while the same server, index and monotonic timer continued.
The final namespace-based exclusion assertion was too broad: 77 std-named rows are namespace reopenings, hash/tuple/error-code specializations, and swap definitions in ANTLR, GoogleTest and LLVM/Clang headers supplied as user includes. They are not standard-library include rows. Every such row was audited in std-name-audit.json; the corrected include-path check finds zero standard-library/builtin/SDK include rows. No product code or indexed data was changed to satisfy these checks.

## Saved evidence

Private endpoint: `unix:///tmp/ctk623-recovered-u8obms9j/q.sock`; server PID `9145`. The completed index is left available; background change detection remains enabled.

Run directory: `/tmp/ctk623-recovered-u8obms9j`. It contains `result.json`, `verified-result.json`, `samples.jsonl`, `events.jsonl`, `std-name-audit.json`, initial observer samples, server log, frozen compile database, source/binary hashes, and the copied binaries. The original observer exception is retained as evidence; the corrected final checks are recorded in verified-result.json.
