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
