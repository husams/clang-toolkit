"""Read inheritance through native base edges, without looking up class names."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from dataclasses import replace

from google.protobuf.json_format import MessageToDict
from clang_toolkit._generated.match.v1.match_result_pb2 import BINDING_MATCH_SCOPE_ROOT_ONLY

if TYPE_CHECKING:
    from action_service import ActionHost

BASE_QUERY = ('cxxBaseSpecifier(optionally(hasType(qualType('
              'hasUnqualifiedDesugaredType(recordType(hasDeclaration('
              'cxxRecordDecl().bind("base"))))))))')


def inheritance(host: ActionHost, target: Any) -> dict[str, Any]:
    """Return bounded, display-only base paths from this exact retained class."""
    items: list[dict[str, Any]] = []
    notice = ''

    def visit(node: Any, depth: int) -> None:
        nonlocal notice
        if depth >= 16 or len(items) >= 128:
            notice = 'Inheritance display limited to 16 levels and 128 base edges.'
            return
        rows = host.client.peek(node, query=BASE_QUERY, max_nodes=1000)
        try:
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
                    visit(row.binding('base'), depth + 1)
                else:
                    item['unresolved'] = True
        finally:
            rows.close()

    visit(target, 0)
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
