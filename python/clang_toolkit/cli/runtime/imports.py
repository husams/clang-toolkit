"""Load local console libraries into the active runtime."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from lark import Tree
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import batch_parser
from clang_toolkit.cli.syntax_diagnostics import syntax_diagnostic

if TYPE_CHECKING:
    from .evaluator import Runtime


def _snapshot_plain_containers(bindings: dict[str, object]) -> list[tuple[object, object]]:
    """Capture mutable built-in containers while retaining native object identities."""
    snapshots: list[tuple[object, object]] = []
    pending = list(bindings.values())
    visited: set[int] = set()
    while pending:
        value = pending.pop()
        if type(value) is list:
            if id(value) in visited:
                continue
            visited.add(id(value))
            contents = list(value)
            snapshots.append((value, contents))
            pending.extend(contents)
        elif type(value) is dict:
            if id(value) in visited:
                continue
            visited.add(id(value))
            contents = list(value.items())
            snapshots.append((value, contents))
            for key, item in contents:
                pending.extend((key, item))
    return snapshots


def _restore_plain_containers(snapshots: list[tuple[object, object]]) -> None:
    for container, contents in snapshots:
        if type(container) is list:
            container[:] = contents
        else:
            container.clear()
            container.update(contents)


@contextmanager
def script_source(runtime: Runtime, path: str | Path | None) -> Iterator[None]:
    """Track the source file currently executing, including a --script file."""
    stack = getattr(runtime, "_import_stack", None)
    if stack is None:
        stack = []
        runtime._import_stack = stack
    resolved = Path(path).resolve() if path is not None else None
    if resolved is not None:
        stack.append(resolved)
    try:
        yield
    finally:
        if resolved is not None:
            stack.pop()


def execute_import(runtime: Runtime, statement: Tree) -> str:
    """Parse and load a definitions-only library into the same Runtime."""
    raw_path = next(
        (
            str(child)
            for child in statement.children
            if getattr(child, "type", None) in {"STRING", "FILE_STRING"}
        ),
        None,
    )
    if raw_path is None:
        from .evaluator import EvaluationError
        raise EvaluationError("import requires a quoted library path")
    requested = runtime._string(raw_path)
    stack: list[Path] | None = getattr(runtime, "_import_stack", None)
    if stack is None:
        stack = []
        runtime._import_stack = stack
    base = stack[-1].parent if stack else runtime.cwd
    path = (base / requested).resolve()
    if path in stack:
        chain = " -> ".join(str(item) for item in (*stack, path))
        from .evaluator import EvaluationError
        raise EvaluationError(f"import cycle: {chain}")
    if len(stack) >= 64:
        from .evaluator import EvaluationError
        raise EvaluationError("library import depth exceeds 64")

    from .evaluator import EvaluationError
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise EvaluationError(f"cannot read library {path}: {exc}") from exc

    if not source.strip() or all(
        not line.strip() or line.lstrip().startswith("#") for line in source.splitlines()
    ):
        return ""

    try:
        batch = batch_parser().parse(source)
    except UnexpectedInput as exc:
        raise EvaluationError(
            f"{path}: {syntax_diagnostic(source, exc)}"
        ) from exc

    statements: list[tuple[Tree, str]] = []
    for item in batch.children:
        if not isinstance(item, Tree) or str(item.data) == "batch_separator":
            continue
        if str(item.data) not in {"assignment", "matcher_definition", "import_command"}:
            line = getattr(item.meta, "line", 1)
            raise EvaluationError(
                f"{path}:{line}: libraries accept let definitions and import statements"
            )
        start, end = item.meta.start_pos, item.meta.end_pos
        statements.append((item, source[start:end].strip()))

    # Restore top-level bindings if definition loading fails. Any server work
    # performed by an assignment expression is external and cannot be rolled back.
    previous_bindings = dict(runtime.bindings)
    previous_containers = _snapshot_plain_containers(runtime.bindings)
    stack.append(path)
    original_scopes = runtime._scopes
    # Imports inside a resource batch define values in that fresh lexical
    # scope. A library must never promote a live batch handle or closure into
    # the persistent runtime bindings.
    if runtime._active_resource_scope is None:
        runtime._scopes = []
    try:
        for item, command in statements:
            try:
                runtime._execute_statement(item, command)
            except Exception as exc:
                line = getattr(item.meta, "line", 1)
                raise EvaluationError(f"{path}:{line}: {exc}") from exc
    except Exception:
        _restore_plain_containers(previous_containers)
        runtime.bindings.clear()
        runtime.bindings.update(previous_bindings)
        raise
    finally:
        runtime._scopes = original_scopes
        stack.pop()
    return ""
