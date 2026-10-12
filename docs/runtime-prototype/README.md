# CTK runtime prototype

This isolated prototype compares a tree interpreter with compile-once Python execution for the proposed scripting language. Both engines evaluate the same parsed AST with the same checked operations, lexical scopes, execution budget and host-function registry.

Branch: `codex/scripting-runtime-prototype`; base: `8907c6a`. The experimental command is separate from the released `ctk` console and native `RunScript` language.

## Run the complete example

The following commands use the existing local Python environment:

```sh
cd /Users/husam/.claude/worktrees/clang-toolkit/scripting-runtime-prototype
export PYTHONPATH="$PWD/python"
/Users/husam/workspace/clang-toolkit/.venv/bin/python -m clang_toolkit.cli.runtime.prototype examples/runtime-prototype/features.ctks --engine compiled
/Users/husam/workspace/clang-toolkit/.venv/bin/python -m clang_toolkit.cli.runtime.prototype examples/runtime-prototype/features.ctks --engine tree
```

Both print:

```json
{"full": 10, "functions": 3, "safe": 7, "short": 10, "total": 12, "unless": {"message": "below threshold", "retry": true}}
```

Inspect actual generated Python without executing it:

```sh
/Users/husam/workspace/clang-toolkit/.venv/bin/python -m clang_toolkit.cli.runtime.prototype examples/runtime-prototype/features.ctks --show-python
```

The compiler builds Python `ast` nodes and uses `compile()` once. Generated loops execute Python `for` statements; generated branches are lazy. Execution calls checked primitive helpers and does not call the tree interpreter. A regression test disables all tree-dispatch functions and still executes compiled loops and conditions.

## Implemented syntax

- Numbers, strings, booleans, `null`, lists and dictionaries with bare identifier keys.
- Checked arithmetic, comparisons, strict Boolean `and/or/not`, and unary signs.
- Value-producing `if/else`, `unless/else`, and `condition ? true_value : false_value`.
- Local `let`, direct and compound assignment to existing bindings and owned list/dictionary entries.
- Single-statement bodies without braces, multi-statement brace bodies, newline separators and same-line semicolons.
- Collected `foreach` values, including assigned and nested loops.
- Field and index reads through existing CTK value adapters, named registered host functions, and bounded `len/range`.

Branches return their final statement value. Locals remain scoped; assignments update the nearest existing binding. Failed target updates preserve the old value. A missing conditional branch returns `null`. A skipped branch performs no host call. Prints capture owned container values at emission while retaining native value identities.

The shared numeric contract uses signed int64 and finite floating-point values. Booleans do not act as integers; mixed float operations reject lossy integer conversion. Integer remainder follows truncation toward zero.

## Reuse a compiled script

```python
from clang_toolkit.cli.runtime.prototype import Context, compile_program, parse

source = "let total=0; foreach item in range(1000) do $total += $item; $total"
compiled = compile_program(parse(source))
first = compiled(Context())
second = compiled(Context())
assert first == second == 499500
```

`run_source(..., engine="compiled")` is the convenience API and parses/compiles per call. Reuse `compile_program(parse(source))` when comparing repeated execution or running the same script again.

## CTK operations

An explicit `ctk(command)` function delegates once to the existing `Runtime.evaluate`. It returns typed values without reconstructing handles from JSON. Prototype bindings and the command-string runtime's bindings are separate namespaces.

```sh
/Users/husam/workspace/clang-toolkit/.venv/bin/python -m clang_toolkit.cli.runtime.prototype examples/runtime-prototype/host.ctks --server unix:///tmp/ctk.sock
```

Supply an existing endpoint. The host example reads status and skips an unselected file-open operation. Real-server BDD tests also retain typed match rows, continue matching from native bindings, and verify zero resource counters after cleanup.

## Measurements

See [the measured matrix](benchmark-summary.md) and [raw results](benchmark-results.json). Seven repetitions at 1,000 and 10,000 iterations compare identical sources, results, bindings, output and counted steps. Parsing, compilation, first execution, repeated execution, and fresh parse-and-execute are separate measurements.

These are local Python runtime measurements. The registered-host workload uses a local callback; it does not measure network or Clang query speed. The experiment supports Python compilation for repeated console scripts, while native-server integration still requires a separate runtime decision.

## Validation

- 1,187 Python unit tests passed, including 66 prototype cases.
- All 340 existing native tests passed in one process with fresh storage. Native source/API/build files match the prebuilt binary's source revision.
- The full existing BDD run passed 119 cases; two version tests initially failed because the new worktree lacked its ignored client build stamp. Generating that stamp with the repository build helper made both pass.
- Two new real-server prototype BDD scenarios passed for both engines. Across the original run and corrected reruns, all 123 distinct BDD cases passed.
- Ruff and whitespace checks passed; the full feature script produced identical visible results in both modes.

Parallel native test processes sharing one storage directory initially hit its exclusive ownership lock; the complete single-process rerun passed. This required test isolation, not a native source change.

## Prototype boundaries

The released console editor/help/completion and native ANTLR language are not connected to this experimental parser. There is no server-side Python runtime integration, automatic compiled-script cache, general user-function syntax, or new RPC.

Item and step limits are enforced, including output, range, collection literals and dictionary growth. Cumulative retained-byte accounting and parser nesting admission remain production integration work. Host operations retain their existing ownership and effect rules; earlier effects are not rolled back by a later script error.

Progress and evidence are in [progress.md](progress.md). The language proposal is in the wiki and the editable Page created for this discussion.
