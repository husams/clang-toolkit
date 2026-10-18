# Plain list kernels and shared chunk runner

PR integration base: main `fae5a59`; branch `codex/plain-list-kernels`.
Implementation and benchmark baseline: main `ac709de`.

- [x] Require generated kernels to contain only one ordinary transform/append loop.
- [x] Move chunk control, cancellation, accounting and observer settlement into one runner.
- [x] Verify aliases, snapshots, exact budgets, cancellation and state restoration.
- [x] Measure paired execution and review the final implementation.
- [x] Run the exact example in the real console and capture selected Python/output.

The eligibility proof and guarded fallback remain in place. A persistent iterator
feeds non-copying batches of at most 128 snapshot elements to a simple generated
kernel. Filter returns its last predicate result for observer settlement; accepted
counts come from output-length deltas. Reverse receives elements in reverse order
and retains its logical pending-work limit.

## Verification

- Sixteen shape/shared-runner checks failed before implementation
  (`/tmp/ctk-kernels-red.log`).
- **397 focused tests passed** in 159.49s, covering both engines, direct/general
  parity, empty and 128-item boundaries, aliased output, exact budget failures,
  cancellation inside three successive chunks and execution-state restoration
  (`/tmp/ctk-kernels-focused.log`).
- Independent read-only review approved the refactor with no concrete blocker.
- Full Python unit run: **3,235 passed, one CLI startup timeout** in 540.32s.
  The same startup test passed an isolated rerun in 10.36s with its original
  assertions and deadlines, covering all **3,236 distinct unit cases** across
  the run and retry (`/tmp/ctk-kernels-unit.log`,
  `/tmp/ctk-kernels-batch-retry.log`).
- All **four compiled/tree real-terminal list-pattern/recursive-list acceptance
  scenarios passed** in 119.15s (`/tmp/ctk-kernels-e2e.log`).
- Native source/build configuration is unchanged. The full native and broader
  209-case E2E suites were not repeated for this Python-only refactor; their
  inherited unresolved baseline limitations (including one stale native test
  binary assertion) remain documented in `docs/chunked-list-loops-progress.md`.
  No claim is made that those inherited failures were resolved.

## Real console

Ran the exact checked-in `examples/recursive_lists.ctk` in a real compiled TTY
console, with a separate native server and isolated storage/history/libraries.
Verified the complete saved history equals the example and the compiler hash
matches the source used for capture. Selective `sys.monitoring` return events on
`prepare_plain` captured six kernel selections (map/filter/reverse for five and
1,000 items), all using `_run_plain_chunks`; tick/cancel/observer hooks were not
changed. Checked-in generated sources now contain only these selected kernels.
Artifacts: `/tmp/ctk-kernels-demo.95cpdr/` (`example.ctk`, `transcript.txt`,
`actual-output.txt`, `generated/records.jsonl`, six kernels and `shared_runner.py`).

Actual output:

```text
[10,20,30,40,50]
[2,4]
[5,4,3,2,1]
[1,2,3,4,5]
Large counts: 1000, 500, 1000
```

## Paired timing

Compared main `ac709de` with the shared runner in the same process, using actual
runtime dispatch and 15 warmed alternating samples per function/size. Results
were mixed under concurrent validation; this refactor makes no speedup claim.

| Items | Function | Previous ms | Shared runner ms |
| ---: | --- | ---: | ---: |
| 1,000 | map | 0.957 | 0.616 |
| 1,000 | filter | 0.559 | 0.672 |
| 1,000 | reverse | 0.447 | 0.561 |
| 10,000 | map | 3.249 | 2.833 |
| 10,000 | filter | 3.864 | 3.116 |
| 10,000 | reverse | 1.628 | 2.072 |

An additional warmed runner-only measurement (30 alternating samples of ten
invocations, excluding preparation/dispatch, validating every output) measured
10,000-item map/filter/reverse at 0.3708/0.5579/0.2346ms versus
0.3533/0.5391/0.2890ms previously. The shared design adds one kernel function call
per chunk, retaining linear work and no per-item runtime dispatch. These local
measurements are not portable performance guarantees.
Evidence: `/tmp/ctk-kernels-benchmark.log`,
`/tmp/ctk-kernels-runner-benchmark.log` and their corresponding scripts.
