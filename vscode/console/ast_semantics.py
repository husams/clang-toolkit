"""Read inheritance through native base edges, without looking up class names."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from dataclasses import replace

from google.protobuf.json_format import MessageToDict
from clang_toolkit._generated.match.v1.match_result_pb2 import BINDING_MATCH_SCOPE_ROOT_ONLY

if TYPE_CHECKING:
    from action_service import ActionHost
    from ast_inspector import AstInspector

BASE_QUERY = ('cxxBaseSpecifier(optionally(hasType(qualType('
              'hasUnqualifiedDesugaredType(recordType(hasDeclaration('
              'cxxRecordDecl().bind("base"))))))))')


def inheritance(inspector: AstInspector, target: Any, file: str) -> dict[str, Any]:
    """Keep exact base declarations alive for navigation and follow-up actions."""
    host = inspector.host
    items: list[dict[str, Any]] = []
    retained: list[Any] = []
    created: set[str] = set()
    related: set[str] = set()
    notice = ''

    def visit(node: Any, depth: int) -> None:
        nonlocal notice
        if depth >= 16 or len(items) >= 128:
            notice = 'Inheritance display limited to 16 levels and 128 base edges.'
            return
        rows = host.client.peek(node, query=BASE_QUERY, max_nodes=1000)
        retained.append(rows)
        if rows:
            for row in rows:
                if len(items) >= 128:
                    notice = 'Inheritance display limited to 16 levels and 128 base edges.'
                    break
                edge = row.bindings['target'].base_specifier
                description = edge.type.description
                name = description.spelling or description.canonical_spelling
                raw = MessageToDict(edge)
                item = dict(name=name or '(dependent base)', depth=depth,
                            access=raw.get('access', ''), virtual=edge.is_virtual)
                items.append(item)
                if 'base' in row.bindings:
                    base = row.binding('base')
                    existing = len(host.nodes)
                    identifier = inspector.retain(base, file, 'Base class')
                    if len(host.nodes) > existing:
                        created.add(identifier)
                    related.add(identifier)
                    item['nodeId'] = identifier
                    if base.value.symbol_identity:
                        item['declaration'] = dict(name=inspector.describe(identifier)['name'],
                                                   symbol=base.value.symbol_identity)
                    existing = len(host.nodes)
                    edge_id = inspector.retain(row.binding('target'), file, 'Base specifier')
                    if len(host.nodes) > existing:
                        created.add(edge_id)
                    inspector.references[edge_id] = identifier
                    visit(base, depth + 1)
                else:
                    item['unresolved'] = True
    try:
        visit(target, 0)
    except BaseException:
        for identifier in created:
            host.nodes.pop(identifier, None)
        inspector.references = {key: value for key, value in inspector.references.items()
                                if key not in created and value not in created}
        for rows in retained:
            rows.close()
        raise
    inspector.collections.extend(retained)
    inspector.related.update(related)
    return dict(inheritance=items, notice=notice)


def parameters(host: ActionHost, target: Any) -> list[dict[str, str]]:
    """Match only this function's direct parameters, never a nested callable."""
    rows = host.client.match_in(
        'functionDecl(functionDecl().bind("function"), '
        'forEachDescendant(parmVarDecl(hasDeclContext(functionDecl('
        'equalsBoundNode("function")))).bind("parameter")))',
        replace(target, scope=BINDING_MATCH_SCOPE_ROOT_ONLY))
    try:
        if len(rows) > 1000:
            raise ValueError('Parameter display limited to 1,000 parameters.')
        return [dict(name=row.binding('parameter').parameter_name or '',
                     type=row.binding('parameter').decl_type or '') for row in rows]
    finally:
        rows.close()
