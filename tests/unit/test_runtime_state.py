"""Durable settings, value exchange, output, and session history."""

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest

from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.runtime import File, Runtime
from clang_toolkit.cli.runtime.config import ConfigError, ConfigStore
from clang_toolkit.cli.runtime.history import HistoryStore
from clang_toolkit.cli.runtime.persistence import PersistenceError, load, save
from clang_toolkit.cli.runtime.values import MatchSet, MatcherExpr
from clang_toolkit.client import Client


def isolated_store(tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    system = tmp_path / "etc/config.yaml"
    project.mkdir()
    home.mkdir()
    system.parent.mkdir()
    return project, home, system


def test_configuration_merges_bottom_up_and_set_clear_persists(tmp_path):
    project, home, system = isolated_store(tmp_path)
    system.write_text(
        "traversal: IgnoreUnlessSpelledInSource\nvars: {origin: system, only_system: yes}\n"
    )
    (home / ".clang_tools.yaml").write_text(
        'vars: {origin: user}\nextra_args: ["-std=c++20"]\n'
    )
    (project / ".clang_tools.yaml").write_text(
        'vars: {origin: project}\nextra_args: ["-std=c++23"]\n'
    )
    store = ConfigStore(project, home=home, system=system)
    assert store.effective["vars"]["origin"] == "project"
    assert store.effective["vars"]["only_system"] is True
    assert store.effective["extra_args"] == ["-std=c++23"]
    assert store.effective["traversal"] == "IgnoreUnlessSpelledInSource"
    store.set("traversal", "AsIs")
    assert (
        ConfigStore(project, home=home, system=system).effective["traversal"] == "AsIs"
    )
    store.clear("traversal")
    assert store.effective["traversal"] == "IgnoreUnlessSpelledInSource"
    store.set("cache_dir", "cache", scope="user")
    assert (
        ConfigStore(project, home=home, system=system).effective["cache_dir"] == "cache"
    )


def test_configuration_rejects_invalid_update_and_concurrent_change(tmp_path):
    project, home, system = isolated_store(tmp_path)
    store = ConfigStore(project, home=home, system=system)
    with pytest.raises(ConfigError, match="traversal"):
        store.set("traversal", "invalid")
    assert not (project / ".clang_tools.yaml").exists()
    (project / ".clang_tools.yaml").write_text("traversal: AsIs\n")
    with pytest.raises(ConfigError, match="changed"):
        store.set("cache_dir", "cache")
    assert store.effective["cache_dir"] is None


def test_yaml_json_csv_round_trips_and_invalid_load_is_atomic(tmp_path):
    matcher = MatcherExpr(
        "varDecl", (MatcherExpr("hasType", (MatcherExpr("pointerType"),)),)
    )
    yaml_path = save(matcher, tmp_path / "matcher")
    assert yaml_path.name == "matcher.yaml"
    assert load(tmp_path / "matcher") == matcher
    json_path = save([1, True, "x"], tmp_path / "values.json")
    assert load(json_path) == [1, True, "x"]
    csv_path = save(
        [{"name": "a", "count": 2}, {"name": "b", "count": 3}], tmp_path / "rows.csv"
    )
    assert load(csv_path) == [{"name": "a", "count": 2}, {"name": "b", "count": 3}]
    assert load(save(MatchSet(("one", "two")), tmp_path / "results.yaml")) == MatchSet(
        ("one", "two")
    )
    (tmp_path / "bad.yaml").write_text("schema_version: 999\n")
    with pytest.raises(PersistenceError, match="schema_version"):
        load(tmp_path / "bad.yaml")
    with pytest.raises(PersistenceError, match="flat lists"):
        save([{"nested": [1]}], tmp_path / "bad.csv")


def test_runtime_save_load_relative_path_and_file_output(tmp_path):
    client = Mock(spec=Client)
    session = Runtime(client, cwd=tmp_path, environment={})
    assert dispatch(client, "let x = [1, 2]", session) == ""
    assert dispatch(client, 'save $x to "values"', session) == ""
    assert (tmp_path / "values.yaml").exists()
    assert dispatch(client, 'load "values" into $restored', session) == ""
    assert session.bindings["restored"] == [1, 2]
    assert dispatch(client, 'set output to "result.txt"', session) == ""
    assert dispatch(client, "print $restored", session) == ""
    assert (tmp_path / "result.txt").read_text() == "1\n2\n"
    assert dispatch(client, 'set output to "result.txt" mode replace', session) == ""
    assert dispatch(client, 'print "replaced"', session) == ""
    assert (tmp_path / "result.txt").read_text() == "replaced\n"
    assert dispatch(client, "clear output", session) == ""
    assert dispatch(client, "$restored", session) == "1\n2"
    session.close()


def test_runtime_settings_commands_persist_and_bad_value_does_not(tmp_path):
    client = Mock(spec=Client)
    session = Runtime(client, cwd=tmp_path, environment={})
    assert dispatch(client, "set traversal IgnoreUnlessSpelledInSource", session) == ""
    assert dispatch(client, 'set extra_args ["-std=c++23"]', session) == ""
    assert dispatch(client, 'add extra_arg "-Iinclude"', session) == ""
    assert dispatch(client, 'set cache_dir to "cache"', session) == ""
    assert dispatch(client, 'set files to glob("*.cpp")', session) == ""
    assert session.config_store.effective["extra_args"] == ["-std=c++23", "-Iinclude"]
    assert session.config_store.effective["cache_dir"] == "cache"
    assert "traversal" in (tmp_path / ".clang_tools.yaml").read_text()
    assert "error:" in dispatch(client, "set extra_args [3]", session)
    assert session.config_store.effective["extra_args"] == ["-std=c++23", "-Iinclude"]
    session.close()


def test_history_records_uuid_label_and_export(tmp_path):
    client = Mock(spec=Client)
    history = HistoryStore(tmp_path / "history.jsonl")
    session = Runtime(client, cwd=tmp_path, environment={}, history=history)
    assert session.session_id.version == 4
    assert dispatch(client, 'session label "pointers"', session) == ""
    assert dispatch(client, "let x = true", session) == ""
    assert dispatch(client, 'history save "saved-history.jsonl"', session) == ""
    records = [
        json.loads(line)
        for line in (tmp_path / "saved-history.jsonl").read_text().splitlines()
    ]
    assert records[0]["session_id"] == str(session.session_id)
    assert records[1]["label"] == "pointers"
    assert records[1]["command"] == "let x = true"
    assert dispatch(client, "history clear", session) == ""
    assert history.path.read_text() == ""
    session.close()


def test_file_values_round_trip_without_losing_type_or_display_path(tmp_path):
    client = Mock(spec=Client)
    (tmp_path / "unit.cpp").write_text("abc")
    session = Runtime(client, cwd=tmp_path, environment={})
    dispatch(client, 'let files = glob("*.cpp")', session)
    original = session.bindings["files"][0]
    save(session.bindings["files"], tmp_path / "files.json")
    loaded = load(tmp_path / "files.json")
    assert loaded == [original]
    assert isinstance(loaded[0], File)
    assert str(loaded[0]) == "unit.cpp"
    assert loaded[0].absolute == str(tmp_path / "unit.cpp")
