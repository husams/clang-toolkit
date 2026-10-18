# Compact generated list loops

Branch: `codex/compact-list-loops`; base main: `b68331c`.

- [x] Measure existing direct loops and add failing compact-generation checks.
- [x] Extract shared invocation guards; retain visible Python traversal and append.
- [x] Batch adjacent pure source ticks without changing the first budget failure.
- [x] Complete semantic parity, cancellation, cleanup and regression checks.
- [x] Review independently and measure paired old/new execution.
- [x] Run the exact example in the real console and publish Python/output.

One invocation guard holds source metadata, scopes and the single shallow snapshot.
There are no per-element continuation requests or frames. Hooks, cleanup and
instrumented tick methods retain individual ticks; normal uninterrupted accounting
updates the count in batches and raises at the original source node on exhaustion.
Cancellation remains checked at each logical source step.

The complete compiled-console example ran in a real TTY using this worktree's
Python package and an isolated local server. Actual output:

```text
[10,20,30,40,50]
[2,4]
[5,4,3,2,1]
[1,2,3,4,5]
Large counts: 1000, 500, 1000
```

Actual generated Python is checked in under `docs/generated-list-loops/`:
map shrank from 48 to 15 lines, filter from 63 to 16, reverse from 58 to 18
(excluding each file's explanatory comment).
The real terminal transcript, exact example, extracted output and generated code
are saved under `/tmp/ctk-compact-list-demo.vsBNmh/`.

Final paired benchmark: 1,000 elements; 15 warmed samples per version, alternating
old and new implementations in the same process; median milliseconds:

| Function | Previous direct loops | Compact loops |
| --- | ---: | ---: |
| map | 14.139 | 12.220 |
| filter | 16.000 | 14.600 |
| reverse | 8.857 | 6.731 |

These timings are environment-specific. Exact scalar appends avoid the old
validator's visitor/set allocation; other values use the original validator.
No per-item continuation objects or repeated list-tail copies are introduced.

The full Python unit suite passed all 3,070 cases. The final focused suite passed
147 cases, including exhaustive budget boundaries, cancellation, cleanup, nested
collection errors, host replacement/rebinding and custom validator type hooks.
Independent review found no blocker. Ruff and whitespace checks passed.
Logs: `/tmp/ctk-compact-unit.log`, `/tmp/ctk-compact-final-focused.log`, and
`/tmp/ctk-compact-benchmark-final.log`.

Final independent review caught a metaclass-equality bypass in the scalar shortcut.
The guard now uses identity comparisons only; its regression test rejects a cyclic
list subclass even when its metaclass claims equality with built-in scalar types.
The fix passed review and all 147 focused cases. The complete example was rerun
in the real compiled TTY after the fix and produced the same output above.

Native validation uses the existing main build. It reproduced the previously
known shared-header index failure: the binary reports an assertion at line 225,
whereas current source has that assertion at line 287. The Python compiler feature
does not modify native source or build configuration.

Final validation after the identity fix:

- Full unit suite: 3,070 passed in 362.69 seconds.
- Focused loop/accounting suite: 147 passed.
- End-to-end: 207 passed initially; the two terminal startup scenarios timed out
  before their prompts appeared. A normal retry also timed out; both passed with
  the installed dependency environment using `UV_OFFLINE=1` (60.47 seconds). Thus
  all 209 distinct scenarios passed across these runs. No test timeout or tracked
  end-to-end test code was changed.
- Native: all 440 test IDs exercised, 439 passed; only the known stale-binary
  shared-header index case failed. Tests 1-174 ran serially; remaining ranges used
  separate storage roots. Aggregate: `/tmp/ctk-compact-native-summary.json`.
- Independent review approved the final identity guard; Ruff and whitespace checks
  passed. The exact complete example passed again in a real compiled TTY.

Final logs include `/tmp/ctk-compact-unit-final.log`,
`/tmp/ctk-compact-e2e.log`, `/tmp/ctk-compact-e2e-offline-retry.log`, and
`/tmp/ctk-compact-native*.log`. The benchmark table above was refreshed against the
final identity-based guard.
