# Compact generated list loops

Branch: `codex/compact-list-loops`; base main: `b68331c`.

- [x] Measure existing direct loops and add failing compact-generation checks.
- [x] Extract shared invocation guards; retain visible Python traversal and append.
- [x] Batch adjacent pure source ticks without changing the first budget failure.
- [ ] Complete semantic parity, cancellation, cleanup and regression checks.
- [ ] Review independently and measure paired old/new execution.
- [ ] Run the exact example in the real console and publish Python/output.

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
map shrank from 48 to 16 lines, filter from 63 to 17, reverse from 58 to 19.
The real terminal transcript, exact example, extracted output and generated code
are saved under `/tmp/ctk-compact-list-demo.vsBNmh/`.

Final paired benchmark: 1,000 elements; 15 warmed samples per version, alternating
old and new implementations in the same process; median milliseconds:

| Function | Previous direct loops | Compact loops |
| --- | ---: | ---: |
| map | 17.942 | 16.070 |
| filter | 18.739 | 17.303 |
| reverse | 10.434 | 8.559 |

These timings are environment-specific. Exact scalar appends avoid the old
validator's visitor/set allocation; other values use the original validator.
No per-item continuation objects or repeated list-tail copies are introduced.

The full Python unit suite passed all 3,068 cases. The final focused suite passed
146 cases, including exhaustive budget boundaries, cancellation, cleanup, nested
collection errors, host replacement/rebinding and custom validator type hooks.
Independent review found no blocker. Ruff and whitespace checks passed.
Logs: `/tmp/ctk-compact-unit.log`, `/tmp/ctk-compact-final-focused.log`, and
`/tmp/ctk-compact-benchmark-final.log`.
