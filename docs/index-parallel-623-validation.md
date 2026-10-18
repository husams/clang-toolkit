# Parallel background indexing: full 623-TU validation

All **623/623 TU variants completed from scratch in 285.197 seconds (4m45.197s)**, compared with **891.129 seconds (14m51.129s)** in the preceding uninterrupted single-extractor run. The observed speedup is **3.125×**, a **68.0% reduction** in elapsed time. No TU failed or was skipped.

During indexing, **397 timed foreground checks passed**, with no deadline failures or status-poll errors. Symbol queries stayed below **60.847 ms**, and fresh parse plus native matching stayed below **87.401 ms**. The default pool actually reached four simultaneous extractors. Aggregate server-plus-worker RSS peaked at **1507.5 MiB** (shared pages can be counted more than once).

## What profiling showed

The prior scheduler overlapped a single extractor with SQLite publication; it never extracted two TUs simultaneously. A fresh private baseline profile observed one live extractor. In the sampled controller, 987 of 1,534 `loop()` stacks waited for its extraction future, while 398 passed through publication validation. Separate successful baseline worker profiles of generated protobuf, Clang implementation, callgraph-test, and ANTLR TUs showed Clang parsing/sema and dependency hashing remaining on the extraction path. The parser still needs headers to resolve C++ semantics; excluding their symbols does not eliminate semantic parsing.

Profile evidence is retained under `/tmp/ctk-parallel-baseline-20261018/` and `/tmp/ctk-baseline-worker-samples/`. These short profiled fixtures were diagnostic runs; the full-run times above come from the separately measured uninterrupted 623-TU runs.

## Change

- A bounded pool extracts different TUs in separate low-priority processes. On this 10-logical-CPU, 32-GiB machine its default is four. The policy caps at four, subtracts two CPUs when sizing concurrency, and accounts for system, controller, worker, and response memory. Constrained or unknown resources fall back to one. Linux sizing also considers CPU affinity and all visible cgroup v1/v2 CPU and memory ancestor limits.
- The controller alone plans TUs, owns SQLite and digest caches, and publishes results in compilation-database order. It replenishes a completed slot before publishing that result, so publication overlaps the next extraction. At most four extractor children run; the controller may additionally retain the completed head response.
- Each worker suspends its process group for foreground native work and resumes the same extraction afterward. Existing per-worker RSS, output-size, and active-time limits remain. Indexing does not use the foreground request pool.
- Pause, resume, cancel, and restart invalidate pending work with an in-memory control counter. Uncommitted results from an earlier counter cannot publish. Cleanup signals every pending extraction before joining any, and reaps child process groups. Preplanned unchanged TUs are revalidated when consumed; changed TUs retain the final commit-time input validation.
- The gRPC contract, three-table schema, incremental affected-TU selection, definitions-only policy, local/internal-symbol exclusion, system/std-header symbol exclusion, and context-aware header reuse remain in place.

## Measurement

The benchmark used the **same exact 623 command entries / 622 unique files** as the prior clean run. The compile-command file SHA-256 is `2b1a78fa8475cd79d45a74997caf94a205e0f5028811a44d79733c7e9ba11ec9`. This includes 141 fetched dependency TUs (ANTLR, GoogleTest/Mock, SQLite), generated APIs, and project source/tests. Two newer build TUs were excluded to preserve that cohort.

The private server used fresh storage, SQLite, and header-cache directories, the same Interactive launch-service policy and three-thread foreground pool as the baseline, and immutable copied binaries. It received exactly one `StartProjectIndex` call, with a 3,600-second reconciliation interval; there were no pause/resume/cancel calls, restarts, input repairs, or incremental skips. Completion was observed between **284.691 and 285.197 seconds**. All 1,978 captured source/build input hashes and both copied binary hashes were unchanged. Only private benchmark/test services were started; the managed server was not replaced or restarted.

Foreground bursts ran every five seconds, versus every fifteen seconds in the longer baseline, with two-second client deadlines. They queried real published symbols by exact name, prefix and USR, queried an out-of-line project definition, parsed a unique new file, matched a native AST node, and checked server/index status. Status was also independently polled every half second. Metrics exclude calls overlapping the completion boundary. OS file caches were not flushed, and these are observed shared-machine timings.

| Request | Active checks | Baseline p95 ms | Parallel p95 ms | Parallel max ms |
|---|---:|---:|---:|---:|
| Exact symbol | 57 | 25.244 | 20.865 | 60.847 |
| Prefix symbols | 56 | 21.231 | 19.832 | 33.578 |
| USR lookup | 56 | 10.424 | 11.614 | 15.953 |
| Out-of-line definition | 57 | 7.857 | 10.333 | 10.897 |
| Fresh parse and native match | 57 | 59.172 | 75.396 | 87.401 |
| Server status | 57 | 13.999 | 16.733 | 43.157 |
| Index status | 57 | 2.711 | 3.562 | 12.279 |

The 168 successful cross-TU exact/prefix/USR checks required definitions contributed by multiple real TUs. There were 28 positive out-of-line definition checks while indexing; their maximum was 10.897 ms. After completion another 98 checks passed. Exact and prefix p95 improved; exact maximum rose from 38.854 to 60.847 ms (prefix maximum was effectively unchanged, 33.573 to 33.578 ms). Native parse/match p95 rose from 59.172 to 75.396 ms, with its maximum remaining below the prior 89.001 ms maximum. No blocking or timeout was observed; the figures above expose the measured tail variation.

## Correctness and regression checks

- SQLite contains exactly `metadata`, `translation_unit`, and `symbol`: 623 main TU variants, 1,601 shared-header groups, and 145,283 definition rows. There are zero declaration-only rows, nonempty signatures, standard C++/Clang-resource header symbol paths, or anonymous-namespace names. System headers remain dependencies for invalidation, while their symbols are excluded.
- All 141,930 distinct definition identities in unchanged files match the baseline. A separate audit also matched each of all 623 TU variants' main/header contributions, including offsets and locations in unchanged files. The six intentionally modified implementation/test/header files are excluded from that comparison.
- Four concurrent real worker processes sharing a cold header cache produced the same symbol tuples as uncached extraction for two macro contexts. Warm runs all reused the expected five header symbols; local/internal/std definitions were absent in that fixture.
- Full C++ suite: **486 passed** in 70.770 seconds, including deterministic worker-cap barriers, all-worker cancellation/reaping, pause with responsive lookups, rapid pause/resume stale-result rejection, foreground yielding, per-TU error attribution, incremental reuse, and portable v1/v2/hybrid cgroup fixtures.
- Full Python unit suite: **2,817 passed** in 232.28 seconds.
- Full end-to-end suite: **207 passed**, zero failures/errors/skips, across two isolated test-file groups (104 and 103 cases). All **3,510 C++/Python unit/end-to-end tests passed**. The initial sandbox-only E2E attempts could not bind local sockets; the complete successful run used host permissions, without source changes.
- Independent final code review: approved, with no actionable regression. Whitespace checks passed.

The portable cgroup file-resolution tests ran on macOS; live RHEL/container validation did not run because the local Podman service is unavailable.

## Evidence

- [Machine-readable run audit](benchmarks/2026-10-18-parallel-623-audit.json)
- [Per-TU definition/provenance comparison](benchmarks/2026-10-18-parallel-623-definitions.json)
- [Full regression-suite audit](benchmarks/2026-10-18-parallel-regressions.json)
- [Previous clean-run baseline](index-clean-623-validation.md)
- Raw run: `/tmp/ctk623-parallel-20261018-1mb5plqg/` (`result.json`, `progress.jsonl`, `resources.jsonl`, request samples, frozen CDB/input manifest, copied executables, executed scripts, and implementation patch).
- Executables SHA-256: server `96735895a9dca80d1e9b0536fb631e5244866a2c917e983e0c9226167c52e7cc`; worker `ec2d29cc9a99e50813d78f8615d7f7bdbc45667eb849d57a09cb0b616542530e`. Built from base `8e34353` plus the implementation patch captured in `run.json`; later documentation/commit metadata does not change the measured copies.
