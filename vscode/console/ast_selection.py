"""Resolve editor byte spans to retained native AST selections."""
from __future__ import annotations

from pathlib import Path
import re
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from clang_toolkit import Matcher

if TYPE_CHECKING:
    from ast_inspector import AstInspector


WRAPPERS = {'implicitCastExpr', 'exprWithCleanups', 'materializeTemporaryExpr',
            'cxxBindTemporaryExpr', 'constantExpr'}


class AstSelection:
    def __init__(self, inspector: AstInspector) -> None:
        self.inspector = inspector
        self.declarations: dict[tuple[str, str], list[tuple[int, int, Any]]] = {}
        self.handles: dict[tuple[str, str, int], str] = {}
        self.bytes: dict[str, bytes] = {}

    def span(self, value: Any, file: str) -> tuple[int, int] | None:
        begin, end = value.range.expansion_begin, value.range.expansion_end_exclusive
        if not (begin.valid and end.valid and begin.file and end.file):
            return None
        if str(Path(begin.file).resolve()) != file or str(Path(end.file).resolve()) != file:
            return None

        def offset(point: Any) -> int | None:
            if point.HasField('offset'):
                return point.offset
            if point.line < 1 or point.column < 1:
                return None
            if file not in self.bytes:
                self.bytes[file] = Path(file).read_bytes()
            lines = self.bytes[file].splitlines(keepends=True)
            if point.line > len(lines) or point.column - 1 > len(lines[point.line - 1].rstrip(b'\r\n')):
                return None
            return sum(map(len, lines[:point.line - 1])) + point.column - 1

        start, stop = offset(begin), offset(end)
        return (start, stop) if start is not None and stop is not None and start <= stop else None

    def locate(self, request: dict[str, Any]) -> dict[str, Any] | None:
        host = self.inspector.host
        if request['settings'] != host.settings:
            raise ValueError('Analysis settings changed; refresh analysis before selecting code.')
        _, root_file, _ = host.check_input(request['nodeId'])
        selection = request['selection']
        start, end = selection['start'], selection['end']
        if type(start) is not int or type(end) is not int or not 0 <= start < end:
            raise ValueError('Select a nonempty source range.')
        file = str(Path(selection['file']).resolve())
        key = (root_file, file)
        if key not in self.declarations:
            if len(self.declarations) >= 16:
                raise ValueError('Source selection file limit reached; refresh analysis.')
            tree, _, _ = host.check_input(host.root(root_file))
            query = Matcher('decl', Matcher('isExpansionInFileMatching', re.escape(file) + '$'),
                            Matcher('unless', Matcher('isImplicit'))).bind('candidate')
            rows = host.client.match_in(query, tree)
            try:
                if len(rows) > 5000:
                    raise ValueError('Source selection declaration limit reached (5000); narrow the file or refresh analysis.')
                candidates = []
                for row in rows:
                    span = self.span(row.bindings['candidate'], file)
                    if span:
                        candidates.append((*span, row.binding('candidate')))
            except BaseException:
                rows.close()
                raise
            self.inspector.collections.append(rows)
            self.declarations[key] = candidates
        covering = [(stop - begin, index, target) for index, (begin, stop, target) in
                    enumerate(self.declarations[key]) if begin <= start and end <= stop]
        if not covering:
            return None
        _, index, target = min(covering, key=lambda item: (item[0], item[1]))
        handle_key = (*key, index)
        if handle_key not in self.handles:
            if len(host.nodes) >= 10000:
                raise ValueError('AST selection handle limit reached; refresh analysis.')
            identifier = str(uuid4())
            host.nodes[identifier] = (target, root_file, 'Source selection')
            self.handles[handle_key] = identifier
        identifier = self.handles[handle_key]
        best: tuple[Any, dict[str, Any]] | None = None
        pending = [(identifier, 0)]
        visited: set[str] = set()
        while pending:
            current_id, depth = pending.pop()
            if current_id in visited:
                continue
            if depth > 64 or len(visited) >= 128:
                raise ValueError('Source selection traversal limit reached; narrow the selection or refresh analysis.')
            visited.add(current_id)
            page = self.inspector.inspect(dict(settings=host.settings, nodeId=current_id))
            native, _, _ = host.check_input(current_id)
            span = self.span(native.value, file)
            if span:
                kind = native.value.node.WhichOneof('payload')
                kind = native.value.node.DESCRIPTOR.fields_by_name[kind].json_name if kind else ''
                macro = native.value.range.expansion_begin.is_macro
                score = (span[1] - span[0], kind in WRAPPERS, depth if macro else -depth)
                if best is None or score < best[0]:
                    best = (score, page)
            for child in page['children']:
                native_child, _, _ = host.check_input(child['id'])
                child_span = self.span(native_child.value, file)
                if child_span:
                    if child_span[0] <= start and end <= child_span[1]:
                        pending.append((child['id'], depth + 1))
                elif not native_child.value.range.expansion_begin.valid:
                    # Type-location visitors can own source-bearing parameters.
                    pending.append((child['id'], depth + 1))
        return best[1] if best else None

    def clear(self) -> None:
        self.declarations.clear()
        self.handles.clear()
        self.bytes.clear()
