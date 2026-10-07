"""Presence, selectors and the formal cursor CLI command surface."""

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest
from lark.exceptions import UnexpectedInput

from clang_toolkit._generated.match.v1 import match_result_pb2 as results
from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.client import Client
from clang_toolkit.cursors import file_request, retained_request


def test_row_zero_and_revision_presence_are_preserved():
    request = retained_request("id", "callExpr()", bind="f", match_index=0,
                               expected_result_revision=1)
    assert request.WhichOneof("target") == "binding"
    assert request.binding.HasField("match_index")
    assert request.binding.match_index == 0
    assert request.binding.expected_result_revision == 1
    assert request.binding.scope == results.BINDING_MATCH_SCOPE_SUBTREE
    unspecified = retained_request("id", "callExpr()", bind="f")
    assert not unspecified.binding.HasField("match_index")
    assert not unspecified.binding.HasField("expected_result_revision")


def test_restart_and_file_requests_keep_compilation_context(tmp_path):
    request = file_request("fixture.cc", "functionDecl()", working_directory=tmp_path,
                           compile_arguments=["-std=c++23", "-Iinclude"])
    assert request.file.working_directory == str(tmp_path)
    assert list(request.file.compile_arguments) == ["-std=c++23", "-Iinclude"]
    assert request.file.file_path == "fixture.cc"
    restart = retained_request("id", "decl()", expected_result_revision=2)
    assert restart.WhichOneof("target") == "session"
    assert restart.session.expected_result_revision == 2
    with pytest.raises(ValueError):
        retained_request("id", "decl()", match_index=0)


def test_cursor_cli_open_continue_restart_and_close(tmp_path):
    client = Mock(spec=Client)
    response = pb.MatchResponse(session_id="id", result_revision=1)
    client.match_file.return_value = response
    client.continue_match.return_value = response
    client.restart_match.return_value = response
    runtime = Runtime(client, cwd=tmp_path)
    output = runtime.execute('cursor open "fixture.cc" functionDecl().bind("f")')
    assert json.loads(output)["session_id"] == "id"
    client.match_file.assert_called_once_with(
        "fixture.cc", 'functionDecl().bind("f")', working_directory=tmp_path,
        compile_arguments=[], traversal_mode=pb.MATCH_TRAVERSAL_MODE_AS_IS,
    )
    runtime.execute('cursor continue "id" "f" callExpr().bind("c") row 0 scope root_only revision 1')
    client.continue_match.assert_called_once_with(
        "id", "f", 'callExpr().bind("c")', match_index=0,
        scope=results.BINDING_MATCH_SCOPE_ROOT_ONLY, expected_result_revision=1,
        traversal_mode=pb.MATCH_TRAVERSAL_MODE_AS_IS,
    )
    runtime.execute('cursor restart "id" varDecl() revision 2')
    client.restart_match.assert_called_once_with(
        "id", "varDecl()", expected_result_revision=2,
        traversal_mode=pb.MATCH_TRAVERSAL_MODE_AS_IS,
    )
    assert runtime.execute('cursor close "id"') == ""
    client.close_match.assert_called_once_with("id")


@pytest.mark.parametrize("command", [
    'cursor continue "id" "f" decl() row -1',
    'cursor continue "id" "f" decl() revision 0',
    'cursor continue "id" "f" decl() row 0 row 1',
    'cursor continue "id" "f" decl() scope invalid',
    'cursor restart "id" decl() row 0',
])
def test_cursor_cli_rejects_invalid_selectors_before_rpc(tmp_path, command):
    client = Mock(spec=Client)
    runtime = Runtime(client, cwd=tmp_path)
    with pytest.raises((EvaluationError, UnexpectedInput)):
        runtime.execute(command)
    assert not client.continue_match.called
    assert not client.restart_match.called


@pytest.mark.parametrize("artifact_flags", [
    ["-include-pch", "build/header.pch"],
    ["-fmodule-file=numbers=build/numbers.pcm"],
])
def test_native_artifact_flags_survive_formal_cli_and_client_requests(tmp_path, artifact_flags):
    client = Mock(spec=Client)
    client.match_file.return_value = pb.MatchResponse(session_id="native", result_revision=1)
    runtime = Runtime(client, cwd=tmp_path)
    flags = ["-std=c++20", *artifact_flags]
    runtime.execute("set extra_args " + json.dumps(flags))
    runtime.execute('cursor open "main.cc" functionDecl().bind("f")')
    assert client.match_file.call_args.kwargs["compile_arguments"] == flags
    request = file_request("main.cc", "functionDecl()", working_directory=tmp_path,
                           compile_arguments=flags)
    assert list(request.file.compile_arguments) == flags
