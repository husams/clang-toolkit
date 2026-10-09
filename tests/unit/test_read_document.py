from unittest.mock import Mock

import pytest

from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.persistence import PersistenceError, read_document
from clang_toolkit.client import Client


@pytest.mark.parametrize("suffix, content", [
    ("json", '{"project": {"name": "λ", "sources": ["a.cpp", "b.cpp"], "enabled": true, "value": null}}'),
    ("yaml", 'project:\n  name: λ\n  sources: [a.cpp, b.cpp]\n  enabled: true\n  value: null\n'),
    ("yml", 'project:\n  name: λ\n  sources: [a.cpp, b.cpp]\n  enabled: true\n  value: null\n'),
])
def test_read_nested_document_and_use_fields(tmp_path, suffix, content):
    path = tmp_path / f"data.{suffix}"
    path.write_text(content, encoding="utf-8")
    client = Mock(spec=Client)
    runtime = Runtime(client, cwd=tmp_path, environment={"HOME": str(tmp_path)})
    try:
        assert runtime.execute(f'let data = read "~/data.{suffix}"') == ""
        assert runtime.execute("print $data.project.name") == "λ"
        assert runtime.execute("print $data.project.sources[1]") == "b.cpp"
        assert runtime.execute("print $data.project.enabled") == "true"
        assert runtime.bindings["data"]["project"]["value"] is None
        runtime.execute("let names = foreach $source in $data.project.sources do $source done")
        assert runtime.bindings["names"] == ["a.cpp", "b.cpp"]
        runtime.execute(f'let filename = "$HOME/data.{suffix}"')
        runtime.execute("let second = read $filename")
        assert runtime.bindings["second"] == runtime.bindings["data"]
        runtime.execute(f'let files = glob("*.{suffix}")')
        runtime.execute("let third = read $files[0]")
        assert runtime.bindings["third"] == runtime.bindings["data"]
    finally:
        runtime.close()
    client.match.assert_not_called()
    assert path.read_text(encoding="utf-8") == content


@pytest.mark.parametrize("content, expected", [
    ("[1, true, null]", [1, True, None]), ("null", None),
    ('"hello"', "hello"), ("42", 42), ("{}", {}),
])
def test_read_json_root_values(tmp_path, content, expected):
    path = tmp_path / "root.json"
    path.write_text(content)
    assert read_document(path) == expected


def test_read_does_not_decode_persistence_envelope(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("schema_version: 4\ntype: config\nvalue: custom\n")
    assert read_document(path) == {"schema_version": 4, "type": "config", "value": "custom"}


@pytest.mark.parametrize("name, content, message", [
    ("bad.json", "{bad}", "cannot read"),
    ("bad.yaml", "key: [", "cannot read"),
    ("unsafe.yaml", "!!python/object/apply:os.system ['exit 1']", "cannot read"),
    ("cycle.yaml", "&cycle [*cycle]", "recursive YAML aliases"),
    ("bad.txt", "{}", ".json, .yaml or .yml"),
])
def test_read_failure_preserves_binding(tmp_path, name, content, message):
    (tmp_path / name).write_text(content)
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    try:
        runtime.execute('let data = "previous"')
        assert message in dispatch(runtime.client, f'let data = read "{name}"', runtime)
        assert runtime.bindings["data"] == "previous"
        assert "cannot read" in dispatch(runtime.client, 'let data = read "missing.json"', runtime)
        assert runtime.bindings["data"] == "previous"
    finally:
        runtime.close()


def test_yaml_shared_aliases_and_empty_document(tmp_path):
    path = tmp_path / "aliases.yaml"
    path.write_text("first: &value [1, 2]\nsecond: *value\n")
    assert read_document(path) == {"first": [1, 2], "second": [1, 2]}
    path.write_text("")
    assert read_document(path) is None
