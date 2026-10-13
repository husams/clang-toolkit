# Loop control and indexed iteration

The compiled CTK console supports indexed `foreach`, `while`, `repeat … until`,
`break` and `continue`. These are console forms; the native ANTLR server dialect
is a separate language and needs its own expression and mutation prerequisites.
Use `help loops` in either console view.

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
```

`item.index` is a read-only, zero-based visit ordinal belonging to the active
loop binding. Assigning the item variable preserves its index; declaring a new
binding shadows it. Ordinary item operations still use the original value.
`item.value` bypasses reserved metadata: use `item.value.index` or
`item.value.value` for a record's own fields. Aliases, arguments, collected and
exported items contain the underlying value without loop metadata. Nested loops
retain their own binding indices.

The index advances even on `continue`. The source runs once; list growth remains
visible through the existing live iterator. Rebinding the source does not
replace that iterator. Dictionary iteration yields keys with traversal ordinals.
Native match values retain ownership and `source_match_index` provenance, which
is independent of the loop ordinal.

Bodies can be one statement or a brace block. `while` accepts the same optional
`do` before braces as `foreach`; use `do` for a single statement. `repeat` always
ends with `until CONDITION`, which may start on the next line. Both condition
forms require a Boolean. `while` checks before each iteration; `repeat` runs at
least once and stops when its trailing condition becomes true. Nested `until`
clauses attach to the nearest unfinished `repeat`.

`break` exits the nearest enclosing loop. `continue` skips the rest of its body;
in `repeat`, it still evaluates the trailing condition. Invalid control outside
a loop and control crossing a runnable or isolated
batch boundary fail before submission effects. An inner loop can use its own
control within those boundaries.

Each iteration has a fresh scope. Ordinary mutation updates the nearest
existing binding; local declarations and iterator bindings disappear on exit.
Conditions run outside the body scope. Exit handlers run before scope release
on normal completion, control transfer, errors and cancellation.

```text
let x = 0
let samples = repeat {
    x += 1
    x
} until x >= 3
print samples

let selected = foreach item in [1, 2, 3, 4, 5] do {
    if item % 2 == 0 then continue
    if item == 5 then break
    item * 2
}
print selected
```

`samples` is `[1, 2, 3]`; `selected` is `[2, 6]`. Consumed loops collect the final
value of normally completed bodies. Empty bodies contribute `null`, assignments
contribute their assigned values, and continued or broken iterations contribute
nothing. Assignment suppresses ordinary body display. Standalone `while` and
`repeat` display final body values without building an unused result list;
standalone `foreach` keeps its existing collected-result behavior.

All loops share step limits and cancellation, including empty and constantly
continued bodies. Consumed results retain the existing item bound. Errors and
cancellation preserve an assignment target's previous value; earlier mutation,
explicit output and external effects persist. Existing cumulative retained-byte
accounting and parser-nesting admission gaps remain separate runtime work.
