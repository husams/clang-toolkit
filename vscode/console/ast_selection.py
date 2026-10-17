"""Resolve editor byte spans to retained native AST selections."""
from __future__ import annotations

from pathlib import Path
import re
from typing import TYPE_CHECKING, Any

from clang_toolkit import Matcher

if TYPE_CHECKING:
    from ast_inspector import AstInspector


WRAPPERS = {'implicitCastExpr', 'exprWithCleanups', 'materializeTemporaryExpr',
            'cxxBindTemporaryExpr', 'constantExpr'}


class AstSelection:
    def __init__(self, inspector: AstInspector) -> None:
        self.inspector = inspector
        self.files: set[tuple[str, str]] = set()
        self.bytes: dict[str, bytes] = {}

    def file_page(self, root_file: str, file: str) -> dict[str, Any]:
        host = self.inspector.host
        root_id = self.inspector.file_node(root_file)
        page = self.inspector.inspect(dict(settings=host.settings, nodeId=root_id))
        key = (root_file, file)
        if key in self.files:
            return page
        if len(self.files) >= 16:
            raise ValueError('Source selection file limit reached; refresh analysis.')
        if file != root_file:
            # Header declarations remain real TU children, fetched only when needed.
            target, _, _ = host.check_input(root_id)
            query = Matcher('decl', Matcher('isExpansionInFileMatching', re.escape(file) + '$'))
            rows = host.client.peek(target, axis='children', query=query, max_nodes=1000)
            pending = {}
            children = []
            try:
                if len(page['children']) + len(rows) > 1000:
                    raise ValueError('AST child limit reached; refresh or narrow the file context.')
                for row in rows:
                    existing = len(host.nodes)
                    identifier = self.inspector.retain(row.binding('target'), root_file, 'AST child')
                    if len(host.nodes) > existing:
                        pending[identifier] = host.nodes[identifier]
                    children.append(self.inspector.describe(identifier))
                host.nodes.update(pending)
                page = {**page, 'children': [*page['children'], *children]}
            except BaseException:
                for identifier in pending:
                    host.nodes.pop(identifier, None)
                rows.close()
                raise
            self.inspector.collections.append(rows)
            self.inspector.cache[root_id] = page
        self.files.add(key)
        return page

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
                self.bytes[file] = self.inspector.host.buffers.read_bytes(file)
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
        if type(start) is not int or type(end) is not int or not 0 <= start <= end:
            raise ValueError('Select a source position or an ordered source range.')

        def covers(span: tuple[int, int]) -> bool:
            # A caret belongs to the token on its right, never one ending here.
            return (span[0] <= start < span[1] if start == end
                    else span[0] <= start and end <= span[1])

        file = str(Path(selection['file']).resolve())
        root = self.file_page(root_file, file)
        best: tuple[Any, dict[str, Any], list[dict[str, Any]]] | None = None
        pending = [(root['node']['id'], 0, [])]
        visited: set[str] = set()
        while pending:
            current_id, depth, parents = pending.pop()
            if current_id in visited:
                continue
            if depth > 64 or len(visited) >= 128:
                raise ValueError('Source selection traversal limit reached; narrow the selection or refresh analysis.')
            visited.add(current_id)
            page = self.inspector.inspect(dict(settings=host.settings, nodeId=current_id,
                                               resolveRelated=False))
            path = [*parents, {key: page[key] for key in ('node', 'children', 'semantics') if key in page}]
            if current_id == request.get('expectedId'):
                return {**page, 'path': path}
            native, _, _ = host.check_input(current_id)
            span = self.span(native.value, file)
            if span:
                kind = native.value.node.WhichOneof('payload')
                kind = native.value.node.DESCRIPTOR.fields_by_name[kind].json_name if kind else ''
                macro = native.value.range.expansion_begin.is_macro
                score = (span[1] - span[0], kind in WRAPPERS, depth if macro else -depth)
                if best is None or score < best[0]:
                    best = (score, page, path)
            for child in page['children']:
                native_child, _, _ = host.check_input(child['id'])
                child_span = self.span(native_child.value, file)
                if child_span:
                    if covers(child_span):
                        pending.append((child['id'], depth + 1, path))
                elif depth > 0 and not native_child.value.range.expansion_begin.valid:
                    # Type-location visitors can own source-bearing parameters.
                    pending.append((child['id'], depth + 1, path))
        return {**best[1], 'path': best[2]} if best and not request.get('expectedId') else None

    def related(self, identifier: str) -> dict[str, Any]:
        host = self.inspector.host
        target, _, _ = host.check_input(identifier)
        file = target.value.location.file
        if not file:
            raise ValueError('This base declaration has no source location.')
        file = str(Path(file).resolve())
        span = self.span(target.value, file)
        if span is None:
            raise ValueError('This base declaration has no usable source range.')
        page = self.locate(dict(settings=host.settings, nodeId=identifier,
                                expectedId=identifier,
                                selection=dict(file=file, start=span[0], end=span[1])))
        if page is None:
            raise ValueError('Could not reveal the exact base declaration in the file AST.')
        return page

    def clear(self) -> None:
        self.files.clear()
        self.bytes.clear()
