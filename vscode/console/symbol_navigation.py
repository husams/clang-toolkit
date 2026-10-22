"""Resolve native Clang reference bindings and global index USRs for the editor."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import re
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
_workspace = Path(__file__).resolve().parents[2] / 'python'
if (_workspace / 'clang_toolkit').is_dir():
    sys.path.insert(0, str(_workspace))

from clang_toolkit.client import Client
from editor_buffers import EditorBuffers

# Bind the referenced declaration in Clang, preserving overloads and scopes.
QUERIES = (
    'declRefExpr(isExpansionInMainFile(), to(namedDecl().bind("declaration"))).bind("reference")',
    'memberExpr(isExpansionInMainFile(), member(namedDecl().bind("declaration"))).bind("reference")',
    'typeLoc(isExpansionInMainFile(), loc(qualType(hasDeclaration(namedDecl().bind("declaration"))))).bind("reference")',
    'nestedNameSpecifierLoc(loc(nestedNameSpecifier(specifiesNamespace(namespaceDecl().bind("declaration"))))).bind("reference")',
    'namedDecl(isExpansionInMainFile(), unless(isImplicit()), namedDecl().bind("declaration")).bind("reference")',
)
DEFINITIONS = ('namedDecl(isExpansionInMainFile(), anyOf(functionDecl(isDefinition()), '
               'varDecl(isDefinition()), tagDecl(isDefinition()))).bind("declaration")')


class NavigationBuffers(EditorBuffers):
    """Read each immutable source once, rather than once per reference."""
    def __init__(self, contents: dict[str, str]) -> None:
        super().__init__(contents)
        self._bytes: dict[str, bytes] = {}

    def read_bytes(self, file: str) -> bytes:
        if file not in self._bytes:
            self._bytes[file] = super().read_bytes(file)
        return self._bytes[file]


def declaration_name(node: Any) -> str:
    """Read the declaration's own NamedDeclInfo, without descending into children."""
    if node.DESCRIPTOR.name == 'NamedDeclInfo':
        return node.qualified_name or node.name.identifier
    for descriptor, value in node.ListFields():
        if descriptor.message_type and not descriptor.is_repeated:
            name = declaration_name(value)
            if name:
                return name
    return ''


def native_definition(node: Any) -> bool:
    for descriptor, value in node.ListFields():
        if descriptor.name in ('is_this_declaration_a_definition', 'is_complete_definition'):
            if value is True:
                return True
        if descriptor.message_type and not descriptor.is_repeated and native_definition(value):
            return True
    return False


def token_span(binding: Any, name: str, sources: EditorBuffers, file: str,
               *, declaration: bool = False) -> tuple[int, int] | None:
    span = binding.range
    begin, end = span.expansion_begin, span.expansion_end_exclusive
    if (not begin.valid or not end.valid or begin.file != end.file or
            str(Path(begin.file).resolve()) != file or not begin.HasField('offset') or
            not end.HasField('offset')):
        return None
    data = sources.read_bytes(file)
    left, right = int(begin.offset), int(end.offset)
    if left < 0 or right > len(data) or left >= right:
        return None
    # Match only the spelled token inside Clang's proven reference span. This
    # excludes macro expansions whose invocation does not spell the symbol.
    simple = name.rsplit('::', 1)[-1].split('<', 1)[0]
    if not simple:
        return None
    text = data[left:right].decode('utf-8')
    searchable = text
    if not declaration and text.rstrip().endswith('>'):
        # An explicitly written template argument can repeat the callee name
        # (choose<choose>). Its TypeLoc is matched separately by Clang.
        depth = 0
        for index in range(len(text.rstrip()) - 1, -1, -1):
            if text[index] == '>':
                depth += 1
            elif text[index] == '<':
                depth -= 1
                if depth == 0:
                    searchable = text[:index]
                    break
    matches = list(re.finditer(r'(?<!\w)' + re.escape(simple) + r'(?!\w)', searchable))
    if not matches:
        return None
    match = matches[0] if declaration else matches[-1]
    start = left + len(text[:match.start()].encode('utf-8'))
    return start, start + len(match[0].encode('utf-8'))


def target_location(binding: Any, name: str, sources: EditorBuffers) -> dict[str, Any] | None:
    point = binding.location
    if not point.valid or not point.file or point.line < 1:
        return None
    file = str(Path(point.file).resolve())
    try:
        span = token_span(binding, name, sources, file, declaration=True)
        if span:
            prefix = sources.read_bytes(file)[:span[0]]
            return dict(file=file, line=prefix.count(b'\n') + 1,
                        column=len(prefix.rsplit(b'\n', 1)[-1]) + 1)
    except OSError:
        pass
    return dict(file=file, line=int(point.line), column=max(1, int(point.column)))


def scan(client: Any, request: dict[str, Any], buffers: EditorBuffers) -> dict[str, Any]:
    file = str(Path(request['file']).resolve())
    references: dict[tuple[int, int], dict[str, Any]] = {}
    locations: dict[tuple[str, str, int, int], dict[str, Any] | None] = {}
    with client.parse(file, working_directory=request['directory'],
                      compile_arguments=[*request['compileArguments'], *buffers.arguments]) as tree:
        for query in QUERIES:
            with client.match_in(query, tree) as rows:
                for row in rows:
                    reference = row.bindings['reference']
                    declaration = row.bindings['declaration']
                    name = declaration_name(declaration.node)
                    # Headers often contain declarations without any usages.
                    # Their own name token must link to the indexed definition.
                    payload = reference.node.WhichOneof('payload')
                    is_declaration = bool(payload and payload.endswith('_decl'))
                    span = token_span(reference, name, buffers, file, declaration=is_declaration)
                    point = declaration.location
                    key = (declaration.symbol_identity, point.file, point.line, point.column)
                    if key not in locations:
                        locations[key] = target_location(declaration, name, buffers)
                    target = locations[key]
                    if span and target:
                        references[span] = dict(start=span[0], end=span[1], name=name,
                                                usr=declaration.symbol_identity, target=target,
                                                nativeDefinition=native_definition(declaration.node))
        identities = {item['usr'] for item in references.values() if item['usr']}
        definitions = {}
        if identities:
            with client.match_in(DEFINITIONS, tree) as rows:
                for row in rows:
                    declaration = row.bindings['declaration']
                    if declaration.symbol_identity in identities:
                        target = target_location(declaration, declaration_name(declaration.node), buffers)
                        if target:
                            definitions[declaration.symbol_identity] = target
        for item in references.values():
            if item['usr'] in definitions:
                item['target'] = definitions[item['usr']]
                item['nativeDefinition'] = True
    return dict(references=sorted(references.values(), key=lambda item: item['start']))


def resolve(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    """Use exact USRs across every indexed project, never a name fallback."""
    definitions = {}
    errors = []
    usr = request['usr']
    # File-scoped USRs can coincide between equally named source files in
    # separate projects. Their native lexical binding is authoritative.
    if request.get('nativeDefinition') or (usr.startswith('c:') and not usr.startswith('c:@')):
        return dict(targets=[request['target']], errors=[])
    if usr:
        for project in client.list_project_indexes().projects:
            try:
                response = client.lookup_symbol(project.project_root, usr)
                for symbol in response.symbols:
                    if (symbol.usr == usr and symbol.is_definition and not symbol.stale and
                            not response.stale and symbol.file_path and symbol.line > 0 and
                            Path(symbol.file_path).is_file()):
                        key = (symbol.file_path, int(symbol.line), max(1, int(symbol.column)))
                        definitions[key] = dict(file=key[0], line=key[1], column=key[2])
            except Exception as error:
                errors.append(f'{project.project_root}: {error}')
    return dict(targets=list(definitions.values()) or [request['target']], errors=errors)


def execute(request: dict[str, Any]) -> dict[str, Any]:
    client = Client(request.get('endpoint') or None,
                    config_path=request.get('configPath') or None,
                    compilation_database=request.get('compilationDatabase') or None)
    client._resolved_config = replace(client._configuration(), rpc_timeout=request['timeoutMs'] / 1000)
    try:
        if request['mode'] == 'resolve':
            return resolve(client, request)
        buffers = NavigationBuffers(request.get('buffers', {}))
        try:
            return scan(client, request, buffers)
        finally:
            buffers.close()
    finally:
        client.close()


if __name__ == '__main__':
    try:
        print(json.dumps(execute(json.loads(sys.stdin.readline()))), flush=True)
    except Exception as error:
        print(json.dumps(dict(error=str(error))), flush=True)
        sys.exit(1)
