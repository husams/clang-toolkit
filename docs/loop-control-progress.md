# Loop control and indexed iteration progress

Proposal: https://chatgpt.com/space/page_5c74c8c079608191b1cc6be4d2daf660
Baseline: cb02f8f6be0c7d1da57b61df2dd63c5d82e061e7 (merged bare references and runnable handlers).
Worktree: codex/loop-control-indexed-iteration.
Integration base: 5d85b0a (merged expression-bodied runnables, PR #21).

- [x] Indexed foreach bindings in the standalone and combined parsers and both engines.
- [x] While and repeat until with strict conditions, loop control, scopes and shared limits.
- [x] Editor completion, highlighting, multiline input, help and user examples.
- [x] Both engine acceptance, real prompt/workspace console checks and full repository gates.
- [x] Review and draft delivery preparation.

Native ANTLR/C++ parity is a separate delivery, as specified by the proposal; its expression and mutation prerequisites remain pending.

Indexed slice validation: 90 focused engine, indexed iteration and handler tests passed.

Condition-loop slice: 233 focused loop, console, handler and engine cases passed, including nested loop values and pre-effect batch-boundary validation.

Integrated Python gate: 1,844 unit tests passed; all 34 loop console checks also passed, including six new expression-bodied runnable cases added after the full unit run. Ruff and patch checks passed.

Native build passed. All 360 registered native tests passed with an isolated CTK_STORAGE_ROOT for each test. A shared-storage parallel run caused cache-hit assertion interference, so the final gate used independent roots.

Full end-to-end gate: 143 scenarios passed, including the real prompt/workspace loop scenarios and workspace cancellation/recovery. The three dependency scenarios failed only because this checkout had no local build compiler-path file; all three passed when CTK_TEST_CLANG pointed to the existing native build compiler. All 146 scenarios are therefore verified.

Page revision 2 follow-up: replace experimental comma bindings with scoped
`item.index` and the `item.value` escape, including read-only metadata, rebinding,
shadowing, aliases, host references and cleanup. Console and repository
verification for this revision is in progress. Focused metadata, loop, console
and editor coverage: 269 checks passed; Ruff and patch checks passed.
