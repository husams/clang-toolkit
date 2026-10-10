from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.language import parser
from clang_toolkit.client import Client

scenarios("console_file_batches.feature")


@given(
    "an offline console client for file resource help", target_fixture="offline_client"
)
def offline_client() -> Client:
    return Client("unix:///tmp/ctk-file-resource-help-no-server.sock")


@when(parsers.parse('I request console help for "{topic}"'), target_fixture="help_text")
def request_help(offline_client: Client, topic: str) -> str:
    return dispatch(offline_client, f"help {topic}") or ""


@then(parsers.parse('the help output includes "{expected}"'))
def help_includes(help_text: str, expected: str) -> None:
    assert expected in help_text


@given("the file resource console grammar", target_fixture="grammar")
def resource_grammar():
    return parser()


@when("I parse the supported resource statements", target_fixture="parsed_commands")
def parse_resource_commands(grammar):
    statements = (
        ('let inputs = files "src/"', "assignment"),
        ('file open "src/a.cpp" into $source', "file_open"),
        ("file list", "file_list"),
        ("resource status", "resource_status"),
        ("batch part in $inputs size 10 do { print $part.index; }", "batch_statement"),
    )
    return [
        (grammar.parse(source).children[0].data, expected)
        for source, expected in statements
    ]


@then("each statement has its expected command node")
def resource_command_shapes(parsed_commands) -> None:
    assert all(actual == expected for actual, expected in parsed_commands)
