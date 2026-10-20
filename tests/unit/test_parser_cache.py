"""LALR tables persist across processes without ever risking the console."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from lark import Lark

from clang_toolkit.cli import language, parser_cache
from clang_toolkit.cli.parser_cache import cached_lalr

GRAMMAR = '''
start: WORD+
other: WORD
WORD: /[a-z]+/
%ignore " "
'''


class Upper:
    """Module-level so it can be pickled with the parser tables."""

    always_accept = ()

    def __init__(self, *, loud: bool = False) -> None:
        self.loud = loud

    def process(self, tokens):
        for token in tokens:
            yield token.update(value=token.upper()) if self.loud else token


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return tmp_path / "cache" / "clang-toolkit" / "parsers"


@pytest.fixture
def builds(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every real table construction; loading from disk skips it."""
    built: list[str] = []
    original = Lark._build_parser

    def counting(self: Lark):
        built.append(self.options.start[0])
        return original(self)

    monkeypatch.setattr(Lark, "_build_parser", counting)
    return built


def test_entry_is_created_once_and_reused(isolated_cache: Path, builds: list[str]) -> None:
    first = cached_lalr(GRAMMAR, start="start")
    [entry] = isolated_cache.glob("*.lark")
    assert (entry.stat().st_mode & 0o777) == 0o600
    assert (isolated_cache.stat().st_mode & 0o777) == 0o700

    second = cached_lalr(GRAMMAR, start="start")
    assert builds == ["start"]
    assert list(isolated_cache.iterdir()) == [entry]
    assert first.parse("one two") == second.parse("one two")


def test_loaded_parser_keeps_postlex_and_positions(isolated_cache: Path, builds: list[str]) -> None:
    options = {"start": "start", "propagate_positions": True}
    cached_lalr(GRAMMAR, postlex=Upper(loud=True), **options)
    loaded = cached_lalr(GRAMMAR, postlex=Upper(loud=True), **options)

    tree = loaded.parse("one  two")
    assert builds == ["start"]
    assert [str(token) for token in tree.children] == ["ONE", "TWO"]
    assert (tree.meta.line, tree.meta.column, tree.meta.end_column) == (1, 1, 9)


@pytest.mark.parametrize(
    "changed",
    [
        {"grammar": GRAMMAR + "extra: WORD\n"},
        {"start": "other"},
        {"lexer": "basic"},
        {"propagate_positions": True},
        {"postlex": Upper(loud=True)},
        {"postlex": Upper(loud=False)},
    ],
)
def test_every_input_that_changes_the_tables_changes_the_path(
    isolated_cache: Path, changed: dict[str, object],
) -> None:
    base = {"grammar": GRAMMAR, "start": "start", "lexer": "contextual",
            "propagate_positions": False, "postlex": None}

    def path(settings: dict[str, object]) -> Path:
        merged = {**base, **settings}
        grammar, postlex = merged.pop("grammar"), merged.pop("postlex")
        return parser_cache._entry_path(grammar, postlex, merged)

    assert path(changed) != path({})
    assert path({}) == path({})


def test_interpreter_and_lark_versions_are_part_of_the_path(monkeypatch: pytest.MonkeyPatch) -> None:
    original = parser_cache._entry_path(GRAMMAR, None, {"start": "start"})
    monkeypatch.setattr(parser_cache.lark, "__version__", "0.0-other")
    assert parser_cache._entry_path(GRAMMAR, None, {"start": "start"}) != original
    monkeypatch.undo()
    monkeypatch.setattr(parser_cache.sys, "version", "3.0 other")
    assert parser_cache._entry_path(GRAMMAR, None, {"start": "start"}) != original


@pytest.mark.parametrize("damage", [b"", b"not a pickle", b"\x80\x05\x95truncated"])
def test_damaged_entry_is_rebuilt_silently(
    isolated_cache: Path, builds: list[str], capsys: pytest.CaptureFixture[str], damage: bytes,
) -> None:
    cached_lalr(GRAMMAR, start="start")
    [entry] = isolated_cache.glob("*.lark")
    entry.write_bytes(damage)
    builds.clear()

    assert cached_lalr(GRAMMAR, start="start").parse("a b").data == "start"
    assert builds == ["start"]
    with entry.open("rb") as repaired:
        assert Lark.load(repaired).parse("a b").data == "start"
    cached_lalr(GRAMMAR, start="start")
    assert builds == ["start"]
    assert capsys.readouterr() == ("", "")


def test_entry_that_is_not_a_private_regular_file_is_replaced(
    isolated_cache: Path, builds: list[str],
) -> None:
    cached_lalr(GRAMMAR, start="start")
    [entry] = isolated_cache.glob("*.lark")
    target = isolated_cache.parent / "elsewhere"
    target.write_bytes(entry.read_bytes())
    entry.unlink()
    entry.symlink_to(target)
    builds.clear()

    assert cached_lalr(GRAMMAR, start="start").parse("a").data == "start"
    assert builds == ["start"]
    assert not entry.is_symlink()
    assert entry.is_file()


def test_directory_open_to_other_writers_is_not_trusted(
    isolated_cache: Path, builds: list[str],
) -> None:
    cached_lalr(GRAMMAR, start="start")
    isolated_cache.chmod(0o777)
    builds.clear()

    assert cached_lalr(GRAMMAR, start="start").parse("a").data == "start"
    assert builds == ["start"]


def test_uncreatable_directory_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    builds: list[str],
) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where the cache directory should be")
    monkeypatch.setenv("XDG_CACHE_HOME", str(blocker))

    assert cached_lalr(GRAMMAR, start="start").parse("a b").data == "start"
    assert cached_lalr(GRAMMAR, start="start").parse("a b").data == "start"
    assert builds == ["start", "start"]
    assert blocker.read_text() == "a file where the cache directory should be"
    assert capsys.readouterr() == ("", "")


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_unwritable_directory_falls_back(
    isolated_cache: Path, capsys: pytest.CaptureFixture[str], builds: list[str],
) -> None:
    isolated_cache.mkdir(parents=True, mode=0o700)
    isolated_cache.chmod(0o500)
    try:
        assert cached_lalr(GRAMMAR, start="start").parse("a b").data == "start"
        assert not list(isolated_cache.iterdir())
        assert capsys.readouterr() == ("", "")
    finally:
        isolated_cache.chmod(0o700)


def test_unwritable_home_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_home() -> Path:
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.delenv("XDG_CACHE_HOME")
    monkeypatch.setattr(Path, "home", staticmethod(no_home))
    assert cached_lalr(GRAMMAR, start="start").parse("a").data == "start"


def test_relative_cache_home_uses_dot_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", "relative/cache")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    assert parser_cache.cache_root() == tmp_path / ".cache" / "clang-toolkit"


def test_failed_publication_leaves_no_partial_files(
    isolated_cache: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(source: object, destination: object) -> None:
        raise PermissionError("cannot publish")

    monkeypatch.setattr(parser_cache.os, "replace", refuse)
    assert cached_lalr(GRAMMAR, start="start").parse("a").data == "start"
    assert not list(isolated_cache.iterdir())


def test_old_entries_are_pruned(isolated_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parser_cache, "_MAX_ENTRIES", 2)
    for index in range(4):
        cached_lalr(GRAMMAR + f"unused{index}: WORD\n", start="start")
    assert len(list(isolated_cache.glob("*.lark"))) == 2
    assert not list(isolated_cache.glob(".*"))


def test_concurrent_processes_share_one_complete_entry(tmp_path: Path) -> None:
    script = f'''
from clang_toolkit.cli.parser_cache import cached_lalr
assert cached_lalr({GRAMMAR!r}, start="start").parse("a b c").data == "start"
'''
    env = {**os.environ, "XDG_CACHE_HOME": str(tmp_path / "shared")}
    processes = [
        subprocess.Popen([sys.executable, "-c", script], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(4)
    ]
    for process in processes:
        assert process.communicate(timeout=30) == ("", "")
        assert process.returncode == 0
    directory = tmp_path / "shared" / "clang-toolkit" / "parsers"
    [entry] = directory.iterdir()
    assert Lark.load(entry.open("rb")).parse("x y").data == "start"


def test_console_parsers_behave_identically_when_loaded_from_disk(
    isolated_cache: Path, builds: list[str],
) -> None:
    commands = "file list\nresource status\nbatch part in $inputs size 1 do { print $part.index; }\n"
    built = [language.batch_parser.__wrapped__(), language._editor_parser.__wrapped__()]
    assert len(builds) == 2
    loaded = [language.batch_parser.__wrapped__(), language._editor_parser.__wrapped__()]
    assert len(builds) == 2

    assert built[0].parse(commands) == loaded[0].parse(commands)
    assert [(t.type, str(t), t.start_pos) for t in built[1].lex(commands)] == [
        (t.type, str(t), t.start_pos) for t in loaded[1].lex(commands)
    ]
