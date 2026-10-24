# Console pipelines, tuples, and filters

## Finding help

Bare `help` lists pipeline syntax and every built-in callable. Use `help pipes`
for the `|` operator, `help callables` for the catalog, and `help NAME` or `NAME?`
for a callable's purpose, ordinary and pipeline signatures, arguments, defaults,
and self-contained examples. All help works without a server in both plain and
workspace consoles. For example:

```ctk
help pipes
help map
first?
help sort_by
help let
```

The [complete callable reference](console-command-reference.md#built-in-callable-reference)
is generated from the same help metadata. It includes every registered filter
below plus `len(value)`, `range(stop)` / `range(start, stop, step)`, and
`ctk(command)` for dynamic console commands. Use `help let` for user-defined
runnables, inline and trailing callbacks, defaults, public labels and closures;
`help NAME` shows the active local definition when a built-in is shadowed.

## List selection

Compiled and tree consoles support negative indexing and Python-style slices:

```ctk
let xs = [10, 20, 30, 40, 50]
print xs[-1]              // 50
print xs[1:4]             // [20, 30, 40]
print xs[-3:]             // [30, 40, 50]
print xs[::2]             // [10, 30, 50]
print xs[::-1]            // [50, 40, 30, 20, 10]
print xs | first          // 10
print xs | last(2)        // [40, 50]
print xs | reverse        // [50, 40, 30, 20, 10]
```

Indexes are zero-based; negative indexes count from the end. Out-of-range
indexes fail. Slices use an exclusive stop and clamp out-of-range bounds.
Start, stop and step must be integers when supplied; booleans and null are
invalid, and step cannot be zero. With a negative step, an omitted stop is
before the first element: `xs[3::-1]` includes position zero, while
`xs[3:0:-1]` excludes it. An explicit `-1` stop denotes the last position;
`xs[:-1:-1]` therefore returns `[]`.

`first` and `last` return a scalar or null on empty input. `first(n)` and
`last(n)` always return lists, with up to n elements and nonnegative integer
counts. `last(0)` returns `[]`; `last(n)` preserves the original order.
This changes the earlier empty-input behavior, which raised an error.
Use `[0]` or `[-1]` when emptiness should fail, and `first(1)` or `last(1)`
to distinguish `[]` from `[null]`.

Slices and selection filters require finite lists, tuples or supported native
collection views, and return shallow lists without changing the source.
Native rows retain their handles and can be used for follow-up matching.
Selection covers available rows only; check the original query's completion
and truncation status. Convert arbitrary iterators explicitly with `to_list`
before selection. Slice assignment is unsupported. These forms do not extend
native server scripts or server-side batch bodies.

## Pipelines

The compiled and tree interactive consoles can compose local values with `|`.
A pipeline passes the value on its left as the first argument to the callable
on its right. Each stage returns the value passed to the next stage:

```ctk
let names = ["Widget", "Empty", "Widget", "Other"]
let counts = [2, 0, 5, 2]
let report = names
    | zip(counts)
    | filter((name, count) count > 0)
    | sort_by((name, count) count, reverse = true)
    | unique_by((name, count) name)
    | map((name, count) {name: name, count: count})
print report | json(indent = 2)
```

Expected output:

```json
[
  {
    "name": "Widget",
    "count": 5
  },
  {
    "name": "Other",
    "count": 2
  }
]
```

`zip` pairs corresponding values as tuples. A callback with two or
more required parameters receives the tuple elements as separate arguments;
a unary callback receives the complete item, so defaults keep an optional
second parameter from changing that rule.

Callbacks can be inline expressions or named console runnables. A named
runnable can use an explicit tuple parameter followed by ordinary parameters:

```ctk
let my_filter(input, arg) = input + arg
print 10 | my_filter(1)
let describe((name, count), prefix = "") = prefix + name
print ("Widget", 5) | describe("item: ")
let multiply(value, by: factor = 2) = value * factor
let add(value, to: amount) = value + amount
print 5 | multiply by 6 | add to 2
```

This prints `32`. For a labeled runnable parameter, the label is public and
the following name is local: `by` is the keyword and `factor` is available
inside `multiply`. The same-name shorthand `by:` binds local `by`; it can also
have a default, as in `let scale(value, by: = 2) = value * by`. Word calls such
as `multiply 5 by 6` accept at most one leading positional value and then
labeled values; ordinary calls such as `multiply(5, by = 6)` and positional
calls such as `multiply(2, 4)` remain available. Pipeline input supplies slot
zero, so natural pipeline stages accept labeled arguments only: write
`5 | multiply by 6`, with no extra unlabeled argument. Group compound values
and use ordinary parentheses for multiple positional arguments. Whitespace
arguments may be atomic postfix values such as `record.count`, `limits[0]`, or
`source()`; group arithmetic and predicates, for example
`multiply (value + 1) by (factor + 2)`. Reserved expression and structural
words (`and`, `or`, `in`, `is`, `then`, `do`, `else`, `until`, and `on`) cannot
appear as word labels, though conventional named calls can use those labels.
Tab completion offers public labels.

Trailing callable blocks make longer callback pipelines easier to read:

```ctk
let selected = [1, 2, 3, 4]
    | filter { (item) item > 2 }
    | map { (item) item * 10 }
let descending = selected | sort_by(reverse = true) { (item) item }
let normal = map(filter([1, 2, 3, 4], { (item) item > 2 }), { (item) item * 10 })
```

`selected` and `normal` are `[30, 40]`; `descending` is `[40, 30]`.
The trailing block supplies the final positional argument before named options,
so `items | sort_by(reverse = true) { (item) item }` is equivalent to
`sort_by(items, { (item) item }, reverse = true)`. Start the opening brace on
the same line as the stage name or its closing parenthesis. Each block has
explicit parameters and can contain a statement body such as
`map { (item) { let doubled = item * 2; doubled + 1 } }`.

An ungrouped parameter colon now introduces a label: in
`let first(head : tail) = tail`, `head` is the public keyword and `tail` is
the local parameter. Group cons callback patterns, for example
`map(((head : tail)) head)`. Standalone and `foreach` cons patterns retain
their existing spelling.

Tuple values can be unpacked directly by `foreach`:

```ctk
let pairs = [("Widget", 5), ("Other", 2)]
foreach (name, count) in pairs do {
    print name
    print count
}
foreach (index, (name, _)) in (pairs | enumerate) do {
    print "{index}: {name}"
}
```

Use `()` for an empty tuple, `(value,)` for a singleton, and `(a, b)` for a
pair. Tuple patterns require matching tuple shapes; `_` discards an element.
Loop bindings stay local to each iteration.

Pipelines evaluate eagerly from left to right. Each stage receives its input
once, and `print` prints the final value once. A leading `|` continues the
preceding expression across newlines, including blank and comment-only lines;
outer parentheses are optional. A semicolon always ends the statement.
`on error` applies to the whole preceding pipeline:

```ctk
print 10 | my_filter(1) | json
print "value" | missing_filter on error "fallback"
```

Collection filters include `map`, `filter`, `take`, `drop`, `flatten`, `zip`,
`zip_longest`, `enumerate`, `first`, `last`, `length`, `reverse`, `sort`,
`sort_by`, `unique`, `unique_by`, `to_list`, and `to_tuple`. `zip` requires
equal lengths unless `strict=false`; `zip_longest` accepts `fill=null`.
`filter` requires boolean callback results. Sorting is stable and accepts
finite numbers or strings; deduplication keeps the first matching item.

Record filters are `keys`, `values`, `entries`, and `pick("name", "count")`.
`entries` produces records with `key` and `value` fields. String filters
include `upper`, `lower`, `casefold`, `camel_case`, `pascal_case`, `snake_case`,
`kebab_case`, `split_by`, `join`, `trim`, `trim_start`, `trim_end`, `replace`,
`strip_prefix`, `strip_suffix`, `starts_with`, `ends_with`, and `contains`.

`pretty` produces a bounded preview; `table(columns=["name", "count"])`
formats selected record fields. Both show omission markers when clipped.
`json(indent=2)` returns complete JSON or an error, with tuples represented
as JSON arrays. Collection visits and callback execution use the current
submission's item, step, and cancellation limits.

Pretty and table previews are limited to 20,000 characters; JSON output is
limited to 1 MiB of UTF-8 text. Format native results into ordinary records
with `map` before JSON serialization or table rendering.

When editing a pipeline, Tab completion suggests callable stages after `|`.
Callable hints show the signatures for built-in stages and user-defined
runnables. `help pipes` describes the pipeline syntax and examples offline.

These features belong to the compiled interactive console language. They do
not add pipeline, tuple, or filter syntax to `script "..."`, native server
scripts, or server-side batch bodies.
