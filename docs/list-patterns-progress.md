# List patterns and multi-clause functions

- [x] Exact list, tuple, wildcard and right-associative cons patterns.
- [x] Atomic destructuring bindings and named/inline parameter matching.
- [x] Ordered grouped clauses with single argument evaluation and no fallthrough on body errors.
- [x] Compiled Python pattern checks and allocation-free recognized numeric right folds.
- [x] Admission inspection, help, libraries and editor integration.
- [x] Regression tests, full required checks and real-console example output.

Compatibility: existing `let` declarations still rebind. Grouped clauses have
equal positional arity and no defaults; ordinary runnable defaults remain.
Bound tails are independent lists; discarded tails allocate nothing. The
compiler may optimize only provably pure self-recursive numeric right folds,
preserving right-to-left checked arithmetic and execution limits.

Validation:

- Native build succeeded; all 440 native cases pass across the full run and
  sequential retries of four fixture/timing failures.
- All 2,816 current unit cases are covered: the full run passed 2,777 cases;
  the final 145-case run passed the corrected/new feature cases and the one
  unrelated console-startup timeout. It also covers the 36 cases added after
  the full run collected its tests.
- All 144 feature cases and 20 offline editor adapter tests pass.
- The complete example passes in real compiled/tree console terminals; its
  actual output is recorded in [the feature guide](list-patterns.md).
- All 207 end-to-end cases pass across the full run and reduced-concurrency
  retries of 22 timeout failures (both retry batches passed 11 cases).
- Targeted lint and whitespace checks pass. Independent review approved the
  implementation, including fixes for fold step accounting, recursive alias
  admission, self shadowing and compiled loop patterns.

The initial high-concurrency validation exposed startup/native deadlines and
a shared native temporary-file collision. Retries use isolated storage and
lower concurrency; no existing deadline was increased.
