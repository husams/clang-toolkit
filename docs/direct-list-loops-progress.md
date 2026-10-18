# Direct Python loops for recursive list functions

Branch: `codex/direct-list-loops`; base main: `a4650ba`.

- [x] Measure the current map/filter/reverse example and pin exact step semantics.
- [x] Recognize safe structural forms and emit indexed Python loops with guarded fallback.
- [x] Verify shallow-list behavior, callback ordering, rebinding, cancellation and limits.
- [ ] Run regressions, independent review and real-console examples; publish generated Python.


Paired benchmark (1,000 elements, seven warmed alternating samples, median):

| Function | Direct | General |
| --- | ---: | ---: |
| map | 21.1 ms | 52.5 ms |
| filter | 23.0 ms | 54.0 ms |
| reverse | 11.6 ms | 30.4 ms |

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
