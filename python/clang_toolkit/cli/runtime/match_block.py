"""Execute ordinary console statements for each provisional streamed row."""

from __future__ import annotations

from threading import RLock
from typing import Any, TYPE_CHECKING

from lark import Tree

from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.client import _absolute_source_file
from clang_toolkit.match_values import MatchRow, MatchValueError

if TYPE_CHECKING:
    from .evaluator import Runtime


class _StreamingOwner(CursorOwner[Any]):
    """Copied semantic bindings have no published native cursor yet."""

    def check(self, client: Any) -> None:
        raise MatchValueError(
            "streamed bindings are semantic snapshots; native continuation "
            "requires a completed match result"
        )


class _BlockExit(BaseException):
    """Propagate a block's quit/exit through stream cancellation."""


def execute_match_block(runtime: Runtime, node: Tree, source: str) -> str | None:
    from .evaluator import EvaluationError

    block = runtime._match_block(node)
    assert block is not None
    statements = [item for item in block.children if isinstance(item, Tree)]
    owner = _StreamingOwner(getattr(runtime.client, "client", runtime.client), "", 0, lambda _: None)
    owner.closed = True
    lock = RLock()
    outputs: list[str] = []
    row_count = 0
    output_size = 0

    def on_row(message: Any, target: Any) -> None:
        nonlocal row_count, output_size
        # Files stream concurrently; each body has exclusive use of lexical
        # scopes and settings, including while it runs nested requests.
        with lock:
            index = row_count
            row_count += 1
            if row_count > 10_000:
                raise EvaluationError("match do exceeds 10000 rows")
            row = MatchRow(message.SerializeToString(), owner, index,
                           _absolute_source_file(target, runtime.cwd))
            scope = {name: row.binding(name) for name in row.bindings}
            owners: set[Any] = set()
            runtime._scopes.append(scope)
            runtime._block_owners.append(owners)
            try:
                for statement in statements:
                    output = runtime._execute_statement(statement, source)
                    if output is None:
                        raise _BlockExit
                    if output:
                        output_size += len(output.encode("utf-8"))
                        if output_size > 1_000_000:
                            raise EvaluationError("match do output exceeds 1000000 bytes")
                        outputs.append(output)
            except Exception as error:
                line = statement.meta.line
                column = statement.meta.column
                raise EvaluationError(
                    f"match row {index}: {error} (line {line}, column {column})"
                ) from error
            finally:
                runtime._block_owners.pop()
                runtime._scopes.pop()
                scope.clear()
                for acquired in owners:
                    acquired.close()

    try:
        result = runtime._execute_match(node, source=source, on_row=on_row)
    except _BlockExit:
        return None
    for acquired in runtime._native_owners(result):
        acquired.close()
    return "\n".join(outputs)
