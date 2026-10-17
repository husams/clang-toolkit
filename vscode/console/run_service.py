"""Run one editor submission through the console's actual batch entry point."""
from __future__ import annotations

import asyncio
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import signal
import sys
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
from google.protobuf.json_format import MessageToDict
from clang_toolkit.cli import app
from clang_toolkit.cli.runtime.prototype.repl import _ReplContext
from clang_toolkit.cli.runtime.semantic import MessageView
from clang_toolkit.cli.runtime.values import MatchSet, render
from clang_toolkit.match_values import (
    BindingSelection, MatchRow, MatchValue, NativeBindingCollection, NativeMatchCollection,
)


class Output(io.StringIO):
    """Bound retained UI output without changing console output routing."""
    limit = 2 * 1024 * 1024

    def write(self, text: str) -> int:
        remaining = self.limit - self.tell()
        if remaining > 0:
            super().write(text[:remaining])
        return len(text)


class Results:
    def __init__(self, maximum: int) -> None:
        self.maximum = maximum
        self.items: list[dict[str, Any]] = []
        self.seen: set[str] = set()
        self.truncated = False
        self.sources: dict[str, list[str]] = {}

    def add(self, binding: Any) -> None:
        location = binding.location
        if not location.valid or not location.file or location.line < 1:
            return
        raw = MessageToDict(binding)
        node = raw.get('node', {})

        def named(value: Any) -> str:
            if isinstance(value, dict):
                if value.get('qualifiedName'):
                    return value['qualifiedName']
                for child in value.values():
                    if result := named(child):
                        return result
            return ''

        kind = next(iter(node), 'Match').removesuffix('Decl').removeprefix('cxx')
        kind = kind[:1].upper() + kind[1:]
        name = named(node) or raw.get('symbolIdentity') or kind
        self.add_location(name, kind, location.file, int(location.line), max(1, int(location.column)), raw)

    def add_location(self, name: str, kind: str, file: str, line: int, column: int, raw: Any) -> None:
        identifier = f'{file}:{line}:{column}:{name}'
        if identifier in self.seen:
            return
        self.seen.add(identifier)
        if len(self.items) >= self.maximum:
            self.truncated = True
            return
        if file not in self.sources:
            try:
                self.sources[file] = Path(file).read_text().splitlines()
            except (OSError, UnicodeError):
                self.sources[file] = []
        lines = self.sources[file]
        self.items.append(dict(id=identifier, name=name, kind=kind, file=file,
                               line=line, column=column, raw=json.loads(json.dumps(raw, default=render, skipkeys=True)),
                               excerpt=lines[line - 1].strip() if line <= len(lines) else ''))

    def collect(self, value: Any, depth: int = 0) -> None:
        if depth > 12 or self.truncated:
            return
        if isinstance(value, BindingSelection):
            if value._index is not None:
                self.add(value.value)
        elif isinstance(value, MessageView):
            message = value._message()
            if message.DESCRIPTOR.name == 'MatchBinding':
                self.add(message)
        elif isinstance(value, MatchSet):
            self.collect(value.rows, depth + 1)
        elif isinstance(value, MatchRow):
            bindings = value.bindings
            binding = bindings.get('symbol') or bindings.get('root') or next(iter(bindings.values()), None)
            if binding is not None:
                self.add(binding)
        elif isinstance(value, (MatchValue, NativeMatchCollection, NativeBindingCollection, list, tuple)):
            for child in value:
                self.collect(child, depth + 1)
                if self.truncated:
                    break
        elif isinstance(value, dict):
            # Console helpers return ordinary symbol summaries with explicit
            # source coordinates, rather than retained match cursors.
            if isinstance(value.get('file'), str) and value['file'] and type(value.get('line')) is int and value['line'] > 0 and isinstance(value.get('name'), str):
                self.add_location(value['name'], str(value.get('kind', 'Symbol')), value['file'], value['line'], 1, value)
            for child in value.values():
                self.collect(child, depth + 1)


def run(request: dict[str, Any], send: Any) -> dict[str, Any]:
    action = request['action']
    source_path = Path(action['script']).resolve() if action.get('script') else None
    label = str(source_path or action['title'])
    results = Results(request['maxResults'])
    output = Output()
    errors: list[str] = []
    factory, source_context, original_emit = app._runtime_for_engine, app.script_source, _ReplContext.emit
    load_config = app.load_network_config
    arguments = ['ctk', '--script-engine', 'compiled', '--execute', action.get('source', '')]
    for flag, key in [('--server', 'endpoint'), ('--config-path', 'configPath'),
                      ('--compile-commands', 'compilationDatabase'), ('--lib-dir', 'libraryDirectory')]:
        if request.get(key):
            arguments.extend([flag, request[key]])
    values = {**request['values'], 'FILE': next(iter(request['files']), '')}
    arguments.extend(f'{key}={value}' for key, value in values.items())

    def configuration(*args: Any, **kwargs: Any) -> Any:
        return replace(load_config(*args, **kwargs), rpc_timeout=request['timeoutMs'] / 1000)

    def collect(value: Any) -> None:
        try:
            results.collect(value)
        except Exception as error:
            message = f'Cannot display source result: {error}'
            if message not in errors:
                errors.append(message)

    def runtime_factory(*args: Any, **kwargs: Any) -> Any:
        runtime = factory(*args, cwd=Path(request['directory']), **kwargs)
        runtime.config_store.effective['files'] = request['files']
        runtime.config_store.effective['extra_args'] = request['compileArguments']
        runtime.client._resolved_config = replace(runtime.client._configuration(), rpc_timeout=request['timeoutMs'] / 1000)
        session = runtime._prototype_session
        original_record = session.record

        def record(kind: str, value: Any, **options: Any) -> None:
            # Observe visible values while their native owners remain open.
            # Rendering, output routing and execution stay with the console.
            if runtime.output.destination == 'stdout':
                collect(value)
            original_record(kind, value, **options)

        session.record = record
        return runtime

    def emit(context: Any, value: Any, node: Any = None) -> Any:
        if not context.consume_depth and context.session.runtime.output.destination == 'stdout':
            collect(value)
        return original_emit(context, value, node)

    def script_context(runtime: Any, path: Any) -> Any:
        send(dict(type='progress', file=f'Running {label}', index=0))
        return source_context(runtime, source_path or path)

    # The console owns SIGINT cancellation, resource scopes, onerror/onexit,
    # session commands and client cleanup. Map the worker's stop signal to it.
    previous_term = signal.signal(signal.SIGTERM, lambda *_: os.kill(os.getpid(), signal.SIGINT))
    try:
        with patch.object(sys, 'argv', arguments), patch.object(app, '_runtime_for_engine', runtime_factory), \
             patch.object(app, 'load_network_config', configuration), \
             patch.object(app, 'script_source', script_context), patch.object(_ReplContext, 'emit', emit), \
             redirect_stdout(output), redirect_stderr(output):
            code = asyncio.run(app._run(script_engine_default='compiled'))
        if code:
            errors.append(f'{label}: script cancelled' if code == 130 else f'{label}: script failed (exit {code}); see console output')
    except Exception as error:
        errors.append(f'{label}: {error}')
    finally:
        signal.signal(signal.SIGTERM, previous_term)
    text = output.getvalue().rstrip('\n')
    if output.tell() >= output.limit:
        text += '\n… console output truncated at 2 MiB'
    return dict(results=sorted(results.items, key=lambda item: (item['file'], item['line'], item['column'])),
                errors=errors, output=[text] if text else [], truncated=results.truncated,
                files=len(request['files']))


if __name__ == '__main__':
    protocol = sys.stdout

    def send(event: dict[str, Any]) -> None:
        protocol.write(json.dumps(event, ensure_ascii=False) + '\n')
        protocol.flush()

    try:
        request = json.load(sys.stdin)
        send(dict(type='complete', report=run(request, send)))
    except Exception as error:
        send(dict(type='error', message=str(error)))
