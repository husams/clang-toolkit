# Callable labels implementation progress

Approved scope: colon public labels, word-style calls, normal calls, natural
pipeline stages, and same-public/local label shorthand. Trailing callbacks and
null operators remain outside this implementation.

Worktree: ~/.claude/worktrees/clang-toolkit/callable-labels-proposal.
Inspected base: 3076c60.

| Work | Owner | Status |
| --- | --- | --- |
| Formal grammar, shared IR, natural-call lowering, syntax tests | labels_grammar | Complete; 154 combined syntax/predicate/parser checks pass |
| Label binding, dependency admission, cache metadata, engine tests | labels_runtime | Complete; runtime/import/cache checks pass |
| Signature help/completion, cons-pattern migration, docs/examples, BDD | labels_tooling | Complete; focused tests and both-engine PTY scenarios pass |
| Integration, full validation, real-console checks, independent review | root | Complete; review approved, all required cases have passing results |

Acceptance includes the exact multiply examples, defaults and shorthand,
natural pipelines, conventional calls, preflight checks before effects,
aliases/imports/cached libraries, grouped cons patterns and preserved
indexing/subtraction/callable references in both console engines.

## Validation

The earlier 237-test result validates only the pre-implementation baseline.
Focused syntax/predicate/parser checks: 154 passed. Runtime/default-admission checks:
22 passed; runtime/import/library-cache checks: 51 passed. Both-engine real
console checks produce CALLS_8_30_30_10_30_30_10_32_10. Independent review found
and verified fixes for postfix/newline boundaries and completion regressions;
final review is approved, including reserved-word membership regressions. Ruff
and diff checks pass. The exact final example was rerun in both TTY-backed
console engines and produced the same marker after the final parser fix.

A fresh native backend has been built inside this worktree. All 543 native
tests were exercised: 541 passed on the parallel run; two watcher tests passed
on focused reruns (the inventory test twice with an isolated temporary folder).
No native source was changed. The initial failures and successful reruns are
retained in the validation evidence.

The full Python unit suite passes: 3,640 tests in 338.12 seconds. The full E2E
run exercised 220 cases: 217 passed, and the three failures were corrected and
verified with focused reruns. Validation corrected existing test assumptions:
compiled libraries create both syntax and compiled-code cache files, and two
completion tests must await populated asynchronous results rather than an empty
completion state. The workspace status check also briefly enlarges its compact
terminal so the asserted project row remains visible, retaining the original
status and styling assertions. Cache reuse passed in both engines (2 cases),
node completion passed (1 case), and the workspace interaction passed (1 case).
The full unit suite was restarted after its synchronization fix. Independent
review approved the implementation and all test corrections. Ruff passes for
every changed/new Python file; the staged diff passes its whitespace check.

Earlier checks against the older reference native build and interrupted unit
runs are not final acceptance evidence.

Final source and complete test transcripts are collected in
[the implementation evidence](/Users/husam/workspace/wiki/raw/2026-10-20-ctk-callable-labels-implementation-validation.md).
The wiki record is [[pages/planning/clang-toolkit-callable-labels]].
