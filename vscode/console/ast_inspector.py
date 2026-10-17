"""Navigate live AST selections; never recreate nodes from serialized display data."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from google.protobuf.json_format import MessageToDict

from run_service import Results
from ast_selection import AstSelection

if TYPE_CHECKING:
    from action_service import ActionHost


class AstInspector:
    def __init__(self, host: ActionHost) -> None:
        self.host = host
        self.collections: list[Any] = []
        self.cache: dict[str, dict[str, Any]] = {}
        self.locations: dict[tuple[Any, ...], str] = {}
        self.selection = AstSelection(self)

    def describe(self, identifier: str) -> dict[str, Any]:
        target, _, _ = self.host.check_input(identifier)
        value = target.value
        raw = MessageToDict(value)
        display = Results(1)
        display.sources = self.host.sources
        display.add(value)
        kind = next(iter(raw.get('node', {})), 'Node')
        item = display.items[0] if display.items else dict(
            name=kind, kind=kind, file='', line=1, column=1, excerpt='', raw=raw)
        return {**item, 'id': identifier, 'locationValid': bool(value.location.valid),
                'raw': {'binding': raw}}

    def locate(self, request: dict[str, Any]) -> str:
        result = request['result']
        key = (request['translationUnit'], result['file'], result['line'],
               result['column'], result['kind'])
        if key in self.locations:
            identifier = self.locations[key]
            self.host.check_input(identifier)
            return identifier
        root_id = self.host.root(request['translationUnit'])
        tree, file, _ = self.host.check_input(root_id)
        category = 'decl' if result['kind'].endswith('Decl') else 'stmt'
        predicate = 'unless(isImplicit())' if category == 'decl' and not result.get('implicit') else ''
        rows = self.host.client.match_in(f'{category}({predicate}).bind("candidate")', tree)
        selected = []
        for row in rows:
            value = row.bindings['candidate']
            field_name = value.node.WhichOneof('payload')
            kind = value.node.DESCRIPTOR.fields_by_name[field_name].json_name if field_name else ''
            location = value.location
            # Exact native category and coordinates identify the original result.
            if (location.valid and location.file and
                    str(Path(location.file).resolve()) == str(Path(result['file']).resolve()) and
                    location.line == result['line'] and location.column == result['column'] and
                    kind == result['nativeKind']):
                selected.append(row.binding('candidate'))
        if len(selected) != 1:
            rows.close()
            raise ValueError('Could not identify one live AST node for this result; rerun the analysis or select a binding in Actions.')
        identifier = str(uuid4())
        self.host.nodes[identifier] = (selected[0], file, result['name'])
        self.collections.append(rows)
        self.locations[key] = identifier
        return identifier

    def inspect(self, request: dict[str, Any]) -> dict[str, Any]:
        if request.get('settings') != self.host.settings:
            raise ValueError('Analysis settings changed; refresh analysis before inspecting AST nodes.')
        identifier = request.get('nodeId') or self.locate(request)
        target, file, _ = self.host.check_input(identifier)
        if identifier in self.cache:
            return self.cache[identifier]
        if len(self.cache) >= 128 or len(self.host.nodes) >= 10000:
            raise ValueError('AST inspection limit reached; refresh analysis to release inspected nodes.')
        rows = self.host.client.peek(target, axis='children', max_nodes=1000)
        pending: dict[str, tuple[Any, str, str]] = {}
        children = []
        try:
            for row in rows:
                child = row.binding('target')
                child_id = str(uuid4())
                pending[child_id] = (child, file, 'AST child')
            if len(self.host.nodes) + len(pending) > 10000:
                raise ValueError('AST inspection limit reached; refresh analysis to release inspected nodes.')
            self.host.nodes.update(pending)
            for child_id in pending:
                children.append(self.describe(child_id))
            response = dict(node=self.describe(identifier), children=children,
                            parseCount=self.host.parse_count,
                            root=dict(id=self.host.roots[file][0], file=file, label='File root'))
        except BaseException:
            for child_id in pending:
                self.host.nodes.pop(child_id, None)
            rows.close()
            raise
        self.collections.append(rows)
        self.cache[identifier] = response
        return response

    def close(self) -> None:
        self.selection.clear()
        self.cache.clear()
        self.locations.clear()
        for rows in self.collections:
            rows.close()
        self.collections.clear()
