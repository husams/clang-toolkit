# Optional callable labels and natural calls

Status: implemented and verified in the isolated worktree, 20 October 2026.
See [implementation and verification](callable-labels-progress.md), including
the initial full-suite results and successful focused reruns.
Isolated worktree: ~/.claude/worktrees/clang-toolkit/callable-labels-proposal.
Branch: codex/callable-labels-proposal; inspected base: 3076c60.

## Preferred syntax

Use a colon between the public label and the local parameter name. At a call
site, use the label as a word between arguments. Keep ordinary calls available.

~~~ctk
let multiply(value, by: m) = value * m

let x = multiply 5 by 6       // 30
let y = multiply(2, 4)        // 8
~~~

Here by is the public label; m is the local name used inside the block.
The value parameter has no explicit public label. Labels are optional at the
call site when using the conventional positional form.

This replaces the earlier recommendation of "label local" declarations and
"name = value" shorthand. The user preferred the natural wording above.

## More examples

~~~ctk
let multiply(value, by: m = 2) = value * m

let a = multiply 5 by 6       // 30
let b = multiply 5            // 10: default m
let c = multiply(2, 4)        // 8
let d = multiply(5)           // 10: same default

let clamp(value, between: low, and_max: high) = {
    if value < low then low else if value > high then high else value
}

let bounded = clamp 15 between 0 and_max 10  // 10
let ordinary = clamp(15, 0, 10)              // 10
~~~

The clamp labels are illustrative; do not use expression operators such as
"and" as word labels in the initial shorthand grammar.

~~~ctk
let describe(from: path, named: symbol, limit: maximum = 10) = {
    {source: path, symbol: symbol, limit: maximum}
}

let report = describe from "sample.cc" named "Box" limit 5
let defaults = describe from "sample.cc" named "Box"
let positional = describe("sample.cc", "Box", 5)
~~~

There may be zero or one leading unlabeled value in a natural call, followed
by labeled segments. Multiple unlabeled arguments keep ordinary parentheses.

## Binding rules

| Declaration | Name inside the block | Public named argument |
| --- | --- | --- |
| value | value | value = expression, as today |
| by: m | m | by = expression; or word form "by value" |
| by: m = 2 | m | optional value, defaulting to 2 |
| by: | by | by = expression; or word form "by value" |
| by: = 2 | by | optional value, defaulting to 2 |

Conventional named calls remain useful: multiply(5, by = 6) and
multiply(value = 5, by = 6). Keep the current equals spelling inside ordinary
calls; the requested colon belongs in the declaration. A colon spelling at
call sites would be a separate choice, not required by this proposal.

A labeled slot's public keyword is its external label, not a second alias for
its local name. Thus by names the second slot; m is local. Existing unlabeled
declarations retain their current local-name keywords. Adding a label to an
existing published function changes its named-argument API; positional calls
retain their meaning. Require unique local bindings and public keywords.

The first delivery covers simple-name parameters in ordinary named/inline
runnables. For example, (value, by: m) value * m is the corresponding inline
form. Labeled destructuring and grouped-clause keyword calls remain deferred;
existing grouped clauses retain their positional-call contract.

Validate duplicate/unknown labels, missing required values, positional/named
double supply and excess values before argument effects. Evaluate the callee
once, supplied arguments once in source order, then omitted defaults in
declaration order in the captured lexical frame. Preserve aliases, imports,
handlers, native-value ownership and execution limits.

Both execution engines, pipeline insertion and batch dependency admission must
share one label-to-slot resolver. Labels travel with callable metadata through
aliases, closures, imports, snapshots and cached IR.

## Whitespace-call boundaries

Parse the form structurally, without consulting a definition or signature:

~~~text
natural_call := NAME HORIZONTAL_SPACE [value] (label value)+
              | NAME HORIZONTAL_SPACE unambiguous_single_value
~~~

The parser records generic label segments. An unknown label remains a label:
"multiply 5 via 6" produces an unknown-label diagnostic before argument effects.
It must not acquire a different parse after callable lookup.

A whitespace value is a literal, reference, member/index access, an ordinary
parenthesized call, or an explicitly grouped expression. Group arithmetic and
predicates; use ordinary parenthesized calls for nesting:

~~~ctk
let a = multiply record.count by limits[0]
let b = multiply source() by factor()
let c = multiply (value + 1) by (factor + 2)
let d = multiply square(5) by square(6)
~~~

Do not silently decide whether an ungrouped operator belongs to an argument or
the call result. Write multiply 5 by (6 + 2), or multiply(5, 6) + 2.

Accept natural calls initially as whole expression statements and complete
let/ordinary-assignment right sides. In a brace body they can be the final
value-producing statement. Keep ordinary calls in conditions, interpolation,
collection elements and expression-bodied definitions. Pipeline stages also
support the labeled form described below. Use
ordinary calls for member/index callees such as operations[0](5, 6).

A physical newline or semicolon ends a natural call outside grouped values.
Require horizontal whitespace after the callee. Current expression productions
allow operator continuation across newlines, so the new value production must
enforce this boundary explicitly.

Preserve valid existing parses when there is no label tail:

~~~ctk
let operation = multiply     // Callable reference, not an implicit call.
ready()                      // Explicit zero-argument invocation.
items [0]                    // Existing indexing.
f (x)                        // Existing ordinary call.
value - 5                    // Existing subtraction.
~~~

An initial list/group can be a new whitespace argument when a following label
makes the full form explicit; otherwise existing indexing/calls win.
Likewise, multiply -5 by 6 can use a signed first value, while a lone f - 5
remains subtraction. Use f(-5) when no label tail disambiguates it.

Keep prefix-command precedence; callable names colliding with commands use
adjacent parentheses, such as read(path = p). Reserve expression operators and
structural delimiters such as and, or, in, is, then, do, else, until and on from
word-label position initially. Such external labels can still use conventional
named calls. Common labels such as by, from and to remain available.

## Colon conflict and migration

Before this implementation, the requested declaration parsed as a cons pattern,
not a label. This live command at the inspected base:

~~~ctk
let multiply(value, by: m) = value * m
print multiply(2, 4)
~~~

failed with:

~~~text
error: pattern by : m does not match int at line 1, column 47
~~~

Adopting the user's spelling therefore requires an explicit grammar change:
an ungrouped colon in a parameter list introduces a label. Preserve cons
patterns there with grouping:

~~~ctk
// Existing spelling needing migration:
let first(head : tail) = head

// Grouped cons pattern:
let first((head : tail)) = head

// Standalone destructuring retains its meaning:
let head : tail = [10, 20]
~~~

Grouped cons parameters work in both engines. This is a
documented compatibility change, not a claim that old cons signatures remain
unchanged. Audit and migrate examples, tests, helper libraries and grouped-clause
signatures when adopting this version. Repository examples, tests and guide
references have been migrated. No whitespace-sensitive colon heuristic,
body inspection, or signature-dependent call parsing should select the meaning.

## Delivery and verification

The implementation adds colon-label declarations and the bounded natural-call
grammar to the composed console parser. Conventional positional/named calls
remain available. Shared metadata and slot resolution cover tree and compiled
calls, dependency admission, cached libraries, aliases and pipeline insertion.
Help and completion display public labels and defaults. The native ANTLR
language is a separate scope.

Acceptance must include the user's exact two call forms, defaults, multiple
labels, unknown/duplicate labels before effects, reordered argument evaluation,
grouped expressions, command collisions, multiline boundaries, preserved
indexing/subtraction/references, and migrated cons patterns in both engines.
Run the repository's required full suites when implementing code.

The earlier baseline had 237 focused tests passing in 22.14 seconds; that is
historical evidence. The final example at
[examples/callable_labels.ctk](../examples/callable_labels.ctk) runs through the
real TTY-backed console in both engines and prints
CALLS_8_30_30_10_30_30_10_32_10. This covers ordinary positional/named calls,
word calls, explicit/default shorthand, pipelines and grouped cons parameters.
The [progress record](callable-labels-progress.md) tracks full-suite validation.

## Additional readability candidates

The user approved the first two additions for implementation alongside the
latest label/word-call revision. Trailing callbacks and null operators remain
separate, unapproved ideas outside this implementation.

### Natural pipeline stages (implemented)

~~~ctk
let multiply(value, by: m) = value * m
let add(value, to: amount) = value + amount

let result = 5
    | multiply by 6
    | add to 2                 // 32
~~~

Existing pipelines supply the input as positional slot zero and already support
newline-before-pipe layout. The new part is label/value stages without their
ordinary argument parentheses. Stage arguments are labeled only; an extra
unlabeled value would compete with the injected input. Reuse preflight and
atomic/grouped word-argument rules; an ungrouped pipe ends the stage. This is an
explicit extension to the baseline's restriction on natural calls in pipelines.

### Same-name public/local label shorthand (implemented)

~~~ctk
let multiply(value, by:) = value * by
let result = multiply 5 by 6    // 30

let double(value, by: = 2) = value * by
let defaulted = double 5       // 10
~~~

The shorthand by: expands to by: by. It introduces a required parameter, not a
default. It has the same uniqueness, slot-resolution and positional-call rules
as the explicit label form. Keep by: m when a different local name reads better.

### Trailing callable blocks in pipelines

~~~ctk
let doubled = [1, 2, 3] | map {
    (item) item * 2
}
~~~

The proposed result is [2, 4, 6]. The callable clause block already has an
existing representation; the new stage spelling expands to
map({ (item) item * 2 }). Initially accept one explicit callable clause with no
defaults or additional arguments. Keep ordinary calls in control headers where
the braces could compete with the body. Do not infer callable parameters from
the host function or introduce an implicit item variable.

### Null-safe access and null-only defaults

~~~ctk
let name = node?.qualified_name ?? "anonymous"
let count = supplied ?? 10
~~~

These operators are a separate expression-language proposal. Optional access
skips only a null receiver; it does not suppress undefined variables, missing
properties, unavailable/unrequested semantic fields or operation errors.
Fallback is lazy and applies only to null, preserving false, zero and empty
values. Evaluate the receiver/left operand once. Specify optional-chain scope
and token/precedence rules before implementation; a possible rule is ?? below
Boolean operators and above ternary, associating right. Complex fallback
expressions in word-call arguments require grouping.

Avoid indentation-sensitive continuation of a complete word call in this
round: it changes the agreed physical-newline boundary. Multiline pipelines
already provide a visible continuation marker.

The first two additions are implemented and exercised in the example script.
The callback and null-operator sections remain design examples only.

## Sources

- [User revision and fresh controls](/Users/husam/workspace/wiki/raw/2026-10-20-ctk-callable-labels-natural-call-revision.md).
- [Pinned source snapshot](/Users/husam/workspace/wiki/raw/2026-10-20-ctk-callable-labels-current-source.md).
- [Earlier baseline transcript](/Users/husam/workspace/wiki/raw/2026-10-20-ctk-callable-labels-live-baseline.md).
- [Readability-extension baseline](/Users/husam/workspace/wiki/raw/2026-10-20-ctk-readability-extension-baseline.md).
- [Implementation and validation](/Users/husam/workspace/wiki/raw/2026-10-20-ctk-callable-labels-implementation-validation.md).
- [Current runnable contract](runnable-let.md) and [list patterns](list-patterns.md).
- Wiki: [[pages/planning/clang-toolkit-callable-labels]].
