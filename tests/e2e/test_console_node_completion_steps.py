"""Native prompt completion checks for descriptor-backed node fields."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import to_plain_text
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from pytest_bdd import given, scenarios, then, when

from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.prompt import create_session
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.client import Client
from tests.e2e.test_network_steps import _launch_server

scenarios("console_node_completion.feature")

_PAYLOAD_PATHS = {
    "function_decl": "function_decl.function",
    "cxx_method_decl": "cxx_method_decl.method.function",
    "cxx_constructor_decl": "cxx_constructor_decl.method.function",
    "cxx_destructor_decl": "cxx_destructor_decl.method.function",
    "cxx_conversion_decl": "cxx_conversion_decl.method.function",
    "cxx_deduction_guide_decl": "cxx_deduction_guide_decl.function",
}


async def _wait_for_text(session, expected: str) -> None:
    for _ in range(300):
        if session.default_buffer.text == expected:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(
        f"expected prompt text {expected!r}, got {session.default_buffer.text!r}"
    )


async def _prompt_completions(runtime: Runtime, reference: str) -> dict[str, str]:
    with create_pipe_input() as pipe:
        session = create_session(
            input=pipe,
            output=DummyOutput(),
            references=runtime.completion_references,
            field_resolver=runtime.completion_suggestions,
            presence_resolver=runtime.completion_presence_fields,
        )
        task = asyncio.create_task(session.prompt_async("ctk> "))
        try:
            pipe.send_text(reference)
            await _wait_for_text(session, reference)
            pipe.send_text("\t")
            reset_for_metadata = False
            for _ in range(300):
                state = session.default_buffer.complete_state
                if state is not None and state.original_document.text == reference:
                    return {
                        completion.text: to_plain_text(completion.display_meta)
                        for completion in state.completions
                    }
                if (
                    not reset_for_metadata
                    and session.default_buffer.text != reference
                ):
                    # A unique completion may be inserted directly by Tab. Restore
                    # the typed path and ask the same live prompt buffer for choices.
                    session.default_buffer.set_document(
                        Document(reference), bypass_readonly=True
                    )
                    session.default_buffer.start_completion(select_first=False)
                    reset_for_metadata = True
                await asyncio.sleep(0.01)
            raise AssertionError(
                "Tab did not expose prompt completion metadata; "
                f"text={session.default_buffer.text!r}, "
                f"state={session.default_buffer.complete_state!r}"
            )
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


@given(
    "a private server with native function declarations for completion",
    target_fixture="function_completion_context",
)
def function_completion_context(tmp_path: Path, request):
    server = _launch_server("unix", tmp_path, request)
    source = tmp_path / "function-kinds.cc"
    source.write_text(
        "int forward(int value);\n"
        "int ordinary(int value) { return value; }\n"
        "struct Widget {\n"
        "  Widget() {}\n"
        "  ~Widget() {}\n"
        "  int method(int value) { return value; }\n"
        "  operator int() const { return 0; }\n"
        "  int operator+(int value) const { return value; }\n"
        "};\n"
        "template<class T> struct Box {};\n"
        "Box(int) -> Box<int>;\n",
        encoding="utf-8",
    )
    # The deduction guide is a C++17 feature; keep the native fixture explicit.
    (tmp_path / ".clang_tools.yaml").write_text(
        'extra_args: ["-std=c++20"]\n', encoding="utf-8"
    )
    return server, source, tmp_path


@when(
    "I complete and inspect native function nodes in the real prompt",
    target_fixture="function_completion_result",
)
def explore_native_completion(function_completion_context):
    server, source, tmp_path = function_completion_context
    client = Client(server.endpoint)
    runtime = Runtime(client, cwd=tmp_path, environment={})
    try:
        assert dispatch(client, f'let tree = parse "{source}"', runtime) == ""
        assert (
            dispatch(
                client,
                'let m = match functionDecl(isExpansionInMainFile()).bind("f") in $tree',
                runtime,
            )
            == ""
        )
        rows = runtime.evaluate("$m")
        assert len(rows) >= len(_PAYLOAD_PATHS)

        # Completion runs against local snapshots. A prompt Tab must not send a
        # second parse or match request to the native server.
        with (
            patch.object(client, "parse", wraps=client.parse) as parse_rpc,
            patch.object(client, "match", wraps=client.match) as match_rpc,
        ):
            node_suggestions = {}
            name_suggestions = {}
            presence_suggestions = {}
            presence_fields = {}
            for index in range(len(rows)):
                node_reference = f"$m[{index}].f.value.node"
                node_suggestions[index] = asyncio.run(
                    _prompt_completions(runtime, node_reference + ".")
                )
                name_suggestions[index] = asyncio.run(
                    _prompt_completions(runtime, node_reference + ".name.")
                )
                presence_suggestions[index] = asyncio.run(
                    _prompt_completions(runtime, node_reference + ".hasField(")
                )
                presence_fields[index] = set(
                    runtime.completion_presence_fields(node_reference)
                )
            quoted_presence = {
                quote: asyncio.run(
                    _prompt_completions(
                        runtime, "$m[0].f.value.node.hasField(" + quote
                    )
                )
                for quote in ('"', "'")
            }
            parse_rpc.assert_not_called()
            match_rpc.assert_not_called()

        payload_rows = {}
        path_equalities = {}
        for index in range(len(rows)):
            node_reference = f"$m[{index}].f.value.node"
            payload = next(
                (
                    candidate
                    for candidate in _PAYLOAD_PATHS
                    if runtime.evaluate(
                        f'{node_reference}.hasField("{candidate}")'
                    )
                ),
                None,
            )
            if payload is None:
                continue
            payload_rows[payload] = index
            function_path = _PAYLOAD_PATHS[payload]
            raw_function = runtime.evaluate(
                f"{node_reference}.{function_path}"
            )
            raw_name = runtime.evaluate(
                f"{node_reference}.{function_path}.declarator.value.named.name"
            )
            raw_qualified_name = runtime.evaluate(
                f"{node_reference}.{function_path}.declarator.value.named.qualified_name"
            )
            direct_name = runtime.evaluate(f"{node_reference}.name")
            direct_qualified_name = runtime.evaluate(
                f"{node_reference}.qualified_name"
            )
            direct_return_type = runtime.evaluate(f"{node_reference}.return_type")
            raw_return_type = runtime.evaluate(
                f"{node_reference}.{function_path}.return_type"
            )
            direct_parameters_present = runtime.evaluate(
                f'{node_reference}.hasField("parameters")'
            )
            raw_parameters_present = runtime.evaluate(
                f'{node_reference}.{function_path}.hasField("parameters")'
            )
            direct_body_present = runtime.evaluate(
                f'{node_reference}.hasField("body")'
            )
            raw_body_present = runtime.evaluate(
                f'{node_reference}.{function_path}.hasField("body")'
            )
            assert direct_name._data == raw_name._data
            assert direct_qualified_name == raw_qualified_name
            assert direct_return_type._data == raw_return_type._data
            assert direct_parameters_present is raw_parameters_present is False
            assert direct_body_present is raw_body_present
            path_equalities[index] = {
                "qualified_name": direct_qualified_name,
                "return_type": direct_return_type.descriptor.full_name,
                "return_type_spelling": runtime.evaluate(
                    f"{node_reference}.return_type.description.spelling"
                ),
                "parameters_present": direct_parameters_present,
                "function_body_present": runtime.evaluate(
                    f'{node_reference}.hasField("body")'
                ),
                "typed_name_fields": tuple(
                    candidate
                    for candidate in (
                        "identifier",
                        "constructor_type",
                        "destructor_type",
                        "conversion_type",
                        "overloaded_operator",
                        "deduction_guide_template",
                    )
                    if runtime.evaluate(
                        f'{node_reference}.name.hasField("{candidate}")'
                    )
                ),
                "raw_function": raw_function,
            }

        assert set(payload_rows) == set(_PAYLOAD_PATHS)
        # Resolve the actual row index independently of the payload dictionary.
        forward_row = next(
            index
            for index in range(len(rows))
            if runtime.evaluate(
                f'$m[{index}].f.value.node.hasField("function_decl")'
            )
            and runtime.evaluate(
                f'$m[{index}].f.value.node.qualified_name'
            )
            == "forward"
        )
        absent_body_error = dispatch(
            client,
            f"print $m[{forward_row}].f.value.node.body",
            runtime,
        )
        ordinary_row = next(
            index
            for index in range(len(rows))
            if runtime.evaluate(
                f'$m[{index}].f.value.node.qualified_name'
            ) == "ordinary"
        )
        unrequested_body_error = dispatch(
            client,
            f"print $m[{ordinary_row}].f.value.node.body",
            runtime,
        )
        missing_presence_argument = dispatch(
            client,
            f"print $m[{forward_row}].f.value.node.hasField()",
            runtime,
        )

        # Check a real continuation through the existing native binding selector.
        continuation = dispatch(
            client,
            'let literals = match integerLiteral().bind("n") in $m.f',
            runtime,
        )
        assert continuation == ""
        continued_count = runtime.evaluate("$literals.length")
        return (
            node_suggestions,
            name_suggestions,
            presence_suggestions,
            presence_fields,
            quoted_presence,
            payload_rows,
            path_equalities,
            absent_body_error,
            unrequested_body_error,
            missing_presence_argument,
            continued_count,
        )
    finally:
        runtime.close()
        client.close()


@then(
    "the prompt completes projected fields and preserves typed schema and continuation"
)
def verify_native_completion(function_completion_result):
    (
        node_suggestions,
        name_suggestions,
        presence_suggestions,
        presence_fields,
        quoted_presence,
        payload_rows,
        path_equalities,
        absent_body_error,
        unrequested_body_error,
        missing_presence_argument,
        continued_count,
    ) = function_completion_result

    assert set(payload_rows) == set(_PAYLOAD_PATHS)
    assert any(
        "name" in values
        and "qualified_name" in values
        and "return_type" in values
        and "parameters" not in values
        and "body" not in values
        for values in node_suggestions.values()
    )
    assert all("spelling" not in values for values in node_suggestions.values())
    assert any("identifier" in values for values in name_suggestions.values())
    assert any("conversion_type" in values for values in name_suggestions.values())
    assert any(
        "overloaded_operator" in values for values in name_suggestions.values()
    )

    # The completion is the real, quoted set of fields understood by hasField;
    # it does not fall back to matcher names or dotted path fragments.
    assert presence_suggestions.keys() == presence_fields.keys()
    for index, suggestions in presence_suggestions.items():
        assert suggestions
        assert {text[1:-1] for text in suggestions} == presence_fields[index]
        assert all(text.startswith('"') and text.endswith('"') for text in suggestions)
        assert all(meta == "field presence" for meta in suggestions.values())
        assert '"name"' in suggestions
        assert '"qualified_name"' in suggestions
        assert '"return_type"' in suggestions
        assert '"parameters"' not in suggestions
        assert '"body"' in suggestions
        assert '"function_decl"' in suggestions
        assert '"cxx_deduction_guide_decl"' in suggestions
        assert not any("functionDecl" in text or "." in text for text in suggestions)

    for quote, suggestions in quoted_presence.items():
        assert set(suggestions) == {name + quote for name in presence_fields[0]}

    names = {values["qualified_name"]: values for values in path_equalities.values()}
    assert names["ordinary"]["return_type"].endswith("QualType")
    assert names["ordinary"]["parameters_present"] is False
    assert names["ordinary"]["function_body_present"] is False
    assert names["ordinary"]["return_type_spelling"] == "int"
    assert names["forward"]["function_body_present"] is False
    assert names["Widget::Widget"]["typed_name_fields"] == ("constructor_type",)
    assert names["Widget::~Widget"]["typed_name_fields"] == ("destructor_type",)
    assert names["Widget::operator int"]["typed_name_fields"] == ("conversion_type",)
    assert names["Widget::operator+"]["typed_name_fields"] == ("overloaded_operator",)
    assert path_equalities[payload_rows["cxx_deduction_guide_decl"]]["typed_name_fields"] == ("deduction_guide_template",)
    assert absent_body_error.startswith("error:") and "body" in absent_body_error
    assert unrequested_body_error.startswith("error:") and "body" in unrequested_body_error
    assert "not requested" in unrequested_body_error
    assert 'hasField requires a field name: `hasField("field_name")`' in missing_presence_argument
    assert "line 1, column" in missing_presence_argument
    assert "^" in missing_presence_argument
    assert "matcher call" not in missing_presence_argument
    assert continued_count > 0
