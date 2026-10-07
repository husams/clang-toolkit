"""Run against ctk-server: python examples/parse_match.py example.cc."""

from __future__ import annotations

import argparse
import json

from clang_toolkit import Client, MatchValue


def main() -> None:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("file")
    arguments.add_argument("--server", default=None)
    arguments.add_argument("-c", "--config-path", default=None)
    options = arguments.parse_args()
    client_options = {}
    if options.server is not None:
        client_options["address"] = options.server
    if options.config_path is not None:
        client_options["config_path"] = options.config_path
    with Client(**client_options) as client:
        with client.match('functionDecl(isDefinition()).bind("f")', file=options.file,
                          compile_arguments=["-std=c++23"]) as functions:
            count = len(functions)
            calls = functions.binding("f").match('callExpr().bind("call")')
            if count:
                with functions[0].binding("f").match('callExpr().bind("call")') as first:
                    print(f"first function calls: {len(first)}")
        # Each continuation owns a fresh cursor, so calls survive functions.
        with calls:
            call_count = len(calls)
            with calls.binding("call").match('integerLiteral().bind("n")') as integers:
                print(f"call arguments after parent close: {len(integers)}")
        with client.parse(options.file, compile_arguments=["-std=c++23"]) as tree:
            with tree.match('functionDecl(isDefinition()).bind("f")') as functions2:
                print(f"functions: {count}, functions2: {len(functions2)}, calls: {call_count}")
        client.execute("let tree = parse " + json.dumps(options.file),
                       compile_arguments=["-std=c++23"])
        analysis = client.execute('''in $tree {
            let functions = match functionDecl(isDefinition()).bind("f");
            let calls = match callExpr().bind("call") in $functions.f;
            yield calls;
        }''')
        if not isinstance(analysis, MatchValue):
            raise TypeError("block did not yield live match results")
        print(f"block calls: {len(analysis)}")
        for row in analysis:
            print(row.to_dict())
    # Exiting value/tree and client contexts releases native cursors.


if __name__ == "__main__":
    main()
