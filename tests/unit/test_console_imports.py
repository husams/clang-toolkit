from unittest.mock import Mock

import pytest

from clang_toolkit.client import Client
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.cli.runtime.imports import script_source


@pytest.fixture
def runtime(tmp_path):
    session = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    yield session
    session.close()


def test_import_loads_variables_and_matcher_definitions_into_same_runtime(runtime):
    library = runtime.cwd / "lib.ctk"
    library.write_text(
        '# reusable predicates\n'
        'let prefix = "pkg"\n'
        'let named(name) = functionDecl(hasName("${prefix}_${name}"))\n',
        encoding="utf-8",
    )

    assert runtime.execute('import "lib.ctk"') == ""
    assert runtime.execute('let selected = named("alpha")') == ""
    assert runtime.execute("$selected") == 'functionDecl(hasName("pkg_alpha"))'


def test_nested_imports_resolve_from_importing_library(runtime):
    (runtime.cwd / "parts").mkdir()
    (runtime.cwd / "parts" / "inner.ctk").write_text(
        'let suffix = "nested"\n', encoding="utf-8"
    )
    (runtime.cwd / "parts" / "outer.ctk").write_text(
        'import "inner.ctk"\nlet value = $suffix', encoding="utf-8"
    )

    runtime.execute('import "parts/outer.ctk"')
    assert runtime.bindings["value"] == "nested"
    assert runtime.bindings["suffix"] == "nested"


def test_script_source_makes_top_level_script_parent_the_import_base(runtime):
    script = runtime.cwd / "scripts" / "main.ctk"
    library = runtime.cwd / "scripts" / "lib.ctk"
    script.parent.mkdir()
    library.write_text('let value = 17', encoding="utf-8")

    with script_source(runtime, script):
        runtime.execute('import "lib.ctk"')
    assert runtime.bindings["value"] == 17
    assert runtime._import_stack == []


def test_import_rejects_cycles_with_chain_and_cleans_stack(runtime):
    first = runtime.cwd / "first.ctk"
    second = runtime.cwd / "second.ctk"
    first.write_text('import "second.ctk"', encoding="utf-8")
    second.write_text('import "first.ctk"', encoding="utf-8")

    with pytest.raises(EvaluationError, match=r"import cycle:.*first.ctk.*second.ctk.*first.ctk"):
        runtime.execute('import "first.ctk"')
    assert runtime._import_stack == []


def test_import_reports_source_line_and_rolls_back_definitions(runtime):
    library = runtime.cwd / "broken.ctk"
    library.write_text('let value = 1\nlet invalid = $missing', encoding="utf-8")

    with pytest.raises(EvaluationError, match=r"broken.ctk:2: unknown variable: missing"):
        runtime.execute('import "broken.ctk"')
    assert "value" not in runtime.bindings
    assert runtime._import_stack == []


def test_failed_import_restores_mutated_containers_and_preserves_aliases(runtime):
    items = [1]
    record = {"items": items}
    runtime.bindings["existing"] = record
    runtime.bindings["alias"] = record
    library = runtime.cwd / "mutating.ctk"
    library.write_text(
        'let added = $existing.items.push(2)\nlet invalid = $missing',
        encoding="utf-8",
    )

    with pytest.raises(EvaluationError, match="unknown variable: missing"):
        runtime.execute('import "mutating.ctk"')

    assert runtime.bindings["existing"] is record
    assert runtime.bindings["alias"] is record
    assert record["items"] is items
    assert items == [1]
    assert "added" not in runtime.bindings


def test_import_validates_whole_library_before_executing(runtime):
    library = runtime.cwd / "invalid.ctk"
    library.write_text('let value = 1\nquit', encoding="utf-8")

    with pytest.raises(EvaluationError, match="libraries accept let definitions"):
        runtime.execute('import "invalid.ctk"')
    assert "value" not in runtime.bindings


def test_repeated_import_is_allowed_after_active_import_finishes(runtime):
    library = runtime.cwd / "lib.ctk"
    library.write_text('let value = 1', encoding="utf-8")

    runtime.execute('import "lib.ctk"')
    runtime.execute('import "lib.ctk"')
    assert runtime.bindings["value"] == 1
    assert runtime._import_stack == []


@pytest.mark.parametrize("content", ["", "# only a comment\n\n"])
def test_empty_or_comment_only_library_is_a_noop(runtime, content):
    library = runtime.cwd / "empty.ctk"
    library.write_text(content, encoding="utf-8")

    assert runtime.execute('import "empty.ctk"') == ""
    assert runtime.bindings == {}


def test_import_reports_invalid_utf8(runtime):
    library = runtime.cwd / "invalid-encoding.ctk"
    library.write_bytes(b"\xff")

    with pytest.raises(EvaluationError, match="cannot read library.*invalid start byte"):
        runtime.execute('import "invalid-encoding.ctk"')


def test_import_rejects_excessive_nesting_and_cleans_stack(runtime):
    for index in range(65):
        target = f'import "level-{index + 1}.ctk"' if index < 64 else 'let final = true'
        (runtime.cwd / f"level-{index}.ctk").write_text(target, encoding="utf-8")

    with pytest.raises(EvaluationError, match="library import depth exceeds 64"):
        runtime.execute('import "level-0.ctk"')
    assert runtime._import_stack == []
