# CTK runtime prototype progress

Status: complete; independent review approved the isolated experiment. Isolated branch `codex/scripting-runtime-prototype`, base `8907c6a`.

## Scope

Implement the proposed pure scripting syntax as an experimental Python package with two engines over one formal Lark AST. Compare direct tree evaluation with compile-once generated Python AST. Explicit host functions may reuse CTK operations; released console/native language integration follows the measured prototype decision.

## Tasks

- [x] Formal grammar and source-positioned AST: verify layout, precedence, conditional/dictionary ambiguities, and mutation targets.
- [x] Shared checked operations and execution context: verify types, limits, lazy effects, scopes, and atomic target updates.
- [x] Tree evaluator and generated Python compiler: run identical semantic cases and compare outputs/errors.
- [x] Experimental CLI, complete examples, and CTK adapter: demonstrate selected/untaken existing console operations.
- [x] Repeatable measurements: record parsing, compilation, first execution and repeated execution separately.
- [x] Full existing Python and native regression gates, independent review, and documented limitations.

## Ownership

Syntax worker owns syntax.py/grammar.lark and syntax tests. Engine worker owns semantics.py/tree.py/compiler.py and engine tests. Root owns API wrapper, CLI, adapter tests, examples, benchmark, documentation and final validation.

## Validation

Passed 1,187 complete Python unit tests (66 prototype cases), 340 native tests with fresh single-process storage, and all 123 distinct BDD cases across the full run and corrected version-stamp reruns. Two new real-server cases exercise both engines and native resource cleanup. Ruff and whitespace checks pass. Complete feature outputs agree. Benchmark JSON and summary record seven-sample matrices at 1,000 and 10,000 iterations. The main checkout remains clean and production defaults are unchanged.

## Independent review

Approved after parsed-source counterexamples confirmed native value identity, lazy effects, error locations, output snapshots, int64 boundaries, and nested collected loops. Compiled control flow still executes with all tree dispatchers disabled. Production native-language parity remains a separate step.
