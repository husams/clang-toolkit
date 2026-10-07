"""Server DSL request bounds and grammar-driven CLI dispatch."""
from __future__ import annotations
import json
from unittest.mock import Mock
import pytest
from clang_toolkit._generated.analysis.v1 import script_response_pb2 as pb
from clang_toolkit.client import Client
from clang_toolkit.scripting import script_request
from clang_toolkit.cli.runtime import Runtime, EvaluationError

def test_script_target_and_step_presence(tmp_path):
    pure = script_request("emit 7;")
    assert not pure.HasField("file") and not pure.HasField("max_steps")
    assert pure.profile.working_directory
    assert not pure.profile.compile_arguments
    profiled = script_request("emit 7;", working_directory=tmp_path,
                              compile_arguments=["-std=c++23"])
    assert not profiled.HasField("file")
    assert profiled.profile.working_directory == str(tmp_path.resolve())
    assert list(profiled.profile.compile_arguments) == ["-std=c++23"]
    native = script_request("emit callgraph();", path="file.cc", working_directory=tmp_path, max_steps=8)
    assert native.file.file_path == "file.cc" and native.max_steps == 8
    assert native.profile.working_directory == str(tmp_path.resolve())
    for steps in (0,10001):
        with pytest.raises(ValueError):
            script_request("",max_steps=steps)
    with pytest.raises(ValueError):
        script_request("λ"*(1024*1024))

def test_cli_runs_pure_script(tmp_path):
    client = Mock(spec=Client)
    response = pb.ScriptResponse(executed_steps=1)
    response.emissions.add().value.scalar.integer = 7
    client.run_script.return_value = response
    output = Runtime(client,cwd=tmp_path).execute('script "emit 7;"')
    assert json.loads(output)["emissions"][0]["value"]["scalar"]["integer"] == "7"
    client.run_script.assert_called_once_with("emit 7;", working_directory=tmp_path,
                                              compile_arguments=[])

def test_cli_runs_native_script_with_target(tmp_path):
    client = Mock(spec=Client)
    client.run_script.return_value = pb.ScriptResponse()
    Runtime(client,cwd=tmp_path).execute('script "emit cfg(\\\"f\\\");" in "file.cc"')
    client.run_script.assert_called_once_with('emit cfg("f");',path="file.cc",
        working_directory=tmp_path,compile_arguments=[])

def test_cli_rejects_non_string_before_dispatch(tmp_path):
    client = Mock(spec=Client)
    with pytest.raises(EvaluationError):
        Runtime(client,cwd=tmp_path).execute("script 7")
    client.run_script.assert_not_called()
