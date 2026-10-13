# Loop control and indexed iteration progress

Proposal: https://chatgpt.com/space/page_5c74c8c079608191b1cc6be4d2daf660
Baseline: 5d85b0a (merged expression-bodied runnables, PR #21).
Worktree: codex/loop-control-indexed-iteration.

- [x] Scoped loop-variable `.index` and `.value` in both console engines.
- [x] While and repeat until, strict conditions, break/continue, collected values and shared limits.
- [x] Read-only metadata, item rebinding, shadowing, live iterators, alias/export behavior and cleanup.
- [x] Native console references, string interpolation, completion, highlighting, multiline input and help.
- [x] Prompt/workspace console acceptance, cancellation and recovery.
- [x] Full verification and draft PR delivery.

Verification on 2026-10-13:

- 269 focused loop, metadata, engine, console and editor checks passed.
- All 1,916 Python unit tests passed.
- All 360 native tests passed, with a separate CTK_STORAGE_ROOT for each test.
- All 146 end-to-end scenarios passed. CTK_SERVER and CTK_TEST_CLANG used the existing native build; server/API source trees match the baseline.
- The Page examples ran through terminal-backed compiled and tree consoles with identical output.
- Prompt/workspace acceptance verified native values, cancellation/recovery and zero retained-resource counters.
- Ruff and patch checks passed. The main checkout remains clean.

Native ANTLR/C++ parity remains a separate delivery as specified by the proposal;
its expression and mutation prerequisites remain pending.
