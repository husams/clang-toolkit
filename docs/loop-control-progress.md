# Loop control and indexed iteration progress

Proposal: https://chatgpt.com/space/page_5c74c8c079608191b1cc6be4d2daf660
Baseline: cb02f8f6be0c7d1da57b61df2dd63c5d82e061e7 (merged bare references and runnable handlers).
Worktree: codex/loop-control-indexed-iteration.

- [x] Indexed foreach bindings in the standalone and combined parsers and both engines.
- [x] While and repeat until with strict conditions, loop control, scopes and shared limits.
- [ ] Editor completion, highlighting, multiline input, help and user examples.
- [ ] Both engine acceptance, real prompt/workspace console checks and full repository gates.
- [ ] Review and delivery.

Native ANTLR/C++ parity is a separate delivery, as specified by the proposal; its expression and mutation prerequisites remain pending.

Indexed slice validation: 90 focused engine, indexed iteration and handler tests passed.

Condition-loop slice: 233 focused loop, console, handler and engine cases passed, including nested loop values and pre-effect batch-boundary validation.
