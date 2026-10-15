"""JSON-lines adapter for the console's real completer; never evaluates drafts."""
from __future__ import annotations

import ast
import json
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
import re
import sys
from typing import Any

# The package is copied from the same checkout when the VSIX is built.
sys.path.insert(0, str(Path(__file__).parent))
from lark import Token, Tree
from lark.exceptions import UnexpectedInput
from prompt_toolkit.completion import CompleteEvent, Completion
from prompt_toolkit.document import Document
from clang_toolkit.cli.callable_help import CallableHelp
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.path_completion import path_context, path_completions
from clang_toolkit.cli.help import COMMAND_HELP, MATCHER_HELP
from clang_toolkit.cli.matcher_catalog import MATCHER_METADATA
from clang_toolkit.cli.runtime.evaluator import CompletionField, Runtime
from clang_toolkit.cli.runtime.prototype.repl_editor import PrototypeCompleter, lex, _kind as console_kind
from clang_toolkit.cli.runtime.prototype.repl_language import parse
from clang_toolkit.cli.runtime.prototype.syntax import Node
from clang_toolkit.match_values import BindingSelection, MatchRow, MatchValue, ParsedTree
from clang_toolkit._generated.match.v1 import match_result_pb2 as results


def _kind(token: Token) -> str:
    kind = console_kind(token)
    return 'WS' if kind.startswith('WS') else kind


class DraftMatch(MatchValue):
    """Schema-only stand-in: no client, cursor, native query, or invented values."""
    def __init__(self, names: set[str], node_kind: str) -> None:
        row = results.MatchResult()
        for name in names:
            binding = row.bindings[name]
            descriptor = binding.node.DESCRIPTOR.fields_by_name.get(node_kind)
            if descriptor is not None:
                getattr(binding.node, node_kind).SetInParent()
        object.__setattr__(self, '_row', row)
        object.__setattr__(self, '_owner', None)
        object.__setattr__(self, '_source_file', None)

    def binding_names(self) -> set[str]:
        return set(self._row.bindings)

    def __len__(self) -> int:
        return 1

    def __getitem__(self, index: int) -> MatchRow:
        return MatchRow(self._row.SerializeToString(), None, index)

    def binding(self, name: str, **_: Any) -> BindingSelection:
        if name not in self._row.bindings:
            raise KeyError(name)
        return BindingSelection(name, None, 0, _binding_data=self._row.bindings[name].SerializeToString())


def statements(source: str) -> Iterator[str]:
    """Recover complete statements without dropping multiline function bodies."""
    tokens = lex(source)
    start, stack = 0, []
    for token in tokens:
        kind, value = _kind(token), str(token)
        if kind in {'COMMENT', 'WS', 'STRING', 'OPEN_STRING', 'PREDICATE_STRING', 'FILE_STRING', 'DIRECTORY_STRING', 'PATH_STRING'}:
            continue
        if value == 'let' and not stack and source[start:int(token.start_pos)].strip():
            yield source[start:int(token.start_pos)]
            start = int(token.start_pos)
        if value in '([{':
            stack.append(value)
        elif value in ')]}' and stack:
            stack.pop()
        if (value == ';' or '\n' in value) and not stack:
            part = source[start:int(token.start_pos)]
            if part.rstrip().endswith('='):
                continue
            yield part
            start = int(token.end_pos)
    if source[start:].strip():
        yield source[start:]


@lru_cache(maxsize=64)
def declarations(source: str) -> tuple[tuple[Node, str], ...]:
    found = []
    for part in statements(source):
        if re.match(r'\s*(?://[^\n]*\n\s*)*let\s+\w+\s*\(', part):
            continue  # Function headers are inspected without parsing their bodies.
        try:
            program = parse(part)
        except (UnexpectedInput, ValueError):
            continue
        for node in program.children:
            if node.kind == 'observe':
                node = node.children[0]
            if node.kind in {'let', 'runnable'}:
                found.append((node, part))
    return tuple(found)


@lru_cache(maxsize=64)
def function_headers(source: str) -> dict[str, CallableHelp]:
    raw_tokens = lex(source)
    tokens = [token for token in raw_tokens if _kind(token) not in {'WS', 'COMMENT', 'NEWLINE', 'BATCH_SEPARATOR'}]
    boundaries, nesting = [], 0
    for token in raw_tokens:
        kind, value = _kind(token), str(token)
        if kind in {'COMMENT', 'WS', 'STRING', 'OPEN_STRING', 'PREDICATE_STRING', 'FILE_STRING', 'DIRECTORY_STRING', 'PATH_STRING'}:
            continue
        if value in '([{': nesting += 1
        elif value in ')]}': nesting = max(0, nesting - 1)
        if nesting == 0 and ('\n' in value or value == ';'):
            boundaries.append(int(token.start_pos))
    starts, depth = [], 0
    for index, token in enumerate(tokens):
        value = str(token)
        if value == 'let' and depth == 0:
            starts.append(index)
        if _kind(token) not in {'STRING', 'OPEN_STRING', 'PREDICATE_STRING', 'FILE_STRING', 'DIRECTORY_STRING', 'PATH_STRING'}:
            if value in '([{': depth += 1
            elif value in ')]}': depth = max(0, depth - 1)
    found = {}
    for number, index in enumerate(starts):
        if index + 3 >= len(tokens) or str(tokens[index + 2]) != '(':
            continue
        depth, closing = 0, None
        for end in range(index + 2, len(tokens)):
            if str(tokens[end]) == '(': depth += 1
            elif str(tokens[end]) == ')':
                depth -= 1
                if depth == 0:
                    closing = end
                    break
        if closing is None or closing + 1 >= len(tokens) or str(tokens[closing + 1]) != '=':
            continue
        name = str(tokens[index + 1])
        signature = source[int(tokens[index + 1].start_pos):int(tokens[closing].end_pos)]
        end = int(tokens[starts[number + 1]].start_pos) if number + 1 < len(starts) else len(source)
        body_start = int(tokens[closing + 1].end_pos)
        end = next((boundary for boundary in boundaries if body_start < boundary <= end and source[body_start:boundary].strip()), end)
        found[name] = CallableHelp(name, signature, source[int(tokens[index].start_pos):end].rstrip())
    return found


def value_of(node: Node, source: str, bindings: dict[str, Any]) -> Any:
    if node.kind == 'literal':
        return node.value
    if node.kind == 'ref':
        return bindings.get(node.value)
    if node.kind == 'list':
        return [value_of(item, source, bindings) for item in node.children]
    if node.kind == 'dict':
        return {entry.value: value_of(entry.children[0], source, bindings) for entry in node.children}
    if node.kind == 'get':
        base = value_of(node.children[0], source, bindings)
        if type(base) is dict:
            return base.get(node.value)
        if isinstance(base, DraftMatch) and node.value in base.binding_names():
            return base.binding(node.value)
    if node.kind == 'index':
        base = value_of(node.children[0], source, bindings)
        index = value_of(node.children[1], source, bindings)
        if isinstance(base, (DraftMatch, list, dict)) and isinstance(index, (int, str)):
            try:
                return base[index]
            except (KeyError, IndexError, TypeError):
                return None
    if node.kind == 'host':
        tree = node.value[0]
        if tree.data == 'parse_expression':
            return ParsedTree(static_file_operand(tree.children[1], bindings) or '', None)
        if tree.data in {'match', 'match_expression'}:
            names = {'root'}
            for bound in tree.find_data('bind'):
                for token in bound.scan_values(lambda item: isinstance(item, Token) and item.type == 'STRING'):
                    names.add(ast.literal_eval(str(token)))
            root = next((str(token) for token in tree.scan_values(lambda item: isinstance(item, Token) and 'ROOT_MATCHER_NAME' in item.type)), '')
            node_kind = re.sub(r'(?<!^)(?=[A-Z])', '_', root).lower()
            return DraftMatch(names, node_kind)
        if tree.data == 'display' and len(tree.children) == 1 and isinstance(tree.children[0], Token):
            token = tree.children[0]
            if token.type in {'STRING', 'NUMBER'}:
                try:
                    return ast.literal_eval(str(token))
                except (ValueError, SyntaxError):
                    pass
    # Calls and arbitrary expressions are deliberately never executed.
    return None


def load_source(path: Path) -> str:
    try:
        if path.stat().st_size <= 1024 * 1024:
            return path.read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        pass
    return ''


def describe_source(source: str, bindings: dict[str, Any], functions: dict[str, CallableHelp]) -> None:
    functions.update(function_headers(source))
    for node, part in declarations(source):
        if node.kind == 'let':
            bindings[node.value] = value_of(node.children[0], part, bindings)


@lru_cache(maxsize=1)
def host_starts() -> frozenset[str]:
    options = ReplCompleter().get_completions(Document(''), CompleteEvent(completion_requested=True))
    return frozenset(item.text.strip().removesuffix('(') for item in options
                     if item.text.strip().removesuffix('(') not in MATCHER_METADATA
                     and item.text.strip().removesuffix('(').isidentifier())


def filesystem_options(document: Document, cwd: Path, script_directory: Path) -> list[Completion] | None:
    """Recover a host operand after compiled syntax; let the console select path roles."""
    tokens = lex(document.text_before_cursor)
    if tokens and _kind(tokens[-1]) == 'COMMENT':
        return None
    starts = host_starts()
    offsets = [0, *(int(token.start_pos) for token in reversed(tokens)
                    if token.start_pos and str(token) in starts and str(token).isidentifier())]
    for start in offsets[:33]:
        candidate = Document(document.text[start:], cursor_position=document.cursor_position - start)
        context = path_context(candidate)
        if context is None:
            continue
        prefix = [token for token in lex(candidate.text[:context.start])
                  if _kind(token) not in {'WS', 'COMMENT', 'NEWLINE', 'BATCH_SEPARATOR'}]
        directory = script_directory if prefix and str(prefix[-1]) == 'import' else cwd
        return path_completions(candidate, directory)
    return None


def argument_stack(source: str) -> list[tuple[str, int, int, int]]:
    """Track name, argument index, editable start and first-argument start."""
    stack: list[tuple[str, int, int, int]] = []
    previous, preceding = '', ''
    for token in lex(source):
        kind, value = _kind(token), str(token)
        if kind in {'WS', 'COMMENT', 'NEWLINE', 'BATCH_SEPARATOR'}:
            continue
        if kind in {'STRING', 'OPEN_STRING', 'PREDICATE_STRING', 'FILE_STRING', 'DIRECTORY_STRING', 'PATH_STRING'}:
            previous, preceding = '', ''
            continue
        if value in '([{':
            name = previous if value == '(' and previous.isidentifier() and preceding not in {'let', '.'} else ''
            stack.append((name, 0, int(token.end_pos), int(token.end_pos)))
        elif value in ')]}' and stack:
            stack.pop()
        elif value == ',' and stack:
            name, parameter, _, first = stack[-1]
            stack[-1] = (name, parameter + 1, int(token.end_pos), first)
        preceding, previous = previous, value
    return stack


@lru_cache(maxsize=256)
def function_path_facts(definition: str) -> tuple[tuple[str, ...], frozenset[str], tuple[tuple[str, int, str], ...], frozenset[str]]:
    """Inspect syntax only; function bodies and defaults are never executed."""
    empty = ((), frozenset(), (), frozenset())
    if len(definition) > 64 * 1024:
        return empty
    try:
        program = parse(definition)
    except (UnexpectedInput, ValueError):
        return empty
    routine = next((item for item in program.children if item.kind == 'runnable'), None)
    if routine is None:
        return empty
    parameters = routine.value[1]
    direct: set[str] = set()
    blocked: set[str] = set()
    calls: list[tuple[str, int, str]] = []

    def reference(value: Any) -> str | None:
        if isinstance(value, Node) and value.kind == 'ref':
            return value.value
        if isinstance(value, Tree) and value.data == 'reference':
            names = [str(child) for child in value.children if isinstance(child, Token) and child.type == 'NAME']
            if len(names) == 1 and len(value.children) == 2:
                return names[0]
        return None

    def host(tree: Tree) -> None:
        kind = str(tree.data)
        # Native targets are explicit syntax operands, not matcher-name strings.
        targets = []
        if kind in {'match', 'background', 'script', 'cfg_file'}:
            targets = [tree.children[index + 1] for index, child in enumerate(tree.children[:-1])
                       if isinstance(child, Token) and child.type == 'IN']
        elif kind in {'parse_expression', 'read_expression', 'files_expression', 'callgraph_file', 'traverse', 'file_open'}:
            targets = [child for child in tree.children if isinstance(child, (Tree, Node))][:1]
        for target in targets:
            if name := reference(target):
                direct.add(name)
        if kind == 'reference' and len(tree.children) > 2:
            root = tree.children[1]
            if isinstance(root, Token):
                blocked.add(str(root))
        for child in tree.children:
            if isinstance(child, Tree):
                host(child)
            elif isinstance(child, Node):
                visit(child)

    def visit(node: Node) -> None:
        if node.kind in {'runnable', 'inline_runnable'}:
            return
        if node.kind == 'call':
            calls.extend((node.value, index, name) for index, child in enumerate(node.children)
                         if (name := reference(child)) in parameters)
        if node.kind == 'get' and node.children and (name := reference(node.children[0])):
            blocked.add(name)
        if node.kind == 'let':
            blocked.add(node.value)
        if node.kind == 'assign' and node.children and (name := reference(node.children[0])):
            blocked.add(name)
        if node.kind == 'host':
            host(node.value[0])
        for child in node.children:
            visit(child)

    visit(routine.children[0])
    return parameters, frozenset(direct), tuple(calls), frozenset(blocked)


@lru_cache(maxsize=32)
def path_parameters(definitions: tuple[tuple[str, str], ...], root: str) -> dict[str, frozenset[int]]:
    sources = dict(definitions)
    facts = {}
    pending = [root]
    while pending:
        name = pending.pop()
        if name in facts or name not in sources:
            continue
        facts[name] = function_path_facts(sources[name])
        pending.extend(callee for callee, _, _ in facts[name][2])
    paths = {name: set(direct) - set(blocked) for name, (_, direct, _, blocked) in facts.items()}
    for _ in range(len(facts)):
        changed = False
        for name, (_, _, calls, blocked) in facts.items():
            for callee, index, forwarded in calls:
                target = facts.get(callee)
                if target and index < len(target[0]) and target[0][index] in paths[callee] and forwarded not in blocked and forwarded not in paths[name]:
                    paths[name].add(forwarded)
                    changed = True
        if not changed:
            break
    return {name: frozenset(index for index, parameter in enumerate(parameters) if parameter in paths[name])
            for name, (parameters, _, _, _) in facts.items()}


def helper_filesystem_options(document: Document, cwd: Path, functions: dict[str, CallableHelp]) -> list[Completion] | None:
    stack = argument_stack(document.text_before_cursor)
    if not stack:
        return None
    name, index, start, _ = stack[-1]
    if name not in functions:
        return None
    paths = path_parameters(tuple((name, entry.definition) for name, entry in functions.items()), name)
    if index not in paths.get(name, ()):
        return None
    tokens = lex(document.text[start:document.cursor_position])
    if tokens and _kind(tokens[-1]) == 'COMMENT':
        return []
    atom = next((token for token in tokens if _kind(token) not in {'WS', 'COMMENT', 'NEWLINE', 'BATCH_SEPARATOR'}), None)
    start = start + int(atom.start_pos) if atom is not None else document.cursor_position
    # Reuse the console's quoting, directory navigation and suffix-preservation
    # rules for this operand. Relative insertion offsets remain cursor-based.
    prefix = 'parse '
    candidate = Document(prefix + document.text[start:], cursor_position=len(prefix) + document.cursor_position - start)
    return path_completions(candidate, cwd)


def static_file_operand(value: Any, bindings: dict[str, Any]) -> str | None:
    """Resolve only literal paths and already inferred values; never call code."""
    if isinstance(value, Token) and value.type in {'STRING', 'FILE_STRING'}:
        try:
            value = ast.literal_eval(str(value))
        except (ValueError, SyntaxError):
            return None
    elif isinstance(value, Tree) and value.data == 'reference':
        if any(not isinstance(child, Token) or child.type not in {'DOLLAR', 'NAME', 'DOT'} for child in value.children):
            return None
        names = [str(child) for child in value.children if child.type == 'NAME']
        value = bindings.get(names[0]) if names else None
        for name in names[1:]:
            value = value.get(name) if type(value) is dict else None
    if isinstance(value, ParsedTree):
        value = value.path
    if not isinstance(value, str) or not value or any(char in value for char in '{}$\0'):
        return None
    return value


def class_name_context(document: Document, cwd: Path, bindings: dict[str, Any], functions: dict[str, CallableHelp]) -> dict[str, Any] | None:
    stack = argument_stack(document.text_before_cursor)
    if not stack:
        return None
    name, index, start, first = stack[-1]
    if name != 'classByName' or index != 1 or name not in functions:
        return None
    if 0 not in path_parameters(tuple((key, entry.definition) for key, entry in functions.items()), name).get(name, ()):
        return None
    try:
        expression = parse(document.text[first:start - 1].strip()).children[0]
    except (UnexpectedInput, ValueError, IndexError):
        return None
    file = static_file_operand(value_of(expression, document.text[first:start - 1], bindings), bindings)
    if file is None:
        return None
    tokens = lex(document.text[start:document.cursor_position])
    if tokens and _kind(tokens[-1]) == 'COMMENT':
        return None
    atom = next((token for token in tokens if _kind(token) not in {'WS', 'COMMENT', 'NEWLINE', 'BATCH_SEPARATOR'}), None)
    start = start + int(atom.start_pos) if atom is not None else document.cursor_position
    prefix = 'parse '
    context = path_context(Document(prefix + document.text[start:], cursor_position=len(prefix) + document.cursor_position - start))
    if context is None or any(char in context.spelling for char in '{}$\0'):
        return None
    path = Path(file).expanduser()
    return dict(file=str(path if path.is_absolute() else (cwd / path).resolve()), prefix=context.spelling,
                start=start + context.start - len(prefix), quote=context.quote, close=not context.has_closing_quote)


def request(data: dict[str, Any]) -> dict[str, Any]:
    source, cursor = data['source'], data['cursor']
    if not isinstance(source, str) or len(source) > 1024 * 1024 or not isinstance(cursor, int) or not 0 <= cursor <= len(source):
        raise ValueError('Invalid completion source or cursor')
    cwd = Path(data.get('directory') or '.').resolve()
    script_directory = Path(data.get('scriptDirectory') or cwd).resolve()
    bindings, functions = {}, {}
    if data.get('targetFile'):
        bindings['arg'] = {'FILE': data['targetFile']}
    library = Path(data.get('library') or Path.home() / '.ctk/lib').expanduser()
    if library.is_dir():
        for path in sorted(library.glob('*.ctk'))[:256]:
            # Metadata only: do not import or execute a user's library.
            functions.update(function_headers(load_source(path)))
    # Local imports contribute definitions, never execution or side effects.
    for match in re.finditer(r'(?m)^\s*import\s+["\']([^"\']+)["\']', source[:cursor]):
        functions.update(function_headers(load_source(script_directory / match[1])))
    describe_source(source[:cursor], bindings, functions)
    # Function definitions later in the file are useful to an editor too.
    functions.update(function_headers(source))
    runtime = Runtime.__new__(Runtime)
    runtime.bindings, runtime.environment, runtime.config_vars, runtime._scopes = bindings, {}, {}, []
    runtime.cwd = cwd
    def fields(reference: str) -> tuple[CompletionField, ...]:
        if not re.fullmatch(r'\$?[A-Za-z_]\w*(?:\[\d+\]|\.[A-Za-z_]\w*)*', reference):
            return ()
        return runtime.completion_suggestions(reference if reference.startswith('$') else '$' + reference)
    base = ReplCompleter(references=runtime.completion_references, field_resolver=fields,
                         matcher_functions=lambda: tuple(functions), function_help=functions, cwd=cwd)
    document = Document(source, cursor_position=cursor)
    options = list(PrototypeCompleter(base).get_completions(document, CompleteEvent(completion_requested=True)))
    paths = helper_filesystem_options(document, cwd, functions)
    if paths is None:
        paths = filesystem_options(document, cwd, script_directory)
    if paths is not None:
        options = [*paths, *(item for item in options if item.display_meta_text not in {'file', 'directory'})]
    items = []
    for item in options:
        label = item.display_text if item.display_meta_text in {'file', 'directory'} else item.display_text.rstrip('(')
        name = label.lstrip('$').removeprefix('.')
        help_entry = functions.get(name) or MATCHER_HELP.get(name) or COMMAND_HELP.get(name)
        documentation = ''
        if name in functions:
            documentation = functions[name].markdown()
        elif name in MATCHER_METADATA:
            metadata = MATCHER_METADATA[name]
            documentation = metadata[1] + '\n\n' + '\n\n'.join('```ctk\n' + signature + '\n```' for signature in metadata[2])
        elif help_entry is not None:
            documentation = str(getattr(help_entry, 'purpose', ''))
        items.append(dict(label=label, text=item.text, start=cursor + item.start_position,
                          detail=item.display_meta_text, documentation=documentation))
    active = set(re.findall(r'[A-Za-z_]\w*', source[max(0, cursor - 256):cursor]))
    help_items = {name: dict(signature=entry.signature, documentation=entry.markdown()) for name, entry in functions.items() if name in active}
    for name in active - functions.keys():
        if name in MATCHER_METADATA:
            metadata = MATCHER_METADATA[name]
            help_items[name] = dict(signature=metadata[2][0] if metadata[2] else name + '()', signatures=list(metadata[2]), documentation=metadata[1])
    stack = argument_stack(source[:cursor])
    current = next((entry for entry in reversed(stack) if entry[0] in help_items), None)
    return dict(items=items, functions=help_items, call=dict(name=current[0], parameter=current[1]) if current else None,
                symbols=class_name_context(document, cwd, bindings, functions))


if __name__ == '__main__':
    for line in sys.stdin:
        identity = None
        try:
            data = json.loads(line)
            identity = data.get('id')
            print(json.dumps(dict(id=identity, **request(data))), flush=True)
        except Exception as error:
            print(json.dumps(dict(id=identity, error=str(error))), flush=True)
