"""Offline CTK front end for the standalone native JIT runner."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys

from lark import Token, Tree
from lark import __version__ as lark_version
from lark.exceptions import LarkError

from .jit_cache import (
    Toolchain,
    bundle_object,
    cache_directory,
    cached_script_bundle,
    precompile,
    write_atomic,
)
from .jit_language import LanguageIR
from .jit_repl import run_repl
from .runtime.prototype.repl_language import parse
from .runtime.prototype.syntax import Node

_ROOT_MATCHERS = {"functionDecl", "cxxMethodDecl"}
_NULLARY_PREDICATES = {"isDefinition", "isExpansionInMainFile", "isImplicit", "isConst"}
_PROJECTIONS = {
    "decl_name": "getNameAsString",
    "qualified_name": "getQualifiedNameAsString",
}
_CLI_DIRECTORY = Path(__file__).parent
_PARSER_DIRECTORY = _CLI_DIRECTORY / "runtime/prototype"
_FRONTEND_FILES = (
    Path(__file__),
    _CLI_DIRECTORY / "jit_cache.py",
    _CLI_DIRECTORY / "jit_dependencies.py",
    _CLI_DIRECTORY / "jit_language.py",
    _CLI_DIRECTORY / "grammar.lark",
    _CLI_DIRECTORY / "language.py",
    _CLI_DIRECTORY / "runtime/templates.py",
    _CLI_DIRECTORY / "runtime/cpp_snippet.py",
    _CLI_DIRECTORY / "matcher_catalog.py",
    _CLI_DIRECTORY / "_matcher_catalog_generated.py",
    *(
        _PARSER_DIRECTORY / name
        for name in ("grammar.lark", "repl_language.py", "syntax.py", "patterns.py")
    ),
)
_ENTRY = """
#line 1 "<ctk-jit-entry>"
extern "C" void ctk_jit_run_v1(ctk::jit::RunContext *ctx) {
  run(*ctx);
}
"""


@dataclass(frozen=True)
class Matcher:
    name: str
    arguments: tuple[Matcher | str, ...]


@dataclass(frozen=True)
class Query:
    matcher: Matcher
    binding: str
    projection: str
    match_line: int


def _unsupported(node: Node | Tree, message: str) -> ValueError:
    location = node if isinstance(node, Node) else node.meta
    return ValueError(f"line {location.line}, column {location.column}: {message}")


def _only_child(node: Node, kind: str, message: str) -> Node:
    if node.kind != kind or len(node.children) != 1:
        raise _unsupported(node, message)
    return node.children[0]


def _host_call(binding: Node, name: str | None = None) -> Tree:
    value = _only_child(binding, "let", "expected a let binding")
    if value.kind == "host":
        tree, mode = value.value
        if mode == "expression" and (name is None or tree.data == name):
            return tree
    raise _unsupported(
        value, f"expected {name or 'parse or match'} as the binding value"
    )


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


def _predicate(node: Tree | Token | Node, context: Tree) -> Matcher:
    if not isinstance(node, Tree) or node.data != "matcher":
        raise _unsupported(context, "expected a supported matcher predicate")
    name = str(node.children[0])
    arguments = _matcher_arguments(node)
    if any(isinstance(child, Tree) and child.data == "bind" for child in node.children):
        raise _unsupported(node, "only the outer matcher can bind a node")
    if name in _NULLARY_PREDICATES and not arguments:
        return Matcher(name, ())
    if name == "unless" and len(arguments) == 1:
        return Matcher(name, (_predicate(arguments[0], node),))
    if name == "hasName" and len(arguments) == 1:
        token = arguments[0]
        if isinstance(token, Token) and str(token).startswith(('"', "'")):
            return Matcher(name, (ast.literal_eval(str(token)),))
    raise _unsupported(node, f"unsupported matcher predicate or arguments: {name}")


def _parse_matcher(matcher: Tree) -> tuple[Matcher, str]:
    name = str(matcher.children[0])
    if name not in _ROOT_MATCHERS:
        raise _unsupported(matcher, f"unsupported outer matcher: {name}")
    for child in matcher.children:
        if isinstance(child, Tree) and child.data == "bind":
            binding = ast.literal_eval(str(child.children[2]))
            predicates = tuple(
                _predicate(argument, matcher)
                for argument in _matcher_arguments(matcher)
            )
            return Matcher(name, predicates), binding
    raise _unsupported(matcher, "the outer matcher requires an explicit .bind()")


def _projection(
    loop: Node, rows: str | None = None, binding: str | None = None
) -> tuple[str, str, str]:
    if loop.kind != "foreach" or len(loop.children) != 2:
        raise _unsupported(loop, "expected foreach over the matched rows")
    collection, block = loop.children
    if collection.kind != "ref" or (rows is not None and collection.value != rows):
        raise _unsupported(
            collection, f"expected foreach over {rows or 'a match binding'}"
        )
    statement = _only_child(block, "block", "expected one print in foreach")
    field = _only_child(statement, "print", "expected print in foreach")
    message = "expected a bound declaration's decl_name or qualified_name"
    bound = _only_child(field, "get", message)
    row = _only_child(bound, "get", message)
    if (
        row.kind != "ref"
        or row.value != loop.value
        or (binding is not None and bound.value != binding)
    ):
        raise _unsupported(field, message)
    if field.value not in _PROJECTIONS:
        raise _unsupported(field, message)
    return collection.value, bound.value, field.value


def _validate_target(call: Tree) -> None:
    match call.children:
        case [_, Node("get", "file", (Node("ref", "arg"),))]:
            return
    raise _unsupported(call, "expected parse arg.file")


def _match_target(call: Tree, expected: str | None = None) -> tuple[Matcher, str, str]:
    match call.children:
        case [_, Tree("matcher") as matcher, "in", Node("ref", name)] if (
            expected is None or name == expected
        ):
            root, binding = _parse_matcher(matcher)
            return root, binding, name
    raise _unsupported(call, "expected match ... in the parsed target binding")


def _parse_query(program: Node) -> Query:
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

    _validate_target(parse_call)
    root, binding, _ = _match_target(match_call, target.value)
    _, _, projection = _projection(loop, rows.value, binding)
    return Query(root, binding, projection, match_call.meta.line)


def _cpp_matcher(matcher: Matcher) -> str:
    arguments = ", ".join(
        _cpp_string(arg) if isinstance(arg, str) else _cpp_matcher(arg)
        for arg in matcher.arguments
    )
    return f"{matcher.name}({arguments})"


def lower_script(source: str, filename: Path) -> str:
    """Lower the pilot's parse, match and print subset to typed Clang calls."""
    query = _parse_query(parse(source))
    binding = _cpp_string(query.binding)
    getter = _PROJECTIONS[query.projection]
    return f"""\
#include <ctk/jit/runtime.hpp>
#include <string>
#include <vector>

void run(ctk::jit::RunContext &ctx) {{
  using namespace clang::ast_matchers;
#line {query.match_line} {_cpp_string(str(filename))}
  const auto matcher = {_cpp_matcher(query.matcher)}.bind({binding});
#line 1 "<ctk-jit>"
  std::vector<std::string> names;
  ctx.match(matcher, [&](const MatchFinder::MatchResult &result) {{
    if (const auto *node = result.Nodes.getNodeAs<clang::FunctionDecl>({binding}))
      names.push_back(node->{getter}());
  }});
  for (const auto &name : names)
    ctx.emit_text(name);
}}
"""


class _IrConstants:
    def __init__(self) -> None:
        self.definitions: list[str] = []

    def constant(self, value: str) -> str:
        symbol = f"@.ctk.{len(self.definitions)}"
        self.definitions.append(f"{symbol} = private unnamed_addr constant {value}")
        return symbol

    def string(self, value: str) -> str:
        data = value.encode("utf-8") + b"\0"
        escaped = "".join(f"\\{byte:02X}" for byte in data)
        return self.constant(f'[{len(data)} x i8] c"{escaped}"')

    def argument(self, value: Matcher | str) -> str:
        if isinstance(value, str):
            return f"%arg {{ ptr null, ptr {self.string(value)}, ptr null, i32 0 }}"
        name = self.string(value.name)
        children = [self.argument(child) for child in value.arguments]
        count = len(children)
        args = (
            self.constant(f"[{count} x %arg] [{', '.join(children)}]")
            if count
            else "null"
        )
        return f"%arg {{ ptr {name}, ptr null, ptr {args}, i32 {count} }}"


def _ir_module(constants: _IrConstants, declarations: str, body: str) -> str:
    data = "\n".join(constants.definitions)
    return f"""\
%arg = type {{ ptr, ptr, ptr, i32 }}
{data}

{declarations}

define i32 @ctk_jit_run_ir_v1(ptr %context) {{
entry:
{body}
}}
"""


def _ir_loop(setup: str, emit: str) -> str:
    return f"""\
  %status = {setup}
  %failed = icmp ne i32 %status, 0
  br i1 %failed, label %done, label %next

next:
  %decl = call ptr @ctk_jit_next_row_v1(ptr %context)
  %end = icmp eq ptr %decl, null
  br i1 %end, label %done, label %print

print:
  {emit}
  br label %next

done:
  ret i32 %status"""


def _ir_call(name: str, *arguments: str) -> tuple[str, str]:
    operands = ", ".join(f"ptr {argument}" for argument in ("%context", *arguments))
    types = ", ".join(["ptr"] * (len(arguments) + 1))
    return f"declare i32 @{name}({types})", f"call i32 @{name}({operands})"


def lower_ir(source: str) -> str:
    """Emit LLVM assembly for a complete one-shot query."""
    program = parse(source)
    try:
        query = _parse_query(program)
    except ValueError:
        return _lower_language(program)
    constants = _IrConstants()
    matcher = constants.constant(constants.argument(query.matcher))
    binding = constants.string(query.binding)
    declaration, setup = _ir_call("ctk_jit_match_v1", matcher, binding)
    printer = f"ctk_jit_print_{query.projection}_v1"
    return _ir_module(
        constants,
        f"{declaration}\ndeclare ptr @ctk_jit_next_row_v1(ptr)\ndeclare void @{printer}(ptr)",
        _ir_loop(setup, f"call void @{printer}(ptr %decl)"),
    )


def _lower_host(ir: LanguageIR, node: Node) -> str:
    tree, mode = node.value
    if tree.data == "parse_expression":
        return ir.call(
            "ctk_jit_parse_v1",
            "ptr",
            ("ptr", "%context"),
            ("ptr", _host_value(ir, tree.children[1])),
        )
    if tree.data == "parse_cpp_expression":
        from .runtime.cpp_snippet import source_text

        code = ir.literal(source_text(str(tree.children[1])))
        options = (
            _host_value(ir, tree.children[3]) if len(tree.children) > 3 else "null"
        )
        return ir.call(
            "ctk_jit_parse_cpp_v1",
            "ptr",
            ("ptr", "%context"),
            ("ptr", code),
            ("ptr", options),
        )
    if tree.data == "matcher_definition":
        _, name, _, *parameters, _, _, matcher = tree.children
        names = (
            tuple(str(item) for item in parameters[0].children if item != ",")
            if parameters
            else ()
        )
        body = Node("block", children=(Node("host", (matcher, "expression")),))
        return ir.runnable(
            Node("runnable", (str(name), names), (body,), node.line, node.column)
        )
    if tree.data == "match":
        match tree.children:
            case [_, matcher]:
                target = "null"
            case [_, matcher, "in", selection]:
                target = _host_value(ir, selection)
            case _:
                raise _unsupported(node, "unsupported standalone match options")
        rows = ir.call(
            "ctk_jit_match_value_v1",
            "ptr",
            ("ptr", "%context"),
            ("ptr", _host_value(ir, matcher)),
            ("ptr", target),
        )
        if mode == "statement":
            ir.native("print", "void", ("ptr", rows))
        return rows
    if tree.data == "push_command":
        _, base, _, value = tree.children
        return _host_method(ir, _host_value(ir, base), "push", [value])
    if tree.data == "pop_expression":
        return _host_method(ir, _host_value(ir, tree.children[1]), "pop", [])
    if tree.data in {"split_expression", "join_expression", "flatten_expression"}:
        if tree.data == "flatten_expression":
            name, items = "flatten", tree.children[2:3]
        else:
            name = "split_by" if tree.data == "split_expression" else "join"
            items = tree.children[1::2]
        arguments = _host_arguments(ir, items)
        return ir.value("call", ir.string(name), arguments, ir.collection(2))
    if tree.data in {"display", "matcher", "reference"}:
        return _host_value(ir, tree)
    raise _unsupported(node, f"unsupported standalone CTK command {tree.data!r}")


def _host_arguments(ir: LanguageIR, items: list[Node | Tree | Token]) -> str:
    result = ir.collection(0)
    for item in items:
        if item != ",":
            ir.value("add", result, "null", _host_value(ir, item))
    return result


def _host_method(
    ir: LanguageIR, base: str, name: str, items: list[Node | Tree | Token]
) -> str:
    if name == "bind" and len(items) == 1:
        return ir.value("bind_matcher", base, _host_value(ir, items[0]))
    return ir.value("method", base, ir.string(name), _host_arguments(ir, items))


def _host_value(ir: LanguageIR, item: Node | Tree | Token) -> str:
    if isinstance(item, Node):
        return ir.expression(item)
    if isinstance(item, Token):
        if item.type in {"STRING", "FILE_STRING", "NUMBER", "NEGATIVE_NUMBER"}:
            if item.type == "STRING":
                from .runtime.templates import string_parts

                parts = [
                    ir.literal(part)
                    if isinstance(part, str)
                    else ir.value("render", _host_value(ir, part))
                    for part in string_parts(str(item))
                ]
                if not parts:
                    return ir.literal("")
                result, *rest = parts
                for value in rest:
                    result = ir.value("binary", ir.string("+"), result, value)
                return result
            return ir.literal(ast.literal_eval(str(item)))
        raise ValueError(f"unsupported standalone CTK token {item.type!r}")
    if item.data in {"true", "false"}:
        return ir.literal(item.data == "true")
    if item.data == "display":
        return _host_value(ir, item.children[0])
    if item.data == "reference":
        _, name, *access = item.children
        result = ir.value("lookup", ir.string(str(name)))
        while access:
            sep, part, *access = access
            if sep == "[":
                result = ir.value("index", result, _host_value(ir, part))
                access.pop(0)
            elif isinstance(part, Token):
                result = ir.value("get", result, ir.string(str(part)), "null")
            elif part.data == "generic_method_call":
                name = str(part.children[0].children[0])
                arguments = next(
                    (
                        child.children
                        for child in part.children
                        if isinstance(child, Tree) and child.data == "method_arguments"
                    ),
                    [],
                )
                result = _host_method(ir, result, name, arguments)
            elif part.data in {"has_field_call", "has_key_call"}:
                name = "hasField" if part.data == "has_field_call" else "hasKey"
                result = _host_method(ir, result, name, [part.children[2]])
            else:
                raise _unsupported(part, "unsupported standalone CTK reference method")
        return result
    if item.data == "dict_value":
        result = ir.collection(2)
        for entry in item.children:
            if not isinstance(entry, Tree) or entry.data != "dict_entry":
                continue
            key, _, value = entry.children
            name = ast.literal_eval(str(key)) if key.type == "STRING" else str(key)
            ir.value("add", result, ir.literal(name), _host_value(ir, value))
        return result
    if item.data == "matcher":
        args = ir.collection(0)
        for argument in _matcher_arguments(item):
            ir.value("add", args, "null", _host_value(ir, argument))
        binding = next(
            (
                _host_value(ir, child.children[2])
                for child in item.children
                if isinstance(child, Tree) and child.data == "bind"
            ),
            "null",
        )
        return ir.value("matcher", ir.string(str(item.children[0])), args, binding)
    if item.data == "nested_qualified_name":
        return ir.literal("".join(str(child) for child in item.children))
    raise _unsupported(item, f"unsupported standalone CTK value {item.data!r}")


def _lower_language(program: Node, *, display: bool = False) -> str:
    constants = _IrConstants()
    declarations, body = LanguageIR(
        constants.string, constants.constant, _lower_host
    ).program(program, display=display)
    return _ir_module(constants, declarations, body)


def lower_repl(source: str) -> str | None:
    """Lower CTK against the runner's retained AST and session bindings."""
    program = parse(source)
    return _lower_language(program, display=True) if program.children else None


def _runner() -> Path | None:
    local = Path(__file__).resolve().parents[3] / "build/jit/ctk-jit-runner"
    if local.is_file():
        return local
    installed = shutil.which("ctk-jit-runner")
    return Path(installed) if installed else None


def _script_input(
    path: Path, contents: bytes | None = None, *, llvm_ir: bool = False
) -> tuple[bytes, str]:
    try:
        script = path.resolve()
        source = (script.read_bytes() if contents is None else contents).decode("utf-8")
        source = source.replace("\r\n", "\n").replace("\r", "\n")
        if script.suffix == ".ctk":
            if llvm_ir:
                return lower_ir(source).encode("utf-8"), ""
            return (lower_script(source, script) + "\n" + _ENTRY).encode("utf-8"), ""
        source = f"#line 1 {_cpp_string(str(script))}\n{source}\n{_ENTRY}"
        return source.encode("utf-8"), str(script.parent)
    except (LarkError, OSError, SyntaxError, ValueError) as error:
        raise ValueError(f"{path}: {error}") from error


def _cached_script(
    path: Path, toolchain: Toolchain, cache: Path, *, llvm_ir: bool
) -> bytes:
    script = path.resolve()
    contents = script.read_bytes()
    return cached_script_bundle(
        toolchain,
        cache,
        script,
        contents,
        _FRONTEND_FILES,
        (sys.version, lark_version),
        lambda: _script_input(script, contents, llvm_ir=llvm_ir)[0],
        llvm_ir=llvm_ir,
    )


def _native_command(args: argparse.Namespace, runner: Path) -> int:
    if args.bundle is not None:
        mode, program = bundle_object(
            args.bundle.read_bytes(), Toolchain.from_runner(runner)
        )
    else:
        bundle = None
        if args.script.suffix == ".ctk" and not args.no_cache:
            try:
                toolchain = Toolchain.from_runner(runner)
                bundle = _cached_script(
                    args.script, toolchain, cache_directory(), llvm_ir=args.llvm_ir
                )
            except OSError:
                # Source JIT is still usable if the compiler or cache is unavailable.
                pass
        if bundle is None:
            mode = "ir" if args.llvm_ir else "source"
            program, quote_dir = _script_input(args.script, llvm_ir=args.llvm_ir)
        else:
            mode, program = bundle_object(bundle, toolchain)
    command = [str(runner), mode, str(args.file), str(args.compdb)]
    if mode == "source":
        command.append(quote_dir)
    result = subprocess.run(command, input=program, check=False)
    if result.returncode < 0:
        print(
            f"ctk-jit: native runner terminated by signal {-result.returncode}",
            file=sys.stderr,
        )
        return 128 - result.returncode
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a CTK script with LLVM JIT")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run source or a precompiled bundle")
    run.add_argument("script", type=Path, nargs="?")
    run.add_argument("--bundle", type=Path, help="run a precompiled bundle")
    repl = commands.add_parser("repl", help="start a standalone LLVM IR session")
    for command in (run, repl):
        command.add_argument(
            "--file", type=Path, required=True, help="target translation unit"
        )
        command.add_argument(
            "--compdb",
            type=Path,
            required=True,
            help="compilation database or its directory",
        )
    build = commands.add_parser("precompile", help="compile source to a local bundle")
    build.add_argument("script", type=Path)
    build.add_argument("--output", "-o", type=Path, required=True)
    for command in (run, build):
        backend = command.add_mutually_exclusive_group()
        backend.add_argument(
            "--llvm-ir",
            action="store_true",
            help="use direct LLVM IR (default for .ctk)",
        )
        backend.add_argument(
            "--cpp-jit",
            dest="llvm_ir",
            action="store_false",
            help="use the C++ backend",
        )
        command.set_defaults(llvm_ir=None)
        command.add_argument(
            "--no-cache", action="store_true", help="bypass the local cache"
        )
    for command in (run, build, repl):
        command.add_argument(
            "--runner", type=Path, help="override the native runner executable"
        )
    args = parser.parse_args(argv)
    if args.command != "repl":
        if args.command == "run" and (args.script is None) == (args.bundle is None):
            parser.error("provide either a script or --bundle")
        if args.llvm_ir and (args.script is None or args.script.suffix != ".ctk"):
            parser.error("--llvm-ir requires a .ctk script")
        if args.llvm_ir is False and args.script is None:
            parser.error("--cpp-jit requires a source script")
        if args.script is not None and args.script.suffix not in {".ctk", ".cpp"}:
            parser.error("expected a .ctk script or .cpp extension")
        if args.llvm_ir is None:
            args.llvm_ir = args.script is not None and args.script.suffix == ".ctk"
        if (
            args.command == "precompile"
            and args.output.resolve() == args.script.resolve()
        ):
            parser.error("bundle output must differ from the source script")
    runner = args.runner or _runner()
    if runner is None:
        parser.error("build the native runner in build/jit or specify --runner")
    try:
        runner = runner.resolve()
        if args.command == "repl":
            return run_repl(runner, args.file, args.compdb, lower_repl)
        if args.command == "run":
            return _native_command(args, runner)
        cache = None if args.no_cache else cache_directory()
        toolchain = Toolchain.from_runner(runner)
        if cache is not None and args.script.suffix == ".ctk":
            data = _cached_script(args.script, toolchain, cache, llvm_ir=args.llvm_ir)
        else:
            source, quote_dir = _script_input(args.script, llvm_ir=args.llvm_ir)
            data = precompile(toolchain, source, quote_dir, cache, llvm_ir=args.llvm_ir)
        write_atomic(args.output, data)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"ctk-jit: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
