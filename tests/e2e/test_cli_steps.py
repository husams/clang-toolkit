import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from clang_toolkit.cli.app import dispatch
from clang_toolkit.client import Client

pytestmark = pytest.mark.e2e

scenarios("cli.feature")


@given("a CLI connected to the server", target_fixture="client")
def client():
    return Client()


@when(parsers.parse('I enter "{line}"'), target_fixture="output")
def enter(client, line):
    return dispatch(client, line)


@then(parsers.parse('the output contains "{text}"'))
def output_contains(output, text):
    assert text in output
