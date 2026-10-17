# Index validation bottleneck and fix

The previous fresh 623-TU run completed in 2,623.467 seconds (43m43s).
Both fixes completed a fresh 623-TU run in **1,035.916 seconds (17m15.916s)**,
versus 2,623.467 seconds (43m43.467s) previously: an observed **2.53x speedup**
and **60.5% less elapsed time**. All 771 sampled active requests succeeded:
symbol lookups stayed below 9 ms, fresh native parse/match below 36 ms, and
status requests below 10 ms. No RPC failures or timeouts were observed.

| Full 623-TU run | Elapsed |
| --- | ---: |
| Definitions-only/context-reuse baseline | 43m43.467s |
| Directory-digest cache alone | 35m06.108s |
| Directory cache plus retained foreground yields | **17m15.916s** |

The intermediate run exposed a second bottleneck: foreground bursts discarded
the active extractor, and the next pass revalidated every preceding TU.
These are observed timings; OS cache warmth and unrelated host activity were
not controlled. See [the final measurement](index-full-623-optimized-validation.md).

## Measured bottleneck

A five-second sample of the isolated server caught its entire sampled background
index thread in `replace -> manifest_current -> digest_file -> include_inventory`,
mostly `stat`, directory enumeration and filesystem metadata calls. This sample
identifies an expensive validation interval, not a percentage of the whole run.
The worker constructs include-directory inventories, and the controller previously
repeated full walks before and after each publication. Foreground interruptions
could also restart reconciliation and repeat validation of completed TUs.

Standalone extraction of representative small declaration/expression TUs took
1.38–2.56 seconds. A generated query protobuf TU took 5.73 seconds with derived
header reuse disabled and 17.18 seconds with a populated derived cache in one
probe. Native parsing is still required; extracted-record reuse alone does not
guarantee a speedup.

Cold/warm effects were substantial: a six-TU server probe took 76.38 seconds,
while a repeat on the old binary took 19.49 seconds. An experimental disk-policy
adjustment was reverted because its apparent gain did not survive the warm-cache
control. The final fix retains the existing CPU and I/O priority policy.

Raw evidence is under `/tmp/ctk-index-profile-7elxptnq/`: `server-before/cpu.sample.txt`,
the server timing logs, `workers-before.jsonl`, and saved source changes. The small
profiling cohorts are not used to claim a full-project speedup.

## Change

The background controller now retains only bounded include-directory digests,
guarded by kernel directory notifications: kqueue on macOS, inotify on Linux.
Unchanged directories reuse their digest. Changes, lost watches and queue errors
invalidate cached inventories; unavailable or exhausted watches use full walks.
Directory timestamps and a time-to-live are not freshness criteria.

Watches cover directory ancestors and intermediate symlinks, including external
targets. Root inode identity is checked, and a changing initial walk is retried.
Directory inventories also record symlink targets, so direct retargets with
unchanged relative filenames invalidate the old digest. An external-symlink-chain
regression test failed before the guard fix and passed afterward.

Header contents still receive fresh hashes before and after publication. Existing
macro-sensitive definition extraction/reuse, standard-header exclusion, three
SQLite tables, worker limits, foreground admission, pause/resume/cancel and
affected-TU refresh remain in place. This change adds no parallel extraction
workers.

Resource bounds are 128 cached digests and at most 2,048 directory watches. macOS
additionally caps watch descriptors below half the available allowance after a
256-descriptor reserve; unsupported/resource-constrained cases fall back to walks.

Foreground admission now suspends the isolated worker process group and resumes
the same extraction once foreground work clears. The worker consumes no CPU
while suspended. Its 120-second wall deadline excludes that suspension, while
the existing CPU, memory and output limits remain. Cancellation kills and reaps
the entire suspended group. Publication waits for foreground admission instead
of rolling back solely because another request arrived; pause/cancel and input
freshness checks still gate every commit.

A regression reproduced six worker launches for one discovery and three TUs;
after the fix it requires exactly four. Process tests verify retained extraction
across suspend/resume and cancellation of a suspended group. All 29 focused
indexing/admission/process cases pass before the final timing run.

## Verification of the final code

- All **462 native tests pass** in one full run (112.848 seconds). An earlier
  concurrent run hit the existing 60-second completion limit in one standard-
  header fixture; both its isolated retry and the final full suite passed.
- All **2,500 Python unit cases have passing results**. The full run passed
  2,499 cases; one 10-second local-console startup timeout passed when rerun
  from the project directory. That test never contacts the server. Python
  product code was unchanged by these performance fixes.
- All **199 end-to-end cases pass** together (1,547.25 seconds), with the
  configured Clang compiler set explicitly. This includes the console indexing,
  pause/resume, affected-TU refresh and foreground-request scenarios.
- End-to-end tests ran from a neutral directory with absolute package paths.
  Running discovery from the Release checkout exposes an existing `-O1` to
  `/O1` normalization bug on both the old and new binaries; it is unrelated to
  this patch and is not fixed here.
- A separate process constrained to 64 file descriptors verified that an
  unavailable watch budget still performs fresh directory scans and detects
  new headers.
- Formatting and diff whitespace checks pass. Linux execution was unavailable
  because the local Podman service was stopped; the Linux notification path
  has not been exercised in this session.

## Full-run verification

The fresh private run uses the same frozen 623-TU compile database as the 43m43s
measurement, the same Release flags (`-O1 -DNDEBUG -g0`), empty persistent and
derived caches, one-second status polling, and concurrent symbol/status/new-parse
bursts approximately every minute. OS filesystem caches are not flushed.

The managed server is untouched. The private run copies its binaries and stores
its evidence outside the worktree to survive another checkout cleanup.
Final elapsed time and request latency are recorded in
`index-full-623-optimized-validation.md`; the completed run is
`/tmp/ctk623-final-g0icnyxg/`.

Final status recorded COMPLETE, 623 indexed/completed, zero skipped/failed/
pending, and revision 623. Unlike the interrupted passes, completion counters
did not reset during this measured run. All 202,255 physical definition rows
are identical to the intermediate completed index, including their owner IDs
and compilation contexts; all 623 TU-variant/header-group memberships also
match. SQLite still has exactly three tables, zero non-definition rows and
zero checked standard/builtin include-path rows. User-defined specializations
inside namespace `std` are not mistaken for standard-header definitions.

The private endpoint is `unix:///tmp/ctk623-final-g0icnyxg/q.sock` (PID 53809).
Its periodic refresher was paused after timing and after the idle probes,
preserving the completed index for inspection without ongoing background work.
The final binary/source hashes and raw samples are retained in that run folder;
the source patch/new-file archive is in `/tmp/ctk-index-profile-7elxptnq/`.

Latest validation logs: `/tmp/ctk-yield-native-final.log`,
`/tmp/ctk-yield-python.log`, `/tmp/ctk-yield-python-cwd-retry.log`, and
`/tmp/ctk-yield-e2e.log`. The expected failing-before regression is retained in
`/tmp/ctk-yield-red.log`; the 29-case focused pass is `ctk-yield-green.log`.

The intermediate directory-cache run retained all 623 TU variants and identical
header-group memberships. Its 202,255 definition rows differ from the previous
202,257 only in `server/tests/test_match_cursors.cpp`, which changed in the main
checkout between runs: 352 old records versus 350 replacement records, with
different recorded source digests. Every definition record outside that edited
file is identical. The compile database is frozen; source files and unrelated
host activity are not frozen. Raw comparisons are in the intermediate run folder
`/tmp/ctk623-optimized-s98xsvzi/semantic-comparison.json` and
`semantic-differences.json`.
