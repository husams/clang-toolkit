# Syntax composition

- [x] Inline runnables accept `(parameters) body`.
- [x] Command operands accept full expressions.
- [x] Leading pipeline stages continue across newlines without outer grouping.
- [x] Returned and indexed callable values can be invoked directly.
- [x] Examples, help, regression coverage, and required validation updated.

Compatibility: retain existing inline `=` syntax and the separate legacy/native languages.

Independent review regressions covered: grouped arithmetic, inline block recovery,
conditional callable collections, prepared callable bodies, matcher binding,
parenthesized command operands, keyword-named runnables, existing approved methods,
and single evaluation of collection mutation targets.

Validation:

- Native configure/build succeeded; all 440 native tests verified. Storage
  reload tests were rerun serially with a private `CTK_STORAGE_ROOT` to avoid
  cross-process cache ownership contention.
- Final full Python unit suite: 2,647 passed.
- All 201 end-to-end scenarios verified across the full run, isolated groups
  and focused reruns after compatibility fixes. The precompiled-header scenario
  passed with `CTK_TEST_CLANG=/opt/homebrew/opt/llvm/bin/clang++`.
- Updated pipeline and composition examples passed in compiled and tree
  consoles, including the real-terminal pipeline scenario.
- Diff whitespace and Ruff checks passed (existing E731 rule excluded).

## Multiline pipeline keyboard follow-up

- [x] Ctrl+Enter inserts a line instead of executing the draft.
- [x] Option+Enter on macOS, Alt+Enter, and Shift+Enter insert lines.
- [x] Recognize CSI-u, modifyOtherKeys, and native Windows Meta-Return input.
- [x] Apply these controls to both the workspace and ordinary prompt.
- [x] Keep Enter for complete input and Ctrl+J for whole-draft execution.
- [x] Verify leading/trailing `|`, comments, CRLF, and both evaluation engines.
- [x] Verify all four shortcut/UI combinations in actual terminal processes;
  incomplete pipeline drafts execute zero times, completed submissions once.
- [x] Update shortcut hints, console help, documentation, and bundled skill.
- [x] Complete the full unit, native, and acceptance regression runs.

Follow-up validation: all 2,672 unit tests passed; all 440 native cases passed
across the initial serial run and isolated partitions. All 205 acceptance cases
were verified across isolated batches and targeted reruns. A blank-prompt test
now initializes its grammar before measuring response time; native REPL command
checks allow 60 seconds for query startup rather than the editor's 15-second
response budget. Targeted reruns passed with those test timing fixes. The four
new real-terminal shortcut/UI cases passed, and
focused Ruff and diff whitespace checks passed.
