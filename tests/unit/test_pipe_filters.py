from __future__ import annotations

import inspect
import json
import math

import pytest

from clang_toolkit.cli.runtime.prototype.filters import (
    FILTER_DESCRIPTIONS,
    FILTER_SIGNATURES,
    make_filters,
)
from clang_toolkit.cli.runtime.prototype.semantics import Context, ExecutionLimitError


@pytest.fixture
def filters() -> dict[str, object]:
    return make_filters(Context(max_steps=10_000, max_items=100))


def test_registry_exposes_documented_signatures(filters: dict[str, object]) -> None:
    assert set(filters) == set(FILTER_SIGNATURES) == set(FILTER_DESCRIPTIONS)
    assert tuple(inspect.signature(filters["take"]).parameters) == ("value", "n")
    assert tuple(inspect.signature(filters["unique_by"]).parameters) == (
        "value",
        "callback",
    )


def test_sequence_and_mapping_filters(filters: dict[str, object]) -> None:
    assert filters["take"]([0, 1, 2, 3], 2) == [0, 1]
    assert filters["drop"]([0, 1, 2], 1) == [1, 2]
    assert filters["split_by"]("a,,b,", ",") == ["a", "", "b", ""]
    assert filters["join"](["a", "b"], "-") == "a-b"
    record = {"b": 2, "a": 1, "skip": 3}
    assert filters["keys"](record) == ["b", "a", "skip"]
    assert filters["values"](record) == [2, 1, 3]
    assert filters["entries"](record) == [
        {"key": "b", "value": 2},
        {"key": "a", "value": 1},
        {"key": "skip", "value": 3},
    ]
    assert filters["pick"](record, "a", "b") == {"a": 1, "b": 2}
    assert filters["flatten"]([[1, 2], (3,), [4]]) == [1, 2, 3, 4]
    with pytest.raises(TypeError, match="child at index 1"):
        filters["flatten"]([[1], 2])
    with pytest.raises(TypeError, match="collection filters"):
        filters["take"]("abc", 1)
    with pytest.raises(TypeError, match="collection filters"):
        filters["take"]({"a": 1}, 1)


@pytest.mark.parametrize("count", [-1, True, 1.0, "1"])
def test_take_drop_reject_invalid_counts(
    filters: dict[str, object], count: object
) -> None:
    with pytest.raises((ValueError, TypeError)):
        filters["take"]([1], count)
    with pytest.raises((ValueError, TypeError)):
        filters["drop"]([1], count)


def test_zip_enumerate_and_sequence_utilities(filters: dict[str, object]) -> None:
    assert filters["zip"]([1, 2], ["a", "b"]) == [(1, "a"), (2, "b")]
    assert filters["zip"]([1], [2, 3], strict=False) == [(1, 2)]
    assert filters["zip_longest"]([1], [2, 3], fill="x") == [(1, 2), ("x", 3)]
    assert filters["enumerate"](["a", "b"], start=4) == [(4, "a"), (5, "b")]
    assert filters["length"]("😀a") == 2
    assert filters["length"]({"x": 1}) == 1
    assert filters["first"]([1, 2]) == 1
    assert filters["last"]((1, 2)) == 2
    assert filters["reverse"]([1, 2]) == [2, 1]
    assert filters["to_list"]((1, 2)) == [1, 2]
    assert filters["to_tuple"]([1, 2]) == (1, 2)


def test_duplicate_mismatch_empty_and_missing_errors(
    filters: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="equal lengths"):
        filters["zip"]([1], [2, 3])
    with pytest.raises(ValueError, match="empty"):
        filters["first"]([])
    with pytest.raises(ValueError, match="empty"):
        filters["last"]([])
    with pytest.raises((KeyError, ValueError), match="missing|unknown"):
        filters["pick"]({"a": 1}, "missing")
    with pytest.raises((KeyError, ValueError), match="duplicate"):
        filters["pick"]({"a": 1}, "a", "a")
    with pytest.raises(ValueError, match="separator"):
        filters["split_by"]("x", "")


def test_stable_unique_and_callback_transforms(filters: dict[str, object]) -> None:
    assert filters["unique"]([True, 1, True, 1, False]) == [True, 1, False]
    assert filters["unique"]([(1, "x"), (1, "x"), (2, "x")]) == [(1, "x"), (2, "x")]
    assert filters["map"]([1, 2], lambda item: item * 2) == [2, 4]
    assert filters["filter"]([0, 1, 2], lambda item: item > 0) == [1, 2]
    assert filters["take"]([1, 2, 3], 1) == [1]
    assert filters["unique_by"](["A", "a", "B"], lambda item: item.lower()) == [
        "A",
        "B",
    ]
    with pytest.raises(TypeError, match="bool"):
        filters["filter"]([1], lambda item: 1)


def test_callbacks_use_one_signature_mode_once_and_report_item_index() -> None:
    context = Context(max_steps=100, max_items=20)
    filters = make_filters(context)
    calls: list[object] = []

    def unary(pair: tuple[int, int], suffix: str = "") -> tuple[tuple[int, int], str]:
        calls.append(pair)
        return pair, suffix

    assert filters["map"]([(1, 2)], unary) == [((1, 2), "")]
    assert calls == [(1, 2)]

    def binary(left: int, right: int) -> int:
        calls.append((left, right))
        return left + right

    assert filters["map"]([(2, 3)], binary) == [5]
    assert calls[-1] == (2, 3)

    context.current_location = (3, 4)

    def fail(_item: int) -> int:
        calls.append("failed-once")
        raise ValueError("callback boom")

    with pytest.raises(ValueError, match="source item 0.*line 3, column 4"):
        filters["map"]([7], fail)
    assert calls.count("failed-once") == 1
    assert filters["map"].__ctk_filter_name__ == "map"


def test_case_conversion_handles_unicode_and_acronyms(
    filters: dict[str, object],
) -> None:
    assert filters["snake_case"]("HTTPServerID café") == "http_server_id_café"
    assert filters["snake_case"]("écoleÉclair") == "école_éclair"
    assert filters["kebab_case"]("helloWorld") == "hello-world"
    assert filters["camel_case"]("hello_WORLD") == "helloWorld"
    assert filters["pascal_case"]("hello-world") == "HelloWorld"
    assert filters["upper"]("straße") == "STRASSE"
    assert filters["casefold"]("Straße") == "strasse"


def test_string_helpers_and_exact_boolean_predicates(
    filters: dict[str, object],
) -> None:
    assert filters["trim"]("  abc \n") == "abc"
    assert filters["trim_start"]("  abc") == "abc"
    assert filters["trim_end"]("abc  ") == "abc"
    assert filters["replace"]("aaa", "a", "b", count=2) == "bba"
    assert filters["replace"]("aaa", "a", "b", count=0) == "aaa"
    assert filters["strip_prefix"]("pre-file", "pre-") == "file"
    assert filters["strip_suffix"]("file.txt", ".txt") == "file"
    for name, result in (
        ("starts_with", True),
        ("ends_with", True),
        ("contains", True),
    ):
        assert (
            filters[name](
                "abc",
                "a" if name == "starts_with" else "c" if name == "ends_with" else "b",
            )
            is result
        )
    with pytest.raises(ValueError, match="old"):
        filters["replace"]("a", "", "b")
    with pytest.raises(ValueError, match="count"):
        filters["replace"]("a", "a", "b", count=-2)
    with pytest.raises(ValueError, match="byte limit"):
        filters["replace"]("a" * 200_000, "a", "x" * 8)


def test_sort_domains_and_unique_keys_are_checked(filters: dict[str, object]) -> None:
    assert filters["sort"]([3, 1, 2]) == [1, 2, 3]
    assert filters["sort_by"](["bb", "a"], lambda value: len(value)) == ["a", "bb"]
    assert filters["unique"]([1, 1.0]) == [1]
    with pytest.raises(TypeError, match="homogeneous"):
        filters["sort"]([1, "1"])
    with pytest.raises(TypeError, match="finite"):
        filters["sort"]([1.0, math.inf])
    with pytest.raises(TypeError, match="unsupported"):
        filters["unique"]([[1]])


def test_nested_unique_keys_obey_item_and_depth_budgets() -> None:
    context = Context(max_steps=100, max_items=2)
    filters = make_filters(context)
    large_key = tuple(range(100_000))
    with pytest.raises(ExecutionLimitError, match="item budget"):
        filters["unique"]([large_key])
    with pytest.raises(ExecutionLimitError, match="item budget"):
        filters["unique_by"]([0], lambda _item: large_key)

    deeply_nested: object = 1
    for _ in range(33):
        deeply_nested = (deeply_nested,)
    bounded = make_filters(Context(max_steps=100, max_items=100))
    with pytest.raises(TypeError, match="depth limit"):
        bounded["unique"]([deeply_nested])


def test_string_outputs_are_bounded_before_large_allocations() -> None:
    filters = make_filters(Context(max_steps=100, max_items=10))
    with pytest.raises(ValueError, match="byte limit"):
        filters["join"](["😀" * 300_000], "")
    with pytest.raises(ValueError, match="byte limit"):
        filters["lower"]("İ" * 400_000)
    with pytest.raises(ValueError, match="byte limit"):
        filters["json"]("\x00" * 500_000)
    preview = filters["pretty"]("x" * 2_000_000)
    assert "string omitted" in preview


def test_formatters_preserve_json_and_bound_pretty_output(
    filters: dict[str, object],
) -> None:
    encoded = filters["json"]({"x": (1, 2)}, indent=0)
    assert type(encoded) is str
    assert json.loads(encoded) == {"x": [1, 2]}
    assert filters["pretty"]((1,), indent=0) == "(1,)"
    assert "omitted" in filters["pretty"](list(range(12)), indent=2, max_items=3)
    assert "omitted" in filters["table"](
        [{"a": 1}, {"a": 2}], columns=["a"], max_items=1
    )
    assert filters["table"]([], columns=["a"]).startswith("a\n")
    assert "omitted" not in filters["table"]([{"a": 1}], columns=["a"], max_items=1)
    assert "omitted" in filters["table"]([{"a": 1}], columns=["a"], max_items=0)
    with pytest.raises(ValueError, match="nonfinite"):
        filters["table"]([{"a": math.inf}], columns=["a"])
    with pytest.raises(TypeError, match="serializable"):
        filters["table"]([{"a": object()}], columns=["a"])
    table = filters["table"](
        [{"name": "first\nsecond", "value": 1}], columns=["name", "value"]
    )
    assert "first\\nsecond" in table
    assert table.count("\n") == 1
    with pytest.raises(TypeError, match="serializable"):
        filters["json"]({"bad": object()})
    cyclic: list[object] = []
    cyclic.append(cyclic)
    with pytest.raises((ValueError, TypeError), match="cycle"):
        filters["json"](cyclic)


def test_iteration_obeys_context_budgets_and_take_does_not_overread() -> None:
    context = Context(max_steps=2, max_items=2)
    filters = make_filters(context)
    seen: list[int] = []

    def source():
        for item in range(10):
            seen.append(item)
            yield item

    assert filters["take"](source(), 1) == [0]
    assert seen == [0]
    with pytest.raises(ExecutionLimitError):
        filters["to_list"](iter(range(5)))


@pytest.mark.parametrize("name", ["zip", "zip_longest"])
def test_zip_cell_work_obeys_step_budget(name: str) -> None:
    filters = make_filters(Context(max_steps=3, max_items=10))
    with pytest.raises(ExecutionLimitError, match="step limit"):
        filters[name]([1, 2], [3, 4])


@pytest.mark.parametrize("name", ["zip", "zip_longest"])
def test_zip_width_obeys_item_budget(name: str) -> None:
    filters = make_filters(Context(max_steps=10, max_items=1))
    with pytest.raises(ExecutionLimitError, match="column count"):
        filters[name]([1], [2])


def test_zip_longest_fill_cells_consume_steps() -> None:
    filters = make_filters(Context(max_steps=1, max_items=10))
    with pytest.raises(ExecutionLimitError, match="step limit"):
        filters["zip_longest"]([1], [])


def test_zip_non_strict_stops_at_first_exhausted_input() -> None:
    filters = make_filters(Context(max_steps=10, max_items=10))
    advanced: list[bool] = []

    def source():
        advanced.append(True)
        yield 1

    assert filters["zip"]([], source(), strict=False) == []
    assert advanced == []
