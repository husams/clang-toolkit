# Pipes, tuples and structured output

Use the compiled console (`ctk` default) or `--script-engine tree`. Legacy mode,
native `script "..."`, SDK `run_script`, and durable/background server batch
bodies do not support this syntax. `help pipes` works offline; Tab after `|`
completes callable stages and shows signatures.

## Parameterized filters

A stage receives the preceding value as its first argument. Bare stages mean a
call with no additional arguments. Ordinary console runnables are user-defined
filters; no registration or separate declaration is required.

```ctk
let my_filter(input, arg) = input + arg
print 10 | my_filter(1)
let prefixed(input, prefix = "item: ") = prefix + input
print "widget" | upper | prefixed(prefix = "class: ")
let multiply(value, by: factor = 2) = value * factor
let add(value, to: amount) = value + amount
print 5 | multiply by 6 | add to 2
```

Output is `11`, then `class: WIDGET`; the final chain result is `32`. `by` is
the public keyword and `factor` is the local name. The shorthand `by:` uses the
same name for both, and it can have a default, as in
`let scale(value, by: = 2) = value * by`. Word calls such as
`multiply 5 by 6` accept one leading positional value followed by labeled
values; ordinary calls such as `multiply(5, by = 6)` and `multiply(2, 4)` remain
available. A pipe supplies slot zero, so natural stages take labeled arguments
only: write `5 | multiply by 6`, with no extra unlabeled argument. Group
compound values and use ordinary parentheses for multiple positional arguments.
Whitespace arguments may be atomic postfix values such as `record.count`,
`limits[0]`, or `source()`; group arithmetic and predicates, for example
`multiply (value + 1) by (factor + 2)`. Expression and structural words (`and`,
`or`, `in`, `is`, `then`, `do`, `else`, `until`, and `on`) cannot be word
labels, though conventional named calls can use those labels. Tab completes
public labels in named calls and pipeline stages. Functions retain ordinary
lexical scope, defaults and named arguments. Built-in names can be shadowed; choose helper names
that do not hide filters you intend to call.

Pipes evaluate eagerly once per stage, from left to right. They bind below
arithmetic, Boolean and conditional expressions. A leading `|` continues a
pipeline across newlines without outer parentheses. A semicolon ends the
statement. While typing, use Ctrl+Enter or Option+Enter (macOS) to add a line
before another `|` stage, then Enter at the end to execute; Ctrl+J executes the
whole draft from any cursor position. A trailing `|` automatically requests a
continuation line on Enter. Terminals must report modified Return distinctly;
Alt+Enter or Escape then Enter is an alternative. `on error` applies to the
whole preceding pipeline. Execution budgets and cancellation still apply;
`take(3)` does not prevent earlier eager stages from processing their input.
Command value and path operands accept full expressions, so a pipeline can be
passed directly: `save (rows | map(project)) to "report.json" as json`.

## Tuples and callback unpacking

Use `()` for an empty tuple, `(value,)` for a singleton and `(a, b)` for a pair.
Tuples are immutable, support checked indexing, and render as arrays through the
`json` filter. The older structured `save` path does not accept tuples; convert
them explicitly before saving, for example `let saved = pairs | map(to_list)`.

`zip(other, *others, strict = true)` produces tuples and requires equal lengths
by default. `strict = false` stops at the shortest input.
`zip_longest(other, *others, fill = null)` fills missing positions.

```ctk
let pairs = ["Widget", "Other"] | zip([5, 2])
foreach (name, count) in pairs do print "{name}: {count}"
foreach (index, (name, _)) in (pairs | enumerate) do print "{index}: {name}"
let describe((name, count), prefix = "") = "{prefix}{name}: {count}"
print ("Widget", 5) | describe("item: ")
```

Tuple patterns can nest, require exact tuple shapes and use `_` to discard a
slot. Bindings are local to an iteration or call. For `map`, `filter`, `sort_by`
and `unique_by`, use the simplified callback form:

```ctk
let selected = pairs | filter((name, count) = count > 0)
let ordered = selected | sort_by((name, count) = count, reverse = true)
let distinct = ordered | unique_by((name, count) = name)
let labels = distinct | map((name, count) = "{name}: {count}")
```

An ungrouped colon in a runnable parameter now introduces a label: in
`let first(head : tail) = tail`, `head` is the public keyword and `tail` is
the local parameter. Group cons patterns in callbacks, such as
`map(((head : tail)) head)`; standalone and `foreach` cons patterns keep
`head : tail`.

A callback with two or more required parameters receives tuple elements as
arguments. A unary callback receives the complete item; optional trailing
parameters keep that rule: `(pair, suffix = "!") = pair[0] + suffix` receives
one tuple. To explicitly match a nested tuple in one parameter, use a tuple
pattern such as `let describe((name, count)) = ...`. A shape or arity mismatch
raises an error before that item's callback body executes. `filter` callbacks
must return Boolean values.

## Complete report

Run [pipe_report.ctk](../scripts/pipe_report.ctk) using its resolved absolute
path: `ctk --script-engine compiled --script /absolute/path/pipe_report.ctk`.
It needs no C++ fixture and combines a parameterized user filter with `zip`,
`filter`, `sort_by`, `unique_by` and `map`:

```ctk
let prefixed(input, prefix) = prefix + input
let names = ["Widget", "Empty", "Widget", "Other"]
let counts = [2, 0, 5, 2]
let report = names
    | zip(counts)
    | filter((name, count) count > 0)
    | sort_by((name, count) count, reverse = true)
    | unique_by((name, count) name)
    | map((name, count) {name: name | snake_case | prefixed("class_"), count: count})
print report | json(indent = 2)
```

Expected output:

```json
[
  {
    "name": "class_widget",
    "count": 5
  },
  {
    "name": "class_other",
    "count": 2
  }
]
```

Sorting is stable; `unique_by` keeps the first item for each key, so the highest
count for `Widget` survives. Unary callbacks also work with ordinary records or
native rows: `rows | map((row) = {name: row.f.qualified_name})`.

## Available stages

| Purpose | Filters |
| --- | --- |
| Transform/select | `map(callback)`, `filter(callback)`, `take(n)`, `drop(n)`, `flatten` (one level) |
| Pair/index | `zip(other, *others, strict = true)`, `zip_longest(other, *others, fill = null)`, `enumerate(start = 0)` |
| Order/deduplicate | `sort(reverse = false)`, `sort_by(callback, reverse = false)`, `unique`, `unique_by(callback)` |
| Inspect/convert | `length`, `first`, `last`, `reverse`, `to_list`, `to_tuple` |
| Records | `keys`, `values`, `entries`, `pick("name", "count")` |
| Words/case | `upper`, `lower`, `casefold`, `camel_case`, `pascal_case`, `snake_case`, `kebab_case` |
| Text | `split_by(separator)`, `join(separator = "")`, `trim`, `trim_start`, `trim_end`, `replace(old, new, count = -1)`, `strip_prefix(prefix)`, `strip_suffix(suffix)` |
| Text predicates | `starts_with(part)`, `ends_with(part)`, `contains(part)` |
| Output | `pretty(indent = 2, depth = 8, max_items = 100)`, `json(indent = 0)`, `table(columns = ["name", "count"], max_items = 100)` |

`entries` produces records `{key, value}`, not tuples. `first` and `last` return
null on empty input; `first(n)` and `last(n)` return lists of up to n items.
`last(n)` preserves original order, including `last(0)` returning `[]`.
Selection requires finite lists, tuples or supported retained collection views;
arbitrary iterators must be explicitly materialized with `to_list` first.
Sorting keys must be finite numbers or strings; convert complex
records with `map` and choose explicit keys for ordering or deduplication.
`unique` supports typed scalar/tuple keys, rather than arbitrary records.

`pretty` and `table` are previews with omission markers, bounded to 20,000
characters. `json` produces complete ordinary JSON or an error, bounded to 1 MiB
of UTF-8. Project native values to ordinary records before JSON/table output;
keep the original live result for subsequent native continuation. Formatting
does not expand unrequested AST fields or run extra queries.

## Maintained sources

- `docs/pipe-filters.md`
- `python/clang_toolkit/cli/runtime/prototype/{grammar.lark,filters.py,runnables.py}`
- `tests/unit/test_pipe_{language,filters,repl,completion}.py`
- `tests/unit/test_tuple_patterns.py`
- `tests/e2e/test_pipe_filters_steps.py`
- `tests/e2e/test_ctk_skill_helpers_steps.py`
