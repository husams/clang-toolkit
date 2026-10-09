"""Noninteractive execution of Lark-parsed console command batches."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from lark import Tree
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import batch_parser
from clang_toolkit.cli.syntax_diagnostics import syntax_diagnostic


@dataclass(frozen=True)
class BatchResult:
    exit_code: int
    outputs: tuple[str, ...]


@dataclass(frozen=True)
class BatchRequirements:
    query_session: bool = False
    background_query: bool = False


def batch_requirements(source: str) -> BatchRequirements:
    """Identify commands needing async services from the formal batch tree."""
    if not source.strip():
        return BatchRequirements()
    try:
        batch = batch_parser().parse(source)
    except UnexpectedInput:
        # execute_batch owns diagnostics. A malformed script must not trigger
        # any network setup before it can report its atomic parse failure.
        return BatchRequirements()

    commands = {"session_start", "session_add", "session_match", "session_pause", "session_resume", "session_close"}
    query_session = any(
        subtree.data in commands
        for statement in batch.children if isinstance(statement, Tree)
        for subtree in statement.iter_subtrees()
    )
    background_query = any(
        subtree.data == "background"
        for statement in batch.children if isinstance(statement, Tree)
        for subtree in statement.iter_subtrees()
    )
    return BatchRequirements(query_session=query_session, background_query=background_query)


def execute_batch(
    source: str,
    execute: Callable[[str], object],
    *,
    continue_on_error: bool = False,
) -> BatchResult:
    """Parse a complete batch, then execute each command with explicit status.

    ``execute`` returns a DispatchResult-like object with ``output`` and
    ``success`` attributes. Keeping those fields separate preserves literal
    command results such as a string beginning with ``error:``.
    """
    if not source.strip():
        return BatchResult(0, ())
    try:
        batch = batch_parser().parse(source)
    except UnexpectedInput as error:
        return BatchResult(1, (syntax_diagnostic(source, error),))

    outputs: list[str] = []
    failed = False
    for item in batch.children:
        if not isinstance(item, Tree) or str(item.data) == "batch_separator":
            continue
        start = item.meta.start_pos
        end = item.meta.end_pos
        command = source[start:end].strip()
        if not command:
            continue
        outcome = execute(command)
        output = getattr(outcome, "output", None)
        success = bool(getattr(outcome, "success", False))
        if output:
            if success:
                outputs.append(str(output))
            else:
                line = source.count("\n", 0, start) + 1
                outputs.append(f"error at line {line}: {output}")
        if not success:
            failed = True
            if not continue_on_error:
                break
        if output is None and success:
            break

    return BatchResult(1 if failed else 0, tuple(outputs))
