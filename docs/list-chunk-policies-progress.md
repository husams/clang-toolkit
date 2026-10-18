# Per-operation list chunk policies

PR integration base: main `64d382d`; branch `codex/list-chunk-policies`.
Implementation and benchmark baseline: main `52a7daf`.

- [x] Add failing checks for policy selection and a branch-light shared loop.
- [x] Select setup, checkpoint, settlement and finish policies once per invocation.
- [x] Verify source accounting, cancellation, aliases, snapshots and restoration.
- [x] Measure the policy overhead and obtain independent review.
- [x] Run the exact map/filter/reverse example in the real console and capture Python/output.
- [x] Complete the full Python unit suite.
- [x] Complete available native test validation, including isolated storage retries.

## Design

The frozen `_ChunkPolicy` records select setup, checkpoint, settlement and finish
functions once per invocation. A small `_ChunkState` holds invocation-local state.
The common loop binds checkpoint/settlement functions before iterating and has
only one conditional: polling cancellation before invoking each bounded kernel.
It has no operation dispatch or observer conditionals inside the loop.

Forward setup retains the caller's output list and creates an iterator over the
existing shallow input snapshot. Map settlement charges its exact source cost;
filter additionally charges three steps per appended item and retains the last
predicate result for the observer. The first forward chunk retains its two-step
adjustment, and forward completion retains its final cancellation checkpoint.

Reverse setup charges logical descent and initializes the output; its checkpoint
policy restores the precise unwind depth and observer state before cancellation
is polled. Settlement charges four steps per completed element and settles unwind
depth. Its finish policy retains the original final-node selection and poll count.

Eligibility proofs, scalar/overflow guards, budget admission and guarded fallback
are unchanged. Batches remain non-copying `islice` views of at most 128 snapshot
items. Unsupported callbacks or insufficient budgets retain the general path and
its exact failure/partial-mutation behavior. Reverse retains the pending-work
limit. No runtime policy calls are added per element; checkpoint and settlement
are called once per chunk.

## Verification

- The new structural and selection/lifecycle tests failed before implementation:
  **13 failed**, `/tmp/ctk-policies-red.log`.
- **410 focused tests passed** in 62.08s, covering both engines, source-step parity,
  empty/chunk boundaries, aliased outputs, cancellation within successive chunks,
  observer state, limits and scope/depth restoration
  (`/tmp/ctk-policies-focused.log`).
- **Six additional final-chunk cancellation cases passed** in 5.23s: forward
  completion observes cancellation after settling all items, while reverse keeps
  its original poll count (`/tmp/ctk-policies-finish.log`). This final test was
  added after full-suite collection and was run separately.
- All **four compiled/tree real-terminal list acceptance scenarios passed** in
  28.86s (`/tmp/ctk-policies-e2e.log`).
- Independent read-only review approved the diff, checking source accounting,
  cancellation ordering, observers, aliases and snapshots.
- Full Python suite: **3,256 passed** in 278.75s
  (`/tmp/ctk-policies-unit.log`, `/tmp/ctk-policies-unit-results.xml`). Together
  with the six separately added final-chunk cases, all **3,262 distinct current
  unit cases** passed.
- Available native suite: **481 passed, seven storage-related failures** in
  298.70s without an explicit storage root. Reran those seven with a fresh
  `CTK_STORAGE_ROOT`: **all seven passed** in 31.22s. All **488 distinct native
  cases** therefore passed across the run and retry; native code was unchanged
  (`/tmp/ctk-policies-native.log`, `/tmp/ctk-policies-native-retry.log`).
- The broader E2E suite was not repeated for this runtime-only refactor; the four
  list acceptance scenarios above were run in both execution engines.
- Ruff checks and formatting, and `git diff --check`, passed for changed files.

## Real console

Executed the exact `examples/recursive_lists.ctk` in a real compiled TTY console
using an isolated native server, storage, libraries and history. Verified the saved
history equals the complete script, the compiler hash matches the source, and all
six native kernel selections used the policy runner (map/filter/reverse for 5 and
1,000 elements). Selective monitoring on `prepare_plain` return events captured
actual kernels, shared runner and selected policy functions without modifying
cancellation, observer or tick hooks. The native server and console were then
stopped.

Capture directory: `/tmp/ctk-policies-demo.amrHh2/`; `report.md` contains the exact
script, selected Python and output. Supporting files include `transcript.txt`,
`actual-output.txt`, `compiler.sha256` and `generated/records.jsonl`.

```text
[10,20,30,40,50]
[2,4]
[5,4,3,2,1]
[1,2,3,4,5]
Large counts: 1000, 500, 1000
```

The generated kernels remain unchanged in `docs/generated-list-loops/plain_*.py`.
The signed remainder expression in filter preserves CTK remainder semantics for
negative inputs. Reverse gets a reversed snapshot iterator from its setup policy.

## Paired timings

Compared main `52a7daf` with this refactor using 15 warmed alternating samples
through actual runtime dispatch, validating outputs and original inputs.

| Items | Operation | Main ms | Policies ms |
| ---: | --- | ---: | ---: |
| 1,000 | map | 0.291 | 0.289 |
| 1,000 | filter | 0.368 | 0.374 |
| 1,000 | reverse | 0.170 | 0.170 |
| 10,000 | map | 1.632 | 1.593 |
| 10,000 | filter | 1.788 | 1.773 |
| 10,000 | reverse | 0.845 | 0.892 |

Runner-only measurements excluded preparation/dispatch: 30 alternating samples
of ten invocations each, validating every output. For 10,000 elements,
map/filter/reverse measured 0.2688/0.4553/0.2076ms versus
0.2697/0.4469/0.1971ms on main. Reverse's policy overhead was approximately
0.0105ms (5.3%) in this measurement. The refactor simplifies dispatch, but does
not claim a speedup; these local timings are not portable guarantees.

Evidence: `/tmp/ctk-policies-benchmark.log`,
`/tmp/ctk-policies-runner-benchmark.log` and their corresponding scripts.

## PR integration

Rebased onto main `64d382d` without conflicts. Runtime and regression-test sources
are byte-for-byte unchanged from the reviewed implementation. On that integration
base, all **416 focused list tests** and all **four compiled/tree real-terminal
acceptance scenarios** passed again (`/tmp/ctk-policies-pr-focused.log`,
`/tmp/ctk-policies-pr-e2e.log`). The console scenarios completed in 35.37s.
