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

## Compiled REPL follow-up — 2026-10-12

Status: complete; both real console views and independent review passed.

- [x] Opt-in `--script-engine compiled` in both workspace and prompt consoles, with a one-command `scripts/ctk-prototype` launcher.
- [x] Formal combined grammar for prototype expressions and native CTK operation leaves; persistent shared bindings, scopes and a bounded compilation cache.
- [x] Multiline validation, highlighting and completion keywords in both editors.
- [x] Existing output sinks, consumed values, structured result outlines and recoverable errors/cancellation.
- [x] Complete regression and real-server PTY gates, independent review and updated Page/wiki evidence.

Ownership: language worker owns repl_language.py/tests, editor worker owns repl_editor.py plus minimal prompt/workspace plumbing/tests, E2E worker owns new real-console BDD cases, root owns session/compiler/app/launcher/docs integration. Independent explorer reviews native value, output and cleanup behavior.

Follow-up validation: 1,242 full Python unit tests and 79 final focused cases passed; all 343 native tests passed against the existing main-checkout binary at e399a47c332e. Existing BDD full run passed 122/123 cases; the one native-parse PTY deadline failure passed in isolation, so all 123 distinct existing cases passed. Two new compiled-console PTY scenarios passed, giving 125 distinct passing cases across the runs. Both editors accept real multiline paste, direct native matching and retained-node continuation, recover after script errors and quit normally; the workspace also cancels a nested compiled loop with Ctrl-C and executes the next script successfully. Independent review also verified output limits, prior-output preservation during cancellation, native query/rendering exactly once and zero resource counters after cleanup. The launcher example prints the expected total 12 and next calculation 13. Ruff and whitespace checks pass.


## Default prototype entrypoint follow-up — 2026-10-12

Status: complete; ordinary `uv run ctk` in the isolated checkout now opens the compiled interactive REPL.

- [x] Isolated package entrypoint selects compiled scripting with accurate CLI help and explicit engine overrides.
- [x] Preserve the existing main/module legacy default and production checkout.
- [x] Verify the exact user arithmetic example, script/stdin/named arguments and exit codes.
- [x] Exercise both real console views through the installed default entrypoint without an engine flag.

Ownership: root owns app.py, pyproject.toml, entrypoint unit tests and documentation; E2E worker owns the two default-launch terminal cases; independent explorer reviews argument handling and refreshed installation metadata.

Validation: all 1,252 Python unit tests passed in 27.76 seconds; both default-entrypoint PTY BDD scenarios passed in 20.26 seconds, including native continuation, cancellation/recovery and resource cleanup. The exact `let x = 1` / `let y = $x + 1` example followed by `print $y` prints 2 through `uv run ctk`. Independent review verified the installed entrypoint, explicit overrides, help and version behavior. Ruff and whitespace checks pass. Prior 343 native and 123 existing BDD checks remain applicable because native code and the core module default are unchanged. Main checkout remains clean.
