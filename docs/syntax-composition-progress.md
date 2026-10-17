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
