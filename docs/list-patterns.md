# List patterns and grouped function clauses

The compiled and tree console engines support destructuring in `let`, runnable
parameters and `foreach`. The native server script language is unchanged.

```ctk
let [a, b] = [10, 20]
let (name, count) = ("Widget", 3)
let head : tail = [10, 20, 30]
let first(head : _) = head
let add_first_two(a : b : _) = a + b
let heads = [[10, 20], [30, 40]] | map((head : _) head)
```

`[]`, `[x]`, and `[x, y]` match lists of exactly zero, one and two elements.
`head : tail` matches a non-empty list; `:` associates to the right, so
`a : b : rest` requires at least two elements. Tuple patterns match tuples;
list patterns match lists. Patterns can nest and `_` discards a value.
Duplicate binding names are rejected. A destructuring mismatch binds nothing,
and the right-hand expression is evaluated once. A bound tail is a new shallow
list, so mutating it leaves the original list unchanged; elements retain their
existing identity, including native handles. A discarded tail is not copied.

Group ordered clauses in one declaration:

```ctk
let total = {
    ([]) 0
    (head : tail) head + total(tail)
}
print total([10, 20, 30])
```

This prints `60`. Clauses have equal positional arity, do not have defaults,
and try patterns from top to bottom. All supplied argument expressions are
evaluated once after argument-count validation. A matching body runs once;
its errors do not fall through to another clause. No match reports an error.
Ordinary named and inline functions retain their existing defaults and named
arguments. Existing `let` declarations still rebind, rather than accumulate
clauses. Grouped functions may be aliased, returned, stored and used as pipeline
callbacks. Their bodies and defaults remain dormant during admission inspection
and library loading.

## Python compilation and limits

Patterns compile once to Python type, length and index checks, cached by pattern.
All shape checks precede tail allocation and binding. Clause bodies use the
existing Python-AST compiler; dispatch never interprets a body syntax tree in
the compiled engine.

The exact pure numeric right-fold form shown for `total` compiles to an indexed
loop. It uses linear time and constant additional space, with no recursive
Python frames or list-tail copies. Arithmetic still runs from right to left,
preserving floating-point order and checked integer overflow. Execution steps
and cancellation checks remain enforced. Other direct self-recursive list
functions can use generated continuation loops and internal indexed tails; see
[recursive list functions](recursive-lists.md) for supported forms and semantic
fallbacks. Escaping tails remain independent shallow lists.

Run [the complete example](../examples/list_patterns.ctk) in the console. Paste
the whole script and press Ctrl+J; Ctrl+Enter or macOS Option+Enter inserts lines
while typing.

Actual output from the complete example in the real console (both compiled and
tree engines):

```text
60
0
30
[10,30]
Destructured: 10, 20, 30
Large total: 12497500
```
