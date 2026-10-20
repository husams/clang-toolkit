"""Persist library syntax and generated Python; keep runtime bindings fresh."""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import marshal
import os
import secrets
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache
from pathlib import Path
from types import CodeType
from typing import Any

import lark
from lark import Token, Tree
from lark.tree import Meta

from clang_toolkit.cli.parser_cache import cache_root

from .syntax import Node

_FORMAT = 1
_MAX_ENTRIES = 128
_MAX_BYTES = 16 * 1024 * 1024
_META_FIELDS = {"empty", "line", "column", "start_pos", "end_line", "end_column",
                "end_pos", "container_line", "container_column", "container_start_pos",
                "container_end_line", "container_end_column", "container_end_pos"}


@cache
def _fingerprint() -> str:
    """Invalidate on interpreter, Lark, grammar, compiler or IR changes."""
    directory = Path(__file__).parent
    cli = directory.parents[1]
    files = [*directory.glob("*.py"), *directory.glob("*.lark"),
             cli / "grammar.lark", cli / "language.py", cli / "matcher_catalog.py",
             cli / "_matcher_catalog_generated.py"]
    digest = hashlib.sha256(f"{_FORMAT}:{sys.version}:{lark.__version__}".encode())
    for path in sorted(files):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _directory(namespace: str = "libraries") -> Path:
    if namespace not in {"libraries", "templates", "blocks"}:
        raise ValueError(f"unknown script cache namespace {namespace!r}")
    directory = cache_root() / "scripts"
    return directory if namespace == "libraries" else directory / namespace


def _encode(value: Any) -> Any:
    if isinstance(value, Token):
        return ["token", value.type, str(value), value.start_pos, value.line,
                value.column, value.end_line, value.end_column, value.end_pos]
    if isinstance(value, Node):
        return ["node", value.kind, _encode(value.value), _encode(value.children),
                value.line, value.column, _encode(value.source_span)]
    if isinstance(value, Tree):
        return ["tree", _encode(value.data), [_encode(item) for item in value.children],
                _encode(vars(value.meta))]
    if isinstance(value, tuple):
        return ["tuple", [_encode(item) for item in value]]
    if isinstance(value, dict):
        return ["dict", [[_encode(key), _encode(item)] for key, item in value.items()]]
    if value is None or type(value) in {str, int, float, bool}:
        return value
    from .selection import OMITTED
    if value is OMITTED:
        return ["omitted"]
    raise TypeError(f"unsupported cached syntax: {type(value).__name__}")


def _decode(value: Any) -> Any:
    if value is None or type(value) in {str, int, float, bool}:
        return value
    if not isinstance(value, list) or not value:
        raise ValueError("invalid cached syntax")
    match value:
        case ["omitted"]:
            from .selection import OMITTED
            return OMITTED
        case ["node", str(kind), raw, raw_children, int(line), int(column), raw_span]:
            children = _decode(raw_children)
            span = _decode(raw_span)
            if not isinstance(children, tuple) or not all(isinstance(item, Node) for item in children):
                raise ValueError("invalid cached children")
            if span is not None and (not isinstance(span, tuple) or len(span) != 2
                                     or not all(type(item) is int for item in span)):
                raise ValueError("invalid cached source span")
            return Node(kind, _decode(raw), children, line, column, span)
        case ["tree", raw, list(raw_children), raw_meta]:
            data = _decode(raw)
            fields = _decode(raw_meta)
            if not isinstance(data, str) or not isinstance(fields, dict) or fields.keys() - _META_FIELDS:
                raise ValueError("invalid cached host tree")
            if any(type(item) not in {int, bool} for item in fields.values()):
                raise ValueError("invalid cached source location")
            meta = Meta()
            vars(meta).update(fields)
            return Tree(data, [_decode(item) for item in raw_children], meta=meta)
        case ["token", str(kind), str(text), start, line, column, end_line, end_column, end]:
            if any(item is not None and type(item) is not int
                   for item in (start, line, column, end_line, end_column, end)):
                raise ValueError("invalid cached token location")
            return Token(kind, text, start, line, column, end_line, end_column, end)
        case ["tuple", list(items)]:
            return tuple(_decode(item) for item in items)
        case ["dict", list(items)]:
            return {_decode(key): _decode(item) for key, item in items}
    raise ValueError("invalid cached syntax record")


@contextmanager
def _cache_directory(path: Path, *, create: bool = False) -> Iterator[int]:
    """Pin a private directory while reading, publishing and pruning entries."""
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ValueError("script cache directory permits other writers")
        yield descriptor
    finally:
        os.close(descriptor)


def _read_entry(path: Path) -> Any:
    with _cache_directory(path.parent) as directory:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        with os.fdopen(descriptor, "rb") as entry:
            info = os.fstat(entry.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o022 or info.st_size > _MAX_BYTES):
                raise ValueError("unsafe or oversized script cache entry")
            payload = entry.read(_MAX_BYTES + 1)
            if len(payload) > _MAX_BYTES:
                raise ValueError("oversized script cache entry")
    return json.loads(payload)


def _write_entry(path: Path, payload: str) -> None:
    if len(payload.encode("utf-8")) > _MAX_BYTES:
        return
    with _cache_directory(path.parent, create=True) as directory:
        temporary = f".script-{secrets.token_hex(16)}"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o600, dir_fd=directory)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                output.write(payload)
            os.replace(temporary, path.name, src_dir_fd=directory, dst_dir_fd=directory)
            # Syntax and Python artifacts have independent bounded budgets in
            # each namespace. A disappearing entry from another writer is fine.
            python = path.name.endswith(".python.json")
            entries = []
            for name in os.listdir(directory):
                if not name.endswith(".json") or name.endswith(".python.json") != python:
                    continue
                try:
                    info = os.stat(name, dir_fd=directory, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if stat.S_ISREG(info.st_mode):
                    entries.append((info.st_mtime_ns, name))
            for _, name in sorted(entries)[:-_MAX_ENTRIES]:
                try:
                    os.unlink(name, dir_fd=directory)
                except FileNotFoundError:
                    pass
        finally:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass


def parse_library(source: str, *, namespace: str = "libraries") -> Node:
    """Reuse unchanged syntax across processes without caching bindings or effects."""
    from .repl_language import parse

    destination = None
    try:
        key = hashlib.sha256((_fingerprint() + source).encode("utf-8")).hexdigest()
        destination = _directory(namespace) / f"{key}.json"
        payload = _read_entry(destination)
        if payload["key"] == key and payload["format"] == _FORMAT:
            serialized = json.dumps(payload["program"], ensure_ascii=True, separators=(",", ":"))
            if hashlib.sha256(serialized.encode()).hexdigest() != payload["digest"]:
                raise ValueError("damaged cached syntax")
            program = _decode(payload["program"])
            if isinstance(program, Node) and program.kind == "program":
                return program
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        # The cache is optional: damaged or unavailable entries reparse the source.
        pass

    program = parse(source)
    if destination is not None:
        try:
            encoded = _encode(program)
            serialized = json.dumps(encoded, ensure_ascii=True, separators=(",", ":"))
            payload = json.dumps({"format": _FORMAT, "key": key, "program": encoded,
                                  "digest": hashlib.sha256(serialized.encode()).hexdigest()},
                                 ensure_ascii=True, separators=(",", ":"))
            _write_entry(destination, payload)
        except (OSError, ValueError, TypeError, RecursionError):
            pass
    return program


def _objects(program: Node) -> dict[tuple[Any, ...], Any]:
    """Address compiler operands in the prepared tree, retaining object identity.

    Host metadata contains session-local executables and templates. Referencing
    the current tree instead of serializing operands keeps those objects fresh.
    """
    objects: dict[tuple[Any, ...], Any] = {}

    def visit(value: Any, path: tuple[Any, ...]) -> None:
        objects[path] = value
        if isinstance(value, Node):
            visit(value.value, (*path, "value"))
            visit(value.children, (*path, "children"))
        elif isinstance(value, Tree):
            visit(value.children, (*path, "children"))
        elif isinstance(value, (tuple, list)):
            for index, item in enumerate(value):
                visit(item, (*path, index))
        elif isinstance(value, dict):
            for key, item in value.items():
                if isinstance(key, str):
                    visit(item, (*path, key))

    visit(program, ())
    return objects


def _python_path(source: str, namespace: str = "libraries") -> Path:
    key = hashlib.sha256((_fingerprint() + source).encode("utf-8")).hexdigest()
    return _directory(namespace) / f"{key}.python.json"


def load_python(source: str, program: Node, *, namespace: str = "libraries") -> tuple[str, CodeType, ast.Module, list[Any], list[Any]] | None:
    """Load generated Python without running the DSL lowerer on warm startup."""
    try:
        path = _python_path(source, namespace)
        payload = _read_entry(path)
        body = payload["body"]
        if hashlib.sha256(body.encode()).hexdigest() != payload["digest"]:
            return None
        artifact = json.loads(body)
        if artifact["fingerprint"] != _fingerprint() or artifact["source"] != source:
            return None
        objects = _objects(program)
        def operands(records: list[Any]) -> list[Any]:
            if not isinstance(records, list):
                raise ValueError("invalid compiler operands")
            values = []
            for record in records:
                if not isinstance(record, list) or len(record) != 2:
                    raise ValueError("invalid compiler operand")
                if record[0] == "path":
                    values.append(objects[tuple(record[1])])
                elif record[0] == "data":
                    values.append(_decode(record[1]))
                else:
                    raise ValueError("unknown compiler operand")
            return values
        python = artifact["python"]
        if not isinstance(python, str):
            return None
        code = marshal.loads(base64.b64decode(artifact["code"], validate=True))
        if not isinstance(code, CodeType):
            return None
        return python, code, ast.parse(python), operands(artifact["nodes"]), operands(artifact["values"])
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError,
            RecursionError, SyntaxError, EOFError, OverflowError):
        return None


def store_python(source: str, program: Node, python: str, code: CodeType,
                 nodes: list[Any], values: list[Any], *, namespace: str = "libraries") -> None:
    """Atomically persist Python and operand addresses, never runtime bindings."""
    try:
        path = _python_path(source, namespace)
        paths = {id(value): location for location, value in _objects(program).items()}
        def operands(items: list[Any]) -> list[Any]:
            return [["path", paths[id(item)]] if id(item) in paths else ["data", _encode(item)]
                    for item in items]
        body = json.dumps({"fingerprint": _fingerprint(), "source": source,
                           "python": python, "code": base64.b64encode(marshal.dumps(code)).decode("ascii"),
                           "nodes": operands(nodes), "values": operands(values)},
                          ensure_ascii=True, separators=(",", ":"))
        payload = json.dumps({"body": body, "digest": hashlib.sha256(body.encode()).hexdigest()})
        _write_entry(path, payload)
    except (OSError, ValueError, TypeError, RecursionError):
        pass
