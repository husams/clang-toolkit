from unittest.mock import Mock

import pytest

from clang_toolkit.client import Client
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.persistence import PersistenceError, load, save
from clang_toolkit.cli.runtime.values import MatchSet, MatcherExpr


@pytest.mark.parametrize("kind", ["json", "yaml", "proto"])
def test_variable_and_environment_paths_roundtrip(tmp_path, kind):
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={"HOME": str(tmp_path)})
    try:
        runtime.execute('let filename = "$HOME/results"')
        runtime.execute("let x = [1, true, 9007199254740993]")
        runtime.execute(f"save $x to $filename as {kind}")
        runtime.execute(f'load "$HOME/results.{kind}" into $restored')
        assert runtime.bindings["restored"] == runtime.bindings["x"]
    finally:
        runtime.close()


def test_per_print_replace_append_and_persistent_sink(tmp_path):
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={"HOME": str(tmp_path)})
    try:
        runtime.execute('let filename = "$HOME/log.txt"')
        runtime.execute('print "old" to $filename')
        runtime.execute('print "new" to $filename mode replace')
        runtime.execute('print "added" to $filename mode append')
        assert (tmp_path / "log.txt").read_text() == "new\nadded\n"
        assert runtime.execute('print "terminal"') == "terminal"
        runtime.execute('set output to $filename mode append')
        runtime.execute('print "persistent"')
        assert (tmp_path / "log.txt").read_text().endswith("persistent\n")
    finally:
        runtime.close()


def test_proto_nested_types_and_invalid_save_preserve_file(tmp_path):
    path = tmp_path / "values.proto"
    value = [2**128, -2**128, [], {}, None, 1.25, "λ", MatcherExpr("functionDecl"),
             MatchSet(({"name": "f", "count": 3},))]
    assert load(save(value, path)) == value
    before = path.read_bytes()
    with pytest.raises(PersistenceError):
        save(object(), path)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]
    path.write_bytes(b"broken")
    with pytest.raises(PersistenceError):
        load(path)
