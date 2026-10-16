# Reusable let bodies

The default compiled console accepts named runnable definitions alongside values
and custom matcher definitions. Both parameterized and zero-parameter bodies use
let signatures:

```ctk
let scale(value, factor) = { value * factor }
let announce() = { print "ready" }
let answer = scale(6, 7)
announce()
print "answer={answer}"
```

Braces are optional for a single expression. The expression is dormant until
called and its value is the result. Calls, defaults and conditionals use the
same Python compiler, lexical scopes and execution limits as brace bodies.

```ctk
let add(l, r = 1) = l + r
let inc(x) = add(x, 1)
let add_if(l, h) = if l < h then l + h else 0
let ready() = true
inc(4)
add_if(2, 5)
```

These calls return `5` and `7`. Use braces for multiple statements or prefix
handlers; expression bodies can use `EXPR on error FALLBACK`. Existing direct
built-in matcher definitions keep their template behavior; wrappers calling a
custom matcher use ordinary runnable calls and can still return matchers.

Inline runnable values omit `let` and the name. Pass one directly as an
argument with `(PARAM, ...) = EXPR` or `(PARAM, ...) = { STATEMENTS }`:

```ctk
let apply(operation, value) = operation(value)
apply((x) = x + 1, 5)
apply((x) = { on error 0; x + 1 }, 5)
let run(operation) = operation()
run(() = 42)
```

Both `apply` calls return `6`; `run` returns `42`. Inline definitions create a
dormant callable without adding a binding. They compile their expression or
brace body to Python functions and share named runnables' defaults, handlers,
lexical captures, fresh call frames and checked execution limits. Use `()` for
zero parameters. An expression body extends through the complete expression;
a following argument comma or enclosing delimiter ends it.

For host commands such as `print` or `save`, assign an inline callback or its
result with `let` first; those commands still have legacy operand parsing and do
not accept an inline definition in every argument position. For example, use
`let result = apply((x) = x + 1, 5)` followed by `print result`.

Inline callables can also be assigned, stored in collections and returned:

```ctk
let make_adder(base) = (value, extra = base) = value + extra
let add_ten = make_adder(10)
add_ten(5)
```

This returns `15`, retaining `base` after `make_adder` finishes. Invocation uses
a callable's bound name; assign a returned or indexed value before invoking it.
`make_adder(10)(5)` and `operations[0](5)` are not supported call forms.
Inline bodies form the same loop-control boundary as named bodies. Foreground
batches inspect reachable inline callbacks before admission and snapshot their
captures; dormant bodies do not request native work.

Defaults are optional trailing parameters. An omitted default is evaluated once
per call, left to right, after supplied arguments, in the definition's lexical
call frame. It can use earlier parameters. Mutable default literals create fresh values; a default that refers to an existing
container retains its normal alias. Explicit arguments skip their defaults. Required parameters precede defaults.

```ctk
let divide(lhs, rhs = 1) = {
    on error 0
    on exit { print "cleanup" }
    lhs / rhs
}
divide(10)
divide(10, 0)
(1 / 0) on error { print "fallback"; 7 }
```

Both handlers are optional. Declare them once at the beginning of a brace body,
in either order. Each accepts an expression or a statement block. The error
handler runs only on an ordinary error and supplies the body result; it does
not resume the failed statement. The exit handler runs after success, recovery,
or failure, while body locals remain in scope. Its result is ignored. A handler
failure propagates and can be caught by an enclosing body or call-site fallback.
A call-site fallback handles only errors that escape the called body; it is lazy.
A call-site fallback block has its own local scope, like other expression blocks.
Defaults and argument failures occur before entering the runnable body, so use
a call-site fallback to recover from those failures.

```ctk
let values = foreach item in [2, 0, 5] do {
    on error continue
    on exit { print "finished {item}" }
    10 / item
}
let prefix = foreach item in [2, 0, 5] do {
    on error { break }
    10 / item
}
```

The first loop collects `[5.0, 2.0]`; the second collects `[5.0]`. Break stops the
nearest lexical loop; continue skips the failed iteration without appending a
result. Iteration cleanup runs before either transfer. Runnable definitions form
a new control boundary: they cannot break or continue a caller's loop.

Cancellation, step/item limits and call-depth limits cannot be recovered. Cleanup
uses the ordinary step budget first, then a shared emergency reserve of at most 10,000 execution steps per submission, with
cancellation deferred during cleanup; output/item and call-depth limits still
apply. Exhausting cleanup's reserve raises an execution-limit error. Its work
still counts in the submission's total steps, and cannot turn a terminal failure
into success. No handler runs if execution never enters its body.

Names are bare identifiers in expressions, matcher arguments, fields, indexes,
mutation targets and command operands. There is no extra declaration keyword.
Double quotes interpolate expressions in braces; doubled braces are literal.
Single quotes retain literal text.

Bodies are parsed by the combined Lark grammar into the same IR as expressions.
The Python AST compiler emits a function for each body, using the existing
checked expression, loop and host-operation helpers. Definitions bind dormant
values; calls invoke retained compiled functions directly. Submission cache
eviction does not invalidate their code or compiled interpolation expressions.

Each call has fresh parameters and locals and returns its final statement value.
An empty body returns null. Captures retain the definition's lexical scopes by
reference. Aliases keep their original function through redefinition, including
recursive self calls. Nested closures can retain completed call frames. An inner
body sees its own parameters/locals, enclosing definition scopes and session
bindings; caller-only locals are not visible. `let` shadows in the current scope,
while assignment updates an existing captured binding.
Callee and arity checks precede argument effects; arguments execute once, left
to right. Calls share the submission's cancellation, step and output limits and
the matcher/runnable call-depth limit of 64. Errors retain definition and call
locations, including the library filename for imported definitions.

```ctk
let named(name) = functionDecl(hasName(name))
let find(path, name) = { match named(name).bind("f") in path }
let operation = find
let rows = operation("sample.cc", "Sample")
print "found={rows.length}"
```

Assignment consumes body output in the same way as existing expressions. Native
operations and explicit file writes still run. Standalone calls display their
final value without repeating an already displayed final statement.

Imports and console library preloads use the combined grammar, validate complete
libraries before execution and restore bindings and plain containers on failure.
Runnable definitions and aliases remain dormant while loading. The reference
tree engine accepts the same syntax for comparison; the default engine compiles
to Python AST.

Foreground batch bodies also compile to Python AST. Each group snapshots plain
values and captured callable scopes, preserving aliases and recursion. Reachable
call bodies are inspected before admission; native command checks also apply
during execution. Callable values cannot be exported or retained in batch
results. Dynamic ctk command strings are unsupported inside foreground groups.
Native handle lifetimes and ownership checks continue to apply.

The native server's independent ANTLR script engine and durable/background batch
language do not compile these Python bodies. This implementation does not add
native language parity. Existing prefixed-reference scripts remain accepted for
compatibility; new examples, help and completion use bare names.

## Filters and tuple callbacks

An ordinary runnable can serve as a filter: the pipeline supplies its first
argument. Tuple patterns also work in named parameters.

```ctk
let my_filter(input, arg) = input + arg
print 10 | my_filter(1)
let describe((name, count), prefix = "") = "{prefix}{name}: {count}"
print ("Widget", 5) | describe("item: ")
let labels = [("Widget", 5)] | map((name, count) = "{name}: {count}")
```

Use the same `(name, count) = ...` form with `filter`, `sort_by` and `unique_by`.
Two or more required callback parameters spread a tuple; a unary callback,
including one with optional trailing defaults, receives the whole item.
See [pipes.md](pipes.md) for shape checks, formatting and a complete report.

## Using callbacks with the bundled library

```ctk
import "/Users/husam/.codex/skills/ctk-script/scripts/ctk_helpers.ctk"
let doubled = [1, 2, 3] | map((x) = x * 2)
let selected = doubled | filter((x) = x > 2)
print selected | json
```

`selected` holds `[4, 6]`; `json` renders a single JSON array. Resolve the import
path from the active skill installation.
`mapValues(items, callback)` and `filterValues(items, callback)` remain compatible
bundled functions, implemented with pipes. They always pass one complete item,
including tuples; built-in `map` and `filter` support automatic tuple spreading.
An inline brace body can perform several steps and use optional handlers.

## Maintained sources

- `docs/runnable-let.md`
- `python/clang_toolkit/cli/runtime/prototype/{grammar.lark,repl_language.py,syntax.py,compiler.py,runnables.py,semantics.py,dependencies.py}`
- `tests/unit/test_inline_runnables.py` and `tests/unit/test_runnable_*.py`
- `tests/e2e/test_prototype_repl_steps.py`
