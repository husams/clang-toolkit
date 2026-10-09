"""Real console graph composition, projection and scope coverage."""
from pathlib import Path
import os
import subprocess
import sys

import pytest
from pytest_bdd import given, scenarios, when, then
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios('reasoning_graphs.feature')


@given('a private server and a graph fixture with a header call', target_fixture='reasoning_graph_fixture')
def graph_fixture(tmp_path: Path, request):
    server = _launch_server('unix', tmp_path, request)
    (tmp_path/'common.hpp').write_text('inline int header_fn(){return 7;}\n')
    source = tmp_path/'main.cc'
    source.write_text('#include "common.hpp"\nint main(){return header_fn();}\n')
    return server, source, tmp_path


@when('I inspect composable graph values through the console', target_fixture='reasoning_graph_run')
def inspect_graphs(reasoning_graph_fixture):
    server, source, directory = reasoning_graph_fixture
    script = '\n'.join([
        f'let tree = traverse "{source}" depth 1 projection shallow main-file true',
        'print "DEPTH_NODES=${tree.nodes.length}"',
        'print "DEPTH_LIMITED=${tree.depth_limited}"',
        'let depths = foreach $node in $tree.nodes do $node.depth done',
        'print "DEPTHS=${depths.joinWith(\'|\')}"',
        f'let calls = callgraph "{source}" main-file true projection shallow',
        'print "CALL_NODES=${calls.nodes.length}"',
        'print "SCOPE=${calls.main_file_only}"',
        'print "OMITTED=${calls.external_edges_omitted}"',
        f'let flows = cfg main in "{source}" projection shallow',
        'print "FLOW_COUNT=${flows.graphs.length}"',
        'print "FLOW_NAME=${flows.graphs[0].function.qualified_name}"',
        'print "FLOW_ENTRY=${flows.graphs[0].entry_block}"',
    ])
    return subprocess.run([sys.executable, '-m', 'clang_toolkit.cli.app', '--server', server.endpoint, '-e', script], cwd=directory, env=dict(os.environ,XDG_STATE_HOME=str(directory/'state')), capture_output=True, text=True, timeout=45)


@then('graph fields are typed and header omissions are explicit')
def typed_graphs(reasoning_graph_run):
    run = reasoning_graph_run
    assert run.returncode == 0, run.stdout+run.stderr
    assert 'DEPTH_NODES=2' in run.stdout
    assert 'DEPTH_LIMITED=true' in run.stdout
    assert 'DEPTHS=0|1' in run.stdout
    assert 'CALL_NODES=2' in run.stdout
    assert 'SCOPE=true' in run.stdout
    omitted = [line.removeprefix('OMITTED=') for line in run.stdout.splitlines() if line.startswith('OMITTED=')]
    assert omitted and int(omitted[0]) > 0
    assert 'FLOW_COUNT=1' in run.stdout and 'FLOW_NAME=main' in run.stdout
    assert 'ctk>' not in run.stdout
