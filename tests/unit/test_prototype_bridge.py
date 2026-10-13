from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from clang_toolkit.cli.runtime.prototype import ExecutionResult, run_source
from clang_toolkit.cli.runtime.prototype.bridge import ctk_function
from clang_toolkit.cli.runtime.prototype.semantics import Node


def test_run_source_uses_fresh_context_and_returns_observable_state(monkeypatch):
    import clang_toolkit.cli.runtime.prototype as prototype

    program = Node(
        "program",
        children=(
            Node("let", "value", (Node("literal", 4),)),
            Node("print", children=(Node("ref", "value"),)),
        ),
    )
    monkeypatch.setattr(prototype, "parse", lambda source: program)
    supplied = {"original": 9}

    result = run_source("ignored", engine="tree", bindings=supplied)

    assert result == ExecutionResult(4, {"original": 9, "value": 4}, [4], result.steps)
    assert supplied == {"original": 9}
    assert result.output == [4]
    with pytest.raises(FrozenInstanceError):
        result.value = 5


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_run_source_supports_both_engines(monkeypatch, engine):
    import clang_toolkit.cli.runtime.prototype as prototype

    program = Node("program", children=(Node("literal", 7),))
    monkeypatch.setattr(prototype, "parse", lambda source: program)

    result = run_source("ignored", engine=engine)

    assert result.value == 7
    assert result.bindings == {}
    assert result.output == []
    assert result.steps > 0


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_run_source_uses_the_real_parser_and_host_registry(engine):
    calls = []

    def host(value):
        calls.append(value)
        return value + 1

    result = run_source(
        "let safe = false and host(1)\nlet answer = 6 * 2 + host(2)\nprint $answer",
        engine=engine,
        functions={"host": host},
    )

    assert result.value == 15
    assert result.bindings["safe"] is False
    assert result.output == [15]
    assert calls == [2]


def test_run_source_rejects_unknown_engine_before_parsing(monkeypatch):
    import clang_toolkit.cli.runtime.prototype as prototype

    parse_calls = []
    monkeypatch.setattr(prototype, "parse", lambda source: parse_calls.append(source))

    with pytest.raises(ValueError, match="unknown prototype engine"):
        run_source("ignored", engine="python")
    assert parse_calls == []


def test_run_source_validates_source():
    with pytest.raises(TypeError, match="source must be a string"):
        run_source(42)  # type: ignore[arg-type]


def test_ctk_function_delegates_once_and_preserves_typed_value():
    typed_value = object()

    class FakeRuntime:
        def __init__(self):
            self.calls = []

        def evaluate(self, source):
            self.calls.append(source)
            return typed_value

    runtime = FakeRuntime()
    function = ctk_function(runtime)

    assert function("status") is typed_value
    assert runtime.calls == ["status"]


def test_ctk_function_rejects_non_string_and_invalid_runtime():
    class FakeRuntime:
        def evaluate(self, source):
            return source

    with pytest.raises(TypeError, match="ctk expression must be a string"):
        ctk_function(FakeRuntime())(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="callable evaluate"):
        ctk_function(object())  # type: ignore[arg-type]
