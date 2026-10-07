"""Expected Pyright failures for misspelled options and invalid option values."""

from clang_toolkit import Client


def invalid_usage(client: Client) -> None:
    tree = client.parse("example.cc", compile_argumemts=["-std=c++23"])
    tree.match("functionDecl()", traversal_mode="invalid")
    client.match_in("functionDecl()", "example.cc", compile_arguments=[23])
    client.match_in("functionDecl()", "example.cc", traversal_mode="invalid")
