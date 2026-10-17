# Full 623-TU isolated indexing measurement

Completed all **623/623 TUs in 1035.916 seconds (17m 15.9s)** with zero failed TUs.

The server and worker were built from the recovered isolated worktree, with Release flags `-O1 -DNDEBUG -g0`. Their binaries were copied into this private run folder. A frozen copy of the main checkout compile database supplied the original 623 TU workload; source paths and working directories were unchanged. The managed server was untouched.

A fresh private index and empty header cache were used. Native parsing was warmed before timing. Timing runs from StartProjectIndex until the first COMPLETE status, including extraction, worker startup, header-cache I/O, publication, foreground admission/yields, and status-poll granularity.

| Request | Active count | Active p95 ms | Active max ms | Idle max ms |
| --- | ---: | ---: | ---: | ---: |
| exact | 124 | 3.649 | 4.376 | 6.188 |
| fresh_parse_and_match | 51 | 34.182 | 35.643 | 53.365 |
| index_status | 170 | 0.998 | 1.741 | 1.492 |
| out_of_line_definition | 8 | 3.223 | 3.223 | 1.817 |
| prefix | 124 | 7.321 | 8.862 | 7.03 |
| server_status | 170 | 6.634 | 9.668 | 18.686 |
| usr | 124 | 3.501 | 4.184 | 3.412 |

Exact/prefix/USR samples assert populated definitions contributed by multiple distinct TUs. The out-of-line lookup locates `ctk::platform::current_executable_sibling` in `server/src/platform/index_worker.cpp`, separate from its call in `server/src/net/index_service.cpp`. Every parse probe uses a new source file and matches its actual native function declaration.

SQLite verification: exactly three tables, 623 indexed main TUs, 202255 physical symbol rows, zero non-definition rows, and zero standard/builtin-header include rows matching the checked paths.

No request failures or timeouts were observed in the sampled workload. Requests were probed concurrently every minute, rather than under continuous saturation; this establishes sampled responsiveness, not a guarantee for every workload. The same definitions-only workload previously completed in 2623.467 seconds; this comparison uses the recorded full-run baseline, with OS cache warmth and unrelated host activity as uncontrolled factors.

Private endpoint: `unix:///tmp/ctk623-final-g0icnyxg/q.sock`; server PID `53809`.
Evidence: `/tmp/ctk623-final-g0icnyxg/result.json`, `samples.jsonl`, `events.jsonl`, binary/source hashes in `run.json`, and server log. The completed index is left available, with its periodic refresher paused after measurement to avoid competing with other work.

The previous complete definitions-only run took 2623.467 seconds (43m43s); both runs use fresh private persistent storage, the same frozen 623-TU database, Release flags and foreground probe pattern. OS filesystem caches are not flushed. The original interrupted run is excluded.

The background controller now reuses include-directory digests guarded by kernel change notifications; foreground bursts suspend/resume the worker process group instead of discarding its extraction and restarting reconciliation. Publication also waits for foreground admission rather than rolling back solely because a request arrived. Additions, removals, renames, symlink retargets, preserved directory timestamps, root replacements and changes during the initial scan are tested. Unavailable or exhausted watches fall back to full walks. Header contents are still hashed independently before publication; macro-sensitive definition reuse, standard-header exclusion and the three-table schema remain unchanged.

## Profile and correctness audit

The observed total is **2.53x faster (60.5% less elapsed time)** than the recorded
43m43.467s run, and 2.03x faster than the 35m06.108s directory-cache-only run.
Foreground interruption now suspends/resumes the worker process group rather than
killing extraction and starting another validation pass. Final counters were
623 completed, zero skipped/failed/pending and revision 623; no observed progress
reset occurred. CPU/output/memory limits remain, with foreground suspension time
excluded from the wall deadline.

There were **771 validated active requests**, zero RPC failures/timeouts and zero
status-poll errors. Real out-of-line definition lookups located
`ctk::platform::current_executable_sibling` in its `.cpp` definition, across the
TU boundary from the caller in `net/index_service.cpp`. The active fresh parse
mean/p95/max was 25.717/34.182/35.643 ms; the three pre-index idle samples averaged
22.456 ms and the three post-index idle samples averaged 34.903 ms. This proves
sampled responsiveness, not literally zero overhead or behavior under saturation.

The final and directory-cache-only indexes have identical **202,255 definition
records**, including raw owner IDs and normalized compilation contexts. All 623
TU-variant/header-group memberships also match. See `semantic-comparison.json` in
the run folder. The earlier 43m43s index had 202,257 records: every difference is
in the main checkout's subsequently edited `server/tests/test_match_cursors.cpp`
(352 old versus 350 new records, with distinct stored source digests). Every
record outside that edited file matched. The compile database was frozen; source
files, OS cache warmth and host activity were not frozen. Header reuse still
requires Clang parsing; this fix does not introduce parallel TU workers.

Final-code verification: 462/462 native tests in one run; 2,499 Python unit cases
in the full run plus the remaining local-console startup case passing on retry;
199/199 E2E cases in one run. An earlier concurrent native run hit a fixture's
60-second completion limit; its retry and the final full suite passed. Linux was
not exercised because the local Podman service was stopped. See
[index-performance-profile.md](index-performance-profile.md) for test logs,
regression evidence and fallback checks.
