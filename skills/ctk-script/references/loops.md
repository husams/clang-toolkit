# Loops and indexes

These forms work in the compiled console (the `ctk` default) and the tree reference
engine. Use `--script-engine compiled` with `python -m clang_toolkit.cli.app` or
`scripts/manual_console.sh`. The legacy engine and native server `script`/batch
language have separate syntax; they do not gain these forms. `help loops` provides
the same offline guidance in the prompt and workspace consoles.

## Complete example

Save the following as `loops.ctk`, then run `ctk --script /absolute/path/loops.ctk`.
It needs no source fixture or query. Use the supplied/configured server for query
scripts; do not replace the user's endpoint just to exercise local loops.

```text
let names = ["alpha", "beta", "gamma"]
let numbered = foreach name in names do ({index: name.index, name: name})
print numbered

let x = 13
while x > 10 do {
    print x
    x -= 1
}
print x

let attempts = 0
repeat {
    attempts += 1
    if attempts < 3 then continue
    print "finished"
} until attempts >= 3

let counter = 0
let samples = repeat { counter += 1; counter } until counter >= 3
print samples

let selected = foreach item in [1, 2, 3, 4, 5] do {
    if item % 2 == 0 then continue
    if item == 5 then break
    item * 2
}
print selected

let collisions = foreach item in [{index: 42, value: "data"}] do ({iteration: item.index, data_index: item.value.index, data_value: item.value.value})
print collisions
```

The console renders list elements on separate lines. The output is:

```text
{"index": 0, "name": "alpha"}
{"index": 1, "name": "beta"}
{"index": 2, "name": "gamma"}
13
12
11
10
finished
1
2
3
2
6
{"data_index": 42, "data_value": "data", "iteration": 0}
```

## Binding metadata

For a single binding, write `foreach item in items do BODY`. `item.index`
is a read-only, zero-based visit ordinal on that binding; it advances even on
`continue`. The item still behaves as its original string, number, dictionary or
native value. `item.value` bypasses metadata: `item.value.index` and
`item.value.value` read the item's own colliding fields. Do not assign these two
reserved metadata properties.

Metadata belongs to the loop binding. Assignment to the item variable preserves
its index; a new `let` shadows it. Aliases, arguments, returned/collected values
and exports contain raw items without loop metadata. Nested loops retain their
own indices. The source is evaluated once using the existing live iterator;
list growth can be visited, while rebinding the source does not replace that
iterator. Dictionary iteration yields keys with traversal ordinals.

Tuples can be unpacked directly: `foreach (name, count) in pairs do BODY`.
Use `foreach (index, (name, _)) in (pairs | enumerate) do BODY` for an explicit
ordinal and nested tuple pattern; `_` discards a slot. Tuple patterns require
matching shapes before the body runs. For collection transformations, prefer
`pairs | map((name, count) = {name: name, count: count})`; see
[pipes.md](pipes.md) for callback spreading, `zip` and complete examples.

For native match results, the loop ordinal does not change node ownership or
server provenance. `source_match_index` still identifies the immediate parent
row within its originating file's retained result; use `source_file` and per-file
parents for cross-file attribution. Never use `.index` as a substitute for that
provenance.

## Conditions, control and results

`while CONDITION do BODY` tests before each iteration. `repeat BODY until
CONDITION` runs at least once and stops when its trailing condition is true.
Both conditions must be Boolean. Bodies accept a single statement or braces;
for example, `while x > 0 do x -= 1` and `repeat x += 1 until x >= 3`. `while`
also accepts braces without `do`; `until` may start on the next line.

`break` exits the nearest loop. `continue` skips the remaining body, and a
continued `repeat` still checks `until`; `break` skips that check. Control outside
a loop or across a runnable/isolated batch boundary is rejected before submission
effects, including inside named or inline runnables. An inner loop inside that
boundary can use its own control.

Each iteration has a fresh scope. Declare counters used in conditions outside
the body. Mutation updates the nearest existing binding; body declarations and
iterator bindings disappear on exit. Exit handlers run during normal completion,
control transfer, errors and cancellation before scope release.

Consumed loops collect the final value of normally completed bodies: assignments
contribute their assigned values, empty bodies contribute `null`, and continued
or broken iterations contribute nothing. Assignment suppresses ordinary body
display; explicit file output still occurs. Standalone `while`/`repeat` display
body values without building an unused result list. Standalone `foreach` retains
its existing collected-result behavior.

All forms share execution limits and cancellation, including empty bodies and
constantly continued loops. On an error, an assignment keeps its previous value;
earlier mutations and explicit effects persist. Use bounded examples and a real
TTY-backed console when verifying scripts; parsing alone is not verification.

## Maintained sources

- `docs/loop-control.md`
- `python/clang_toolkit/cli/runtime/prototype/grammar.lark`
- `python/clang_toolkit/cli/runtime/prototype/semantics.py`
- `python/clang_toolkit/cli/runtime/prototype/compiler.py`
- `python/clang_toolkit/cli/runtime/prototype/help.py`
- `tests/unit/test_loop_control.py`
- `tests/unit/test_loop_repl.py`
- `tests/unit/test_inline_runnables.py`
- `tests/e2e/test_prototype_repl_steps.py`
