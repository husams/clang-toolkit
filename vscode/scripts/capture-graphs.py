"""Capture real native graphs for the visual preview; owns its test server."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'vscode' / 'console'))
sys.path.insert(0, str(ROOT / 'python'))
from action_service import ActionHost
from graph_service import graph
from google.protobuf.json_format import MessageToDict


def fixture() -> str:
    common = ['clock_now', 'hash_key', 'increment_counter', 'format_error', 'emit_event', 'trace']
    lines = [f'int {name}(int value) {{ return value + 1; }}' for name in common]
    lines.append('int append_audit(int value) { return ' + ' + '.join(f'{name}(value)' for name in common) + '; }')
    stages = ['validate_customer', 'calculate_totals', 'authorize_payment', 'reserve_stock', 'save_order', 'notify_customer']
    for stage in stages:
        calls = []
        for i in range(12):
            operation = f'{stage}_{i + 1}'
            for suffix in ('input', 'rule', 'result'):
                lines.append(f'int {operation}_{suffix}(int value) {{ return value + 1; }}')
            lines.append(f'int {operation}(int value) {{ return ' + ' + '.join(
                [f'{operation}_{suffix}(value)' for suffix in ('input', 'rule', 'result')]) + '; }')
            calls.append(f'{operation}(value)')
        lines.append(f'int {stage}(int value) {{ return ' + ' + '.join([*calls, 'append_audit(value)']) + '; }')
    lines.append('int submit(int value) {\n  if (value <= 0) return format_error(value);\n  return ' + ' + '.join(f'{stage}(value)' for stage in stages) + ';\n}')
    return '\n'.join(lines) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', required=True)
    parser.add_argument('--output', default=str(ROOT / 'vscode' / 'artifacts' / 'graph-preview'))
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = output / 'orders.cpp'
    source.write_text(fixture())
    with tempfile.TemporaryDirectory(prefix='ctk-graph-', dir='/tmp') as temporary:
        directory = Path(temporary)
        (directory / 'lib').mkdir()
        config = directory / 'server.yaml'
        socket = directory / 'server.sock'
        config.write_text(f'network:\n  transport: unix\n  unix:\n    socket_path: {socket}\n')
        import os
        env = {**os.environ, 'CTK_STORAGE_ROOT': str(directory / 'storage')}
        with (output / 'server.log').open('w') as log:
            server = subprocess.Popen([args.server, '-c', str(config)], stdout=log, stderr=log, env=env)
            host = None
            try:
                deadline = time.monotonic() + 15
                while not socket.exists():
                    if server.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError(f'Preview server did not start; see {output / "server.log"}')
                    time.sleep(0.05)
                settings = dict(directory=str(output), endpoint=f'unix://{socket}',
                                libraryDirectory=str(directory / 'lib'), timeoutMs=30000,
                                compileArguments=['-std=c++20'])
                host = ActionHost(settings)
                root = host.inspector.inspect(dict(settings=settings, translationUnit=str(source)))
                selected = next(n for n in root['children'] if n['name'] == 'submit')
                request = dict(settings=settings, nodeId=selected['id'])
                calls = graph(host, dict(request, kind='callgraph'))
                cfg = graph(host, dict(request, kind='cfg'))
                (output / 'callgraph.json').write_text(json.dumps(calls))
                (output / 'cfg.json').write_text(json.dumps(cfg))
                target, _, _ = host.check_input(selected['id'])
                (output / 'cfg-native.json').write_text(json.dumps(MessageToDict(host.client.cfg(target, projection='recursive', payload_depth=4)), indent=2))
                print(json.dumps(dict(functions=len(calls['nodes']), edges=len(calls['edges']),
                                      blocks=len(cfg['nodes']), parseCount=host.parse_count, output=str(output))))
            finally:
                if host:
                    host.close()
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == '__main__':
    main()
