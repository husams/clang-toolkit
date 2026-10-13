# CTK runtime prototype

This isolated prototype compares a tree interpreter with compile-once Python execution for the proposed scripting language. Both engines evaluate the same parsed AST with the same checked operations, lexical scopes, execution budget and host-function registry.

Branch: `codex/scripting-runtime-prototype`; base: `8907c6a`. The standalone experiment and a compiled version of both existing console views are available in this checkout. Native `RunScript` remains unchanged.

## Try the compiled REPL

From the isolated prototype folder, launch the compiled workspace console:

```sh
cd /Users/husam/.claude/worktrees/clang-toolkit/scripting-runtime-prototype
uv run ctk
```

For the basic prompt console, use `uv run ctk --ui prompt`; append `--server unix:///tmp/ctk.sock` to select a running server. Interactive launch requires a terminal and a running CTK server. From any directory, the existing launcher also selects this checkout and the compiled engine:

```sh
/Users/husam/.claude/worktrees/clang-toolkit/scripting-runtime-prototype/scripts/ctk-prototype
```

Enter this script, or paste it into either console:

```text
let total = 0
let totals = foreach value in [2, 4, 6] do {
    $total += $value
    $total
}
let report = {
    total: $total,
    label: $total > 10 ? "large" : "small",
    message: unless $total > 20 do "below threshold" else "above threshold"
}
print $report
```

The agreed `if ... then ... else` expression is also accepted:

```text
let x = 2
let y = if $x > 0 then $x * 10 else 1
print $y
```

This prints `20`. `if` and `unless` accept `then` or `do` before a single statement or brace block; `foreach` uses `do` or a brace block. Completed workspace transcript rows use the active scripting grammar, so accepted operators are not shown as syntax errors.

The report has `total: 12`, `label: "large"` and `message: "below threshold"`. The next submission can use `$total += 1; print $total`; it prints `13`. Bindings persist between submissions. Enter continues incomplete expressions and open blocks; the workspace also supports Alt-Enter for a newline and Ctrl-J to submit.

The same engine runs file/stdin/`--execute` scripts:

```sh
/Users/husam/.claude/worktrees/clang-toolkit/scripting-runtime-prototype/scripts/ctk-prototype --execute 'let total=12; print $total > 10 ? 10 : 20'
```

The combined formal grammar keeps native CTK operations such as `let rows = match functionDecl().bind("f")`, `server status`, and `let count = $rows.length + 1`. Native operations execute once through the existing Runtime; compiled branches and loops share their bindings and scoped iterator values. Existing console help and quit remain available. The REPL keeps a 64-submission compilation cache; each execution receives fresh limits and output state. Ctrl-C cancels compiled loops and leaves the console ready for the next command.

`let` and mutation are quiet. Assigned control-flow expressions collect their final values without automatic display, including nested prints to the configured display sink. Explicit `print ... to ...` and `save` remain file effects. Bare values and unconsumed branches display their result; print output that precedes a later failure remains visible. Workspace results retain structured outlines.

This checkout's `uv run ctk` entrypoint defaults to `compiled`; restart an already running console to use the updated default. Use `--script-engine tree` to compare the reference evaluator, or `--script-engine legacy` for the previous parser. The main checkout and direct `python -m clang_toolkit.cli.app` launch retain the legacy default. Older `do ... done` loop syntax and `--continue-on-error` remain available with the legacy engine; the compiled dialect uses `do STATEMENT` or brace blocks, with `then` also available for conditional bodies.

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
- Presence (`$record has field`), list membership (`in` / `not in`), exact semantic node-kind tests, and separate binding `defined` / non-null `set` predicates.
- Value-producing `if/else`, `unless/else`, and `condition ? true_value : false_value`.
- Local `let`, direct and compound assignment to existing bindings and owned list/dictionary entries.
- Single-statement bodies without braces, multi-statement brace bodies, newline separators and same-line semicolons.
- Collected `foreach` values, including assigned and nested loops.
- Field and index reads through existing CTK value adapters, named registered host functions, and bounded `len/range`.

Branches return their final statement value. Locals remain scoped; assignments update the nearest existing binding. Failed target updates preserve the old value. A missing conditional branch returns `null`. A skipped branch performs no host call. Prints capture owned container values at emission while retaining native value identities.

Predicates return booleans in conditions and ordinary expressions. Their five forms are:

| Predicate family | Forms | Meaning |
| --- | --- | --- |
| Field presence | `$record has field`; `$record does not have "field"`; `$record has ($key)` | Tests key presence, including when its value is `null`; a grouped expression supplies a dynamic key. |
| List membership | `$value in $values`; `$value not in $values` | Checks list elements with strict scalar equality and stops at the first match. |
| Semantic node kind | `$row.item is CXXRecord`; `$row.item is not CXXRecordDecl` | Tests the exact serialized kind; `CXXRecord` is the alias for `CXXRecordDecl`. |
| Binding defined | `$name is defined`; `$name is not defined` | Tests whether the root name resolves without reading a missing name. |
| Binding set | `$name is set`; `$name is not set` | A set binding is defined and non-null; `false`, `0`, and empty values still count as set. |

For a complete REPL example, create a small source file that the selected server can parse:

```sh
cat > /tmp/ctk-predicate-example.cc <<'EOF'
struct Sample {};
EOF
```

Launch `uv run ctk` in this checkout with a running CTK server, then submit:

```text
let record = {a: null, enabled: false}
let key = "a"
let has_key = $record has a
let lacks_key = $record does not have "missing"
let has_dynamic_key = $record has ($key)
let in_list = 2 in [1, 2, 3]
let outside_list = 4 not in [1, 2, 3]
let absent = $not_bound is not defined and $not_bound is not set
let enabled = $record.enabled
let enabled_is_set = $enabled is set
let records = match cxxRecordDecl(hasName("Sample")).bind("item") in "/tmp/ctk-predicate-example.cc"
let is_record = $records[0].item is CXXRecord and $records[0].item is CXXRecordDecl
print $has_key
print $lacks_key
print $has_dynamic_key
print $in_list
print $outside_list
print $absent
print $enabled_is_set
print $is_record
```

Each print is `true`. The node-kind query is also exercised against an actual match-bound `CXXRecord` in both prompt and workspace PTY tests. Membership checks stop at their first match, so an unsupported later element is only diagnosed if reached. Defined checks do not read missing names; both defined and set checks follow the REPL's existing name precedence. Node-kind tests inspect the selected semantic binding payload locally, while native field presence preserves existing availability and schema diagnostics.

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

An explicit `ctk(command)` function delegates once to the existing `Runtime.evaluate`. It returns typed values without reconstructing handles from JSON. In this standalone API, prototype bindings and the command-string runtime's bindings are separate namespaces; the REPL integration shares bindings and loop scopes.

```sh
/Users/husam/workspace/clang-toolkit/.venv/bin/python -m clang_toolkit.cli.runtime.prototype examples/runtime-prototype/host.ctks --server unix:///tmp/ctk.sock
```

Supply an existing endpoint. The host example reads status and skips an unselected file-open operation. Real-server BDD tests also retain typed match rows, continue matching from native bindings, and verify zero resource counters after cleanup.

## Measurements

See [the measured matrix](benchmark-summary.md) and [raw results](benchmark-results.json). Seven repetitions at 1,000 and 10,000 iterations compare identical sources, results, bindings, output and counted steps. Parsing, compilation, first execution, repeated execution, and fresh parse-and-execute are separate measurements.

These are local Python runtime measurements. The registered-host workload uses a local callback; it does not measure network or Clang query speed. The experiment supports Python compilation for repeated console scripts, while native-server integration still requires a separate runtime decision.

## Validation

- All 1,381 Python unit tests passed in 31.79 seconds. Ruff passed.
- All 343 native tests passed in 22.118 seconds with fresh storage against the existing `ctk-server 0.1.0` binary at revision `e399a47c332e`. This Python-only worktree remains based on `8907c6a`; no native source, API or build changes are part of this extension.
- The existing BDD suite passed 122 cases in its full run. One workspace PTY case exceeded its 15-second deadline while awaiting a native parse; its isolated rerun passed. All 123 distinct existing cases therefore passed across those runs.
- Two new real-server PTY scenarios passed in the prompt and workspace views. They exercise multiline paste, persistent bindings and mutation, expressions, direct native match/continuation, lazy host calls, error recovery, workspace Ctrl-C cancellation and recovery, ordinary `quit`, and zero resource counters after cleanup. Across existing and new cases, all 125 distinct BDD scenarios passed.
- The final predicate PTY acceptance passed both prompt and workspace scenarios in 22.59 seconds, using the ordinary default `uv run ctk` compiled entrypoint and a match-bound `CXXRecord`. The complete E2E suite passed all 125 scenarios in 565.51 seconds, with warnings only.
- Independent review approved tree/compiled parity, native target and presence-method compatibility, exactly-once query/rendering behavior, shared output limits, preserved output during interruption, scope recovery and native resource cleanup. Separate fresh PTY probes confirmed interpolation and ordinary quit in both views.
- Ruff and whitespace checks passed. The documented launcher example produced the expected structured report with total 12, followed by 13 in the next calculation.

The standalone measurements remain the original seven-sample experiment; they do not measure the REPL editor or native-server performance. Historical standalone validation is recorded in progress.md.

## Prototype boundaries

Both REPL editors support the compiled dialect, including highlighting, completion keywords, multiline validation and structured results. Native ANTLR scripts, server-side Python execution, general user functions and new RPCs remain outside this prototype. The standalone run_source API still compiles per call; the REPL caches validated submissions. Native operation argument syntax continues to follow its existing grammar.

Item and step limits are enforced, including output, range, collection literals and dictionary growth. Cumulative retained-byte accounting and parser nesting admission remain production integration work. Host operations retain their existing ownership and effect rules; earlier effects are not rolled back by a later script error.

Progress and evidence are in [progress.md](progress.md). The language proposal is in the wiki and the editable Page created for this discussion.
