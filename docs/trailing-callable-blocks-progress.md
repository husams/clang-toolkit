# Trailing callable blocks

Worktree: `~/.claude/worktrees/clang-toolkit/trailing-callable-blocks`.
Branch: `codex/trailing-callable-blocks`; base: `76b8fe4`.

## Scope and behavior

- Add `map(items) { (item) item * 2 }` and
  `items | map { (item) item * 2 }`.
- Support multiline pipeline chains, tuple patterns, statement bodies, lexical
  captures, callable aliases and indexed/returned callees.
- A trailing block supplies the final positional argument before named options;
  `items | sort_by(reverse = true) { (item) item }` therefore shares the ordinary
  `sort_by(items, callback, reverse = true)` binding path.
- Public labels, shorthand defaults, normal calls and explicit labeled callbacks
  remain available. Natural labeled pipeline stages accept trailing blocks too.
- Require the opening brace on the same physical line as the callee or closing
  parenthesis. Reuse grouped callable clauses, including existing equal-arity
  and no-default rules. No new runtime node or execution path is introduced.

## Verification

- Red: the initial syntax test rejects a trailing block before implementation.
- The existing focused parser/runtime/callable/pipeline suite passes: 614 tests.
- The complete example runs through both actual console engines and prints:
  `TRAILING=[2,4,6,8]`, `NORMAL=[2,4,6,8]`, `PIPELINE=[30,40]`,
  `EQUIVALENT=[30,40]`, `SORTED=[4,3,2,1]`, `CUSTOM=18,18,18,18`,
  `TUPLES=["Ada: 30","Lin: 50"]`.
- Additional unit coverage checks preflight before argument effects, dormant
  bodies, dependency admission, newline boundaries, dictionaries/control blocks
  and grouped pattern clauses. E2E coverage filters native rows then uses a
  retained row for follow-up field matching.
- Independent review approved the implementation and the terminal synchronization
  correction. Ruff and whitespace checks pass for all changed Python files.
- The full Python unit suite passes: 3,663 tests in 728.30 seconds.
- A fresh native build passes. All 543 native tests pass in 926.36 seconds, using
  the original CTest commands/properties with separate storage and temporary
  directories for each test to prevent cache and watcher interference.
- All 223 E2E cases have passing results across four file partitions. The initial
  run passed 221 cases and exposed two validation issues. One existing keyboard
  test matched the startup Ready footer before its command completed; the helper
  now waits for the first completed command's elapsed-time footer, and all four
  keyboard variants pass (17.12 seconds). The PCH test required an explicit
  `CTK_TEST_CLANG` matching the built server; it passes with the configured LLVM
  compiler (4.03 seconds). Output and history assertions remain intact.
- All three new E2E cases pass: both engines preserve native rows for subsequent
  matching, and the actual interactive terminal executes the complete example.
- Build and test transcripts are retained under
  `build/validation/trailing-callable-blocks/` in this worktree.
