"""Persistent VS Code action host; JSON carries display data, never AST identity."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import replace
import json
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent))

from clang_toolkit.cli.runtime.imports import preload_libraries, script_source
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.semantic import MessageView
from clang_toolkit.cli.runtime.values import MatchSet
from clang_toolkit.client import Client
from clang_toolkit.match_values import MatchRow, MatchValue, NativeMatchCollection
from clang_toolkit.resources import FileSet
from google.protobuf.json_format import MessageToDict
from run_service import Output, Results
from ast_inspector import AstInspector
from editor_buffers import EditorBuffers
from graph_service import graph
from search_service import search


class ActionError(ValueError):
    """An action input, definition, or result violates the action contract."""


class ActionHost:
    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings
        self.client = Client(settings.get('endpoint') or None,
                             config_path=settings.get('configPath') or None,
                             compilation_database=settings.get('compilationDatabase') or None)
        self.client._resolved_config = replace(self.client._configuration(),
                                              rpc_timeout=settings['timeoutMs'] / 1000)
        self.runtime = PrototypeRuntime(self.client, cwd=Path(settings['directory']))
        self.buffers = EditorBuffers(settings.get('buffers', {}))
        self._fingerprints: dict[str, str] | None = None
        self.runtime.config_store.effective['extra_args'] = [
            *settings['compileArguments'], *self.buffers.arguments]
        preload_libraries(self.runtime, settings.get('libraryDirectory') or None)
        self.base_bindings = dict(self.runtime.bindings)
        self.nodes: dict[str, tuple[Any, str, str]] = {}
        self.roots: dict[str, tuple[str, str]] = {}
        # Batch discovery is metadata-only. Keep the frozen per-file profile so
        # a later detached-result inspection can parse the same TU on demand.
        self.batch_inputs: dict[str, Any] = {}
        self.runs: list[list[Any]] = []
        self.parse_count = 0
        self.sources: dict[str, list[str]] = {
            file: text.splitlines() for file, text in self.buffers.contents.items()}
        self.inspector = AstInspector(self)

    def dispatch(self, source: str) -> None:
        result = self.runtime._prototype_session.dispatch(source)
        if not result.success:
            raise ActionError(result.output or 'Action failed')
        if result.output:
            print(result.output)

    def root(self, file: str) -> str:
        file = str(Path(file).resolve())
        current = self._fingerprint(file)
        if file in self.roots:
            identifier, original = self.roots[file]
            if original != current:
                raise ActionError('Source changed; refresh analysis before continuing')
            return identifier
        descriptor = self.batch_inputs.get(file)
        if descriptor is not None:
            # Parse the exact frozen profile discovered for this batch input;
            # this lazily acquires a normal retained tree only when the user
            # asks to inspect or continue from a detached result.
            tree = self.client.parse(descriptor)
        else:
            self.runtime.bindings['__ctk_path'] = file
            self.dispatch('let __ctk_root = parse __ctk_path')
            tree = self.runtime.bindings['__ctk_root']
        identifier = str(uuid4())
        self.nodes[identifier] = (tree, file, 'File root')
        self.roots[file] = (identifier, current)
        self.parse_count += 1
        return identifier

    def check_input(self, identifier: str) -> tuple[Any, str, str]:
        if identifier not in self.nodes:
            raise ActionError('This node has expired; refresh analysis to create a new context')
        value, file, label = self.nodes[identifier]
        if self.roots[file][1] != self._fingerprint(file):
            raise ActionError('Source changed; refresh analysis before continuing')
        return value, file, label

    def _fingerprint(self, file: str) -> str:
        if self._fingerprints is None:
            return self.buffers.fingerprint(file)
        if file not in self._fingerprints:
            self._fingerprints[file] = self.buffers.fingerprint(file)
        return self._fingerprints[file]

    @contextmanager
    def validated_inputs(self) -> Iterator[None]:
        # One wide page must not hash the whole source once per child. Check
        # each touched file on entry/use and again before sending any result.
        if self._fingerprints is not None:
            yield
            return
        self._fingerprints = {}
        try:
            yield
            for file, original in self._fingerprints.items():
                if self.buffers.fingerprint(file) != original:
                    raise ActionError('Source changed; refresh analysis before continuing')
        finally:
            self._fingerprints = None

    def run(self, request: dict[str, Any], send: Any) -> dict[str, Any]:
        if request['settings'] != self.settings:
            raise ActionError('Analysis settings changed; refresh analysis before continuing')
        action = request['action']
        if request.get('batch') is True:
            return self._run_batch(request, action, send)
        if len(self.runs) >= 32:
            raise ActionError('Analysis history is full (32 runs); close or refresh analysis to release it')
        self.runtime.clear_batch_cancel()
        self.runtime.bindings.clear()
        self.runtime.bindings.update(self.base_bindings)
        input_ids = [request['inputId']] if request.get('inputId') else [self.root(file) for file in request['files']]
        if not input_ids:
            raise ActionError('Choose a C++ file or a retained node first')
        run_id = str(uuid4())
        pending_nodes: dict[str, tuple[Any, str, str]] = {}
        retained: list[Any] = []
        results: list[dict[str, Any]] = []
        matches, truncated = 0, False
        first_input: dict[str, str] | None = None
        try:
            for input_id in input_ids:
                target, file, label = self.check_input(input_id)
                if first_input is None:
                    first_input = dict(id=input_id, file=file, label=label)
                self.runtime.bindings.clear()
                self.runtime.bindings.update(self.base_bindings)
                self.runtime.bindings['__ctk_node'] = target
                arguments = []
                for index, argument in enumerate(action['arguments']):
                    key = f'__ctk_argument_{index}'
                    self.runtime.bindings[key] = request['values'][argument['name']]
                    arguments.append(key)
                send(dict(progress=f"{action['title']} · {Path(file).name}"))
                with script_source(self.runtime, action['path']):
                    self.dispatch(action['generated'])
                    self.dispatch(f"let __ctk_result = {action['callable']}(__ctk_node{''.join(', ' + key for key in arguments)})")
                value = self.runtime.bindings['__ctk_result']
                if not isinstance(value, (MatchValue, NativeMatchCollection)):
                    raise ActionError('Action must return retained CTK matches, not text, JSON, a scalar, or a detached list')
                retained.append(value)
                for row in value:
                    if not isinstance(row, MatchRow):
                        raise ActionError('Action result contains a detached match')
                    if matches >= request['maximum']:
                        truncated = True
                        break
                    match_id = f'{run_id}:{matches}'
                    matches += 1
                    for binding_name, binding in sorted(row.bindings.items()):
                        node_id = str(uuid4())
                        display = Results(1)
                        display.sources = self.sources
                        display.add(binding)
                        item = display.items[0] if display.items else dict(name=binding_name, kind='Node', file=file, line=1, column=1, excerpt='', raw={})
                        # Every binding receives its own handle, even when two
                        # bindings share a location or one is the automatic root.
                        pending_nodes[node_id] = (row.binding(binding_name), file, item['name'])
                        results.append({**item, 'id': node_id, 'nodeId': node_id,
                                        'matchId': match_id, 'binding': binding_name,
                                        'raw': {'binding': item['raw'], 'match': row.to_dict()}})
        finally:
            self.runtime.bindings.clear()
            self.runtime.bindings.update(self.base_bindings)
        # Publish only a successful complete run. Failed/cancelled actions leave
        # the earlier node table and result collections available for reuse.
        self.nodes.update(pending_nodes)
        self.runs.append(retained)
        return dict(results=results, input=first_input, runId=run_id, matches=matches,
                    truncated=truncated, parseCount=self.parse_count)

    def _run_batch(self, request: dict[str, Any], action: dict[str, Any], send: Any) -> dict[str, Any]:
        """Run each frozen input through the console's scoped batch evaluator."""
        files = [str(Path(file).resolve()) for file in request.get('files', ())]
        if not files:
            raise ActionError('Choose one or more C++ files before running a batch action')
        self.runtime.clear_batch_cancel()
        run_id = str(uuid4())
        results: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        matches = 0
        truncated = False
        parse_count = 0
        limit = request['maximum']
        profiles = request.get('profiles', {})
        descriptors = []
        for file in files:
            has_profile = file in profiles
            profile = profiles.get(file, {})
            directory = profile.get('directory') or self.settings['directory']
            compile_arguments = [
                *profile.get(
                    'compileArguments',
                    [] if has_profile else self.settings['compileArguments'],
                ),
                *self.buffers.arguments,
            ]
            try:
                manifest = self.client.discover_files(
                    [file],
                    working_directory=directory,
                    compile_arguments=compile_arguments,
                    compilation_database=(
                        profile.get('compilationDatabase')
                        if has_profile
                        else self.settings.get('compilationDatabase')
                    ),
                )
                descriptors.extend(manifest.inputs)
                for descriptor in manifest.inputs:
                    self.batch_inputs[descriptor.path] = descriptor
                if not manifest.inputs:
                    errors.append({
                        'file': file,
                        'message': '; '.join(manifest.diagnostics)
                        or 'Server discovery returned no analysis input',
                    })
            except Exception as error:
                errors.append({'file': file, 'message': str(error)})
        inputs = tuple(descriptors)
        for descriptor in inputs:
            self._fingerprint(descriptor.path)
        first_file = inputs[0].path if inputs else files[0]
        first_input = dict(id='', file=first_file, label='Workspace batch')
        argument_keys = [
            f'__ctk_argument_{index}' for index, _ in enumerate(action['arguments'])
        ]
        call = f"{action['callable']}(__ctk_action_roots[0].tu{''.join(', ' + key for key in argument_keys)})"
        batch_source = (
            'let __ctk_batch_report = batch __ctk_part in __ctk_inputs '
            'size 1 jobs 1 on error continue progress off do { '
            'let __ctk_action_roots = match translationUnitDecl().bind("tu") '
            'in __ctk_part.inputs[0]; '
            f'{call} '
            '}'
        )
        self.runtime.bindings.clear()
        self.runtime.bindings.update(self.base_bindings)
        for key, argument in zip(argument_keys, action['arguments'], strict=True):
            self.runtime.bindings[key] = request['values'][argument['name']]

        try:
            with script_source(self.runtime, action['path']):
                self.dispatch(action['generated'])
                for index, descriptor in enumerate(inputs):
                    if matches >= limit:
                        truncated = True
                        break
                    file = descriptor.path
                    send(dict(progress=f"{action['title']} · {Path(file).name}"))
                    # The evaluator owns admission, operation attribution, scoped
                    # locals, cancellation, detachment, cleanup, and result limits.
                    self.runtime.bindings['__ctk_inputs'] = FileSet((descriptor,))
                    self.dispatch(batch_source)
                    report = self.runtime.bindings['__ctk_batch_report']
                    if not report.get('cleanup_acknowledged', False):
                        raise ActionError(
                            f"Could not confirm cleanup for {file}; stopping workspace action"
                        )
                    parse_count += int(report.get('completed_files', 0))
                    if report.get('status') == 'cancelled':
                        raise KeyboardInterrupt('Action cancelled')
                    if report.get('failed_groups', 0):
                        message = '; '.join(
                            sample['message'] for sample in report.get('group_errors_sample', ())
                        ) or 'Batch group failed'
                        errors.append({'file': file, 'message': message})
                        continue
                    group_results = report.get('results', ())
                    group_indices = report.get('result_group_indices', ())
                    for group_index, group_result in zip(group_indices, group_results, strict=True):
                        if group_index != 1:
                            raise ActionError('Expected one input group from the workspace action')
                        if not isinstance(group_result, MatchSet):
                            raise ActionError('Action must return retained CTK matches')
                        for row in group_result.rows:
                            if not isinstance(row, MessageView):
                                raise ActionError('Batch returned a non-detached match row')
                            raw_match = MessageToDict(row._message())
                            if matches >= limit:
                                truncated = True
                                break
                            match_id = f'{run_id}:{matches}'
                            matches += 1
                            for binding_name, binding in sorted(row._message().bindings.items()):
                                display = Results(1)
                                display.sources = self.sources
                                display.add(binding)
                                item = display.items[0] if display.items else dict(
                                    name=binding_name, kind='Node', file=file, line=1,
                                    column=1, excerpt='', raw={})
                                result_id = str(uuid4())
                                results.append({**item, 'id': result_id, 'nodeId': result_id,
                                                'matchId': match_id, 'binding': binding_name,
                                                'translationUnit': file, 'detached': True,
                                                'raw': {'binding': item['raw'], 'match': raw_match}})
                        if truncated:
                            break
                    if truncated:
                        break
                if inputs and not truncated and matches >= limit and len(inputs) > index + 1:
                    truncated = True
        finally:
            self.runtime.bindings.clear()
            self.runtime.bindings.update(self.base_bindings)

        return dict(results=results, input=first_input, runId=run_id, matches=matches,
                    truncated=truncated, parseCount=parse_count, batch=True,
                    files=len(files), errors=errors)

    def close(self) -> None:
        try:
            self.inspector.close()
            self.nodes.clear()
            self.roots.clear()
            self.batch_inputs.clear()
            self.runs.clear()
            self.runtime.close()
        finally:
            try:
                self.client.close()
            finally:
                self.buffers.close()

    def keep_alive(self) -> int:
        """Renew this host's retained cursors without changing AST identities."""
        # Server listings can include other clients of the same local user.
        # Pin only this client's retained owners while renewing them.
        owners = [owner for reference in tuple(self.client._values.values())
                  if (owner := reference()) is not None and not owner.closed]
        if self.roots and not owners:
            raise ActionError('Analysis session expired; reload the file AST.')
        for owner in owners:
            self.client.attach_session(owner.session_id)
        return len(owners)


def main() -> None:
    protocol = sys.stdout
    host: ActionHost | None = None

    def send(identity: int, value: dict[str, Any]) -> None:
        protocol.write(json.dumps({'id': identity, **value}, ensure_ascii=False) + '\n')
        protocol.flush()

    try:
        for line in sys.stdin:
            request: dict[str, Any] = {}
            output = Output()
            try:
                request = json.loads(line)
                identity = request['id']
                with redirect_stdout(output), redirect_stderr(output):
                    if request['type'] == 'reset':
                        if host is not None:
                            host.close()
                        host = None
                        send(identity, {'reset': True})
                        continue
                    if request['type'] == 'keepAlive':
                        send(identity, {'keptAlive': host.keep_alive() if host else 0})
                        continue
                    if host is None:
                        host = ActionHost(request['settings'])
                    with host.validated_inputs():
                        if request['type'] == 'selectSource':
                            inspection = host.inspector.selection.locate(request)
                            response = {'inspection': inspection} if inspection else {'notFound': True}
                        elif request['type'] == 'inspect':
                            response = {'inspection': host.inspector.inspect(request)}
                        elif request['type'] == 'graph':
                            response = {'graph': graph(host, request)}
                        elif request['type'] == 'search':
                            response = {'searchReport': search(host, request, lambda value: send(identity, value))}
                        else:
                            response = {'report': host.run(request, lambda value: send(identity, value))}
                if 'report' in response:
                    text = output.getvalue().rstrip('\n')
                    response['report']['output'] = [text] if text else []
                send(identity, response)
            except KeyboardInterrupt:
                send(request.get('id', 0), {'error': 'Action cancelled', 'output': [output.getvalue()]})
            except Exception as error:
                send(request.get('id', 0), {'error': str(error), 'output': [output.getvalue()]})
    finally:
        if host is not None:
            with redirect_stdout(sys.stderr):
                host.close()


if __name__ == '__main__':
    main()
