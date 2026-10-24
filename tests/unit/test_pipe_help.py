"""The complete callable catalog is discoverable and its examples execute offline."""

from __future__ import annotations

from unittest.mock import Mock
import sys

import pytest
from prompt_toolkit.document import Document

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.callable_help import builtin_callable_help
from clang_toolkit.cli.callable_reference import BUILTIN_ARGUMENTS, BUILTIN_EXAMPLES
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.help import help_entry, render_help_markdown
from clang_toolkit.cli.language import parser
from clang_toolkit.cli.runtime.prototype import Context, run_source
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.repl_editor import PrototypeCompleter


def test_launcher_help_points_to_offline_pipeline_and_callable_reference(
    monkeypatch, capsys
):
    from clang_toolkit.cli.app import prototype_main

    monkeypatch.setattr(sys, "argv", ["ctk", "--help"])
    with pytest.raises(SystemExit) as stopped:
        prototype_main()
    assert stopped.value.code == 0
    output = capsys.readouterr().out
    for topic in ("help pipes", "help callables", "help map", "first?"):
        assert topic in output


def test_catalog_covers_every_registered_callable_and_has_no_private_sentinels():
    entries = builtin_callable_help(Context().functions)
    assert set(entries) == set(Context().functions) | {"ctk"}
    assert set(entries) == set(BUILTIN_ARGUMENTS) == set(BUILTIN_EXAMPLES)
    for item in entries.values():
        assert item.arguments and item.examples and item.pipeline_signature
        assert "object at 0x" not in item.signature
        assert "object at 0x" not in item.pipeline_signature
    assert entries["first"].signature == "first(value, n=omitted)"
    assert entries["last"].pipeline_signature == "last(n=omitted)"
    assert entries["zip"].pipeline_signature == "zip(other, *others, strict=true)"


@pytest.fixture(params=["tree", "compiled"])
def runtime(request, tmp_path):
    instance = PrototypeRuntime(
        Mock(), script_engine=request.param, cwd=tmp_path, environment={}
    )
    try:
        yield instance
        assert instance.client.mock_calls == []
    finally:
        instance.close()


def submit(runtime, source):
    result = dispatch_result(runtime.client, source, runtime)
    assert result.success, result.output
    return result.output


def test_all_callables_are_listed_and_have_both_help_forms_and_workspace_examples(
    runtime,
):
    overview = submit(runtime, "help")
    catalog = submit(runtime, "help callables")
    assert "pipes" in overview and "|" in overview
    for name, item in runtime.callable_help().items():
        assert item.signature in overview
        assert item.signature in catalog
        detail = submit(runtime, f"help {name}")
        assert detail == submit(runtime, f"{name}?")
        assert "Usage:" in detail and "Arguments, options and defaults:" in detail
        assert "Examples:" in detail
        assert f"VALUE | {item.pipeline_signature}" in detail
        for source in item.examples:
            assert source in detail
            assert source in item.markdown()
            submit(runtime, source)


def test_plain_and_workspace_indexes_and_static_help_work_without_runtime():
    from clang_toolkit.cli.app import dispatch

    client = Mock()
    statement = parser().parse("help").children[0]
    workspace = render_help_markdown(statement)
    plain = dispatch(client, "help")
    for name, item in builtin_callable_help().items():
        assert item.signature in workspace
        assert item.signature in plain
        assert "Examples:" in dispatch(client, f"help {name}")
    assert "pipes" in workspace
    assert client.mock_calls == []


def test_help_completion_includes_every_builtin_once_and_both_catalog_topics(runtime):
    for completer in (
        ReplCompleter(),
        PrototypeCompleter(ReplCompleter(function_help=runtime.callable_help)),
    ):
        choices = [
            item.text for item in completer.get_completions(Document("help "), None)
        ]
        for name in (*builtin_callable_help(), "pipes", "callables"):
            assert choices.count(name) == 1


def test_active_user_definitions_are_listed_and_keep_source_help(runtime):
    submit(runtime, "let scale(value, by: factor = 2) = value * factor")
    assert "scale(value, by: factor = 2)" in submit(runtime, "help")
    assert "scale(value, by: factor = 2)" in submit(runtime, "help callables")
    assert "value * factor" not in submit(runtime, "help")
    assert "value * factor" not in submit(runtime, "help callables")
    assert "User defined expression." in submit(runtime, "help scale")
    assert "value * factor" in submit(runtime, "help scale")
    submit(runtime, "let first(value) = 99")
    assert "let first(value) = 99" in submit(runtime, "first?")


def test_builtin_alias_signatures_do_not_expose_selection_sentinels(runtime):
    submit(runtime, "let head = first; let tail = last")
    for name in ("head", "tail"):
        description = runtime.callable_help()[name]
        assert description.signature == f"{name}(value, n=omitted)"
        assert description.pipeline_signature == f"{name}(n=omitted)"
        assert "object at 0x" not in submit(runtime, f"help {name}")


@pytest.mark.parametrize("topic", ["help", "help callables", "help pipes"])
def test_normal_help_hides_imported_private_helpers(runtime, tmp_path, topic):
    from clang_toolkit.cli.runtime.prototype.help import render_help_markdown

    (tmp_path / "helpers.ctk").write_text(
        "let _ctkBase(edge) = edge + 1\n"
        "let __private(edge) = edge + 2\n"
        "let directBases(edge) = _ctkBase(edge)\n"
        "let visibleBase = _ctkBase\n"
    )
    submit(runtime, 'import "helpers.ctk"')
    statement = parser().parse(topic).children[0]
    for output in (
        submit(runtime, topic),
        render_help_markdown(statement, runtime.callable_help()),
    ):
        assert "_ctkBase" not in output
        assert "__private" not in output
        assert "directBases(edge)" in output
        assert "visibleBase(edge)" in output
        assert "map(value, callback)" in output
    assert submit(runtime, "print directBases(4)") == "5"
    assert submit(runtime, "print visibleBase(4)") == "5"
    assert "_ctkBase(edge)" in submit(runtime, "help _ctkBase")
    assert submit(runtime, "help _ctkBase") == submit(runtime, "_ctkBase?")


def test_help_suggestions_hide_private_helpers_until_explicitly_requested(runtime):
    submit(runtime, "let _ctkBase(edge) = edge; let directBases(edge) = _ctkBase(edge)")
    for completer in (
        ReplCompleter(function_help=runtime.callable_help),
        PrototypeCompleter(ReplCompleter(function_help=runtime.callable_help)),
    ):
        normal = {
            item.text for item in completer.get_completions(Document("help "), None)
        }
        assert "_ctkBase" not in normal
        assert "directBases" in normal
        explicit = {
            item.text
            for item in completer.get_completions(Document("help _ctk"), None)
        }
        assert "_ctkBase" in explicit


def test_pipe_overview_examples_are_self_contained(runtime):
    for source in help_entry("pipes").examples:
        submit(runtime, source)


# Check actual results as well as successful execution; especially distinguish
# scalar selection, empty selection and counted selection for first/last.
EXPECTED = {
    "map": [[2, 4, 6], [2, 3]],
    "filter": [[2, 3]],
    "take": [[10, 20]],
    "drop": [[20, 30]],
    "split_by": [["a", "", "b"]],
    "join": ["a-b"],
    "keys": [["name", "count"]],
    "values": [["Widget", 2]],
    "entries": [[{"key": "name", "value": "Widget"}]],
    "pick": [{"name": "Widget", "count": 2}],
    "flatten": [[1, 2, 3]],
    "zip": [[("a", 1), ("b", 2)], [(1, 2)]],
    "zip_longest": [[(1, 2), (0, 3)]],
    "enumerate": [[(1, "a"), (2, "b")]],
    "length": [3],
    "first": [10, [10, 20], None, [10]],
    "last": [30, [20, 30], None, []],
    "reverse": [[30, 20, 10]],
    "unique": [[2, 1]],
    "unique_by": [[{"name": "a", "n": 1}]],
    "sort": [[3, 2, 1]],
    "sort_by": [[("b", 1), ("a", 2)]],
    "to_list": [[1, 2]],
    "to_tuple": [(1, 2)],
    "upper": ["WIDGET"],
    "lower": ["widget"],
    "casefold": ["strasse"],
    "camel_case": ["helloWorld"],
    "pascal_case": ["HelloWorld"],
    "snake_case": ["hello_world"],
    "kebab_case": ["hello-world"],
    "trim": ["hello"],
    "trim_start": ["hello  "],
    "trim_end": ["  hello"],
    "replace": ["b-b-a"],
    "strip_prefix": ["Widget"],
    "strip_suffix": ["widget"],
    "starts_with": [True],
    "ends_with": [True],
    "contains": [True],
    "pretty": ["[1, 2]"],
    "json": ['{\n  "name": "Widget",\n  "count": 2\n}'],
    "table": ["name    count\nWidget  2    "],
    "len": [2, 2],
    "range": [[1, 3, 5], [0, 1, 2]],
}


@pytest.mark.parametrize("engine", ["tree", "compiled"])
@pytest.mark.parametrize("name", EXPECTED)
def test_documented_examples_produce_expected_values(engine, name):
    examples = BUILTIN_EXAMPLES[name]
    assert len(examples) == len(EXPECTED[name])
    for source, expected in zip(examples, EXPECTED[name], strict=True):
        assert run_source(source, engine=engine).output == [expected], source
