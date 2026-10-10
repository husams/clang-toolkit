from __future__ import annotations

import pytest
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import parser


@pytest.mark.parametrize(
    ("source", "kind"),
    [
        ('files "src/"', "display"),
        ('let inputs = files "src/**/*.cpp"', "assignment"),
        ('let inputs = files ["a.cc", "b.cc"]', "assignment"),
        ('file open "src/a.cc" into $source', "file_open"),
        ("file list", "file_list"),
        ("file list discovered in $inputs", "file_list"),
        ("file info $source", "file_info"),
        ("file close $source", "file_close"),
        ("file close all", "file_close"),
        ("file refresh $source into $updated", "file_refresh"),
        ("resource status", "resource_status"),
        (
            "batch part in $inputs size 4 jobs 1 on error continue do { "
            "print $part.index; }",
            "batch_statement",
        ),
        (
            'batch part in $inputs count 3 memory "512MiB" on error stop do { '
            "let paths = $part.paths; }",
            "batch_statement",
        ),
    ],
)
def test_file_and_batch_language_parses(source: str, kind: str) -> None:
    tree = parser().parse(source).children[0]
    assert tree.data == kind


@pytest.mark.parametrize(
    "source",
    [
        "batch part in $inputs size 2 count 3 do { print $part.index; }",
        "batch part in $inputs jobs 2 size 3 do { print $part.index; }",
    ],
)
def test_invalid_batch_shapes_fail_before_evaluation(source: str) -> None:
    with pytest.raises(UnexpectedInput):
        parser().parse(source)
