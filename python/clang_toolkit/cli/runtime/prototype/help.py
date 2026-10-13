"""Local help for predicates exposed by the prototype consoles."""

from __future__ import annotations

from typing import Any

from clang_toolkit.cli import help as legacy_help

_PLAIN = """Value predicates (prototype)
$record has a / $record does not have a
  Test dictionary key or semantic-field presence; null-valued keys are present.
2 in $items / 2 not in $items
  Search a list using checked scalar equality and stop at the first match.
$node is CXXRecord / $node is not CXXRecord
  Test one selected node's exact semantic kind; CXXRecord aliases CXXRecordDecl.
$x is defined / $x is not defined
  Test root-variable existence without reading a missing binding.
$x is set / $x is not set
  Test existence and a non-null value; false, zero and empty values are set.
Use bare/quoted field names or a grouped dynamic key: $record has ($key).
Predicates return booleans and work with if/else, unless, ?:, and and/or/not.
Native unrequested/unavailable fields keep their diagnostic; use fieldState.
""".replace("$", "")

_MARKDOWN = """# Value predicates (prototype)

| Test | Syntax |
| --- | --- |
| Field presence | `$record has a` / `$record does not have a` |
| List membership | `2 in $items` / `2 not in $items` |
| Exact node kind | `$node is CXXRecord` / `$node is not CXXRecord` |
| Binding existence | `$x is defined` / `$x is not defined` |
| Non-null binding | `$x is set` / `$x is not set` |

A null-valued dictionary key is present. Quote a field name or group a dynamic
key: `$record has ($key)`. Membership uses checked scalar equality and stops at
the first match. Select one bound node before testing its exact semantic kind;
`CXXRecord` aliases `CXXRecordDecl`.

A missing root variable is neither defined nor set. A null binding is defined
but unset. False, zero, empty strings and empty containers are set. All forms
return booleans and work with `if/else`, `unless`, `?:`, and `and/or/not`.
Native unrequested/unavailable fields keep their diagnostic; use `fieldState`.
""".replace("$", "")

_LET = """let: Bind a value, matcher function or runnable body.
Usage:
  let NAME = VALUE
  let NAME(PARAM, ...) = MATCHER
  let NAME(PARAM, OPTIONAL = EXPR, ...) = EXPR
  let NAME(PARAM, OPTIONAL = EXPR, ...) = { STATEMENTS }
  let NAME() = { STATEMENTS }
  NAME(ARG, ...)
References use bare names, fields and zero-based indexes: rows[0].f.
Double quotes interpolate checked expressions: "answer={value * 2}".
Use {{ and }} for literal braces; single quotes keep literal text.
Definitions are dormant. Expression and brace bodies compile to Python AST functions once.
An expression body returns its value; braces are optional for a single expression.
Omitted defaults run per call, left to right, with earlier parameters in scope.
Optional handlers come first: on error EXPR or { STATEMENTS }; on exit EXPR or { STATEMENTS }.
Errors return the error handler value; exit cleanup runs after success or failure
and ignores its value. Call-site EXPR on error EXPR or { STATEMENTS } is lazy.
In loop bodies, on error break stops the nearest loop; on error continue skips
the failed iteration. Cleanup runs first. Limits and cancellation cannot be recovered.
Each call has fresh parameters and locals and returns its final statement value;
an empty body returns null. Captures use the definition's lexical environment.
Aliases retain their original function after redefinition. Recursive calls use
the original function. Calls share execution limits and a maximum depth of 64.
Callee and argument counts are checked before arguments run, once left to right.
Assigned calls suppress body output; effects and explicit file writes still run.
Foreground batches snapshot plain captures per group and inspect reachable calls.
Runnable values cannot be exported or retained as batch results.
Examples:
  let add(l, r) = l + r
  let inc(x) = add(x, 1)
  let add_if(l, h) = if l < h then l + h else 0
  let twice(value) = { value * 2 }
  let scale(value, factor = 2) = { value * factor }
  let answer = twice(21)
  let announce() = { print "ready" }
  announce()
  let operation = twice
  operation(6)
  let named(name) = functionDecl(hasName(name))
  let find(path, name) = { match named(name) in path }
  let rows = find("sample.cc", "Sample")
Libraries accept let definitions and imports; preloads register dormant bodies.
"""


_LOOPS = """Console loops
  foreach item in items do BODY
  foreach index, item in items do BODY
  while CONDITION do BODY
  repeat BODY until CONDITION
  break
  continue
BODY is one statement or a brace block. While accepts optional do before braces.
The index is a zero-based visit ordinal; the source runs once and stays live.
While tests before the body; repeat runs once, then stops when until is true.
Conditions require Boolean values. Break exits the nearest scripting loop.
Continue skips the remaining body; repeat still checks its until condition.
Consumed loops collect completed body values; skipped and broken bodies add none.
Standalone while/repeat display body values without an unused result list.
Iteration locals are scoped; mutation updates the nearest existing binding.
Exit handlers clean up before break, continue, errors and cancellation.
Control cannot cross runnable or isolated batch boundaries. All loops share
execution limits and cancellation. These forms belong to the console dialect.
Examples:
  let x = 0
  let samples = repeat x += 1 until x >= 3
  while x > 0 do x -= 1
"""
_LOOP_TOPICS = {"loops", "foreach", "while", "repeat", "break", "continue"}


def render_help(statement: Any) -> str:
    topic = legacy_help.help_topic(statement)
    if topic in _LOOP_TOPICS:
        return _LOOPS.rstrip()
    if topic == "predicates":
        return _PLAIN.rstrip()
    if topic in {"let", "runnables", "functions"}:
        return _LET.rstrip()
    result = legacy_help.render_help(statement).replace("$", "")
    if not topic:
        result += "\nUse help loops for iteration, help let for runnable bodies and help predicates for value tests."
    return result


def render_help_markdown(statement: Any) -> str:
    topic = legacy_help.help_topic(statement)
    if topic in _LOOP_TOPICS:
        return "# Console loops\n\n```text\n" + _LOOPS.rstrip() + "\n```"
    if topic == "predicates":
        return _MARKDOWN.rstrip()
    if topic in {"let", "runnables", "functions"}:
        return "# Let values and runnable bodies\n\n```text\n" + _LET.rstrip() + "\n```"
    result = legacy_help.render_help_markdown(statement).replace("$", "")
    if not topic:
        result += "\n\nUse `help loops` for iteration, `help let` for runnable bodies and `help predicates` for value tests."
    return result

