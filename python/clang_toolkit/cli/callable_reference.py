"""Offline argument notes and executable examples for console built-ins."""

from __future__ import annotations


# Each example is self-contained and runs without a server. Keep coverage in
# lockstep with Context.functions and the filter registry (see test_pipe_help).
BUILTIN_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "map": ("callback(item) returns the replacement value; the result is a list.",),
    "filter": ("callback(item) must return bool; keep true items in input order.",),
    "take": ("n is a nonnegative integer; return up to n items as a list.",),
    "drop": ("n is a nonnegative integer; return the remaining items as a list.",),
    "split_by": (
        "value is a string; separator is a nonempty exact string. Empty parts are preserved.",
    ),
    "join": (
        "value is a collection of strings; separator defaults to an empty string.",
    ),
    "keys": ("value is a mapping; return its keys as a list in iteration order.",),
    "values": ("value is a mapping; return its values as a list in iteration order.",),
    "entries": (
        "value is a mapping; return a list of {key, value} records, not tuples.",
    ),
    "pick": (
        "value is a mapping; pass distinct string field names positionally, in the desired order. No names returns an empty mapping; missing fields fail.",
    ),
    "flatten": (
        "Flatten one level of list, tuple or supported query-result children into a list; strings, mappings and scalar children fail.",
    ),
    "zip": (
        "other and any additional positional collections are paired with value into tuples. strict defaults to true (equal lengths); strict = false stops at the shortest.",
    ),
    "zip_longest": (
        "Pair value, other and additional positional collections into tuples; fill defaults to null for missing positions.",
    ),
    "enumerate": ("Return (index, item) tuples; start is an integer, default 0.",),
    "length": (
        "Count string code points, mapping fields or collection items; return an integer.",
    ),
    "first": (
        "value must be a finite list, tuple or supported retained collection view. Selection preserves the selected objects and native handles.",
        "Omit n to return one item, or null for empty input. n is a nonnegative integer; first(n) always returns a list of up to n items. omitted is a signature marker, not a value to pass.",
    ),
    "last": (
        "value must be a finite list, tuple or supported retained collection view. Selection preserves the selected objects and native handles.",
        "Omit n to return one item, or null for empty input. n is a nonnegative integer; last(n) always returns a list in original order. last(0) returns []. omitted is a signature marker, not a value to pass.",
    ),
    "reverse": (
        "Return a new reversed list from a finite list, tuple or supported collection view; do not mutate the input.",
    ),
    "unique": (
        "Keep the first item for each typed scalar/tuple key; arbitrary record keys are unsupported.",
    ),
    "unique_by": (
        "callback(item) supplies a typed scalar/tuple key; keep the first item for each key.",
    ),
    "sort": (
        "Items must be homogeneous finite numbers or strings. Sorting is stable; reverse is bool, default false.",
    ),
    "sort_by": (
        "callback(item) supplies homogeneous finite numeric or string keys. Sorting is stable; reverse is bool, default false.",
    ),
    "to_list": (
        "Materialize a collection as a new bounded list; strings and mappings are not collection inputs.",
    ),
    "to_tuple": (
        "Materialize a collection as an immutable bounded tuple; strings and mappings are not collection inputs.",
    ),
    "upper": ("value must be a string; return its Unicode uppercase form.",),
    "lower": ("value must be a string; return its Unicode lowercase form.",),
    "casefold": (
        "value must be a string; return its Unicode case-folded form for caseless comparisons.",
    ),
    "camel_case": ("value must be a string; split words and return lower camel case.",),
    "pascal_case": ("value must be a string; split words and return PascalCase.",),
    "snake_case": (
        "value must be a string; split words and join lowercase words with underscores.",
    ),
    "kebab_case": (
        "value must be a string; split words and join lowercase words with hyphens.",
    ),
    "trim": ("value must be a string; remove whitespace from both ends.",),
    "trim_start": ("value must be a string; remove leading whitespace only.",),
    "trim_end": ("value must be a string; remove trailing whitespace only.",),
    "replace": (
        "value, old and new are strings; old must be nonempty. count is an integer, default -1 (all occurrences); 0 replaces none.",
    ),
    "strip_prefix": (
        "value and prefix are strings; remove one exact prefix if present, otherwise keep value.",
    ),
    "strip_suffix": (
        "value and suffix are strings; remove one exact suffix if present, otherwise keep value.",
    ),
    "starts_with": (
        "value and part are strings; return bool using an exact, case-sensitive prefix test.",
    ),
    "ends_with": (
        "value and part are strings; return bool using an exact, case-sensitive suffix test.",
    ),
    "contains": (
        "value and part are strings; return bool using an exact, case-sensitive substring test.",
    ),
    "pretty": (
        "Return a preview string; indent=2 and depth=8 accept integers 0..8; max_items=100 is nonnegative. Output is capped at 20000 characters with omission markers.",
    ),
    "json": (
        "Return complete strict JSON text for ordinary serializable values; indent=0 (compact), valid 0..8. Limits: 1 MiB UTF-8, depth 32, 10000 items and the active execution budget. Project native rows to ordinary records first.",
    ),
    "table": (
        "columns is a required nonempty list/tuple of unique top-level string field names (at most 50). max_items=100 is nonnegative, capped at 100; output is a preview string capped at 20000 characters. Rows must be ordinary dictionaries; missing fields fail.",
    ),
    "len": (
        "Count a sized value such as a string, list, tuple or mapping; the result cannot exceed the active item limit. Use length for collection iteration.",
    ),
    "range": (
        "Use range(stop), range(start, stop), or range(start, stop, step), with positional signed 64-bit integers only. start defaults to 0, step to 1; stop is exclusive and step must be nonzero. Return a bounded list of integers.",
    ),
    "ctk": (
        "command is a console command string evaluated in the current session. Native operations need a server; help is offline. Dynamic commands are unsupported inside foreground batches.",
    ),
}

BUILTIN_EXAMPLES: dict[str, tuple[str, ...]] = {
    "map": (
        "print [1, 2, 3] | map((item) item * 2)",
        "print [1, 2] | map { (item) item + 1 }",
    ),
    "filter": ("print [1, 2, 3] | filter((item) item > 1)",),
    "take": ("print [10, 20, 30] | take(2)",),
    "drop": ("print [10, 20, 30] | drop(1)",),
    "split_by": ('print "a,,b" | split_by(",")',),
    "join": ('print ["a", "b"] | join("-")',),
    "keys": ('print {name: "Widget", count: 2} | keys',),
    "values": ('print {name: "Widget", count: 2} | values',),
    "entries": ('print {name: "Widget"} | entries',),
    "pick": ('print {name: "Widget", count: 2, skip: true} | pick("name", "count")',),
    "flatten": ("print [[1, 2], [], [3]] | flatten",),
    "zip": (
        'print ["a", "b"] | zip([1, 2])',
        "print [1] | zip([2, 3], strict = false)",
    ),
    "zip_longest": ("print [1] | zip_longest([2, 3], fill = 0)",),
    "enumerate": ('print ["a", "b"] | enumerate(start = 1)',),
    "length": ("print [10, 20, 30] | length",),
    "first": (
        "print [10, 20, 30] | first",
        "print [10, 20, 30] | first(2)",
        "print [] | first",
        "print first([10, 20], 1)",
    ),
    "last": (
        "print [10, 20, 30] | last",
        "print [10, 20, 30] | last(2)",
        "print [] | last",
        "print [10, 20] | last(0)",
    ),
    "reverse": ("print [10, 20, 30] | reverse",),
    "unique": ("print [2, 1, 2] | unique",),
    "unique_by": (
        'print [{name: "a", n: 1}, {name: "a", n: 2}] | unique_by((item) item.name)',
    ),
    "sort": ("print [3, 1, 2] | sort(reverse = true)",),
    "sort_by": ('print [("a", 2), ("b", 1)] | sort_by((name, count) count)',),
    "to_list": ("print (1, 2) | to_list",),
    "to_tuple": ("print [1, 2] | to_tuple",),
    "upper": ('print "Widget" | upper',),
    "lower": ('print "Widget" | lower',),
    "casefold": ('print "Straße" | casefold',),
    "camel_case": ('print "hello_world" | camel_case',),
    "pascal_case": ('print "hello_world" | pascal_case',),
    "snake_case": ('print "HelloWorld" | snake_case',),
    "kebab_case": ('print "HelloWorld" | kebab_case',),
    "trim": ('print "  hello  " | trim',),
    "trim_start": ('print "  hello  " | trim_start',),
    "trim_end": ('print "  hello  " | trim_end',),
    "replace": ('print "a-a-a" | replace("a", "b", count = 2)',),
    "strip_prefix": ('print "class_Widget" | strip_prefix("class_")',),
    "strip_suffix": ('print "widget.cpp" | strip_suffix(".cpp")',),
    "starts_with": ('print "widget.cpp" | starts_with("widget")',),
    "ends_with": ('print "widget.cpp" | ends_with(".cpp")',),
    "contains": ('print "widget.cpp" | contains("get")',),
    "pretty": ("print [1, 2] | pretty(indent = 0)",),
    "json": ('print {name: "Widget", count: 2} | json(indent = 2)',),
    "table": (
        'print [{name: "Widget", count: 2}] | table(columns = ["name", "count"])',
    ),
    "len": ("print len([10, 20])", "print [10, 20] | len"),
    "range": ("print range(1, 6, 2)", "print 3 | range"),
    "ctk": ('print ctk("help first")',),
}
