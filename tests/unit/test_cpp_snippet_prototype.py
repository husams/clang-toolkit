"""Temporary C++ snippets in the active tree and compiled consoles."""

from __future__ import annotations

import pytest
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.repl_editor import (
    PrototypeCompleter,
    highlight,
    input_state,
    lex,
)
from clang_toolkit.cli.runtime.prototype.repl_language import parse
from clang_toolkit.client import Client


def test_cpp_snippet_remains_one_raw_host_expression() -> None:
    body = '\n    const char *text = "${unbound} # }";\n    // }\n    int n = 1;\n'
    program = parse(f'let tree = parse cpp`{body}` using "src/example.cpp"')
    assignment = program.children[0]
    assert assignment.kind == "let"
    expression = assignment.children[0]
    assert expression.kind == "host"
    tree, mode = expression.value
    assert mode == "expression"
    assert tree.data == "parse_cpp_expression"
    source = next(token for token in tree.children if getattr(token, "type", "") == "CPP_SOURCE")
    assert str(source) == f"cpp`{body}`"


@pytest.mark.parametrize("engine", ["tree", "compiled"])
@pytest.mark.parametrize("using", [
    "",
    ' using "src/example.cpp"',
    ' using options',
    ' using {file: "src/example.cpp", includes: ["sample.hpp"], compile_arguments: ["-DMODE=1"]}',
    ' using {\n file: "src/example.cpp",\n includes: ["sample.hpp"],\n compile_arguments: ["-DMODE=1"]\n}',
])
def test_active_console_dispatches_raw_cpp_to_sdk(monkeypatch, tmp_path, engine, using) -> None:
    client = Client()
    calls = []
    sentinel = object()

    def parse_cpp(code: str, **options):
        calls.append((code, options))
        return sentinel

    monkeypatch.setattr(client, "parse_cpp", parse_cpp)
    runtime = PrototypeRuntime(client, script_engine=engine, cwd=tmp_path, environment={})
    runtime.bindings["options"] = {"file": "src/example.cpp", "includes": ["sample.hpp"]}
    body = '\nconst char *text = "${unbound} # }";\n// }\nint n = 1;\n'
    try:
        result = dispatch_result(client, f"let tree = parse cpp`{body}`{using}", runtime)
        assert result.success, result.output
        assert runtime.bindings["tree"] is sentinel
        assert len(calls) == 1
        assert calls[0][0] == body
        assert calls[0][1]["working_directory"] == tmp_path
        if using:
            assert calls[0][1]["file"] == "src/example.cpp"
        if "options" in using or "includes:" in using:
            assert calls[0][1]["includes"] == ["sample.hpp"]
    finally:
        runtime.close()
        client.close()


def test_cpp_multiline_editor_ignores_host_syntax_inside_raw_source() -> None:
    open_source = 'let tree = parse cpp`\n// } ) ]\nconst char *s = "${missing}";\n'
    state = input_state(open_source)
    assert state.needs_more
    assert state.open_string
    assert state.error_at is None
    source = open_source + "`"
    state = input_state(source)
    assert not state.needs_more
    assert state.error_at is None
    assert "".join(str(token) for token in lex(source)) == source
    assert "".join(text for _, text in highlight(source)) == source
    assert any(style == "class:string" and text.startswith("cpp`") for style, text in highlight(source))


def test_cpp_body_does_not_receive_ctk_completions() -> None:
    class HostCompleter(Completer):
        def get_completions(self, document, complete_event):
            yield Completion("functionDecl")

    completer = PrototypeCompleter(HostCompleter())
    for source in ["let tree = parse cpp`\nif", "let tree = parse cpp`\nif\n`"]:
        cursor = len(source) if not source.endswith("`") else len(source) - 2
        assert list(completer.get_completions(Document(source, cursor), CompleteEvent())) == []
