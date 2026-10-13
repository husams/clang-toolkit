# Runnable let implementation progress

Design: https://chatgpt.com/space/page_35dd3616d384819187b445338f5f37ca

Base: 36638a0d3f23c1c65b93f979a4b0cfcf51e78d8c
Branch: codex/runnable-let-python

- [x] Let signatures and bare references in the standalone formal grammar and IR.
- [x] Python AST compiled bodies with lexical capture, aliases and checked calls.
- [x] Combined console, matcher arguments, imports, interpolation and resources.
- [x] Help, completion and real-console BDD verification.
- [x] Complete Python and C++ regression gates.

Bodies must compile to Python AST and reuse compiled code across submissions.
No project implementation changes are made in the main checkout.

Core slice: 28 syntax tests and 23 shared-engine tests pass. Generated body
functions execute without tree dispatch; definitions stay dormant and lexical
captures survive calls, escaping closures, and redefinition.

Console slice: prompt and workspace PTY scenarios pass with an isolated native
server, dormant imported definitions, aliases, zero-argument calls, bare matcher
parameters, brace interpolation and retained native results. See runnable-let.md
for the delivered syntax and boundaries.

Final validation:

- Python unit suite: 1,579 passed.
- CMake dev build and all 360 CTest cases passed with isolated storage.
- Full native E2E run: 144 passed; two inheritance cases exposed an auxiliary
  matcher missing from the offline catalog. The grammar collision was fixed.
- Final navigation and prompt/workspace E2E rerun: all 8 passed, including both
  previously failing Unix/TCP inheritance cases and both runnable PTY scenarios.
- No unresolved regression failures; git diff whitespace checks passed.

Native ANTLR/durable batch parity remains outside this Python compiler delivery.

## Defaults and handlers extension

- [x] Defaults evaluated per omitted argument in the lexical call frame.
- [x] Optional prefix error/exit handlers and call-site fallbacks compiled to Python.
- [x] Loop break/continue after cleanup, shared budgets and resource guards.
- [x] Console/import/batch integration, help, documentation and regression gates.

Extension validation:

- Final Python unit suite: 1,654 passed.
- Native dev build passed; all 360 CTest cases passed with isolated storage
  (1,219.97 seconds).
- Full native E2E run: 145 passed; one workspace PTY scenario raced while
  submitting its next draft, before reaching the new handler examples.
- The PTY harness now waits for a unique evaluated acknowledgement on otherwise
  silent submissions. The final prompt/workspace rerun passed both scenarios,
  including default parameters, expression/block fallbacks, prefix handlers,
  break/continue, native file cleanup, and final zero resource counters.
- A call-site fallback scope leak found during review was fixed and covered in
  both engines; the final unit suite includes the regression.
- No unresolved regression failures. Main checkout remains unchanged.

Extension commits: 9b6470a (defaults), 821338a (handlers), 8dcbe01 (fallback scope).

## Expression bodies extension

Branch: codex/runnable-expression-bodies, based on merged PR #20 (cb02f8f).

- [x] Arithmetic, calls, references, defaults and conditional expression bodies.
- [x] Shared runnable IR and Python AST compilation without tree dispatch.
- [x] Existing built-in matcher templates, imports, batches, help and editor.
- [x] Both real terminal console UIs accept the new syntax.
- [x] Complete E2E suite and final delivery record.

Validation: 1,676 unit tests passed; both prompt/workspace terminal
scenarios passed; native dev build passed. All 360 native tests were exercised:
353 passed in the parallel run, and the seven storage-cache checks passed on
their sequential isolated-storage rerun. Ruff and whitespace checks passed.
The full E2E run passed 145 cases and exposed one workspace PTY harness race:
literal input was mistaken for evaluated output while the prior command was
still running. Every successful submission now waits for a unique evaluated
acknowledgement. Both affected prompt/workspace cases passed in the final rerun
(45.11 seconds), including expression bodies and native resource cleanup.
No unresolved regression failures remain.
Review confirmed expression bodies reuse existing call frames, limits, error
handling and the Python compiler; no evaluator or native API changes were needed.

Automatic approval review rejected creating a separate follow-up PR without fresh
user authorization. The extension remains on its feature branch; main is unchanged.
