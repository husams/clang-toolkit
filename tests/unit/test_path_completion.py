"""Real filesystem candidates, insertion syntax and semantic argument selection."""

from __future__ import annotations

from pathlib import Path

import pytest
from prompt_toolkit.document import Document

from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.language import parser
from clang_toolkit.cli.runtime.templates import evaluate_string


@pytest.fixture
def files(tmp_path):
    (tmp_path / "source file.cc").write_text("int main() {}")
    (tmp_path / "source.cc").write_text("int main() {}")
    (tmp_path / "source dir").mkdir()
    (tmp_path / "source dir" / "nested file.cc").write_text("int value;")
    return tmp_path


def choices(text, cwd, cursor=None):
    return list(
        ReplCompleter(cwd=cwd).get_completions(
            Document(text, cursor_position=cursor), None
        )
    )


def apply(text, item, cursor=None):
    cursor = len(text) if cursor is None else cursor
    return text[: cursor + item.start_position] + item.text + text[cursor:]


def select(text, cwd, display, cursor=None):
    item = next(c for c in choices(text, cwd, cursor) if c.display_text == display)
    return apply(text, item, cursor)


@pytest.mark.parametrize(
    "prefix",
    [
        "parse ",
        "parse",
        "parse sou",
        'parse "sou',
        "parse 'sou",
        "let tree = parse sou",
    ],
)
def test_paths_complete_to_real_parseable_file_arguments(files, prefix):
    completed = select(prefix, files, "source file.cc")
    statement = parser().parse(completed).children[0]
    assert statement
    assert "source file.cc" in completed
    assert completed.endswith(("'", '"'))


@pytest.mark.parametrize(
    "prefix",
    [
        "cursor open ",
        "traverse ",
        "callgraph ",
        "cfg main in ",
        "script 'emit 7;' in ",
        "load ",
        "save $values to ",
        "history save ",
        "session add ",
        "set output to ",
        "set user output to ",
        "match varDecl() in ",
        "match varDecl() in [",
        "background varDecl() in [",
        "set files to [",
        "set user files to [",
        "let files = glob(",
        'in parse "source.cc" { let rows = match varDecl() in ',
    ],
)
def test_file_roles_offer_files_and_navigation_directories(files, prefix):
    displays = {c.display_text for c in choices(prefix, files)}
    if prefix == "cfg main in " and not any(
        rule.origin.name == "cfg_option" for rule in parser().rules
    ):
        assert not {"source file.cc", "source.cc", "source dir/"} & displays
        return
    assert {"source file.cc", "source.cc", "source dir/"} <= displays


def test_directory_role_excludes_regular_files(files):
    assert [c.display_text for c in choices("set cache_dir to ", files)] == [
        "source dir/"
    ]
    assert [c.display_text for c in choices("set user cache_dir to ", files)] == [
        "source dir/"
    ]
    completed = select("set cache_dir to ", files, "source dir/")
    assert parser().parse(completed)


@pytest.mark.parametrize(
    "prefix",
    [
        'match varDecl(hasName("sou',
        'match varDecl().bind("sou',
        'print "sou',
        'let text = "sou',
        'let list = ["sou',
        'add extra_arg "sou',
        'session label "sou',
        'session start "sou',
        'cursor close "sou',
        'cursor restart "sou',
        'cursor continue "id" "sou',
        'script "sou',
        "cfg sou",
        "help sou",
        "unknown sou",
        'match varDecl(hasName("a?b"))',
    ],
)
def test_non_path_roles_never_offer_files(files, prefix):
    assert not {"source file.cc", "source.cc", "source dir/"}.intersection(
        c.display_text for c in choices(prefix, files)
    )


def test_absolute_and_home_expansion_produce_usable_paths(files, monkeypatch):
    absolute = select(f"parse {files}/sou", files, "source file.cc")
    assert str(files / "source file.cc") in absolute
    monkeypatch.setenv("HOME", str(files))
    home = select("parse ~/sou", files, "source file.cc")
    assert str(files / "source file.cc") in home
    assert "~" not in home
    assert parser().parse(home)
    assert choices('let files = glob("~/', files) == []  # glob is relative only


def test_quoted_directory_navigation_and_typing_after_closed_quote(files):
    directory = select('parse "sou', files, "source dir/")
    assert directory == 'parse "source dir/"'
    completed = select(directory, files, "nested file.cc")
    assert completed == 'parse "source dir/nested file.cc"'
    assert parser().parse(completed)
    typed = select(directory + "nes", files, "nested file.cc")
    assert typed == completed


def test_completion_inside_existing_quote_preserves_the_suffix(files):
    source = 'match varDecl() in ["sou", "later.cc"]'
    cursor = source.index("sou") + 3
    completed = select(source, files, "source file.cc", cursor)
    assert completed == 'match varDecl() in ["source file.cc", "later.cc"]'
    assert parser().parse(completed)


def test_no_corruption_when_cursor_is_in_middle_of_path(files):
    source = 'parse "source.cc"'
    assert choices(source, files, source.index("source") + 3) == []


@pytest.mark.parametrize(
    "name", ["dollar$name.cc", "single'quote.cc", 'double"quote.cc', "back\\slash.cc"]
)
@pytest.mark.parametrize("quote", ["'", '"', ""])
def test_filenames_with_syntax_characters_are_literal(files, name, quote):
    (files / name).write_text("int value;")
    completed = select("parse " + quote, files, name)
    token = parser().parse(completed).children[0].children[0].children[1]
    assert (
        evaluate_string(str(token), lambda _: pytest.fail("filename interpolated"))
        == name
    )


def test_missing_and_inaccessible_directories_fail_gracefully(files, monkeypatch):
    assert choices("parse missing/", files) == []
    assert choices('parse "bad\x00/', files) == []

    def denied(_self):
        raise PermissionError("test directory is inaccessible")

    monkeypatch.setattr(Path, "iterdir", denied)
    assert choices("parse ", files) == []


def test_relative_parent_and_dotted_paths(files):
    completed = select('parse "./sou', files, "source.cc")
    assert completed == 'parse "./source.cc"'
    completed = select('parse "../' + files.name + "/sou", files, "source.cc")
    assert "../" + files.name + "/source.cc" in completed


def test_live_references_and_matcher_candidates_still_work(files):
    refs = {"tree": ("path",), "rows": ("f", "length")}
    completer = ReplCompleter(cwd=files, references=refs)

    def complete(text):
        return [c.text for c in completer.get_completions(Document(text), None)]

    assert complete("parse $tr") == ["tree"]
    assert complete("match callExpr() in $rows.") == ["f", "length"]
    assert "functionDecl(" in complete("match ")
    assert "hasName(" in complete("match functionDecl(")
