# Single-call list chunk policies

Implementation base: main `4351794`; branch `codex/single-call-list-policies`.

- [x] Prove the old policies fail the one-policy-call contract.
- [x] Move first checkpoint preparation into setup and subsequent preparation into settlement.
- [x] Preserve aliases, snapshots, exact accounting, cancellation and execution limits.
- [x] Measure the overhead and independently review the implementation.
- [x] Run the exact map/filter/reverse example in the real console and capture Python/output.
- [x] Complete Python validation, including the unchanged startup-test retry.
- [x] Complete native validation with a rebuilt current-main test executable.

The common loop will call one settlement policy per chunk, in addition to the
kernel and cancellation poll. Eligibility proofs, the 128-item interval and the
guarded fallback stay unchanged. Reverse must prepare the next unwind checkpoint
only when another chunk remains, retaining zero depth on successful completion.

## Design and red test

The policy record now has setup, settlement and finish fields; checkpoint getter
functions are removed. Forward settlement already chooses the next cancellation
node. Reverse setup prepares the first unwind checkpoint and tracks remaining
snapshot items; settlement prepares the next boundary only if items remain.
Empty reverse keeps its base state, and final settlement keeps zero depth and the
`ref` observer tail without adding a final cancellation poll.

The new one-call contract and expanded lifecycle cases failed on main before the
implementation: **37 failed** in 22.49s (`/tmp/ctk-single-policy-red.log`).
Policy lifecycle coverage now includes 0, 1, 128, 129, 256 and 257 items in both
engines. Existing deterministic cancellation, final-chunk polling, source-budget
parity, alias/snapshot and guarded fallback assertions are unchanged.

Independent read-only review approved the runtime diff: no concrete behavioral
blocker found. Ruff and diff checks passed.

## Focused verification

All **440 focused tests passed** in 248.91s under substantial host contention
(`/tmp/ctk-single-policy-focused.log`, `/tmp/ctk-single-policy-focused.xml`).
The shared loop retains its single cancellation conditional and calls settlement
once per chunk, plus the plain kernel and optional cancellation poll. For a
1,000-item operation there are eight settlement calls instead of eight checkpoint
plus eight settlement calls; setup and finish remain once per invocation.

## Real console

Ran the exact `examples/recursive_lists.ctk` in a real compiled TTY console, using
a separate native server and isolated storage, history and libraries. Verified
that saved history equals the full script and the compiler hash matches the
implementation. Captured all six native kernel selections (map/filter/reverse
for five and 1,000 items), their runner and three-field policy functions via
selective `prepare_plain` return monitoring. Tick, observer and cancellation
hooks were not changed. The console and native server were stopped afterward.

Artifacts: `/tmp/ctk-single-policy-demo.vsqnw7/`; `report.md` contains the complete
script, actual kernels, shared runner, policies and output. Supporting evidence
includes `transcript.txt`, `actual-output.txt`, `compiler.sha256` and
`generated/records.jsonl`.

```text
[10,20,30,40,50]
[2,4]
[5,4,3,2,1]
[1,2,3,4,5]
Large counts: 1000, 500, 1000
```

## Console acceptance and paired measurements

All **four compiled/tree real-terminal acceptance scenarios passed** in 60.06s
(`/tmp/ctk-single-policy-e2e.log`, `/tmp/ctk-single-policy-e2e.xml`).

Paired measurements compared main `4351794` and the new runner in one process,
validating all outputs and original inputs. Wall timings were noisy under host
load (a sampled load average reached 116), so a runner-only comparison also used
`thread_time_ns` to exclude descheduling: 30 warmed alternating samples of ten
invocations per function/size, excluding preparation and runtime dispatch.

| Items | Function | Two-call CPU ms | Single-call CPU ms |
| ---: | --- | ---: | ---: |
| 1,000 | map | 0.0413 | 0.0405 |
| 1,000 | filter | 0.0664 | 0.0666 |
| 1,000 | reverse | 0.0359 | 0.0356 |
| 10,000 | map | 0.3882 | 0.3975 |
| 10,000 | filter | 0.6399 | 0.6234 |
| 10,000 | reverse | 0.3111 | 0.2784 |

Results remain mixed; the claim is one fewer policy call per chunk, not a
portable speedup. No per-item work or extra input/tail copies were added.
Evidence: `/tmp/ctk-single-policy-benchmark.log`,
`/tmp/ctk-single-policy-runner-benchmark.log`,
`/tmp/ctk-single-policy-runner-cpu-benchmark.log` and corresponding scripts.

The first native run was stopped after a fixed temporary source filename collided
with another active test run (`cannot open source file: .../ctk-native-query.cc`).
The full suite was relaunched with both a private TMPDIR and CTK_STORAGE_ROOT;
this isolates native test fixtures as well as persistent storage.

## Full Python validation

The full suite completed with **3,285 passed and one CLI startup timeout** in
703.95s under host contention (`/tmp/ctk-single-policy-unit.log`,
`/tmp/ctk-single-policy-unit-results.xml`). The unchanged
`test_local_batch_and_syntax_error_do_not_connect_to_server` passed an isolated
retry in 12.50s, retaining its original 10-second per-process deadline and all
assertions (`/tmp/ctk-single-policy-unit-retry.log`,
`/tmp/ctk-single-policy-unit-retry.xml`). All **3,286 distinct unit cases** passed
across the run and retry.

Initially, the available native executable listed 488 cases, all in `ctk_tests`,
with one configured working directory and no disabled cases. After isolating
temporary files, the same cases were launched together in that working directory
with the same GoogleTest flags, avoiding repeated LLVM loading under host memory
pressure. Manifest: `/tmp/ctk-single-policy-native-manifest.json`. No native source
or build configuration was changed.

## Refreshed native validation

The first single-process run of the available binary passed 487 cases but failed
the streaming memory-budget fixture; its isolated retry also failed. The test
executable predated the committed fixture source. Rebuilt `ctk_tests` from
current main without C++ source changes. Compilation and linking succeeded;
CMake's five-second cold test-discovery step timed out, then an unchanged retry
after warming the executable succeeded. Build logs:
`/tmp/ctk-single-policy-native-build.log` and
`/tmp/ctk-single-policy-native-build-retry.log`.

The rebuilt target discovered **507 current native cases**, including 19 missing
from the stale executable. The formerly failing fixture passed its isolated run
in 21.29s and the subsequent full run in 154ms. The complete refreshed native
suite passed **all 507 cases** in 310.58s, with private temporary files/storage
(`/tmp/ctk-single-policy-native-fresh.log`,
`/tmp/ctk-single-policy-native-fresh.xml`). Verified the XML case names exactly
match every case in `/tmp/ctk-single-policy-native-fresh-manifest.json`, with no
failures or skipped cases.

The broader E2E suite was not repeated; both execution engines passed the four
list acceptance scenarios recorded above. The final runtime source hash still
matches the exact implementation used in the captured real-console run.
