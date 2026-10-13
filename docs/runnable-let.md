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
