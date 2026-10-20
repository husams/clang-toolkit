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
let multiply(value, by: factor = 2) = value * factor
let ready() = true
inc(4)
add_if(2, 5)
multiply(2, 4)
multiply 5 by 6
multiply(5, by = 6)
multiply(5)
```

These calls return `5`, `7`, `8`, `30`, `30` and `10`. In a labeled declaration,
`by` is the public keyword and `factor` is the local name in the body. The
same-name shorthand `by:` binds a local also named `by`. Defaults work in
ordinary positional calls, conventional named calls and word calls. Word calls
accept at most one leading positional value, then labeled values; use ordinary
parentheses for multiple positional arguments or to group compound values.
Completion and help display public labels; named and pipeline argument
completion suggest those public names. A word call is a complete expression
statement or the right side of `let`/ordinary assignment; use regular calls in
conditions, collections, interpolation, and other nested expressions. Its
whitespace arguments are atomic values such as `record.count`, `limits[0]`, or
`source()`. Group operators and predicates explicitly, as in
`multiply (value + 1) by (factor + 2)`; an ungrouped operator stays outside the
call. Word labels cannot be expression or structural keywords such as `and`,
`or`, `in`, `is`, `then`, `do`, `else`, `until`, or `on`; those labels remain
available in conventional named calls. Prefix commands keep their precedence,
so use an adjacent call such as `read(path = p)` when a runnable shares a
command's name. A physical newline or semicolon ends a word call outside an
explicitly grouped value.

Use braces for multiple statements or prefix handlers; expression bodies can use
`EXPR on error FALLBACK`. Existing direct
built-in matcher definitions keep their template behavior; wrappers calling a
custom matcher use ordinary runnable calls and can still return matchers.

Inline runnable values omit `let` and the name. Pass one directly as an
argument with `(PARAM, ...) EXPR` or `(PARAM, ...) { STATEMENTS }`:

```ctk
let apply(operation, value) = operation(value)
apply((x) x + 1, 5)
apply((x) { on error 0; x + 1 }, 5)
let run(operation) = operation()
run(() 42)
```

Both `apply` calls return `6`; `run` returns `42`. Inline definitions create a
dormant callable without adding a binding. They compile their expression or
brace body to Python functions and share named runnables' defaults, handlers,
lexical captures, fresh call frames and checked execution limits. Use `()` for
zero parameters. An expression body extends through the complete expression;
a following argument comma or enclosing delimiter ends it.

A grouped callable block can follow a callee or its argument list:

```ctk
let transform(value, using: operation, by: = 2) = operation(value) * by
let a = transform(5) { (item) item + 1 }
let b = 5 | transform { (item) item + 1 }
let c = transform(5, by = 3) { (item) item + 1 }
let d = 5 | transform by 3 { (item) item + 1 }
let normal = transform(5, { (item) item + 1 }, by = 3)
```

These return `12`, `12`, `18`, `18` and `18`. The trailing block is the final
positional argument, placed before named options for ordinary argument binding.
Pipeline input still supplies the first argument. This also works with callable
aliases and expressions such as `operations[0](5) { (item) item + 1 }`.
The opening brace must be on the same physical line as the callee or closing
parenthesis; the block itself can span lines. Use explicit parameters inside
the braces: `{ (item) item + 1 }`, or `{ (item) { STATEMENTS } }` for a body
with several statements. Existing grouped-clause pattern rules apply, including
equal arities and no defaults inside the grouped callback. Normal calls and
labeled callback arguments such as `transform 5 using { (item) item + 1 }`
remain available. See the complete [example](../examples/trailing_callable_blocks.ctk).

Command value and path operands accept full expressions, including callbacks,
pipelines, conditionals and computed paths. For example,
`save (items | map((x) x * 2)) to (directory + "/report.json") as json`.
Prefix commands separate their operand with whitespace: `read (path + suffix)`;
adjacent `read(value)` is a callable invocation when `read` names a runnable.
The older inline `=` spelling remains accepted. Ordinary grouping and calls
take precedence over ambiguous inline bodies: `(x) - 1` subtracts one and
`(f)(x)` invokes f. Use `(x) { -x }` for a callback starting with a unary operator.

Inline callables can also be assigned, stored in collections and returned:

```ctk
let make_adder(base) = (value, extra = base) value + extra
let add_ten = make_adder(10)
add_ten(5)
```

This returns `15`, retaining `base` after `make_adder` finishes. Callable
expressions can be invoked directly: `make_adder(10)(5)`, `operations[0](5)`,
and `record.operation(5)`. The callee runs once, and argument validation
precedes argument effects, as with named calls.
Inline bodies form the same loop-control boundary as named bodies. Foreground
batches inspect reachable inline callbacks before admission and snapshot their
captures; dormant bodies do not request native work.

An ungrouped colon in a runnable parameter is a public label: in
`let first(head : tail) = tail`, `head` is the public keyword and `tail` is the
local parameter. To match a cons pattern there, group it:
`let first((head : tail)) = head`. Inline callbacks
and grouped clauses use the same extra grouping, such as
`map(((head : tail)) head)` and `let first = { ((head : tail)) head }`.
Standalone destructuring (`let head : tail = values`) and `foreach` cons
patterns retain their existing form.

List patterns and grouped multi-clause functions are described in
[List patterns](list-patterns.md), with a complete [example](../examples/list_patterns.ctk).
Exact list, cons and tuple patterns work in named and inline runnable parameters.
Grouped clauses try patterns in order and preserve existing `let` rebinding.

Defaults are optional trailing parameters. An omitted default is evaluated once
per call, left to right, after supplied arguments, in the definition's lexical
call frame. It can use earlier parameters. Mutable defaults are fresh values;
explicit arguments skip their defaults. Required parameters precede defaults.

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
recursive self calls. Nested closures can retain completed call frames.
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
