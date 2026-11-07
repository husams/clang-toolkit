"""Offline CTK front end for the standalone native JIT runner."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import shutil
import subprocess
import sys

from lark import Token, Tree
from lark.exceptions import LarkError

from .jit_cache import (
    Toolchain,
    bundle_object,
    cache_directory,
    cached_prelude,
    precompile,
    write_atomic,
)
from .runtime.prototype.repl_language import parse
from .runtime.prototype.syntax import Node

_ROOT_MATCHERS = {"functionDecl", "cxxMethodDecl"}
_NULLARY_PREDICATES = {"isDefinition", "isExpansionInMainFile", "isImplicit", "isConst"}
_PROJECTIONS = {
    "decl_name": "getNameAsString",
    "qualified_name": "getQualifiedNameAsString",
}
_ENTRY = """
#line 1 "<ctk-jit-entry>"
extern "C" void ctk_jit_run_v1(ctk::jit::RunContext *ctx) {
  run(*ctx);
}
"""


def _unsupported(node: Node | Tree, message: str) -> ValueError:
    location = node if isinstance(node, Node) else node.meta
    return ValueError(f"line {location.line}, column {location.column}: {message}")


def _only_child(node: Node, kind: str, message: str) -> Node:
    if node.kind != kind or len(node.children) != 1:
        raise _unsupported(node, message)
    return node.children[0]


def _host_call(binding: Node, name: str) -> Tree:
    value = _only_child(binding, "let", "expected a let binding")
    if value.kind == "host":
        tree, mode = value.value
        if mode == "expression" and tree.data == name:
            return tree
    raise _unsupported(value, f"expected {name} as the binding value")


def _cpp_string(value: str) -> str:
    if "\0" in value:
        raise ValueError("NUL bytes are unsupported in generated C++ strings")
    encoded = []
    for byte in value.encode("utf-8"):
        if byte in (34, 92):
            encoded.append("\\" + chr(byte))
        elif 32 <= byte < 127:
            encoded.append(chr(byte))
        else:
            encoded.append(f"\\{byte:03o}")
    return '"' + "".join(encoded) + '"'


def _matcher_arguments(matcher: Tree) -> list[Tree | Token | Node]:
    for child in matcher.children:
        if isinstance(child, Tree) and child.data == "arguments":
            return [item for item in child.children if item != ","]
    return []


def _predicate(node: Tree | Token | Node, context: Tree) -> str:
    if not isinstance(node, Tree) or node.data != "matcher":
        raise _unsupported(context, "expected a supported matcher predicate")
    name = str(node.children[0])
    arguments = _matcher_arguments(node)
    if any(isinstance(child, Tree) and child.data == "bind" for child in node.children):
        raise _unsupported(node, "only the outer matcher can bind a node")
    if name in _NULLARY_PREDICATES and not arguments:
        return f"{name}()"
    if name == "unless" and len(arguments) == 1:
        return f"unless({_predicate(arguments[0], node)})"
    if name == "hasName" and len(arguments) == 1:
        token = arguments[0]
        if isinstance(token, Token) and str(token).startswith(('"', "'")):
            return f"hasName({_cpp_string(ast.literal_eval(str(token)))})"
    raise _unsupported(node, f"unsupported matcher predicate or arguments: {name}")


def _matcher_code(matcher: Tree) -> tuple[str, str]:
    name = str(matcher.children[0])
    if name not in _ROOT_MATCHERS:
        raise _unsupported(matcher, f"unsupported outer matcher: {name}")
    for child in matcher.children:
        if isinstance(child, Tree) and child.data == "bind":
            binding = ast.literal_eval(str(child.children[2]))
            predicates = ", ".join(
                _predicate(argument, matcher)
                for argument in _matcher_arguments(matcher)
            )
            return f"{name}({predicates}).bind({_cpp_string(binding)})", binding
    raise _unsupported(matcher, "the outer matcher requires an explicit .bind()")


def _projection(loop: Node, rows: str, binding: str) -> str:
    if loop.kind != "foreach" or len(loop.children) != 2:
        raise _unsupported(loop, "expected foreach over the matched rows")
    collection, block = loop.children
    if collection.kind != "ref" or collection.value != rows:
        raise _unsupported(collection, f"expected foreach over {rows}")
    statement = _only_child(block, "block", "expected one print in foreach")
    field = _only_child(statement, "print", "expected print in foreach")
    message = "expected a bound declaration's decl_name or qualified_name"
    bound = _only_child(field, "get", message)
    row = _only_child(bound, "get", message)
    if row.kind != "ref" or row.value != loop.value or bound.value != binding:
        raise _unsupported(field, message)
    if field.value not in _PROJECTIONS:
        raise _unsupported(field, message)
    return _PROJECTIONS[field.value]


def lower_script(source: str, filename: Path) -> str:
    """Lower the pilot's parse, match and print subset to typed Clang calls."""
    program = parse(source)
    if len(program.children) != 3:
        raise _unsupported(
            program, "expected a parse binding, match binding and foreach"
        )
    target, rows, loop = program.children
    parse_call = _host_call(target, "parse_expression")
    match_call = _host_call(rows, "match")
    if target.value == rows.value:
        raise _unsupported(
            rows, "the target and match bindings must have distinct names"
        )

    match parse_call.children:
        case [_, Node("get", "file", (Node("ref", "arg"),))]:
            pass
        case _:
            raise _unsupported(parse_call, "expected parse arg.file")

    match match_call.children:
        case [_, Tree("matcher") as matcher, "in", Node("ref", name)] if (
            name == target.value
        ):
            matcher_code, binding = _matcher_code(matcher)
        case _:
            raise _unsupported(
                match_call, "expected match ... in the parsed target binding"
            )

    getter = _projection(loop, rows.value, binding)
    return f"""\
#include <ctk/jit/runtime.hpp>
#include <string>
#include <vector>

void run(ctk::jit::RunContext &ctx) {{
  using namespace clang::ast_matchers;
#line {match_call.meta.line} {_cpp_string(str(filename))}
  const auto matcher = {matcher_code};
#line 1 "<ctk-jit>"
  std::vector<std::string> names;
  ctx.match(matcher, [&](const MatchFinder::MatchResult &result) {{
    if (const auto *node = result.Nodes.getNodeAs<clang::FunctionDecl>({_cpp_string(binding)}))
      names.push_back(node->{getter}());
  }});
  for (const auto &name : names)
    ctx.emit_text(name);
}}
"""


def _runner() -> Path | None:
    local = Path(__file__).resolve().parents[3] / "build/jit/ctk-jit-runner"
    if local.is_file():
        return local
    installed = shutil.which("ctk-jit-runner")
    return Path(installed) if installed else None


def _script_input(path: Path) -> tuple[bytes, str]:
    try:
        script = path.resolve()
        source = script.read_text(encoding="utf-8")
        if script.suffix == ".ctk":
            return (lower_script(source, script) + "\n" + _ENTRY).encode("utf-8"), ""
        source = f"#line 1 {_cpp_string(str(script))}\n{source}\n{_ENTRY}"
        return source.encode("utf-8"), str(script.parent)
    except (LarkError, OSError, SyntaxError, ValueError) as error:
        raise ValueError(f"{path}: {error}") from error


def _native_command(args: argparse.Namespace, runner: Path) -> int:
    command = [str(runner)]
    if args.bundle is not None:
        program = bundle_object(args.bundle.read_bytes(), Toolchain.from_runner(runner))
        command.extend(("object", str(args.file), str(args.compdb)))
    else:
        program, quote_dir = _script_input(args.script)
        command.extend(("source", str(args.file), str(args.compdb), quote_dir))
        if args.script.suffix == ".ctk" and not args.no_cache:
            try:
                prelude = cached_prelude(
                    Toolchain.from_runner(runner), cache_directory()
                )
            except (OSError, ValueError):
                prelude = None  # A failed optimization can use source headers.
            if prelude is not None:
                command.append(str(prelude))
    result = subprocess.run(command, input=program, check=False)
    if result.returncode < 0:
        print(
            f"ctk-jit: native runner terminated by signal {-result.returncode}",
            file=sys.stderr,
        )
        return 128 - result.returncode
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a CTK script with Clang JIT")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run source or a precompiled bundle")
    run.add_argument("script", type=Path, nargs="?")
    run.add_argument("--bundle", type=Path, help="run a precompiled bundle")
    run.add_argument("--file", type=Path, required=True, help="target translation unit")
    run.add_argument(
        "--compdb",
        type=Path,
        required=True,
        help="compilation database or its directory",
    )
    build = commands.add_parser("precompile", help="compile source to a local bundle")
    build.add_argument("script", type=Path)
    build.add_argument("--output", "-o", type=Path, required=True)
    for command in (run, build):
        command.add_argument(
            "--runner", type=Path, help="override the native runner executable"
        )
        command.add_argument(
            "--no-cache", action="store_true", help="bypass the local cache"
        )
    args = parser.parse_args(argv)
    if args.command == "run" and (args.script is None) == (args.bundle is None):
        parser.error("provide either a script or --bundle")
    if args.script is not None and args.script.suffix not in {".ctk", ".cpp"}:
        parser.error("expected a .ctk script or .cpp extension")
    if args.command == "precompile" and args.output.resolve() == args.script.resolve():
        parser.error("bundle output must differ from the source script")
    runner = args.runner or _runner()
    if runner is None:
        parser.error("build the native runner in build/jit or specify --runner")
    try:
        runner = runner.resolve()
        if args.command == "run":
            return _native_command(args, runner)
        source, quote_dir = _script_input(args.script)
        cache = None if args.no_cache else cache_directory()
        data = precompile(Toolchain.from_runner(runner), source, quote_dir, cache)
        write_atomic(args.output, data)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"ctk-jit: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
