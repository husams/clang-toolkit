"""Symbol searches retain native bindings in the inspector's owning host."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from run_service import Results

if TYPE_CHECKING:
    from action_service import ActionHost


def search(host: ActionHost, request: dict[str, Any], send: Any) -> dict[str, Any]:
    if request['settings'] != host.settings:
        raise ValueError('Analysis settings changed; rerun the search.')
    display = Results(request['maximum'])
    display.sources = host.sources
    results: list[dict[str, Any]] = []
    retained: list[Any] = []
    created_nodes: set[str] = set()
    errors: list[str] = []
    created_roots: dict[str, str] = {}
    files = 0
    try:
        for index, source in enumerate(request['files']):
            file = str(Path(source).resolve())
            send(dict(progress=f'{index + 1}/{len(request["files"])} · {file}'))
            root_id = None
            created = file not in host.roots
            first_result = len(results)
            try:
                root_id = host.root(file)
                if created:
                    created_roots[file] = root_id
                tree, _, _ = host.check_input(root_id)
                for query in request['queries']:
                    rows = host.client.match_in(query, tree)
                    keep = False
                    try:
                        for row in rows:
                            bindings = row.bindings
                            name = ('symbol' if 'symbol' in bindings else 'root'
                                    if 'root' in bindings else next(iter(bindings), None))
                            if name is None:
                                continue
                            before = len(display.items)
                            display.add(bindings[name])
                            if len(display.items) > before:
                                item = display.items[-1]
                                before_nodes = len(host.nodes)
                                identifier = host.inspector.retain(row.binding(name), file, item['name'])
                                if len(host.nodes) > before_nodes:
                                    created_nodes.add(identifier)
                                results.append({**item, 'nodeId': identifier, 'translationUnit': file})
                                keep = True
                            if display.truncated:
                                break
                    finally:
                        if keep:
                            retained.append(rows)
                        else:
                            rows.close()
                files += 1
            except Exception as error:
                errors.append(f'{file}: {error}')
            finally:
                # Empty/error files need no live parse owner after this search.
                if created and root_id is not None and len(results) == first_result:
                    host.nodes.pop(root_id)[0].close()
                    host.roots.pop(file)
        host.runs.append(retained)
    except BaseException:
        for rows in retained:
            rows.close()
        for identifier in created_nodes:
            host.nodes.pop(identifier, None)
        host.inspector.declarations = {
            key: identifier for key, identifier in host.inspector.declarations.items()
            if identifier not in created_nodes}
        for file, identifier in created_roots.items():
            if identifier in host.nodes:
                host.nodes.pop(identifier)[0].close()
                host.roots.pop(file, None)
        raise
    return dict(results=sorted(results, key=lambda item: (item['file'], item['line'], item['column'])),
                errors=errors, output=[], truncated=display.truncated,
                files=files, parseCount=host.parse_count)
