# Background index performance profile and validation fix

## Current result

Code `4cfb528` indexed all **623 TUs in 1041.032 seconds (17m21.032s)**, with zero failed, skipped or pending TUs and revision 623. Compared with the recorded 43m43.467s baseline, this is an observed **2.52x speedup** and **60.3% less elapsed time**. The earlier 17m15.916s measurement predates the final freshness and worker-completion fixes; the final code has now been measured separately.

All **771 sampled requests during indexing succeeded**: exact/USR lookups were below 6 ms, prefix lookups below 11 ms, real out-of-line definition lookups below 4 ms, fresh native parse/match below 35 ms and status below 12 ms. These are concurrent sampled bursts, not a saturation guarantee. All 202,255 physical definition rows and all 623 TU/header memberships exactly match the previous completed index, including compilation contexts and owner IDs. SQLite has exactly three tables, no non-definition rows and no standard-header rows matching the checked include paths.

The measurement used a temporary private Interactive launchd service, matching the previously approved managed-server policy. The index thread retained Utility priority and extraction workers retained nice 15. The managed server was untouched. The private service was removed after successful verification; its completed database and raw evidence remain in `/tmp/ctk623-pr60-role-bgmli2s4`. See [the full measurement](index-full-623-optimized-validation.md).

## Historical full-project measurements

These runs used the same frozen 623-TU compile database and Release flags (`-O1 -DNDEBUG -g0`) with empty persistent and derived caches. OS filesystem caches and unrelated host activity were not controlled.

| Run | Elapsed | Qualification |
| --- | ---: | --- |
| Earlier baseline | 43m43.467s | historical baseline |
| Directory-digest cache | 35m06.108s | intermediate cache-only implementation |
| Directory cache plus retained foreground yields | 17m15.916s | pre-final worker/admission fixes; not the current final result |
| `4cfb528` | **17m21.032s** | final freshness and worker-exit fixes; private Interactive service |

The historical comparison is directional, not a controlled causal estimate. One source file changed between earlier runs, and host load and OS cache warmth varied.

## Profile evidence and source-difference audit

A five-second sample of the isolated server in the earlier profile caught the background thread in `replace -> manifest_current -> digest_file -> include_inventory`, mostly filesystem metadata calls. This identified an expensive validation interval, not a percentage of total runtime. Separate foreground-burst tests showed that discarding the active worker could restart reconciliation and redo prior validation.

The directory-cache experiment retained all 623 TU variants and matching header-group membership. Its 202,255 definition rows differed from the earlier 202,257 only for `server/tests/test_match_cursors.cpp`: 352 prior records versus 350 replacement records, with changed source digests. All records outside that edited file matched. The compile database was frozen, but source files and other host activity were not. Evidence: `/tmp/ctk623-optimized-s98xsvzi/semantic-comparison.json` and `semantic-differences.json`.

Raw initial profiling evidence remains under `/tmp/ctk-index-profile-7elxptnq/`. Small profiling cohorts are not project-wide timing claims. Earlier private diagnostic runs `q81`, `x6tgz3pq`, and `uobmmbvv` are excluded from performance claims; they failed before a valid full measurement, hit worker suspension permission errors, or had a debugger attached. A 3-TU interactive control took 5.727 seconds and is not a full-project timing.

## Current implementation notes

The controller caches bounded include-directory inventory digests behind kernel notifications (kqueue on macOS, inotify on Linux). Watch loss, overflow, unsupported watching, and inventory changes invalidate cached values and fall back to fresh walks. Directory timestamps and TTLs do not establish freshness. Watches cover ancestors and symlink chains; the root identity and initial walk are rechecked. Resource bounds are 128 cached roots and 2,048 watched directories, with macOS descriptor reserve/cap.

The isolated worker is retained across foreground work by suspending and resuming its process group; worker CPU, memory, output, and wall limits remain. Cancellation kills and reaps the group. A completed-worker race is fixed by reaping completed children and preserving their exit status for the next poll, instead of signaling an exited child. A second poll handles completion between the first poll and the signal.

Publication validates source/header dependencies, compile-command digest, and worker identity after admission. If an admission wait occurs inside manifest validation, the validator discards its partial digest map and retries the entire manifest from empty state before commit. Hashing remains outside the status mutex, and the admission fix adds no extra validation pass on the normal no-wait path. Deterministic regressions cover edits during final commit admission and during an inner manifest-validation wait.

A console terminal progress-ordering correction is also included; it does not affect indexing semantics or performance results. Extraction remains serial and isolated. Each TU is still parsed with its own flags; the derived cache reuses definition records, not the Clang parse. The existing three-table SQLite schema, selective TU refresh, standard/system-header exclusion and foreground APIs remain supported.

## Verification for current code

- Full native suite: 465 passed in 78.525s (`/tmp/ctk-pr60-final465-native.log`).
- Full Python unit suite: 2,817 passed in 355.07s (`/tmp/ctk-pr60-final-unit.log`).
- The full E2E run passed 206 cases and failed one workspace progress-ordering case. After that fix, the failed case and all three indexing scenarios passed together on the final build (4 passed in 37.18s). Logs: `/tmp/ctk-pr60-e2e.log` and `/tmp/ctk-pr60-4cf-e2e.log`.
- Build `4cfb528`: 32 focused native tests passed in 32.206s (`/tmp/ctk-pr60-4cf-native-focused.log`); 4 focused E2E tests passed in 37.18s (`/tmp/ctk-pr60-4cf-e2e.log`).
- Both stale-publication regressions failed against the old implementation; the outer-only intermediate fix still failed the inner-wait regression. The final implementation passes both: `/tmp/ctk-pr60-red.log`, `/tmp/ctk-pr60-inner-red.log`, `/tmp/ctk-pr60-green.log`.
- The completed-worker regression reproduced `suspend index worker: Operation not permitted` before the fix; all 13 process tests pass after it. Evidence: `/tmp/worker-exit-fix-logs/old-red.log` and `final-focused.log`.
- Earlier isolated workspace startup waits hit their 3-second limit; the final full 2,817-case suite passed without changing that limit. A native run using a shared default cache failed seven artifact-storage assertions; subsequent full runs with fresh private storage passed.
- Linux was not run because Podman was stopped; the Linux notification path remains unverified here.

## Final full-run evidence

- Code: `4cfb5282ff3e27e2ec41278c968a52e92e09c6dd`; binaries and source SHA-256 hashes are in `/tmp/ctk623-pr60-role-bgmli2s4/run.json`.
- Workload: the frozen original 623-TU compile database; Release `-O1 -DNDEBUG -g0`; empty private persistent and derived caches. Native parsing warmed before timing (0.503s); the warmup had a 30s budget, while timed client requests retained the 2s budget. Timing runs from StartProjectIndex to the first COMPLETE status, with one-second polling.
- Results and request samples: `/tmp/ctk623-pr60-role-bgmli2s4/result.json`, `samples.jsonl`, `events.jsonl` and `server.log`.
- Exact record/context/membership comparison: `/tmp/ctk623-pr60-role-bgmli2s4/semantic-comparison.json`; all comparisons pass.
- Private service cleanup is recorded in `/tmp/ctk623-pr60-role-bgmli2s4/service-cleanup.json`; index files are retained.
- Host/OS caveat: filesystem cache warmth and unrelated host load were uncontrolled; source files were not frozen. Historical speedups are observational, not controlled causal estimates.
