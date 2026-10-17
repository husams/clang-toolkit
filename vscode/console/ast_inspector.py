"""Navigate live AST selections; never recreate nodes from serialized display data."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from google.protobuf.json_format import MessageToDict
from clang_toolkit import Matcher

from run_service import Results
from ast_selection import AstSelection
from ast_semantics import inheritance, parameters

if TYPE_CHECKING:
    from action_service import ActionHost


class AstInspector:
    def __init__(self, host: ActionHost) -> None:
        self.host = host
        self.collections: list[Any] = []
        self.cache: dict[str, dict[str, Any]] = {}
        self.locations: dict[tuple[Any, ...], str] = {}
        self.file_nodes: dict[str, str] = {}
        self.declarations: dict[tuple[Any, ...], str] = {}
        self.related: set[str] = set()
        self.references: dict[str, str] = {}
        self.selection = AstSelection(self)

    def retain(self, target: Any, file: str, label: str) -> str:
        value = target.value
        kind = value.node.WhichOneof('payload')
        key = None
        if kind in ('cxx_record_decl', 'class_template_specialization_decl',
                    'class_template_partial_specialization_decl'):
            key = (file, value.symbol_identity, value.node.SerializeToString(deterministic=True),
                   value.range.SerializeToString(deterministic=True))
            previous = self.declarations.get(key)
            if previous in self.host.nodes:
                return previous
        elif value.WhichOneof('value') == 'base_specifier':
            key = (file, 'base', value.base_specifier.SerializeToString(deterministic=True),
                   value.range.SerializeToString(deterministic=True))
            previous = self.declarations.get(key)
            if previous in self.host.nodes:
                return previous
        if len(self.host.nodes) >= 10000:
            raise ValueError('AST retention limit reached; refresh analysis.')
        identifier = str(uuid4())
        self.host.nodes[identifier] = (target, file, label)
        if key is not None:
            self.declarations[key] = identifier
        return identifier

    def describe(self, identifier: str) -> dict[str, Any]:
        target, file, _ = self.host.check_input(identifier)
        value = target.value
        raw = MessageToDict(value)
        display = Results(1)
        display.sources = self.host.sources
        display.add(value)
        kind = next(iter(raw.get('node', {})), 'Node')
        item = display.items[0] if display.items else dict(
            name=kind, kind=kind, file='', line=1, column=1, excerpt='', raw=raw)
        if identifier == self.file_nodes.get(file):
            item.update(name=Path(file).name, file=file)
        elif value.WhichOneof('value') == 'base_specifier':
            description = value.base_specifier.type.description
            item['name'] = description.spelling or description.canonical_spelling or '(dependent base)'
        elif identifier in self.references:
            item['name'] = self.describe(self.references[identifier])['name']
        return {**item, 'id': identifier, 'locationValid': bool(value.location.valid),
                'raw': {'binding': raw}}

    def file_node(self, file: str) -> str:
        root_id = self.host.root(file)
        tree, file, _ = self.host.check_input(root_id)
        if file in self.file_nodes:
            return self.file_nodes[file]
        rows = self.host.client.match_in('translationUnitDecl().bind("file")', tree)
        try:
            if len(rows) != 1:
                raise ValueError('Could not locate the parsed file AST root.')
            identifier = str(uuid4())
            self.host.nodes[identifier] = (rows[0].binding('file'), file, 'File AST')
        except BaseException:
            rows.close()
            raise
        self.collections.append(rows)
        self.file_nodes[file] = identifier
        return identifier

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
        identifier = request.get('nodeId') or (self.resolve_reference(request) if request.get('reference') else (
            self.locate(request) if request.get('result')
            else self.file_node(request['translationUnit'])))
        target, file, _ = self.host.check_input(identifier)
        if identifier in self.related and request.get('resolveRelated', True):
            return self.selection.related(identifier)
        if identifier in self.cache:
            return self.cache[identifier]
        if len(self.cache) >= 128 or len(self.host.nodes) >= 10000:
            raise ValueError('AST inspection limit reached; refresh analysis to release inspected nodes.')
        query = 'decl(isExpansionInMainFile())' if identifier == self.file_nodes.get(file) else None
        rows = self.host.client.peek(target, axis='children', query=query, max_nodes=1000)
        pending: dict[str, tuple[Any, str, str]] = {}
        children = []
        try:
            for row in rows:
                child = row.binding('target')
                existing = len(self.host.nodes)
                child_id = self.retain(child, file, 'AST child')
                if len(self.host.nodes) > existing:
                    pending[child_id] = self.host.nodes[child_id]
                if identifier in self.references and child.value.WhichOneof('value') == 'unsupported':
                    if child.value.unsupported.clang_class.endswith('TypeLoc'):
                        self.references[child_id] = self.references[identifier]
                children.append(self.describe(child_id))
            self.host.nodes.update(pending)
            response = dict(node=self.describe(identifier), children=children,
                            parseCount=self.host.parse_count,
                            root=dict(id=self.host.roots[file][0], file=file, label='File root'))
            if response['node']['kind'] in ('Class', 'Struct') or any(
                    key in response['node']['raw']['binding'].get('node', {})
                    for key in ('cxxRecordDecl', 'classTemplateSpecializationDecl',
                                'classTemplatePartialSpecializationDecl')):
                response['semantics'] = inheritance(self, target, file)
            elif any(key in response['node']['raw']['binding'].get('node', {})
                     for key in ('functionDecl', 'cxxMethodDecl', 'cxxConstructorDecl',
                                 'cxxDestructorDecl', 'cxxConversionDecl', 'cxxDeductionGuideDecl')):
                response['semantics'] = dict(parameters=parameters(self.host, target))
            if identifier in self.references:
                declaration = self.references[identifier]
                response.setdefault('semantics', {})['referencedDeclaration'] = dict(
                    nodeId=declaration, name=self.describe(declaration)['name'],
                    symbol=self.host.check_input(declaration)[0].value.symbol_identity)
        except BaseException:
            for child_id in pending:
                self.host.nodes.pop(child_id, None)
            rows.close()
            raise
        self.collections.append(rows)
        self.cache[identifier] = response
        return response

    def resolve_reference(self, request: dict[str, Any]) -> str:
        """Resolve an old base link to an exact declaration in a fresh buffer AST."""
        reference = request['reference']
        root_id = self.host.root(request['translationUnit'])
        tree, file, _ = self.host.check_input(root_id)
        query = Matcher('cxxRecordDecl', Matcher('hasName', reference['name']),
                        Matcher('isDefinition')).bind('base')
        rows = self.host.client.match_in(query, tree)
        try:
            matches = [row.binding('base') for row in rows
                       if row.bindings['base'].symbol_identity == reference['symbol']]
            if len(matches) != 1:
                raise ValueError('This base class changed or was removed; select a base from the updated Properties.')
            identifier = self.retain(matches[0], file, 'Base class')
        except BaseException:
            rows.close()
            raise
        self.collections.append(rows)
        self.related.add(identifier)
        return identifier

    def close(self) -> None:
        self.selection.clear()
        self.cache.clear()
        self.locations.clear()
        self.file_nodes.clear()
        self.declarations.clear()
        self.related.clear()
        self.references.clear()
        for rows in self.collections:
            rows.close()
        self.collections.clear()
