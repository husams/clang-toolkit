"""Reference navigation preserves native identity, source ranges and global scope."""
from __future__ import annotations

from contextlib import nullcontext
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from clang_toolkit._generated.match.v1.match_result_pb2 import MatchBinding

_spec = importlib.util.spec_from_file_location(
    'symbol_navigation', Path(__file__).parents[2] / 'vscode/console/symbol_navigation.py')
assert _spec and _spec.loader
navigation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(navigation)


def binding(file: Path, text: str, name: str, usr: str = 'exact-usr') -> MatchBinding:
    value = MatchBinding(symbol_identity=usr)
    value.node.function_decl.function.declarator.value.named.qualified_name = name
    value.location.valid = True
    value.location.file = str(file)
    value.location.line = 1
    value.location.column = 1
    for point, offset in ((value.range.expansion_begin, 0),
                          (value.range.expansion_end_exclusive, len(text.encode()))):
        point.valid = True
        point.file = str(file)
        point.offset = offset
    return value


def test_reads_the_own_name_instead_of_a_containing_scope(tmp_path: Path) -> None:
    value = binding(tmp_path / 'file.cpp', 'int target();', 'ns::target')
    value.node.function_decl.function.declarator.value.named.declaration.containing_scope.qualified_name = 'ns'
    assert navigation.declaration_name(value.node) == 'ns::target'


def test_reference_token_after_unicode_member_base_and_qualification(tmp_path: Path) -> None:
    file = tmp_path / 'file.cpp'
    text = '/* 😀 */ object.target'
    file.write_text(text)
    value = binding(file, text, 'ns::target')
    buffers = navigation.EditorBuffers({str(file): text})
    try:
        start, end = navigation.token_span(value, 'ns::target', buffers, str(file))
        assert text.encode()[start:end] == b'target'
        assert start == len('/* 😀 */ object.'.encode())
    finally:
        buffers.close()


def test_compiler_inspector_uses_frozen_server_arguments_and_marks_inferred_header(tmp_path: Path) -> None:
    from clang_toolkit.resources import InputDescriptor
    database = tmp_path / 'compile_commands.json'
    database.write_text(json.dumps([dict(directory=str(tmp_path), file='consumer.cpp', arguments=['clang++', '-DMODE=2', 'consumer.cpp'])]))
    descriptor = InputDescriptor(str(tmp_path / 'api.hpp'), working_directory=str(tmp_path), compile_arguments=('-DMODE=2', '-std=c++20'), compilation_database=str(database), frozen_profile=True)
    client = Mock()
    client.discover_files.return_value = SimpleNamespace(inputs=(descriptor,), diagnostics=())
    response = navigation.compiler_profile(client, dict(file=descriptor.path, directory=str(tmp_path), compileArguments=[]))
    assert response['profile']['arguments'] == ['-DMODE=2', '-std=c++20']
    assert response['profile']['provenance'] == 'inferred'
    assert response['profile']['translationUnits'] == [str(tmp_path / 'consumer.cpp')]


def test_header_override_reuses_frozen_tu_profile_without_appending_flags_twice(tmp_path: Path) -> None:
    from clang_toolkit.resources import InputDescriptor
    descriptor = InputDescriptor(str(tmp_path / 'consumer.cpp'), compile_arguments=('-DMODE=2',), frozen_profile=True)
    client = Mock()
    client.discover_files.return_value = SimpleNamespace(inputs=(descriptor,))
    buffers = navigation.NavigationBuffers({})
    try:
        navigation.parse_input(client, dict(file=str(tmp_path / 'api.hpp'), translationUnit=descriptor.path, directory=str(tmp_path), compileArguments=[]), buffers)
        selected = client.parse.call_args.args[0]
        assert selected.path == str(tmp_path / 'api.hpp')
        assert selected.compile_arguments == ('-DMODE=2',)
        assert selected.frozen_profile
    finally:
        buffers.close()


def test_reference_search_checks_native_identity_in_every_project_and_deduplicates_header_usages(tmp_path: Path) -> None:
    from clang_toolkit.resources import InputDescriptor
    header = tmp_path / 'api.hpp'
    header.write_text('target(3);')
    declaration = binding(header, 'target(3);', 'target', 'exact-overload')
    wrong = binding(header, 'target(3);', 'target', 'different-overload')
    reference = binding(header, 'target(3);', 'target')
    reference.node.Clear()
    reference.node.decl_ref_expr.SetInParent()
    rows = [SimpleNamespace(bindings=dict(reference=reference, declaration=value)) for value in (declaration, wrong, declaration)]
    roots = [str(tmp_path / 'consumer'), str(tmp_path / 'library')]
    client = Mock()
    client.list_project_indexes.return_value.projects = [SimpleNamespace(project_root=root) for root in roots]
    client.discover_files.side_effect = lambda paths, **kwargs: SimpleNamespace(inputs=(InputDescriptor(str(header), frozen_profile=True),), diagnostics=())
    client.parse.side_effect = lambda *args, **kwargs: nullcontext('tree')
    client.match_in.side_effect = lambda *args: nullcontext(rows)
    buffers = navigation.NavigationBuffers({})
    try:
        result = navigation.find_references(client, dict(usr='exact-overload', file=str(header), directory=str(tmp_path), compileArguments=[], includeDeclaration=False), buffers)
        assert [item['project'] for item in result['occurrences']] == roots
        assert all(item['column'] == 1 and item['preview'] == 'target(3);' for item in result['occurrences'])
        assert result['coverage'] == dict(completed=2, total=2, projects=2)
        assert all('isExpansionInMainFile' not in call.args[0] for call in client.match_in.call_args_list)
        assert len(client.match_in.call_args_list) == 2 * (len(navigation.QUERIES) - 1)
    finally:
        buffers.close()


def test_header_override_appends_editor_overlay_after_profile_discovery(tmp_path: Path) -> None:
    from clang_toolkit.resources import InputDescriptor
    file = str(tmp_path / 'api.hpp')
    descriptor = InputDescriptor(str(tmp_path / 'consumer.cpp'), profile_id='old-profile', compile_arguments=('-DMODE=2',), frozen_profile=True)
    client = Mock()
    client.discover_files.return_value = SimpleNamespace(inputs=(descriptor,))
    buffers = navigation.NavigationBuffers({file: 'int draft;'})
    try:
        navigation.parse_input(client, dict(file=file, translationUnit=descriptor.path, directory=str(tmp_path), compileArguments=[]), buffers)
        assert client.discover_files.call_args.kwargs['compile_arguments'] == []
        selected = client.parse.call_args.args[0]
        assert selected.compile_arguments == ('-DMODE=2', *buffers.arguments)
        assert selected.profile_id == ''
    finally:
        buffers.close()


def test_reference_discovery_does_not_leak_the_active_database_into_other_projects(tmp_path: Path) -> None:
    from clang_toolkit.resources import InputDescriptor
    consumer, library = str(tmp_path / 'consumer'), str(tmp_path / 'library')
    client = Mock()
    client.compilation_database = '/consumer-build/compile_commands.json'
    client.list_project_indexes.return_value.projects = [SimpleNamespace(project_root=root) for root in (consumer, library)]
    observed = []
    def discover(paths: list[str], **kwargs: object) -> SimpleNamespace:
        observed.append((paths[0], client.compilation_database, kwargs['compilation_database']))
        return SimpleNamespace(inputs=(InputDescriptor(paths[0] + '/main.cpp', frozen_profile=True),), diagnostics=())
    client.discover_files.side_effect = discover
    client.parse.side_effect = lambda *args: nullcontext('tree')
    client.match_in.side_effect = lambda *args: nullcontext([])
    buffers = navigation.NavigationBuffers({})
    try:
        navigation.find_references(client, dict(usr='c:@F@target#I#', file=consumer + '/main.cpp', directory=consumer,
                                               compilationDatabase=client.compilation_database, compileArguments=['-DMODE=2']), buffers)
        assert observed == [(consumer, None, '/consumer-build/compile_commands.json'), (library, None, None)]
        assert client.compilation_database == '/consumer-build/compile_commands.json'
    finally:
        buffers.close()


def test_skips_macros_without_spelled_symbol_and_unrelated_files(tmp_path: Path) -> None:
    file = tmp_path / 'file.cpp'
    file.write_text('CALL')
    value = binding(file, 'CALL', 'target')
    buffers = navigation.EditorBuffers({})
    try:
        assert navigation.token_span(value, 'target', buffers, str(file)) is None
        assert navigation.token_span(value, 'CALL', buffers, str(tmp_path / 'other.cpp')) is None
    finally:
        buffers.close()


def test_local_definition_replaces_forward_declaration(tmp_path: Path) -> None:
    file = tmp_path / 'main.cpp'
    text = 'int target();\nint target() { return 1; }\nint use() { return target(); }'
    file.write_text(text)
    declaration = binding(file, 'int target();', 'target')
    definition = binding(file, text, 'target')
    definition.range.expansion_begin.offset = len('int target();\n'.encode())
    definition.range.expansion_end_exclusive.offset = len('int target();\nint target() { return 1; }'.encode())
    reference = binding(file, text, 'target')
    reference.range.expansion_begin.offset = text.rindex('target')
    reference.range.expansion_end_exclusive.offset = text.rindex('target') + len('target')
    client = Mock()
    client.parse.return_value = nullcontext('tree')
    client.match_in.side_effect = [nullcontext([SimpleNamespace(bindings=dict(reference=reference, declaration=declaration))]), *[nullcontext([]) for _ in range(len(navigation.QUERIES) - 1)], nullcontext([SimpleNamespace(bindings=dict(declaration=definition))])]
    buffers = navigation.EditorBuffers({})
    try:
        response = navigation.scan(client, dict(file=str(file), directory=str(tmp_path), compileArguments=[]), buffers)
        assert response['references'][0]['target']['line'] == 2
        assert response['references'][0]['usr'] == 'exact-usr'
    finally:
        buffers.close()


def symbol(path: Path, *, usr: str = 'selected-overload', definition: bool = True,
           stale: bool = False) -> SimpleNamespace:
    return SimpleNamespace(usr=usr, is_definition=definition, stale=stale,
                           file_path=str(path), line=3, column=7)


def test_global_resolution_uses_every_project_and_exact_overload(tmp_path: Path) -> None:
    external = tmp_path / 'library.cpp'
    external.write_text('// definition\n\nint target(int) { return 1; }')
    client = Mock()
    client.list_project_indexes.return_value.projects = [SimpleNamespace(project_root='/consumer'), SimpleNamespace(project_root='/library')]
    client.lookup_symbol.side_effect = [SimpleNamespace(stale=False, symbols=[]), SimpleNamespace(stale=False, symbols=[symbol(external, usr='wrong-overload'), symbol(external, definition=False), symbol(external), symbol(external)])]
    response = navigation.resolve(client, dict(usr='selected-overload', target=dict(file='/declaration.hpp', line=1, column=1)))
    assert response['targets'] == [dict(file=str(external), line=3, column=7)]
    assert [call.args for call in client.lookup_symbol.call_args_list] == [('/consumer', 'selected-overload'), ('/library', 'selected-overload')]


@pytest.mark.parametrize('stale_response,stale_symbol,missing', [(True, False, False), (False, True, False), (False, False, True)])
def test_stale_or_deleted_definitions_fall_back_to_clang(tmp_path: Path, stale_response: bool,
                                                        stale_symbol: bool, missing: bool) -> None:
    external = tmp_path / 'library.cpp'
    if not missing:
        external.touch()
    client = Mock()
    client.list_project_indexes.return_value.projects = [SimpleNamespace(project_root='/library')]
    client.lookup_symbol.return_value = SimpleNamespace(stale=stale_response, symbols=[symbol(external, stale=stale_symbol)])
    target = dict(file='/declaration.hpp', line=2, column=1)
    assert navigation.resolve(client, dict(usr='selected-overload', target=target))['targets'] == [target]


def test_one_failed_project_does_not_hide_another_projects_definition(tmp_path: Path) -> None:
    external = tmp_path / 'library.cpp'
    external.touch()
    client = Mock()
    client.list_project_indexes.return_value.projects = [SimpleNamespace(project_root='/broken'), SimpleNamespace(project_root='/library')]
    client.lookup_symbol.side_effect = [RuntimeError('index unavailable'), SimpleNamespace(stale=False, symbols=[symbol(external)])]
    response = navigation.resolve(client, dict(usr='selected-overload', target=dict(file='/header.hpp', line=1, column=1)))
    assert response['targets'][0]['file'] == str(external)
    assert response['errors'] == ['/broken: index unavailable']


def test_explicit_template_arguments_do_not_steal_the_callee_link(tmp_path: Path) -> None:
    file = tmp_path / 'file.cpp'
    text = 'ns::choose<choose>'
    file.write_text(text)
    value = binding(file, text, 'ns::choose')
    buffers = navigation.EditorBuffers({})
    try:
        assert navigation.token_span(value, 'ns::choose', buffers, str(file)) == (4, 10)
    finally:
        buffers.close()


@pytest.mark.parametrize('usr,definition', [('c:main.cpp@42@F@main#@local', False), ('c:@F@target#I#', True)])
def test_native_definitions_and_lexical_symbols_do_not_jump_to_other_copies(usr: str, definition: bool) -> None:
    client = Mock()
    target = dict(file='/project/main.cpp', line=2, column=4)
    assert navigation.resolve(client, dict(usr=usr, nativeDefinition=definition, target=target))['targets'] == [target]
    client.list_project_indexes.assert_not_called()


def test_header_declaration_has_a_link_without_any_usage(tmp_path: Path) -> None:
    file = tmp_path / 'api.hpp'
    text = 'int choose(int);'
    file.write_text(text)
    declaration = binding(file, text, 'vendor::choose', 'c:@N@vendor@F@choose#I#')
    # Unlike a definition, this declaration has no body in the current AST.
    client = Mock()
    client.parse.return_value = nullcontext('tree')
    client.match_in.side_effect = [*[nullcontext([]) for _ in range(len(navigation.QUERIES) - 1)],
        nullcontext([SimpleNamespace(bindings=dict(reference=declaration, declaration=declaration))]),
        nullcontext([])]
    buffers = navigation.NavigationBuffers({})
    try:
        response = navigation.scan(client, dict(file=str(file), directory=str(tmp_path), compileArguments=[]), buffers)
        link = response['references'][0]
        assert text.encode()[link['start']:link['end']] == b'choose'
        assert link['usr'] == 'c:@N@vendor@F@choose#I#'
        assert link['nativeDefinition'] is False
    finally:
        buffers.close()
