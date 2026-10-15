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
from lark import Token
from lark.exceptions import UnexpectedInput
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from clang_toolkit.cli.callable_help import CallableHelp
from clang_toolkit.cli.completion import ReplCompleter
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
            return ParsedTree('', None)
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


def request(data: dict[str, Any]) -> dict[str, Any]:
    source, cursor = data['source'], data['cursor']
    if not isinstance(source, str) or len(source) > 1024 * 1024 or not isinstance(cursor, int) or not 0 <= cursor <= len(source):
        raise ValueError('Invalid completion source or cursor')
    cwd = Path(data.get('directory') or '.').resolve()
    bindings, functions = {}, {}
    library = Path(data.get('library') or Path.home() / '.ctk/lib').expanduser()
    if library.is_dir():
        for path in sorted(library.glob('*.ctk'))[:256]:
            # Metadata only: do not import or execute a user's library.
            functions.update(function_headers(load_source(path)))
    # Local imports contribute definitions, never execution or side effects.
    for match in re.finditer(r'(?m)^\s*import\s+["\']([^"\']+)["\']', source[:cursor]):
        functions.update(function_headers(load_source(cwd / match[1])))
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
    options = PrototypeCompleter(base).get_completions(document, CompleteEvent(completion_requested=True))
    items = []
    for item in options:
        label = item.display_text.rstrip('(')
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
    stack, previous = [], ''
    for token in lex(source[:cursor]):
        kind, value = _kind(token), str(token)
        if kind in {'WS', 'COMMENT', 'NEWLINE', 'BATCH_SEPARATOR'}:
            continue
        if kind in {'STRING', 'OPEN_STRING', 'PREDICATE_STRING', 'FILE_STRING', 'DIRECTORY_STRING', 'PATH_STRING'}:
            previous = ''
            continue
        if value in '([{':
            stack.append([previous if value == '(' and previous.isidentifier() else '', 0])
        elif value in ')]}' and stack:
            stack.pop()
        elif value == ',' and stack:
            stack[-1][1] += 1
        previous = value
    current = next((entry for entry in reversed(stack) if entry[0] in help_items), None)
    return dict(items=items, functions=help_items, call=dict(name=current[0], parameter=current[1]) if current else None)


if __name__ == '__main__':
    for line in sys.stdin:
        identity = None
        try:
            data = json.loads(line)
            identity = data.get('id')
            print(json.dumps(dict(id=identity, **request(data))), flush=True)
        except Exception as error:
            print(json.dumps(dict(id=identity, error=str(error))), flush=True)
