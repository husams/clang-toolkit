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
"""

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
"""


def render_help(statement: Any) -> str:
    topic = legacy_help.help_topic(statement)
    if topic == "predicates":
        return _PLAIN.rstrip()
    result = legacy_help.render_help(statement)
    if not topic:
        result += "\nPrototype value predicates: use help predicates."
    return result


def render_help_markdown(statement: Any) -> str:
    topic = legacy_help.help_topic(statement)
    if topic == "predicates":
        return _MARKDOWN.rstrip()
    result = legacy_help.render_help_markdown(statement)
    if not topic:
        result += "\n\nPrototype value predicates: use `help predicates`."
    return result

