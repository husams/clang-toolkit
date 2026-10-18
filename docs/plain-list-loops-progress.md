# Plain generated list loops

Branch: `codex/plain-list-loops`; base main: `bc6013d`.

- [x] Add failing checks rejecting per-item runtime guard calls.
- [x] Recognize and prove bounded pure scalar callbacks; retain guarded fallback.
- [x] Emit native for/append loops with inline source-budget accounting.
- [x] Review budget algebra and close altered-hook bypasses.
- [x] Complete full regression validation.
- [x] Capture the complete example in the real terminal and generated Python.

Map/filter hoist input type and intermediate int64 bounds once. Reverse accepts
exact scalars and retains its logical pending-work limit. All paths retain the
single shallow input snapshot, preserving source/output aliases and nested
identity on fallback. Insufficient step budgets use the original execution, so
error locations and partial outputs remain identical. The plain path supports
cooperative Event cancellation at iteration/effect boundaries; custom hooks and
instrumentation retain exact individual ticks. The standard observer's private
tail state is updated inline only when no inner statement is externally visible.

Independent review found and verified fixes for patched Event.is_set and
class-level tick_many hooks. Both now trigger guarded execution; observer and
callback executable replacement are guarded as well. Final read-only review
approved the implementation and its conservative budget formulas.

Paired benchmark against `bc6013d`: 1,000 elements, 15 warmed alternating samples
per version in the same process; median milliseconds:

| Function | Main compact loop | Plain loop |
| --- | ---: | ---: |
| map | 23.805 | 1.051 |
| filter | 21.591 | 0.744 |
| reverse | 9.897 | 0.473 |

These are environment-specific timings including dispatch. The plain traversal
uses native arithmetic/append and inline counters instead of per-item callback,
scope, validation and runtime-guard dispatch. Benchmark log:
`/tmp/ctk-plain-benchmark-final.log`.

Actual selected source is saved in `docs/generated-list-loops/plain_*.py`.
The compact `map_into.py`, `filter_into.py` and `reverse_list.py` examples remain
as the guarded implementation for comparison.

The complete `examples/recursive_lists.ctk` was pasted unchanged into the real
compiled prompt console, using this checkout's Python and an isolated native
server. Its persisted history equals the exact file contents. Actual output:

```text
[10,20,30,40,50]
[2,4]
[5,4,3,2,1]
[1,2,3,4,5]
Large counts: 1000, 500, 1000
```

Transcript, exact script, extracted output and actual generated Python:
`/tmp/ctk-plain-final-demo.5B7tgP/`. The demo console and its own server were stopped.
The selected Python was exported after executing the same small expressions;
the retained dispatcher functions were refreshed from this compiler as well.

Native source/build settings are unchanged. The inherited main native validation
exercised all 440 IDs: 439 passed; the shared-header index case (ID 387) failed
with the known stale-binary assertion at line 225 versus current source line 287.
This Python optimization does not repair that unrelated build/index baseline.
Native evidence: `/tmp/ctk-compact-native-summary.json`.

A final six-case regression reproduced an Event set/clear race: polling once and
then calling tick polled a second time, so clearing between the two could resume
and add an extra step. The error-only `cancelled` helper now records the original
location and raises immediately after detection, without re-polling or incrementing
steps. Both engines pass all 215 loop tests after the fix. Independent review
approved this final delta. The exact real-console example was rerun after it.

Final validation:

- Full Python unit suite: 3,150 passed in 604.12 seconds, including the six final
  cancellation race cases.
- Focused loop semantics/accounting suite: 215 passed in 34.75 seconds.
- Full end-to-end suite: 207 passed; two console scenarios timed out before any
  prompt appeared. A separate installed-environment retry also timed out.
- Those two fixtures previously loaded personal `~/.ctk/lib` files. They now pass
  an empty temporary `--lib-dir`, matching the other terminal fixtures; their
  explicit fixture import, installed entry point, assertions and original time
  limits are unchanged. Both complete scenarios then passed in 113.31 seconds.
  Thus all 209 distinct end-to-end scenarios passed across the full run and
  the corrected isolated retry. Independent review accepted this test isolation.
- Ruff, formatting and whitespace checks passed; final review approved both the
  runtime changes and the four-line fixture isolation fix.

Final logs: `/tmp/ctk-plain-unit-final.log`,
`/tmp/ctk-plain-final-focused.log`, `/tmp/ctk-plain-e2e.log`,
`/tmp/ctk-plain-e2e-retry.log`, and `/tmp/ctk-plain-e2e-isolated.log`.
The unchanged native baseline limitation is recorded above; it was not rerun for
this Python-only optimization.
