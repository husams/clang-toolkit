# General recursive list functions

Implemented on `codex/general-list-recursion`, based on main `70ea55d`.

- [x] Generated resumable Python bodies and explicit continuations for non-tail self calls.
- [x] Tail-call loop and indexed private tails, with no copy per tail traversal.
- [x] One shared shallow snapshot for a borrowed tail chain before body/runtime effects; real lists on observation or escape.
- [x] Ordered callbacks, checked arithmetic, execution-step parity, cancellation and scope cleanup.
- [x] Conservative fallback for unsupported recursion and arbitrary statement-observer hooks.
- [x] Independent review, full regression coverage and real-terminal examples in both engines.

## Validation

- Full Python unit run: 2,878 passed; two workspace traversal startup timeouts.
  The same scenario also timed out against the unchanged primary package. With
  the large concurrent runs stopped, all three legacy/tree/compiled cases passed
  unchanged (13.04 seconds).
- Final recursive-list and existing pattern coverage: 250 cases. The combined
  run passed 248; two new scalar-hook tests used ambiguous bare-string host
  syntax in the combined parser. After replacing that syntax with an explicit
  empty-string binding, all eight scalar/cancellation-hook cases passed.
- Native suite: all 440 distinct cases passed, using isolated temporary and
  storage directories for parallel batches.
- Acceptance suite: all 209 distinct cases passed across the full run and focused
  retries. Twelve timing failures occurred under concurrent load; ten recovered
  at reduced concurrency and the remaining prompt/workspace startup scenarios
  passed serially, unchanged (76.44 seconds). Both final recursive-list terminal
  scenarios also passed after the final snapshot fix.
- Offline editor adapter: all 20 tests passed.
- Lint and whitespace checks passed.

Independent reviews checked lexical self rebinding, observer fallback, single
call preflight, hook ordering, custom pattern/scalar effects and snapshot timing.
The final snapshot-space explanation explicitly covers a tail chain rather than
claiming a bound for arbitrary repeated plain-list arguments.

## Actual console output

Both real terminal engines ran [the exact example](../examples/recursive_lists.ctk):

```text
[10,20,30,40,50]
[2,4]
[5,4,3,2,1]
[1,2,3,4,5]
Large counts: 1000, 500, 1000
```

See [recursive list functions](recursive-lists.md) for generated execution,
ordinary shallow-list semantics, snapshot costs and unsupported-form fallbacks.
