# Direct Python loops for recursive list functions

Branch: `codex/direct-list-loops`; base main: `a4650ba`.

- [x] Measure the current map/filter/reverse example and pin exact step semantics.
- [x] Recognize safe structural forms and emit indexed Python loops with guarded fallback.
- [x] Verify shallow-list behavior, callback ordering, rebinding, cancellation and limits.
- [x] Run regressions, independent review and real-console examples; publish generated Python.


Paired benchmark (1,000 elements, seven warmed alternating samples, median):

| Function | Direct | General |
| --- | ---: | ---: |
| map | 15.4 ms | 38.2 ms |
| filter | 21.8 ms | 41.7 ms |
| reverse | 9.1 ms | 20.8 ms |

A separate profile counted no recursion driver/frame/leaf calls on direct paths;
the general paths created 1,001 frames per traversal. Timing is environment-specific.

Independent review approved after fixes for snapshot timing, collection-cycle
diagnostics, and dynamically replaced host evaluators/rebound outputs.
The real compiled prompt ran the complete example and produced:

```text
[10,20,30,40,50]
[2,4]
[5,4,3,2,1]
[1,2,3,4,5]
Large counts: 1000, 500, 1000
```

Validation logs are `/tmp/ctk-direct-unit.log`, `/tmp/ctk-direct-e2e.log`,
`/tmp/ctk-direct-cached-focused.log`, and `/tmp/ctk-direct-native*.log`.
Native tests used the existing main build: seven initial storage failures passed
serially with isolated storage; the shared-header index case still failed.
That test executable is stale (its failure refers to line 225; current source
asserts at line 287). Refreshing it was blocked by current main's Protobuf
MODULE/CONFIG target conflict. No native/CMake source changes belong to this feature.


The broad Python unit run passed all 3,010 tests. The final focused suite passed
all 123 cases, including host rebinding and nested collection error diagnostics. The exact
example was rerun in a real compiled TTY console at commit `f658326` with the
output above. Final paired timing/profile evidence: `/tmp/ctk-direct-benchmark-final.log`.


The full end-to-end run completed with 205 passes and four import-related timeouts.
Those four scenarios passed in a subsequent five-case editor/helper retry after
the unit run completed (the fifth helper scenario also passed). All 209 distinct
end-to-end scenarios are therefore verified across the runs. Both tree and
compiled real-terminal recursive-list acceptance scenarios passed.

The last diagnostic audit reproduced and fixed the exception-class mismatch for
nested collection iterators. Independent review approved this fix; all 123 final
parity cases passed in 19.49 seconds. Ruff and whitespace checks passed.
Native validation remains limited as described above: 439 of the 440 existing
binary tests passed across the initial and isolated retry runs; the remaining
index test cannot yet be revalidated against a refreshed build.
