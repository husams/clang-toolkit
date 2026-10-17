# List patterns in console scripts

Compiled and tree console engines support these forms; native server scripts
retain their separate language.

```ctk
let [a, b] = [10, 20]
let head : tail = [10, 20, 30]
let first(head : _) = head
let heads = [[1, 2], [3, 4]] | map((head : _) head)
let total = {
    ([]) 0
    (head : tail) head + total(tail)
}
print total([10, 20, 30])
```

The output is `60`. Lists and tuples have distinct exact patterns. `:` associates
right; `_` discards without binding. Patterns may nest, but names cannot repeat.
Destructuring evaluates its input once and binds nothing on a mismatch. Named
tails are independent shallow lists; discarded tails are not copied.

Grouped clauses have equal positional arity and no defaults. They match in source
order, execute only the selected body, and report an error if no clause matches.
Body errors do not fall through. Ordinary runnable defaults and named arguments
remain supported. Repeating `let` still rebinds rather than accumulating clauses.

Patterns compile to cached Python type/length/index checks. The exact pure numeric
right-fold form above uses an indexed loop, with right-to-left checked arithmetic,
execution budgets and cancellation preserved. Other recursion keeps the ordinary
depth limit for unsupported forms. Direct recursive list functions also support
compiled continuation loops and indexed internal tails; see
`docs/recursive-lists.md` and `examples/recursive_lists.ctk`. Observable tails
materialize as real shallow lists, and opaque effects snapshot shared backings.

Maintained sources: `docs/list-patterns.md`, `examples/list_patterns.ctk`,
`tests/unit/test_list_patterns.py`, `tests/e2e/test_list_patterns_steps.py`.
