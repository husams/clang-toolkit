"""Display projections of native graphs from the inspector's pinned AST."""
from __future__ import annotations

from typing import Any


def callable_target(host: Any, identifier: str) -> Any:
    target, _, _ = host.check_input(identifier)
    callables = ('function_decl', 'cxx_method_decl', 'cxx_constructor_decl',
                 'cxx_destructor_decl', 'cxx_conversion_decl', 'cxx_deduction_guide_decl')
    if target.value.node.WhichOneof('payload') in callables:
        return target
    cache = getattr(host, '_graph_callables', None)
    if cache is None:
        cache = host._graph_callables = {}
    if identifier in cache:
        return cache[identifier]
    # Walk native parents, never descendants: choosing a file/class must not
    # silently choose its first method, or an initializer's nested lambda.
    queue, seen, retained = [target], set(), []
    try:
        for current in queue:
            key = current.value.SerializeToString(deterministic=True)
            if key in seen:
                continue
            seen.add(key)
            if current.value.node.WhichOneof('payload') in callables:
                cache[identifier] = current
                host.inspector.collections.extend(retained)
                retained = []
                return current
            rows = host.client.peek(current, axis='parents')
            retained.append(rows)
            queue.extend(row.binding('target') for row in rows)
    finally:
        for rows in retained:
            rows.close()
    raise ValueError('Select a function or a statement inside a function to view its graph.')


def point(location: Any) -> dict[str, Any]:
    return dict(file=location.file if location.valid else '',
                line=max(1, location.line), column=max(1, location.column))


def graph(host: Any, request: dict[str, Any]) -> dict[str, Any]:
    if request['settings'] != host.settings:
        raise ValueError('Analysis settings changed; reload the file AST.')
    _, file, _ = host.check_input(request['nodeId'])
    target = callable_target(host, request['nodeId'])
    tree, _, _ = host.check_input(host.roots[file][0])
    kind = request['kind']
    revision = host.roots[file][1]
    if kind == 'callgraph':
        # The complete TU is fetched once; UI expansion never discards a branch.
        cache = getattr(host, '_display_callgraphs', None)
        if cache is None:
            cache = host._display_callgraphs = {}
        if file not in cache:
            cache[file] = host.client.callgraph(tree, max_nodes='all',
                                               exclude_system_headers=True)
        native = cache[file]
        focus = next((node for node in native.nodes if not node.is_virtual_root and
                      node.symbol_identity == target.value.symbol_identity), None)
        if focus is None:
            raise ValueError('This callable has no node in the native call graph.')
        nodes = [dict(id=str(node.node_index),
                      name=node.function.qualified_name or node.function.name or '(anonymous)',
                      detail='', **point(node.location))
                 for node in native.nodes if not node.is_virtual_root]
        pairs = dict.fromkeys((str(edge.caller_node), str(edge.callee_node))
                              for edge in native.edges if not edge.is_virtual_root_edge)
        edges = [dict(id=f'{a}:{b}', **{'from': a}, to=b, label='') for a, b in pairs]
        warnings = []
        unresolved = sum(not site.HasField('callee_node') for site in native.call_sites)
        if unresolved:
            warnings.append(f'{unresolved} indirect or excluded call sites have no resolved target.')
        return dict(key=f'{file}:{revision}:{focus.symbol_identity}:calls', kind=kind,
                    root=str(focus.node_index), name=focus.function.qualified_name or focus.function.name,
                    complete=native.HasField('is_complete') and native.is_complete,
                    nodes=nodes, edges=edges, warnings=warnings)
    if kind != 'cfg':
        raise ValueError('Unknown graph view.')
    response = host.client.cfg(target, projection='recursive', payload_depth=4)
    if len(response.graphs) != 1:
        raise ValueError('This callable has no single CFG body to display.')
    native = response.graphs[0]
    nodes, edges = [], []
    for block in native.blocks:
        names = []
        for element in block.elements:
            value = element.WhichOneof('value')
            if value == 'statement':
                statement = element.statement.statement
                payload = statement.WhichOneof('payload')
                if payload == 'expression':
                    payload = statement.expression.WhichOneof('payload')
                names.append((payload or 'statement').replace('_', ' '))
            else:
                names.append((value or 'element').replace('_', ' '))
        name = 'Entry' if block.block_index == native.entry_block else (
            'Exit' if block.block_index == native.exit_block else f'Block {block.block_index}')
        nodes.append(dict(id=str(block.block_index), name=name, detail=' · '.join(names),
                          **point(target.value.location)))
        condition = block.terminator.WhichOneof('payload') == 'if_stmt'
        for index, successor in enumerate(block.successors):
            for field in ('reachable_block', 'possibly_unreachable_block'):
                if not successor.HasField(field):
                    continue
                label = ('True' if index == 0 else 'False') if condition and len(block.successors) == 2 else ''
                if field == 'possibly_unreachable_block' or not successor.is_reachable:
                    label = f'{label} (unreachable)'.strip()
                edges.append(dict(id=f'{block.block_index}:{index}:{field}',
                                  **{'from': str(block.block_index)},
                                  to=str(getattr(successor, field)), label=label))
    return dict(key=f'{file}:{revision}:{target.value.symbol_identity}:cfg', kind=kind,
                root=str(native.entry_block), name=native.function.qualified_name or native.function.name,
                complete=native.HasField('is_complete') and native.is_complete,
                nodes=nodes, edges=edges, warnings=[])
