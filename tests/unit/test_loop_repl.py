from __future__ import annotations

from unittest.mock import Mock

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.repl_editor import (
    PrototypeCompleter, PrototypeReplLexer, input_state, lex,
)


@pytest.fixture(params=['tree', 'compiled'])
def runtime(request, tmp_path):
    instance = PrototypeRuntime(Mock(), script_engine=request.param,
                                cwd=tmp_path, environment={})
    yield instance
    instance.close()


def submit(runtime, source):
    result = dispatch_result(runtime.client, source, runtime)
    assert result.success, result.output
    assert runtime._scopes == []
    return result.output


def test_page_examples_and_collected_values(runtime):
    assert submit(runtime, 'let x = 13; while x > 10 do { print x; x -= 1 }; print x') == '13\n12\n11\n10'
    assert submit(runtime, 'let x = 13; while x > 10 do x -= 1; print x') == '10'
    assert submit(runtime, 'let x = 0; repeat { x += 1; print x } until x >= 3') == '1\n2\n3'
    assert submit(runtime, 'let x = 0; repeat x += 1 until x >= 3; print x') == '3'
    assert submit(runtime, 'let x = 0; let samples = repeat { x += 1; print "silent"; x } until x >= 3') == ''
    assert runtime.bindings['samples'] == [1, 2, 3]
    assert submit(runtime, 'let names = ["alpha", "beta"]; let numbered = foreach index, name in names do ({index: index, name: name})') == ''
    assert runtime.bindings['numbered'] == [{"index": 0, "name": "alpha"}, {"index": 1, "name": "beta"}]


def test_standalone_body_values_display_without_aggregate(runtime):
    assert submit(runtime, 'let x = 0; while x < 3 do { x += 1; x }') == '1\n2\n3'
    assert submit(runtime, 'let x = 0; repeat { x += 1; x } until x >= 3') == '1\n2\n3'
    assert submit(runtime, 'while false do 9') == ''


def test_repeat_continue_terminates_and_keeps_explicit_effects(runtime):
    assert submit(runtime, 'let attempts = 0; repeat { attempts += 1; if attempts < 3 then continue; print "finished" } until attempts >= 3') == 'finished'
    assert runtime.bindings['attempts'] == 3
    assert submit(runtime, 'repeat { print "once"; continue } until true') == 'once'


def test_loop_error_recovery_does_not_leave_scopes(runtime):
    assert submit(runtime, 'let saved = 99; let x = 0') == ''
    result = dispatch_result(runtime.client, 'saved = repeat { x += 1; 1 / 0 } until true', runtime)
    assert not result.success and 'division by zero' in result.output
    assert runtime.bindings['saved'] == 99 and runtime.bindings['x'] == 1
    assert submit(runtime, 'print x') == '1'


def test_foreground_batch_is_a_control_boundary(runtime):
    source = 'print "unreachable"; while true do { batch group in files size 1 do { continue }; break }'
    result = dispatch_result(runtime.client, source, runtime)
    assert not result.success and 'requires an enclosing' in result.output
    assert 'unreachable' not in result.output


@pytest.mark.parametrize('source, incomplete', [
    ('while true do', True),
    ('repeat { 1 }', True),
    ('repeat 1 until', True),
    ('repeat { 1 }\nuntil true', False),
    ('while false do {}', False),
])
def test_loop_editor_multiline_and_lossless_tokens(source, incomplete):
    assert ''.join(str(token) for token in lex(source)) == source
    assert input_state(source).needs_more == incomplete


def test_loop_completion_and_highlighting():
    completer = PrototypeCompleter(ReplCompleter())
    for partial, expected in [('whi', 'while'), ('rep', 'repeat'), ('unt', 'until')]:
        assert expected in {item.text for item in completer.get_completions(Document(partial), CompleteEvent())}
    highlight = PrototypeReplLexer().lex_document(Document('repeat { break } until true'))
    assert all(style == 'class:keyword' for style, text in highlight(0) if text in {'repeat', 'until', 'break'})


@pytest.mark.parametrize('topic', ['loops', 'foreach', 'while', 'repeat', 'break', 'continue'])
def test_loop_help(runtime, topic):
    output = submit(runtime, 'help '+topic)
    assert 'foreach index, item in items' in output
    assert 'repeat' in output and 'until' in output
    assert '$' not in output
