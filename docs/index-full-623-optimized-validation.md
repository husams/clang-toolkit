# Full 623-TU isolated indexing measurement

Completed all **623/623 TUs in 1041.032 seconds (17m 21.0s)** with zero failed TUs.

The server and worker were built from the recovered isolated worktree, with Release flags `-O1 -DNDEBUG -g0`. Their binaries were copied into this private run folder. A frozen copy of the main checkout compile database supplied the original 623 TU workload; source paths and working directories were unchanged. The managed server was untouched. This private server uses a temporary Interactive launchd service, matching the previously approved managed-service policy; the index thread remains Utility and extraction workers retain nice 15.

A fresh private index and empty header cache were used. Native parsing was warmed before timing. Timing runs from StartProjectIndex until the first COMPLETE status, including extraction, worker startup, header-cache I/O, publication, foreground admission/yields, and status-poll granularity.

| Request | Active count | Active p95 ms | Active max ms | Idle max ms |
| --- | ---: | ---: | ---: | ---: |
| exact | 124 | 4.037 | 5.689 | 4.953 |
| fresh_parse_and_match | 51 | 32.75 | 34.172 | 38.78 |
| index_status | 170 | 1.247 | 2.464 | 2.095 |
| out_of_line_definition | 8 | 3.19 | 3.19 | 2.654 |
| prefix | 124 | 6.741 | 10.284 | 8.164 |
| server_status | 170 | 5.224 | 11.224 | 7.685 |
| usr | 124 | 4.318 | 5.678 | 4.148 |

Exact/prefix/USR samples assert populated definitions contributed by multiple distinct TUs. The out-of-line lookup locates `ctk::platform::current_executable_sibling` in `server/src/platform/index_worker.cpp`, separate from its call in `server/src/net/index_service.cpp`. Every parse probe uses a new source file and matches its actual native function declaration.

SQLite verification: exactly three tables, 623 indexed main TUs, 202255 physical symbol rows, zero non-definition rows, and zero standard/builtin-header include rows matching the checked paths.

No request failures or timeouts were observed in the sampled workload. Requests were probed concurrently every minute, rather than under continuous saturation; this establishes sampled responsiveness, not a guarantee for every workload. The same definitions-only workload previously completed in 2623.467 seconds; this comparison uses the recorded full-run baseline, with OS cache warmth and unrelated host activity as uncontrolled factors.

Private endpoint: `unix:///tmp/ctk623-pr60-role-bgmli2s4/q.sock`; server PID `51721`.
Evidence: `/tmp/ctk623-pr60-role-bgmli2s4/result.json`, `samples.jsonl`, `events.jsonl`, binary/source hashes in `run.json`, and server log. The periodic refresher was paused after measurement. The temporary private service was then removed; the completed index files remain available for inspection.

The previous complete definitions-only run took 2623.467 seconds (43m43s); both runs use fresh private persistent storage, the same frozen 623-TU database, Release flags and foreground probe pattern. OS filesystem caches are not flushed. The original interrupted run is excluded.

The background controller now reuses include-directory digests guarded by kernel change notifications; foreground bursts suspend/resume the worker process group instead of discarding its extraction and restarting reconciliation. Publication also waits for foreground admission rather than rolling back solely because a request arrived. Additions, removals, renames, symlink retargets, preserved directory timestamps, root replacements and changes during the initial scan are tested. Unavailable or exhausted watches fall back to full walks. Publication freshness validation restarts whenever it yields to foreground work, so no digest from before the wait authorizes publication. Header contents are still hashed independently before publication; macro-sensitive definition reuse, standard-header exclusion and the three-table schema remain unchanged.

## Final source and correctness audit

The measured binaries were built from runtime-code commit `4cfb5282ff3e27e2ec41278c968a52e92e09c6dd`. The final fixes revalidate publication after all admission waits, preserve completed worker exit status across suspend/resume, and order console completion progress after body output. Binary/source hashes and launch policy are recorded in `run.json`. Startup warmup took 0.503s with a 30s warmup-only budget; measured RPC budgets were unchanged.

Compared with `/tmp/ctk623-final-g0icnyxg`, all **202,255 raw definition records**, their normalized compilation contexts and owner IDs, and all **623 TU/header memberships** match exactly. See `/tmp/ctk623-pr60-role-bgmli2s4/semantic-comparison.json`. No non-definition rows or checked standard/builtin-header include rows remain. The measured improvement over 2,623.467 seconds is 2.52x (60.3% less time), with OS cache warmth, host activity and historical source changes as uncontrolled factors.

Verification: all 465 native tests passed (78.525s) and all 2,817 Python unit tests passed (355.07s). The full E2E run passed 206 cases with one workspace ordering failure; after the correction, that case and all three indexing cases passed together (4 passed, 37.18s). The final build also passed 32 indexing/process/version native cases (32.206s). Linux execution was unavailable because Podman was stopped. See `index-performance-profile.md` for logs and regression evidence.

Unsuccessful earlier private launches and debugger-attached runs are excluded from these results. This complete run had no debugger attached and zero status/probe errors. Its temporary service was removed after verification; the managed server was never restarted or modified.
