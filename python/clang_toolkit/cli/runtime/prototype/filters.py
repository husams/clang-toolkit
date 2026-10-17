"""Context-bound, bounded host filters for the prototype pipe language."""

from __future__ import annotations

import builtins
import json
import math
from collections.abc import Mapping
from functools import wraps
from itertools import islice
from typing import Any, Callable
import unicodedata

from .semantics import Context, ExecutionLimitError, PrototypeError


FILTER_SIGNATURES: dict[str, str] = {
    "map": "(value, callback)",
    "filter": "(value, callback)",
    "take": "(value, n)",
    "drop": "(value, n)",
    "split_by": "(value, separator)",
    "join": "(value, separator='')",
    "keys": "(value)",
    "values": "(value)",
    "entries": "(value)",
    "pick": "(value, *names)",
    "flatten": "(value)",
    "zip": "(value, other, *others, strict=true)",
    "zip_longest": "(value, other, *others, fill=null)",
    "enumerate": "(value, start=0)",
    "length": "(value)",
    "first": "(value, n=omitted)",
    "last": "(value, n=omitted)",
    "reverse": "(value)",
    "unique": "(value)",
    "unique_by": "(value, callback)",
    "sort": "(value, reverse=false)",
    "sort_by": "(value, callback, reverse=false)",
    "to_list": "(value)",
    "to_tuple": "(value)",
    "upper": "(value)",
    "lower": "(value)",
    "casefold": "(value)",
    "camel_case": "(value)",
    "pascal_case": "(value)",
    "snake_case": "(value)",
    "kebab_case": "(value)",
    "trim": "(value)",
    "trim_start": "(value)",
    "trim_end": "(value)",
    "replace": "(value, old, new, count=-1)",
    "strip_prefix": "(value, prefix)",
    "strip_suffix": "(value, suffix)",
    "starts_with": "(value, part)",
    "ends_with": "(value, part)",
    "contains": "(value, part)",
    "pretty": "(value, indent=2, depth=8, max_items=100)",
    "json": "(value, indent=0)",
    "table": "(value, columns, max_items=100)",
}

FILTER_DESCRIPTIONS: dict[str, str] = {
    "map": "Transform each item with a callback.",
    "filter": "Keep items whose callback returns a boolean true.",
    "take": "Return at most the first n items without over-reading.",
    "drop": "Skip the first n items and return the rest.",
    "split_by": "Split a string on an exact nonempty separator, preserving empty parts.",
    "join": "Join a sequence of strings with a separator.",
    "keys": "Return mapping keys in iteration order.",
    "values": "Return mapping values in iteration order.",
    "entries": "Return ordered records with key and value fields.",
    "pick": "Select named fields from a mapping while preserving requested order.",
    "flatten": "Flatten one level of nested lists and tuples.",
    "zip": "Combine sequences, requiring equal lengths unless strict is false.",
    "zip_longest": "Combine sequences and fill missing positions.",
    "enumerate": "Pair each item with its integer index.",
    "length": "Count string code points, mapping fields, or collection items.",
    "first": "Return the first item or null; first(n) returns up to n items as a list.",
    "last": "Return the last item or null; last(n) returns up to n items in original order.",
    "reverse": "Return items in reverse order.",
    "unique": "Keep the first item for each supported typed key.",
    "unique_by": "Keep the first item for each callback-produced key.",
    "sort": "Stably sort homogeneous finite numbers or strings.",
    "sort_by": "Stably sort by homogeneous finite numeric or string callback keys.",
    "to_list": "Materialize an iterable as a bounded list.",
    "to_tuple": "Materialize an iterable as a bounded tuple.",
    "upper": "Convert a string to uppercase.",
    "lower": "Convert a string to lowercase.",
    "casefold": "Apply Unicode case folding to a string.",
    "camel_case": "Convert words to lower camel case.",
    "pascal_case": "Convert words to PascalCase.",
    "snake_case": "Convert words to snake_case.",
    "kebab_case": "Convert words to kebab-case.",
    "trim": "Remove leading and trailing whitespace.",
    "trim_start": "Remove leading whitespace.",
    "trim_end": "Remove trailing whitespace.",
    "replace": "Replace non-overlapping occurrences of a nonempty string.",
    "strip_prefix": "Remove an exact leading prefix when present.",
    "strip_suffix": "Remove an exact trailing suffix when present.",
    "starts_with": "Test whether a string starts with an exact substring.",
    "ends_with": "Test whether a string ends with an exact substring.",
    "contains": "Test whether a string contains an exact substring.",
    "pretty": "Render a bounded human-readable preview.",
    "json": "Render strict JSON for ordinary serializable values.",
    "table": "Render selected top-level record fields as a bounded table.",
}


def make_filters(context: Context) -> dict[str, Callable[..., Any]]:
    """Create host callables whose iteration, callbacks, and output use context."""
    node = _diagnostic_node(context)
    active_item_counts: list[list[int]] = []

    def count_item() -> None:
        if active_item_counts:
            active_item_counts[-1][0] += 1
            if active_item_counts[-1][0] > context.max_items:
                raise _limit_error(context, node, "filter item budget exceeded")

    def guard() -> None:
        count_item()
        _consume(context, node)

    def run_callback(callback: Callable[..., Any]) -> Callable[[Any], Any]:
        from .runnables import prepare_callback

        return prepare_callback(context, node, callback)

    def collect(value: Any) -> list[Any]:
        iterator = _collection_iterable(context, node, value)
        result: list[Any] = []
        for item in iterator:
            guard()
            result.append(item)
            _check_output_count(context, node, len(result))
        return result

    def map_filter(value: Any, callback: Callable[..., Any]) -> list[Any]:
        invoke = run_callback(callback)
        result: list[Any] = []
        for index, item in builtins.enumerate(
            _collection_iterable(context, node, value)
        ):
            guard()
            result.append(_call_callback(invoke, item, index))
            _check_output_count(context, node, len(result))
        return result

    def filter_filter(value: Any, callback: Callable[..., Any]) -> list[Any]:
        invoke = run_callback(callback)
        result: list[Any] = []
        for index, item in builtins.enumerate(
            _collection_iterable(context, node, value)
        ):
            guard()
            keep = _call_callback(invoke, item, index)
            if type(keep) is not bool:
                raise TypeError("filter callback must return bool")
            if keep:
                result.append(item)
                _check_output_count(context, node, len(result))
        return result

    def take(value: Any, n: int) -> list[Any]:
        count = _nonnegative_int(n, "n")
        result: list[Any] = []
        iterator = _collection_iterable(context, node, value)
        for _ in range(count):
            try:
                item = next(iterator)
            except StopIteration:
                break
            guard()
            result.append(item)
            _check_output_count(context, node, len(result))
        return result

    def drop(value: Any, n: int) -> list[Any]:
        count = _nonnegative_int(n, "n")
        result: list[Any] = []
        for index, item in builtins.enumerate(
            _collection_iterable(context, node, value)
        ):
            guard()
            if index >= count:
                result.append(item)
                _check_output_count(context, node, len(result))
        return result

    def split_by(value: str, separator: str) -> list[str]:
        _string(value, "value")
        _string(separator, "separator")
        if not separator:
            raise ValueError("separator must be nonempty")
        _check_text_size(value, 1_048_576)
        piece_count = value.count(separator) + 1
        _check_output_count(context, node, piece_count)
        pieces = value.split(separator)
        for _ in pieces:
            guard()
        return pieces

    def join(value: Any, separator: str = "") -> str:
        _string(separator, "separator")
        items = collect(value)
        if any(type(item) is not str for item in items):
            raise TypeError("join requires a sequence of strings")
        total_bytes = 0
        for item in items:
            total_bytes += _utf8_size_bounded(item, 1_048_576 - total_bytes)
            if total_bytes > 1_048_576:
                raise ValueError("join output exceeds byte limit")
        if len(items) > 1:
            total_bytes += (len(items) - 1) * _utf8_size_bounded(separator, 1_048_576)
        if total_bytes > 1_048_576:
            raise ValueError("join output exceeds byte limit")
        result = separator.join(items)
        _check_text_size(result, 1_048_576)
        return result

    def mapping(value: Any) -> Mapping[Any, Any]:
        if not isinstance(value, Mapping):
            raise TypeError("expected a mapping")
        return value

    def keys(value: Any) -> list[Any]:
        source = mapping(value)
        result: list[Any] = []
        for key in source:
            guard()
            result.append(key)
            _check_output_count(context, node, len(result))
        return result

    def values(value: Any) -> list[Any]:
        source = mapping(value)
        result: list[Any] = []
        for key in source:
            guard()
            result.append(source[key])
            _check_output_count(context, node, len(result))
        return result

    def entries(value: Any) -> list[dict[str, Any]]:
        source = mapping(value)
        result: list[dict[str, Any]] = []
        for key in source:
            guard()
            result.append({"key": key, "value": source[key]})
            _check_output_count(context, node, len(result))
        return result

    def pick(value: Any, *names: str) -> dict[str, Any]:
        source = mapping(value)
        if any(type(name) is not str for name in names):
            raise TypeError("names must be strings")
        if len(names) > context.max_items:
            raise _limit_error(context, node, "pick names exceed item limit")
        if len(set(names)) != len(names):
            raise ValueError("duplicate field name")
        result: dict[str, Any] = {}
        for name in names:
            guard()
            if name not in source:
                raise KeyError(f"missing field {name!r}")
            result[name] = source[name]
            _check_output_count(context, node, len(result))
        return result

    def flatten(value: Any) -> list[Any]:
        outer = _flatten_members(value)
        if outer is None:
            raise TypeError(
                f"flatten requires a list or query-result collection; got {type(value).__name__}"
            )
        result: list[Any] = []
        for index, item in builtins.enumerate(outer):
            guard()
            members = _flatten_members(item)
            if members is None:
                if isinstance(item, str):
                    reason = "strings are scalar values, not collections"
                elif isinstance(item, Mapping):
                    reason = "dictionaries are records, not collections"
                else:
                    reason = f"{type(item).__name__} is not a supported collection"
                raise TypeError(
                    f"flatten child at index {index} is invalid: {reason}; "
                    "expected a list or query-result collection"
                )
            for child in members:
                guard()
                result.append(child)
                _check_output_count(context, node, len(result))
        return result

    def zip_filter(
        value: Any, other: Any, *others: Any, strict: bool = True
    ) -> list[tuple[Any, ...]]:
        if type(strict) is not bool:
            raise TypeError("strict must be bool")
        if len(others) + 2 > context.max_items:
            raise _limit_error(context, node, "zip column count exceeds item limit")
        sources = (value, other, *others)
        iterators = [_collection_iterable(context, node, source) for source in sources]
        result: list[tuple[Any, ...]] = []
        while True:
            row: list[Any] = []
            ended: list[bool] = []
            for iterator in iterators:
                try:
                    item = next(iterator)
                    _consume(context, node)
                    row.append(item)
                    ended.append(False)
                except StopIteration:
                    ended.append(True)
                    if not strict:
                        return result
            if all(ended):
                break
            if any(ended):
                if strict:
                    raise ValueError("zip inputs must have equal lengths")
                break
            count_item()
            result.append(tuple(row))
            _check_output_count(context, node, len(result))
        return result

    def zip_longest(
        value: Any, other: Any, *others: Any, fill: Any = None
    ) -> list[tuple[Any, ...]]:
        if len(others) + 2 > context.max_items:
            raise _limit_error(context, node, "zip column count exceeds item limit")
        iterators = [
            _collection_iterable(context, node, source)
            for source in (value, other, *others)
        ]
        ended = [False] * len(iterators)
        result: list[tuple[Any, ...]] = []
        while not all(ended):
            row: list[Any] = []
            fill_cells: list[bool] = []
            has_value = False
            for index, iterator in enumerate(iterators):
                if ended[index]:
                    row.append(fill)
                    fill_cells.append(True)
                    continue
                try:
                    item = next(iterator)
                    _consume(context, node)
                    row.append(item)
                    fill_cells.append(False)
                    has_value = True
                except StopIteration:
                    ended[index] = True
                    row.append(fill)
                    fill_cells.append(True)
            if not has_value:
                break
            for is_fill in fill_cells:
                if is_fill:
                    _consume(context, node)
            count_item()
            result.append(tuple(row))
            _check_output_count(context, node, len(result))
        return result

    def enumerate_filter(value: Any, start: int = 0) -> list[tuple[int, Any]]:
        if type(start) is not int:
            raise TypeError("start must be an integer")
        result: list[tuple[int, Any]] = []
        for index, item in builtins.enumerate(
            _collection_iterable(context, node, value), start
        ):
            guard()
            result.append((index, item))
            _check_output_count(context, node, len(result))
        return result

    def length(value: Any) -> int:
        if isinstance(value, str):
            return len(value)
        if isinstance(value, Mapping) or _has_bounded_len(value):
            result = len(value)
            if result > context.max_items:
                raise _limit_error(context, node, "collection exceeds item limit")
            return result
        count = 0
        for _ in _collection_iterable(context, node, value):
            guard()
            count += 1
        return count

    def selected(value: Any, n: Any, *, tail: bool) -> Any:
        from .selection import selection_sequence
        from .semantics import index_value

        sequence = selection_sequence(value)
        if n is _MISSING:
            if not len(sequence):
                return None
            guard()
            return index_value(sequence, -1 if tail else 0, context, node)
        count = _nonnegative_int(n, "n")
        size = len(sequence)
        key = slice(max(0, size - count), size) if tail else slice(0, count)
        return index_value(sequence, key, context, node)

    def first(value: Any, n: Any = _MISSING) -> Any:
        return selected(value, n, tail=False)

    def last(value: Any, n: Any = _MISSING) -> Any:
        return selected(value, n, tail=True)

    def reverse(value: Any) -> list[Any]:
        from .semantics import index_value
        from .selection import selection_sequence

        return index_value(selection_sequence(value), slice(None, None, -1), context, node)

    def unique(value: Any) -> list[Any]:
        seen: set[Any] = set()
        result: list[Any] = []
        for item in _collection_iterable(context, node, value):
            guard()
            key = _typed_key(item, visit=guard)
            if key not in seen:
                seen.add(key)
                result.append(item)
                _check_output_count(context, node, len(result))
        return result

    def unique_by(value: Any, callback: Callable[..., Any]) -> list[Any]:
        invoke = run_callback(callback)
        seen: set[Any] = set()
        result: list[Any] = []
        for index, item in builtins.enumerate(
            _collection_iterable(context, node, value)
        ):
            guard()
            key = _typed_key(_call_callback(invoke, item, index), visit=guard)
            if key not in seen:
                seen.add(key)
                result.append(item)
                _check_output_count(context, node, len(result))
        return result

    def validate_sort_key(key: Any, domain: type | None) -> type:
        if type(key) in (int, float):
            if type(key) is float and not math.isfinite(key):
                raise TypeError("sort keys must be finite")
            current = int if type(key) is int else float
        elif type(key) is str:
            current = str
        else:
            raise TypeError("sort keys must be homogeneous finite numbers or strings")
        if (
            domain is not None
            and current is not domain
            and not {current, domain} <= {int, float}
        ):
            raise TypeError("sort keys must be homogeneous finite numbers or strings")
        return (
            current
            if domain is None
            else (float if {domain, current} <= {int, float} else domain)
        )

    def sort(value: Any, reverse: bool = False) -> list[Any]:
        if type(reverse) is not bool:
            raise TypeError("reverse must be bool")
        items = collect(value)
        domain: type | None = None
        for item in items:
            domain = validate_sort_key(item, domain)
        return sorted(items, reverse=reverse)

    def sort_by(
        value: Any, callback: Callable[..., Any], reverse: bool = False
    ) -> list[Any]:
        if type(reverse) is not bool:
            raise TypeError("reverse must be bool")
        invoke = run_callback(callback)
        decorated: list[tuple[Any, Any]] = []
        domain: type | None = None
        for index, item in builtins.enumerate(
            _collection_iterable(context, node, value)
        ):
            guard()
            key = _call_callback(invoke, item, index)
            domain = validate_sort_key(key, domain)
            decorated.append((key, item))
            _check_output_count(context, node, len(decorated))
        decorated.sort(key=lambda pair: pair[0], reverse=reverse)
        return [item for _, item in decorated]

    def to_list(value: Any) -> list[Any]:
        return collect(value)

    def to_tuple(value: Any) -> tuple[Any, ...]:
        return tuple(collect(value))

    def require_string(value: Any) -> str:
        return _string(value, "value")

    def transform_string(value: str, transform: Callable[[str], str]) -> str:
        result = transform(require_string(value))
        _check_text_size(result, 1_048_576)
        return result

    def camel_case(value: str) -> str:
        def convert(text: str) -> str:
            words = _words(text)
            return (
                ""
                if not words
                else words[0].lower() + "".join(_title_word(word) for word in words[1:])
            )

        return transform_string(value, convert)

    def pascal_case(value: str) -> str:
        return transform_string(
            value, lambda text: "".join(_title_word(word) for word in _words(text))
        )

    def snake_case(value: str) -> str:
        return transform_string(
            value, lambda text: "_".join(word.lower() for word in _words(text))
        )

    def kebab_case(value: str) -> str:
        return transform_string(
            value, lambda text: "-".join(word.lower() for word in _words(text))
        )

    def replace(value: str, old: str, new: str, count: int = -1) -> str:
        value = require_string(value)
        _string(old, "old")
        _string(new, "new")
        if not old:
            raise ValueError("old must be nonempty")
        if type(count) is not int or count < -1:
            raise ValueError("count must be -1 or nonnegative")
        _check_text_size(value, 1_048_576)
        _check_text_size(old, 1_048_576)
        _check_text_size(new, 1_048_576)
        occurrences = value.count(old)
        if count >= 0:
            occurrences = min(occurrences, count)
        expected_bytes = len(value.encode("utf-8")) + occurrences * (
            len(new.encode("utf-8")) - len(old.encode("utf-8"))
        )
        if expected_bytes > 1_048_576:
            raise ValueError("replace output exceeds byte limit")
        return value.replace(old, new, count)

    def strip_prefix(value: str, prefix: str) -> str:
        return require_string(value).removeprefix(_string(prefix, "prefix"))

    def strip_suffix(value: str, suffix: str) -> str:
        return require_string(value).removesuffix(_string(suffix, "suffix"))

    def starts_with(value: str, part: str) -> bool:
        return require_string(value).startswith(_string(part, "part"))

    def ends_with(value: str, part: str) -> bool:
        return require_string(value).endswith(_string(part, "part"))

    def contains(value: str, part: str) -> bool:
        return _string(part, "part") in require_string(value)

    def pretty(
        value: Any, indent: int = 2, depth: int = 8, max_items: int = 100
    ) -> str:
        indent = _nonnegative_int(indent, "indent")
        if indent > 8:
            raise ValueError("indent must be at most 8")
        depth = _nonnegative_int(depth, "depth")
        if depth > 8:
            raise ValueError("depth must be at most 8")
        max_items = _nonnegative_int(max_items, "max_items")
        bound = min(max_items, context.max_items)
        from ..semantic import display_value

        safe = display_value(value, max_depth=depth, max_items=bound)
        rendered = _pretty_text(
            safe,
            indent=indent,
            depth=depth,
            max_items=bound,
            context=context,
            node=node,
            guard=guard,
        )
        return _clip_text(rendered, 20_000)

    def json_filter(value: Any, indent: int = 0) -> str:
        if type(indent) is not int or not 0 <= indent <= 8:
            raise ValueError("indent must be an integer from 0 through 8")
        normalized, byte_count = _strict_json_value(
            value,
            max_depth=32,
            max_items=min(10_000, context.max_items),
            max_bytes=1_048_576,
            guard=guard,
        )
        if byte_count > 1_048_576:
            raise ValueError("json output exceeds byte limit")
        encoder = json.JSONEncoder(
            ensure_ascii=False,
            allow_nan=False,
            indent=indent or None,
            separators=None if indent else (",", ":"),
        )
        chunks: list[str] = []
        output_bytes = 0
        for chunk in encoder.iterencode(normalized):
            chunk_bytes = _utf8_size_bounded(chunk, 1_048_576 - output_bytes)
            if chunk_bytes > 1_048_576 - output_bytes:
                raise ValueError("json output exceeds byte limit")
            chunks.append(chunk)
            output_bytes += chunk_bytes
        return "".join(chunks)

    def table(
        value: Any, columns: list[str] | tuple[str, ...], max_items: int = 100
    ) -> str:
        if (
            type(columns) not in (list, tuple)
            or not columns
            or any(type(col) is not str for col in columns)
        ):
            raise TypeError("columns must be a nonempty list of top-level field names")
        if len(set(columns)) != len(columns):
            raise ValueError("duplicate column name")
        if len(columns) > 50:
            raise ValueError("table supports at most 50 columns")
        if len(columns) > context.max_items:
            raise _limit_error(context, node, "table columns exceed item limit")
        max_items = min(
            _nonnegative_int(max_items, "max_items"), context.max_items, 100
        )
        rows: list[list[str]] = []
        more = False
        iterator = _collection_iterable(context, node, value)
        for _ in range(max_items):
            try:
                record = next(iterator)
            except StopIteration:
                break
            guard()
            if type(record) is not dict:
                raise TypeError("table rows must be ordinary dictionaries")
            cells: list[str] = []
            for column in columns:
                try:
                    cell = _field_value(record, column)
                except (KeyError, AttributeError, ValueError) as error:
                    raise ValueError(f"missing field {column!r}: {error}") from error
                cell_budget = max(
                    16, min(512, 20_000 // max(1, (max_items or 1) * len(columns)))
                )
                cells.append(_cell_text(cell, guard=guard, max_chars=cell_budget))
            rows.append(cells)
        if len(rows) >= max_items:
            known_count = _known_count(value)
            if known_count is not None:
                more = known_count > len(rows)
            else:
                sentinel = object()
                extra = next(iterator, sentinel)
                if extra is not sentinel:
                    guard()
                    more = True
        displayed_columns = [_table_text(column, 256) for column in columns]
        widths = [len(column) for column in displayed_columns]
        for row in rows:
            widths = [max(width, len(cell)) for width, cell in zip(widths, row)]
        lines = [
            "  ".join(
                _table_text(col, 256).ljust(widths[index])
                for index, col in enumerate(columns)
            )
        ]
        lines.extend(
            "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))
            for row in rows
        )
        if more:
            lines.append("… more rows omitted")
        rendered = "\n".join(lines)
        if not rows:
            rendered += "\n"
        return _clip_text(rendered, 20_000)

    built: dict[str, Callable[..., Any]] = {
        "map": map_filter,
        "filter": filter_filter,
        "take": take,
        "drop": drop,
        "split_by": split_by,
        "join": join,
        "keys": keys,
        "values": values,
        "entries": entries,
        "pick": pick,
        "flatten": flatten,
        "zip": zip_filter,
        "zip_longest": zip_longest,
        "enumerate": enumerate_filter,
        "length": length,
        "first": first,
        "last": last,
        "reverse": reverse,
        "unique": unique,
        "unique_by": unique_by,
        "sort": sort,
        "sort_by": sort_by,
        "to_list": to_list,
        "to_tuple": to_tuple,
        "upper": lambda value: transform_string(value, str.upper),
        "lower": lambda value: transform_string(value, str.lower),
        "casefold": lambda value: transform_string(value, str.casefold),
        "camel_case": camel_case,
        "pascal_case": pascal_case,
        "snake_case": snake_case,
        "kebab_case": kebab_case,
        "trim": lambda value: transform_string(value, str.strip),
        "trim_start": lambda value: transform_string(value, str.lstrip),
        "trim_end": lambda value: transform_string(value, str.rstrip),
        "replace": replace,
        "strip_prefix": strip_prefix,
        "strip_suffix": strip_suffix,
        "starts_with": starts_with,
        "ends_with": ends_with,
        "contains": contains,
        "pretty": pretty,
        "json": json_filter,
        "table": table,
    }
    bound: dict[str, Callable[..., Any]] = {}
    for name, function in built.items():

        @wraps(function)
        def invoke(
            *args: Any, _function: Callable[..., Any] = function, **kwargs: Any
        ) -> Any:
            nonlocal node
            node = _diagnostic_node(context)
            active_item_counts.append([0])
            try:
                return _function(*args, **kwargs)
            except PrototypeError:
                raise
            except (TypeError, ValueError, KeyError) as error:
                suffix = _location_suffix(node)
                if suffix and suffix not in str(error):
                    raise type(error)(f"{error}{suffix}") from error
                raise
            finally:
                active_item_counts.pop()

        invoke.__name__ = name
        invoke.__ctk_filter_name__ = name
        bound[name] = invoke
    return bound


_MISSING = object()


def _words(value: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    for index, char in enumerate(value):
        if not char.isalnum():
            if current:
                parts.append("".join(current))
                current.clear()
            continue
        previous = value[index - 1] if index else ""
        following = value[index + 1] if index + 1 < len(value) else ""
        boundary = (
            char.isupper()
            and bool(current)
            and (
                previous.islower()
                or previous.isdigit()
                or (previous.isupper() and following.islower())
            )
        )
        if boundary:
            parts.append("".join(current))
            current.clear()
        current.append(char)
    if current:
        parts.append("".join(current))
    return parts


def _title_word(word: str) -> str:
    if not word:
        return ""
    return word[0].upper() + word[1:].lower()


def _string(value: Any, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be a string")
    _check_text_size(value, 1_048_576)
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be a nonnegative integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _iterable(context: Context, node: Any, value: Any):
    from .semantics import iterable_value

    return iterable_value(context, node, value)


def _collection_iterable(context: Context, node: Any, value: Any):
    if isinstance(value, (str, Mapping)):
        raise TypeError(
            "collection filters require a list, tuple, or supported collection view"
        )
    return _iterable(context, node, value)


def _flatten_members(value: Any):
    if type(value) in (list, tuple):
        return iter(value)
    from ..values import MatchSet
    from clang_toolkit.match_values import (
        MatchValue,
        NativeBindingCollection,
        NativeMatchCollection,
    )
    from ..semantic import RepeatedView

    if isinstance(value, MatchSet):
        return iter(value.rows)
    if isinstance(value, MatchValue):
        return value.iter_rows()
    if isinstance(
        value, (NativeMatchCollection, NativeBindingCollection, RepeatedView)
    ):
        return iter(value)
    return None


def _call_callback(callback: Callable[[Any], Any], item: Any, index: int) -> Any:
    try:
        return callback(item)
    except Exception as error:
        raise type(error)(
            f"callback failed for source item {index}: {error}"
        ) from error


def _diagnostic_node(context: Context) -> Any:
    line, column = context.current_location
    if line is None and column is None:
        return None
    return type("Location", (), {"line": line, "column": column})()


def _location_suffix(node: Any) -> str:
    line = getattr(node, "line", None)
    column = getattr(node, "column", None)
    if line is None and column is None:
        return ""
    return f" at line {line}" if column is None else f" at line {line}, column {column}"


def _consume(context: Context, node: Any) -> None:
    consume = getattr(context, "consume_step", None)
    if callable(consume):
        consume(node)
        return
    context.tick(node)


def _check_output_count(context: Context, node: Any, count: int) -> None:
    if count > context.max_items:
        raise _limit_error(context, node, "filter result exceeds item limit")


def _limit_error(context: Context, node: Any, message: str) -> ExecutionLimitError:
    from .semantics import _error

    return _error(context, node, message, ExecutionLimitError)


def _has_bounded_len(value: Any) -> bool:
    return isinstance(value, (list, tuple, str, bytes)) or type(
        value
    ).__module__.startswith("clang_toolkit.cli.runtime")


def _known_count(value: Any) -> int | None:
    if not _has_bounded_len(value):
        return None
    return len(value)


def _typed_key(
    value: Any,
    *,
    visit: Callable[[], None] | None = None,
    active: set[int] | None = None,
    depth: int = 0,
) -> Any:
    if value is None or type(value) in (bool, str, bytes):
        return (type(value), value)
    if type(value) is int:
        return ("number", value)
    if type(value) is float:
        if not math.isfinite(value):
            raise TypeError("unique keys must be finite")
        return ("number", value)
    if type(value) is tuple:
        if depth >= 32:
            raise TypeError("unique key tuple nesting exceeds depth limit")
        active = set() if active is None else active
        identity = id(value)
        if identity in active:
            raise TypeError("unique keys cannot contain cycles")
        active.add(identity)
        try:
            members: list[Any] = []
            for item in value:
                if visit is not None:
                    visit()
                members.append(
                    _typed_key(
                        item,
                        visit=visit,
                        active=active,
                        depth=depth + 1,
                    )
                )
            return (tuple, tuple(members))
        finally:
            active.remove(identity)
    raise TypeError(f"unsupported unique key type: {type(value).__name__}")


def _pretty_text(
    value: Any,
    *,
    indent: int,
    depth: int,
    max_items: int,
    context: Context,
    node: Any,
    guard: Callable[[], None],
) -> str:
    active: set[int] = set()
    remaining = [max_items]

    def walk(item: Any, level: int) -> str:
        if item is None:
            return "null"
        if type(item) is bool:
            return "true" if item else "false"
        if type(item) in (int, float):
            return repr(item)
        if type(item) is str:
            if _utf8_size_bounded(item, 512) > 512:
                item = item[:128] + "… <string omitted>"
            return json.dumps(item, ensure_ascii=False)
        if type(item) not in (list, tuple, dict):
            from ..values import render

            return render(item)
        identity = id(item)
        if identity in active:
            return "<cycle>"
        if level >= depth:
            return "… <depth omitted>"
        active.add(identity)
        try:
            is_mapping = type(item) is dict
            count = len(item)
            selected_count = min(count, remaining[0])
            selected = list(
                islice(item.items() if is_mapping else iter(item), selected_count)
            )
            for _ in selected:
                guard()
            remaining[0] -= len(selected)
            children = []
            for entry in selected:
                if is_mapping:
                    key, child = entry
                    children.append(
                        f"{json.dumps(str(key)[:128], ensure_ascii=False)}: {walk(child, level + 1)}"
                    )
                else:
                    children.append(walk(entry, level + 1))
            omitted = count - len(selected)
            if omitted:
                children.append(f"… {omitted} items omitted")
            if not children:
                return "{}" if is_mapping else "()" if type(item) is tuple else "[]"
            opening, closing = (
                ("{", "}")
                if is_mapping
                else ("(", ")")
                if type(item) is tuple
                else ("[", "]")
            )
            if type(item) is tuple and len(children) == 1 and not omitted:
                children[0] += ","
            if indent == 0:
                text = opening + ", ".join(children) + closing
            else:
                pad = " " * (indent * (level + 1))
                endpad = " " * (indent * level)
                text = (
                    opening
                    + "\n"
                    + pad
                    + (",\n" + pad).join(children)
                    + "\n"
                    + endpad
                    + closing
                )
            return text
        finally:
            active.remove(identity)

    return walk(value, 0)


def _clip_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 24] + "… <output truncated>"


def _strict_json_value(
    value: Any,
    *,
    max_depth: int,
    max_items: int,
    max_bytes: int,
    guard: Callable[[], None],
) -> tuple[Any, int]:
    active: set[int] = set()
    count = 0
    byte_count = 0

    def walk(item: Any, depth: int) -> Any:
        nonlocal count, byte_count
        if item is None or type(item) is bool:
            byte_count += 4 if item is None else (4 if item else 5)
            return item
        if type(item) is int:
            if item.bit_length() > max_bytes * 4:
                raise ValueError("json output exceeds byte limit")
            byte_count += max(1, len(str(abs(item)))) + (1 if item < 0 else 0)
            return item
        if type(item) is float:
            if not math.isfinite(item):
                raise ValueError("json rejects nonfinite numbers")
            byte_count += len(repr(item))
            return item
        if type(item) is str:
            encoded_size = _json_string_size_bounded(item, max_bytes - byte_count)
            if encoded_size > max_bytes - byte_count:
                raise ValueError("json output exceeds byte limit")
            byte_count += encoded_size
            return item
        if type(item) not in (list, tuple, dict):
            raise TypeError(
                f"json accepts ordinary serializable data, got {type(item).__name__}"
            )
        if depth >= max_depth:
            raise ValueError("json exceeds depth limit")
        identity = id(item)
        if identity in active:
            raise ValueError("json rejects a cycle in data")
        active.add(identity)
        try:
            count += len(item)
            if count > max_items:
                raise ValueError("json exceeds item limit")
            if type(item) is dict:
                byte_count += 2 + max(0, len(item) - 1) + len(item)
                if byte_count > max_bytes:
                    raise ValueError("json output exceeds byte limit")
                result: dict[str, Any] = {}
                for key, child in item.items():
                    guard()
                    if type(key) is not str:
                        raise TypeError("json object keys must be strings")
                    key_size = _json_string_size_bounded(key, max_bytes - byte_count)
                    if key_size > max_bytes - byte_count:
                        raise ValueError("json output exceeds byte limit")
                    byte_count += key_size
                    result[key] = walk(child, depth + 1)
                return result
            byte_count += 2 + max(0, len(item) - 1)
            if byte_count > max_bytes:
                raise ValueError("json output exceeds byte limit")
            result = []
            for child in item:
                guard()
                result.append(walk(child, depth + 1))
            return result
        finally:
            active.remove(identity)

    normalized = walk(value, 0)
    return normalized, byte_count


def _field_value(record: Any, name: str) -> Any:
    if type(record) is not dict:
        raise TypeError("table rows must be ordinary dictionaries")
    if name not in record:
        raise KeyError(name)
    return record[name]


def _cell_text(value: Any, *, guard: Callable[[], None], max_chars: int) -> str:
    if value is None:
        return "null"
    if type(value) is str:
        return _table_text(value, max_chars)
    if type(value) in (int, bool):
        return str(value).lower() if type(value) is bool else str(value)
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("table rejects nonfinite numbers")
        return repr(value)
    value = _table_json_value(
        value, guard=guard, active=set(), remaining=[100], depth=0
    )
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text if len(text) <= max_chars else text[:max_chars] + "… <cell truncated>"


def _table_json_value(
    value: Any,
    *,
    guard: Callable[[], None],
    active: set[int],
    remaining: list[int],
    depth: int,
) -> Any:
    if value is None or type(value) in (bool, int, str):
        if type(value) is str and len(value) > 256:
            return value[:256] + "… <cell truncated>"
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("table rejects nonfinite numbers")
        return value
    if type(value) not in (list, tuple, dict):
        raise TypeError(
            f"table cells require ordinary serializable data, got {type(value).__name__}"
        )
    if depth >= 8:
        return {"…": "depth omitted"}
    identity = id(value)
    if identity in active:
        raise ValueError("table cells reject a cycle")
    active.add(identity)
    try:
        if type(value) is dict:
            result: dict[str, Any] = {}
            for key, child in value.items():
                if remaining[0] <= 0:
                    result["…"] = "items omitted"
                    break
                if type(key) is not str:
                    raise TypeError("table object keys must be strings")
                guard()
                remaining[0] -= 1
                result[key] = _table_json_value(
                    child,
                    guard=guard,
                    active=active,
                    remaining=remaining,
                    depth=depth + 1,
                )
            return result
        result_list: list[Any] = []
        for child in value:
            if remaining[0] <= 0:
                result_list.append({"…": "items omitted"})
                break
            guard()
            remaining[0] -= 1
            result_list.append(
                _table_json_value(
                    child,
                    guard=guard,
                    active=active,
                    remaining=remaining,
                    depth=depth + 1,
                )
            )
        return result_list
    finally:
        active.remove(identity)


def _table_text(value: str, max_chars: int) -> str:
    clipped = len(value) > max_chars
    visible = value[:max_chars]
    escaped: list[str] = []
    for char in visible:
        if char == "\n":
            escaped.append("\\n")
        elif char == "\r":
            escaped.append("\\r")
        elif char == "\t":
            escaped.append("\\t")
        elif unicodedata.category(char) == "Cc":
            escaped.append(f"\\u{ord(char):04x}")
        else:
            escaped.append(char)
    text = "".join(escaped)
    return text + "…" if clipped else text


def _check_text_size(value: str, limit: int) -> None:
    if _utf8_size_bounded(value, limit) > limit:
        raise ValueError("filter text exceeds byte limit")


def _utf8_size_bounded(value: str, limit: int) -> int:
    """Measure UTF-8 bytes without encoding an unbounded string at once."""
    if len(value) > limit:
        return limit + 1
    total = 0
    for offset in range(0, len(value), 4096):
        total += len(value[offset : offset + 4096].encode("utf-8"))
        if total > limit:
            return limit + 1
    return total


def _json_string_size_bounded(value: str, limit: int) -> int:
    """Return the compact JSON string size, stopping once its byte cap is crossed."""
    if len(value) > limit:
        return limit + 1
    total = 2  # quotes
    short_escapes = {'"', "\\", "\b", "\f", "\n", "\r", "\t"}
    for char in value:
        codepoint = ord(char)
        if char in short_escapes:
            total += 2
        elif codepoint < 0x20:
            total += 6
        else:
            total += len(char.encode("utf-8"))
        if total > limit:
            return limit + 1
    return total
