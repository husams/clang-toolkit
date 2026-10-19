"""Persistent VS Code action host; JSON carries display data, never AST identity."""
from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import replace
import base64
import gzip
import json
from queue import Queue
from pathlib import Path
import shutil
import sys
import struct
import tempfile
from threading import Event, Lock
from typing import Any
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent))

from clang_toolkit.cli.runtime.imports import preload_libraries, script_source
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.client import Client
from clang_toolkit._generated.match.v1.match_result_pb2 import MatchResult
from clang_toolkit.match_values import MatchRow, MatchValue, NativeMatchCollection
from clang_toolkit.resources import FileSet
from google.protobuf.json_format import MessageToDict
from action_batch_resume import restore_completed_batch
from run_service import Output, Results
from ast_inspector import AstInspector
from editor_buffers import EditorBuffers
from graph_service import graph
from search_service import search


class ActionError(ValueError):
    """An action input, definition, or result violates the action contract."""


def _install_report_output(report: dict[str, Any], captured: str) -> list[str]:
    """Merge bounded action output into the report for both success and stale-input paths."""
    output = report.pop('actionOutput', [])
    text = captured.rstrip('\n')
    if text:
        output.append(text)
    combined = '\n'.join(output)[:Output.limit]
    report['output'] = [combined] if combined else []
    return report['output']


def _batch_worker_input_limit(client: Client) -> int:
    """Use one worker when the native cursor budget cannot be queried."""
    try:
        return int(client.resource_status().max_inputs)
    except Exception:
        return 2


class ActionHost:
    _RESULT_MEMBER_GROUPS = 500

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
        self._result_directory = Path(tempfile.mkdtemp(prefix='ctk-action-results-'))
        self._batch_runs: dict[str, dict[str, Any]] = {}
        self.last_batch_report: dict[str, Any] | None = None
        self._last_changed_files: list[str] = []
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
        self._last_changed_files = []
        try:
            yield
            changed = []
            for file, original in self._fingerprints.items():
                if self.buffers.fingerprint(file) != original:
                    changed.append(file)
            if changed:
                self._last_changed_files = changed
                raise ActionError('Source changed; refresh analysis before continuing')
        finally:
            self._fingerprints = None

    def run(self, request: dict[str, Any], send: Any) -> dict[str, Any]:
        self.last_batch_report = None
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

    def page_batch_results(self, request: dict[str, Any]) -> dict[str, Any]:
        """Read a bounded page, keeping match groups intact across page edges."""
        if request.get('settings') != self.settings:
            raise ActionError('Analysis settings changed; refresh analysis before continuing')
        handle = request.get('resultHandle')
        run = self._batch_runs.get(handle)
        if run is None:
            raise ActionError('Workspace action results have expired; rerun the action')
        offset = min(max(0, int(request.get('offset', 0))), run['totalMatches'])
        limit = max(1, min(int(request.get('limit', 25)), 500))
        rows, next_offset = self._read_match_page(
            Path(run['path']), offset, limit, run['totalMatches'],
            Path(run['indexPath']), self.sources)
        return dict(resultHandle=handle, offset=offset, nextOffset=next_offset,
                    limit=limit, totalMatches=run['totalMatches'], results=rows,
                    hasMore=next_offset < run['totalMatches'],
                    complete=run.get('complete', True),
                    coverageComplete=run.get('coverageComplete', True))

    @staticmethod
    def _read_match_page(path: Path, offset: int, limit: int,
                         total_matches: int,
                         index_path: Path | None = None,
                         display_sources: dict[str, list[str]] | None = None
                         ) -> tuple[list[dict[str, Any]], int]:
        rows: list[dict[str, Any]] = []
        next_offset = min(offset + limit, total_matches)
        if index_path is not None and index_path.exists():
            record_size = struct.calcsize('!QQ')
            with index_path.open('rb') as offsets, path.open('rb') as handle:
                if offset >= total_matches:
                    return rows, total_matches
                offsets.seek(offset * record_size)
                member_start, logical_start = struct.unpack('!QQ', offsets.read(record_size))
                handle.seek(member_start)
                with gzip.GzipFile(fileobj=handle, mode='rb') as result:
                    result.seek(logical_start)
                    current_match: str | None = None
                    groups = 0
                    while line := result.readline():
                        record = json.loads(line)
                        match_id = record['matchId']
                        if match_id != current_match:
                            if current_match is not None:
                                groups += 1
                                if groups >= limit:
                                    break
                            current_match = match_id
                        rows.append(record)
                    else:
                        if current_match is not None:
                            groups += 1
                if groups != next_offset - offset:
                    raise ActionError('Workspace result index does not match compressed results')
            return ActionHost._materialize_page_rows(rows, display_sources or {}), next_offset
        match_index = -1
        previous: str | None = None
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt', encoding='utf-8') as handle:
            for line in handle:
                record = json.loads(line)
                current = record['matchId']
                if current != previous:
                    match_index += 1
                    previous = current
                if match_index >= offset + limit:
                    break
                if match_index >= offset:
                    rows.append(record)
        return ActionHost._materialize_page_rows(rows, display_sources or {}), next_offset

    @staticmethod
    def _materialize_page_rows(records: list[dict[str, Any]],
                               display_sources: dict[str, list[str]]) -> list[dict[str, Any]]:
        """Hydrate protobuf-backed match groups only when their page is requested."""
        output: list[dict[str, Any]] = []
        for record in records:
            if record.get('format') != 'ctk-match-protobuf-v1':
                output.append(record)
                continue
            match = MatchResult.FromString(base64.b64decode(record['protobuf'], validate=True))
            raw_match = MessageToDict(match, preserving_proto_field_name=True)
            match_id = record['matchId']
            translation_unit = record['translationUnit']
            for binding_name, binding in sorted(match.bindings.items()):
                display = Results(1)
                display.sources = display_sources
                display.add(binding)
                item = display.items[0] if display.items else dict(
                    name=binding_name, kind='Node', file=translation_unit,
                    line=1, column=1, excerpt='', raw={})
                result_id = f'{match_id}:{binding_name}'
                output.append({**item, 'id': result_id, 'nodeId': result_id,
                               'matchId': match_id, 'binding': binding_name,
                               'translationUnit': translation_unit, 'detached': True,
                               'raw': {'binding': item['raw'], 'match': raw_match}})
        return output

    @staticmethod
    def _append_staged_results(staged: Path, destination: Path, index_path: Path) -> None:
        """Append a gzip member and index each match-group boundary in bounded memory."""
        destination_size = destination.stat().st_size
        offsets_size = index_path.stat().st_size
        previous: str | None = None
        try:
            with staged.open('rb') as source, destination.open('ab') as raw, \
                    index_path.open('ab') as offsets:
                output = None
                member_start = 0
                member_groups = 0
                try:
                    for line in source:
                        record = json.loads(line)
                        match_id = record['matchId']
                        if match_id != previous:
                            if output is not None and member_groups >= ActionHost._RESULT_MEMBER_GROUPS:
                                output.close()
                                output = None
                            if output is None:
                                member_start = raw.tell()
                                output = gzip.GzipFile(
                                    fileobj=raw, mode='wb', compresslevel=1, mtime=0)
                                member_groups = 0
                            offsets.write(struct.pack('!QQ', member_start, output.tell()))
                            member_groups += 1
                            previous = match_id
                        assert output is not None
                        output.write(line)
                finally:
                    if output is not None:
                        output.close()
                raw.flush()
                offsets.flush()
        except BaseException:
            with destination.open('r+b') as output:
                output.truncate(destination_size)
            with index_path.open('r+b') as offsets:
                offsets.truncate(offsets_size)
            raise

    @staticmethod
    def _compress_staged_results(staged: Path) -> Path:
        """Compress one already-indexed TU spool without loading it in memory."""
        compressed = staged.with_suffix(staged.suffix + '.gz')
        temporary = compressed.with_suffix(compressed.suffix + '.tmp')
        try:
            with staged.open('rb') as source, gzip.open(temporary, 'wb', compresslevel=1) as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
            temporary.replace(compressed)
            staged.unlink()
            return compressed
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def _spill_batch_matches(self, value: Any, path: str, translation_unit: str,
                             run_id: str, first_match: int) -> int:
        """Stream one live match collection to disk while its resource scope is open."""
        if not isinstance(value, (MatchValue, NativeMatchCollection)):
            raise ActionError('Action must return retained CTK matches, not text, JSON, a scalar, or a detached list')
        count = 0
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('w', encoding='utf-8') as output:
            for row in value:
                if not isinstance(row, MatchRow):
                    raise ActionError('Action result contains a detached match')
                match_id = f'{run_id}:{first_match + count}'
                match = MatchResult(bindings=dict(row.bindings))
                if (source_match_index := row.source_match_index) is not None:
                    match.source_match_index = source_match_index
                record = {
                    'format': 'ctk-match-protobuf-v1',
                    'matchId': match_id,
                    'translationUnit': translation_unit,
                    'protobuf': base64.b64encode(match.SerializeToString()).decode('ascii'),
                }
                output.write(json.dumps(record, separators=(',', ':')) + '\n')
                count += 1
        return count

    def _run_batch_file(self, descriptor: Any, action: dict[str, Any],
                        values: dict[str, Any], staged_file: Path,
                        run_id: str, file_index: int) -> dict[str, Any]:
        """Execute one frozen TU using only this worker host's runtime and client."""
        runtime = self.runtime
        runtime.bindings.clear()
        runtime.bindings.update(self.base_bindings)
        outputs: list[str] = []

        def dispatch(source: str) -> None:
            result = runtime._prototype_session.dispatch(source)
            if not result.success:
                raise ActionError(result.output or 'Action failed')
            if result.output:
                outputs.append(result.output)

        try:
            argument_keys = [
                f'__ctk_argument_{index}' for index, _ in enumerate(action['arguments'])
            ]
            for key, argument in zip(argument_keys, action['arguments'], strict=True):
                runtime.bindings[key] = values[argument['name']]
            with script_source(runtime, action['path']):
                dispatch(action['generated'])
                runtime.bindings['__ctk_inputs'] = FileSet((descriptor,))
                runtime.bindings['__ctk_spill_path'] = str(staged_file)
                runtime.bindings['__ctk_spill_file'] = descriptor.path
                runtime.bindings['__ctk_spill_first_match'] = 0
                runtime.bindings['__ctk_spill_matches'] = (
                    lambda value, path, source, first:
                    self._spill_batch_matches(value, path, source,
                                              f'{run_id}:{file_index}', int(first))
                )
                call = (
                    f"{action['callable']}(__ctk_action_roots[0].tu"
                    f"{''.join(', ' + key for key in argument_keys)})"
                )
                batch_source = (
                    'let __ctk_batch_report = batch __ctk_part in __ctk_inputs '
                    'size 1 jobs 1 on error continue progress off do { '
                    'let __ctk_action_roots = match translationUnitDecl().bind("tu") '
                    'in __ctk_part.inputs[0]; '
                    f'let __ctk_action_result = {call}; '
                    '__ctk_spill_matches(__ctk_action_result, __ctk_spill_path, '
                    '__ctk_spill_file, __ctk_spill_first_match) '
                    '}'
                )
                dispatch(batch_source)
            report = runtime.bindings.get('__ctk_batch_report', {})
            if not report.get('cleanup_acknowledged', False):
                return dict(status='cleanup_unknown', message='Could not confirm batch cleanup')
            parse_count = int(report.get('completed_files', 0))
            if report.get('status') == 'cancelled':
                return dict(status='cancelled', message='Action cancelled', parseCount=parse_count)
            if report.get('failed_groups', 0):
                message = '; '.join(
                    sample['message'] for sample in report.get('group_errors_sample', ())
                ) or 'Batch group failed'
                return dict(status='failed', message=message, parseCount=parse_count)
            group_results = report.get('results', ())
            group_indices = report.get('result_group_indices', ())
            if len(group_results) != 1 or len(group_indices) != 1 or group_indices[0] != 1:
                return dict(status='failed', message='Batch spill returned an invalid group report',
                            parseCount=parse_count)
            if type(group_results[0]) is not int:
                return dict(status='failed', message='Batch spill did not return a match count',
                            parseCount=parse_count)
            return dict(status='succeeded', matches=group_results[0], parseCount=parse_count,
                        output=outputs)
        except KeyboardInterrupt:
            return dict(status='cancelled', message='Action cancelled', output=outputs)
        except Exception as error:
            report = runtime.bindings.get('__ctk_batch_report')
            if isinstance(report, dict) and not report.get('cleanup_acknowledged', False):
                return dict(status='cleanup_unknown', message=str(error), output=outputs)
            return dict(status='failed', message=str(error), output=outputs)
        finally:
            runtime.bindings.clear()
            runtime.bindings.update(self.base_bindings)

    def _run_batch(self, request: dict[str, Any], action: dict[str, Any], send: Any) -> dict[str, Any]:
        """Run each frozen input through the console's scoped batch evaluator."""
        files = [str(Path(file).resolve()) for file in request.get('files', ())]
        if not files:
            raise ActionError('Choose one or more C++ files before running a batch action')
        self.runtime.clear_batch_cancel()
        run_id = str(uuid4())
        errors: list[dict[str, str]] = []
        matches = 0
        result_bytes = 0
        parse_count = 0
        profiles = request.get('profiles', {})
        inputs: list[Any] = []
        input_statuses: list[dict[str, Any]] = []
        file_statuses: list[dict[str, Any]] = [
            {'file': file, 'manifestIndex': file_index + 1,
             'status': 'pending', 'attempted': False,
             'totalMatches': 0, 'fullResultPath': None}
            for file_index, file in enumerate(files)
        ]
        for file_index, file in enumerate(files):
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
                for descriptor in manifest.inputs:
                    self.batch_inputs[descriptor.path] = descriptor
                    inputs.append(descriptor)
                    status = file_statuses[file_index]
                    status['canonicalFile'] = descriptor.path
                    input_statuses.append(status)
                if not manifest.inputs:
                    error = {
                        'file': file,
                        'message': '; '.join(manifest.diagnostics)
                        or 'Server discovery returned no analysis input',
                    }
                    errors.append(error)
                    file_statuses[file_index].update(status='failed', message=error['message'])
            except Exception as error:
                errors.append({'file': file, 'message': str(error)})
                file_statuses[file_index].update(status='failed', message=str(error))
        inputs = tuple(inputs)
        for descriptor in inputs:
            self._fingerprint(descriptor.path)
        first_file = inputs[0].path if inputs else files[0]
        first_input = dict(id='', file=first_file, label='Workspace batch')
        result_directory = self._result_directory / run_id
        result_directory.mkdir(parents=True)
        result_file = result_directory / 'all-results.jsonl.gz'
        result_file.touch()
        offsets_file = result_directory / 'all-results.offsets'
        offsets_file.touch()
        checkpoint_file = result_directory / 'coverage.jsonl'
        checkpoint_file.touch()
        resumed = restore_completed_batch(
            request, action, files, self.settings, result_directory,
            result_file, offsets_file)
        resumed_count = len(resumed.statuses)
        if [descriptor.path for descriptor in inputs[:resumed_count]] != [
                status['file'] for status in resumed.statuses]:
            raise ActionError('Completed file provenance does not match native input discovery')
        for index, status in enumerate(resumed.statuses):
            input_statuses[index].update(status)
            with checkpoint_file.open('a', encoding='utf-8') as checkpoint_sink:
                checkpoint_sink.write(json.dumps({
                    'manifestIndex': index + 1, 'file': status['file'],
                    'status': 'succeeded', 'phase': 'indexed', 'attempted': True,
                    'matches': status['totalMatches'], 'resultFile': status['fullResultPath'],
                    'resumed': True,
                }, ensure_ascii=False) + '\n')
        matches = resumed.matches
        result_bytes = resumed.result_bytes
        parse_count = resumed_count
        if resumed_count:
            send(dict(progress=f'{resumed_count}/{len(files)} completed · restored verified results'))
        for status in file_statuses:
            if status['status'] == 'failed':
                with checkpoint_file.open('a', encoding='utf-8') as checkpoint_sink:
                    checkpoint_sink.write(json.dumps({
                        'manifestIndex': status['manifestIndex'],
                        'file': status['file'], 'status': 'failed',
                        'attempted': False, 'matches': 0,
                        'error': status.get('message'),
                    }, ensure_ascii=False) + '\n')
        cancelled = False
        action_output: list[str] = []
        action_output_size = 0
        # Each worker opens two cursors while matching (translation-unit roots
        # and the action matcher); derive concurrency from the native limit.
        worker_hosts = [self]
        worker_setup_errors: list[str] = []
        worker_cleanup_errors: list[str] = []
        worker_input_limit = _batch_worker_input_limit(self.client)
        worker_target = min(len(inputs) - resumed_count, 3, max(1, worker_input_limit // 2))
        for _ in range(worker_target - 1):
            try:
                worker_hosts.append(ActionHost(self.settings))
            except Exception as error:
                worker_setup_errors.append(str(error))
                break
        # Reset cancellation before workers can become active. Resetting in
        # _run_batch_file would erase a cancel delivered after active_indexes
        # is published but before the worker enters its first native request.
        for worker in worker_hosts:
            worker.runtime.clear_batch_cancel()
        tasks: Queue[Any] = Queue()
        completed_tasks: Queue[Any] = Queue()
        abort_pending = Event()
        progress_lock = Lock()
        active_indexes: set[int] = set()
        cancelled_active_indexes: set[int] = set()
        staged_paths: dict[int, Path] = {}
        for index, descriptor in enumerate(inputs):
            if index < resumed_count:
                continue
            staged_file = result_directory / f'file-{index + 1:04d}.jsonl'
            staged_paths[index] = staged_file
            tasks.put((index, descriptor, staged_file))
        for _ in worker_hosts:
            tasks.put(None)

        def worker_loop(worker: ActionHost) -> None:
            while True:
                task = tasks.get()
                if task is None:
                    return
                index, descriptor, staged_file = task
                if abort_pending.is_set():
                    completed_tasks.put((index, dict(
                        status='unattempted',
                        message='Action stopped before this file started')))
                    continue
                try:
                    with progress_lock:
                        send(dict(progress=f"{action['title']} · {Path(descriptor.path).name}"))
                        active_indexes.add(index)
                    outcome = worker._run_batch_file(
                        descriptor, action, request['values'], staged_file,
                        run_id, index + 1)
                    if outcome['status'] in {'cleanup_unknown', 'cancelled'}:
                        abort_pending.set()
                    completed_tasks.put((index, outcome))
                except Exception as error:
                    completed_tasks.put((index, dict(status='failed', message=str(error))))
                finally:
                    with progress_lock:
                        active_indexes.discard(index)

        completed_count = resumed_count + sum(status['status'] == 'failed' for status in file_statuses)
        completed_matches = resumed.matches
        next_merge_index = resumed_count

        def record_outcome(index: int, outcome: dict[str, Any],
                           outcomes: dict[int, dict[str, Any]]) -> None:
            nonlocal cancelled, completed_count, completed_matches
            if cancelled and index in cancelled_active_indexes and outcome.get('status') != 'cleanup_unknown':
                outcome = dict(outcome, status='cancelled',
                               message=outcome.get('message', 'Action cancelled'))
                cancelled = True
            outcomes[index] = outcome
            completed_count += 1
            descriptor = inputs[index]
            status_name = outcome.get('status', 'failed')
            file_matches = int(outcome.get('matches', 0))
            completed_matches += file_matches
            staged_file = staged_paths[index]
            checkpoint_result = (
                str(staged_file) if status_name == 'succeeded'
                or (status_name == 'cancelled' and staged_file.exists()
                    and staged_file.stat().st_size) else None)
            checkpoint = {
                'manifestIndex': input_statuses[index].get('manifestIndex', index + 1),
                'file': descriptor.path,
                'status': status_name,
                'phase': 'worker-complete',
                'attempted': status_name != 'unattempted',
                'matches': file_matches,
                'parseCount': int(outcome.get('parseCount', 0)),
                'resultFile': checkpoint_result,
                'error': outcome.get('message'),
            }
            with checkpoint_file.open('a', encoding='utf-8') as checkpoint_sink:
                checkpoint_sink.write(json.dumps(checkpoint, ensure_ascii=False) + '\n')
            suffix = (f' · matches {file_matches}' if status_name == 'succeeded'
                      else f' · {status_name}')
            with progress_lock:
                send(dict(progress=(f'{completed_count}/{len(files)} completed · '
                                    f'{Path(descriptor.path).name}{suffix}')))

        def merge_outcome(index: int, outcomes: dict[int, dict[str, Any]]) -> None:
            nonlocal cancelled, matches, parse_count, action_output_size, result_bytes
            descriptor = inputs[index]
            status = input_statuses[index]
            outcome = outcomes[index]
            status_name = outcome.get('status', 'failed')
            for text in outcome.get('output', ()):
                remaining = Output.limit - action_output_size
                if remaining <= 0:
                    break
                clipped = str(text)[:remaining]
                action_output.append(clipped)
                action_output_size += len(clipped)
            if status_name != 'unattempted':
                status['attempted'] = True
            parse_count += int(outcome.get('parseCount', 0))
            if status_name == 'succeeded':
                staged_file = staged_paths[index]
                file_matches = int(outcome['matches'])
                try:
                    self._append_staged_results(staged_file, result_file, offsets_file)
                except Exception as error:
                    message = f'Could not preserve completed file results in the workspace index: {error}'
                    status.update(status='failed', message=message,
                                  partialResultPath=str(staged_file))
                    errors.append({'file': descriptor.path, 'message': message})
                else:
                    matches += file_matches
                    file_result_bytes = staged_file.stat().st_size
                    result_bytes += file_result_bytes
                    status.update(status='succeeded', matches=file_matches,
                                  totalMatches=file_matches,
                                  resultBytes=file_result_bytes,
                                  fullResultPath=str(staged_file))
                    try:
                        stored_file = self._compress_staged_results(staged_file)
                    except KeyboardInterrupt:
                        # The aggregate and count are already committed. Keep
                        # the plain per-file copy if compression was interrupted,
                        # and consume this manifest index exactly once.
                        cancelled = True
                        abort_pending.set()
                        with progress_lock:
                            cancelled_active_indexes.update(active_indexes)
                        for worker in worker_hosts:
                            worker.request_batch_cancel()
                        temporary = staged_file.with_suffix(staged_file.suffix + '.gz.tmp')
                        temporary.unlink(missing_ok=True)
                        stored_file = (staged_file.with_suffix(staged_file.suffix + '.gz')
                                       if staged_file.with_suffix(staged_file.suffix + '.gz').exists()
                                       else staged_file)
                        status['fullResultPath'] = str(stored_file)
                    except Exception as error:
                        stored_file = staged_file
                        status['compressionWarning'] = str(error)
                    else:
                        status['fullResultPath'] = str(stored_file)
            elif status_name == 'unattempted':
                status.update(status='unattempted', message=outcome.get(
                    'message', 'Action stopped before this file started'))
            elif status_name == 'cancelled':
                status.update(status='cancelled', message=outcome.get(
                    'message', 'Action cancelled'))
                staged_file = staged_paths[index]
                if staged_file.exists() and staged_file.stat().st_size:
                    status['partialResultPath'] = str(staged_file)
                errors.append({'file': descriptor.path,
                               'message': status['message']})
            else:
                message = outcome.get('message', 'Workspace action failed')
                status.update(status=status_name, message=message)
                errors.append({'file': descriptor.path, 'message': message})
                if status_name == 'cleanup_unknown':
                    status['partialResultPath'] = str(staged_paths[index])
                else:
                    staged_paths[index].unlink(missing_ok=True)
                if status_name == 'cancelled':
                    cancelled = True
            final_checkpoint = {
                'manifestIndex': status.get('manifestIndex', index + 1),
                'file': descriptor.path,
                'status': status.get('status', status_name),
                'phase': 'indexed',
                'attempted': bool(status.get('attempted')),
                'matches': int(status.get('totalMatches', 0)),
                'resultFile': (status.get('fullResultPath')
                               or status.get('partialResultPath')),
                'error': status.get('message'),
            }
            with checkpoint_file.open('a', encoding='utf-8') as checkpoint_sink:
                checkpoint_sink.write(json.dumps(final_checkpoint, ensure_ascii=False) + '\n')

        try:
            with ThreadPoolExecutor(max_workers=len(worker_hosts)) as pool:
                futures = [pool.submit(worker_loop, worker) for worker in worker_hosts]
                outcomes: dict[int, dict[str, Any]] = {}
                try:
                    for _ in inputs[resumed_count:]:
                        index, outcome = completed_tasks.get()
                        record_outcome(index, outcome, outcomes)
                        while next_merge_index in outcomes:
                            merge_outcome(next_merge_index, outcomes)
                            next_merge_index += 1
                except KeyboardInterrupt:
                    cancelled = True
                    abort_pending.set()
                    with progress_lock:
                        cancelled_active_indexes.update(active_indexes)
                    for worker in worker_hosts:
                        worker.request_batch_cancel()
                    while len(outcomes) < len(inputs) - resumed_count:
                        index, outcome = completed_tasks.get()
                        record_outcome(index, outcome, outcomes)
                        while next_merge_index in outcomes:
                            merge_outcome(next_merge_index, outcomes)
                            next_merge_index += 1
                for future in futures:
                    future.result()
        except KeyboardInterrupt:
            cancelled = True
            abort_pending.set()
            with progress_lock:
                cancelled_active_indexes.update(active_indexes)
            for worker in worker_hosts:
                worker.request_batch_cancel()
        except Exception as error:
            errors.append({'file': first_file, 'message': str(error)})
        finally:
            for worker_index, worker in enumerate(worker_hosts[1:], start=2):
                try:
                    worker.close()
                except Exception as error:
                    message = f'Worker {worker_index} cleanup failed: {error}'
                    worker_cleanup_errors.append(message)
                    errors.append({'file': f'worker {worker_index}', 'message': message})

        for status in file_statuses:
            if status['status'] == 'pending':
                status.update(status='unattempted', message=(
                    'Action cancelled before this file started' if cancelled
                    else 'Action stopped before this file started'))

        self._batch_runs[run_id] = dict(path=str(result_file), indexPath=str(offsets_file),
                                        totalMatches=matches)
        while len(self._batch_runs) > 32:
            expired = next(iter(self._batch_runs))
            metadata = self._batch_runs.pop(expired)
            shutil.rmtree(Path(metadata['path']).parent, ignore_errors=True)
        page_size = max(1, min(int(request['maximum']), 500))
        first_page, next_offset = self._read_match_page(
            result_file, 0, page_size, matches, offsets_file)
        succeeded = sum(status['status'] == 'succeeded' for status in file_statuses)
        failed = sum(status['status'] == 'failed' for status in file_statuses)
        coverage_complete = all(status['status'] in {'succeeded', 'failed'}
                                for status in file_statuses)
        complete = coverage_complete and failed == 0
        self._batch_runs[run_id].update(complete=complete,
                                        coverageComplete=coverage_complete)
        index_file = result_directory / 'results.md'
        index_lines = [
            '# Workspace action results', '',
            f'- Status: {"complete" if complete else "partial"}',
            f'- Translation units: {len(files)} requested, {succeeded} succeeded, {failed} failed',
            f'- Total matches: {matches}',
            f'- Uncompressed result bytes: {result_bytes}',
            f'- Complete results: [{result_file.name}]({result_file.as_uri()})', '',
            '| File | Status | Matches | Per-file results | Error |',
            '| --- | --- | ---: | --- | --- |',
        ]
        for status in file_statuses:
            path = status.get('fullResultPath') or status.get('partialResultPath') or ''
            result_link = f'[{Path(path).name}]({Path(path).as_uri()})' if path else ''
            message = str(status.get('message', '')).replace('|', '\\|').replace('\n', ' ')
            index_lines.append(
                f"| `{status['file']}` | {status['status']} | "
                f"{status.get('totalMatches', 0)} | {result_link} | {message} |"
            )
        index_file.write_text('\n'.join(index_lines) + '\n', encoding='utf-8')
        self._batch_runs[run_id]['resultIndexFile'] = str(index_file)
        report = dict(results=first_page, input=first_input, runId=run_id,
                      resultHandle=run_id, resultFile=str(result_file),
                      resultIndexFile=str(index_file), matches=matches,
                      totalMatches=matches, resultBytes=result_bytes,
                      pageOffset=0, nextOffset=next_offset,
                      pageSize=page_size, hasMore=next_offset < matches, complete=complete,
                      coverageComplete=coverage_complete, cancelled=cancelled,
                      truncated=False, parseCount=parse_count, batch=True, files=len(files),
                      attemptedFiles=sum(bool(status.get('attempted')) for status in file_statuses),
                      completedFiles=succeeded,
                      failedFiles=failed,
                      unattemptedFiles=sum(status['status'] == 'unattempted'
                                           for status in file_statuses),
                      workerCount=len(worker_hosts), workerSetupErrors=worker_setup_errors,
                      workerCleanupErrors=worker_cleanup_errors,
                      workerInputLimit=worker_input_limit,
                      resumedFiles=resumed_count,
                      fileStatuses=file_statuses, errors=errors,
                      actionOutput=action_output)
        self.last_batch_report = report
        return report

    def close(self) -> None:
        try:
            self.inspector.close()
            self.nodes.clear()
            self.roots.clear()
            self.batch_inputs.clear()
            self.runs.clear()
            self._batch_runs.clear()
            shutil.rmtree(self._result_directory, ignore_errors=True)
            self.runtime.close()
        finally:
            try:
                self.client.close()
            finally:
                self.buffers.close()

    def request_batch_cancel(self) -> None:
        """Signal this worker and cancel its currently active native batch scope."""
        self.runtime.request_batch_cancel()
        scope = self.runtime._active_resource_scope
        if scope is not None:
            try:
                scope.cancel()
            except Exception:
                # The evaluator's cancellation flag still stops work at its
                # next boundary if the scope is already closing.
                pass

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
                    if request['type'] == 'pageActionResults':
                        response = {'actionResults': host.page_batch_results(request)}
                    else:
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
                    _install_report_output(response['report'], output.getvalue())
                send(identity, response)
            except KeyboardInterrupt:
                send(request.get('id', 0), {'error': 'Action cancelled', 'output': [output.getvalue()]})
            except Exception as error:
                if (request.get('type') == 'run' and request.get('batch') is True
                        and host is not None and host.last_batch_report is not None):
                    report = host.last_batch_report
                    report['complete'] = False
                    report['sourceValidationError'] = str(error)
                    report['sourceChangedFiles'] = list(host._last_changed_files)
                    report.setdefault('errors', []).append({
                        'file': host._last_changed_files[0] if host._last_changed_files else '',
                        'message': str(error),
                    })
                    if report.get('resultIndexFile'):
                        with Path(report['resultIndexFile']).open('a', encoding='utf-8') as index:
                            index.write(f'\nSource validation failed: {error}\n')
                    metadata = host._batch_runs.get(report.get('resultHandle'))
                    if metadata is not None:
                        metadata['complete'] = False
                    _install_report_output(report, output.getvalue())
                    send(request.get('id', 0), {
                        'report': report, 'output': [output.getvalue()],
                    })
                else:
                    send(request.get('id', 0), {'error': str(error), 'output': [output.getvalue()]})
    finally:
        if host is not None:
            with redirect_stdout(sys.stderr):
                host.close()


if __name__ == '__main__':
    main()
