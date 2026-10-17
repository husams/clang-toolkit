"""Regressions for the VS Code adapter using the console's real engine."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import weakref
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('editor_service', Path(__file__).parents[1] / 'console/editor_service.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)

from action_service import ActionError, ActionHost


class SessionLifetimeTests(unittest.TestCase):
    def test_renews_each_owned_cursor_without_parsing(self):
        host = ActionHost.__new__(ActionHost)
        host.roots = {'demo.cpp': ('root', 'digest')}
        host.client = Mock()
        class Owner:
            def __init__(self, session_id):
                self.session_id = session_id
                self.closed = False
        root, children, closed = Owner('root'), Owner('children'), Owner('closed')
        closed.closed = True
        host.client._values = {node.session_id: weakref.ref(node)
                               for node in (root, children, closed)}
        self.assertEqual(host.keep_alive(), 2)
        self.assertEqual([call.args for call in host.client.attach_session.call_args_list],
                         [('root',), ('children',)])
        host.client.parse.assert_not_called()
        host.client.list_sessions.assert_not_called()

    def test_missing_native_sessions_are_reported_for_an_existing_file(self):
        host = ActionHost.__new__(ActionHost)
        host.roots = {'demo.cpp': ('root', 'digest')}
        host.client = Mock()
        host.client._values = {}
        with self.assertRaisesRegex(ActionError, 'Analysis session expired'):
            host.keep_alive()


class CompletionTests(unittest.TestCase):
    def test_worker_acknowledges_startup_before_serving_completions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = 'match functionD'
            payload = dict(id=7, source=source, cursor=len(source), directory=directory, library=directory)
            result = subprocess.run(
                [sys.executable, '-I', '-B', '-u', str(Path(service.__file__).resolve())],
                input=json.dumps(payload) + '\n', capture_output=True, text=True,
                timeout=30, check=True,
            )
        ready, response = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(ready, {'ready': True})
        self.assertEqual(response['id'], 7)
        self.assertIn('functionDecl', {item['label'] for item in response['items']})

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def complete(self, source, cursor=None):
        return service.request(dict(source=source, cursor=len(source) if cursor is None else cursor,
                                    directory=str(self.root), library=str(self.root)))

    def names(self, source, cursor=None):
        return {item['label']: item for item in self.complete(source, cursor)['items']}

    def test_native_match_members_and_bound_node_fields(self):
        prefix = 'let x = match functionDecl().bind("fn")\n'
        items = self.names(prefix + 'x.')
        self.assertTrue({'length', 'isEmpty', 'one', 'unique', 'fn', 'root'} <= items.keys())
        self.assertEqual(items['one']['text'], 'one(')
        self.assertIn('method', items['one']['detail'])
        self.assertIn('decl_name', self.names(prefix + 'x[0].fn.'))

    def test_action_argument_roles_follow_helpers_and_class_matchers_without_execution(self):
        helpers = Path(__file__).parents[2] / 'skills/ctk-script/scripts/ctk_helpers.ctk'
        (self.root / 'helpers.ctk').write_text(helpers.read_text())
        source = 'let inspect(node, cpp, wanted, label) = { let tree = parse cpp; let cls = classByName(tree, wanted); match fieldDecl().bind("field") in cls }'
        data = service.request(dict(source=source, cursor=len(source), directory=str(self.root), library=str(self.root), parametersFor='inspect'))
        self.assertEqual(data['parameterRoles'], {'cpp': 'path', 'wanted': 'class'})
        source = 'let inspect(node, wanted) = { match cxxRecordDecl(hasName(wanted)).bind("class") in node }'
        data = service.request(dict(source=source, cursor=len(source), directory=str(self.root), library=str(self.root), parametersFor='inspect'))
        self.assertEqual(data['parameterRoles'], {'wanted': 'class'})
        source = 'let inspect(node, wanted) = { match cxxRecordDecl(hasName("demo::" + wanted)).bind("class") in node }'
        data = service.request(dict(source=source, cursor=len(source), directory=str(self.root), library=str(self.root), parametersFor='inspect'))
        self.assertEqual(data['parameterRoles'], {'wanted': 'class'})
        source = 'let forward(cpp, wanted) = classByName(cpp, wanted)\nlet inspect(node, cpp, wanted) = forward(cpp, wanted)'
        data = service.request(dict(source=source, cursor=len(source), directory=str(self.root), library=str(self.root), parametersFor='inspect'))
        self.assertEqual(data['parameterRoles'], {'cpp': 'path', 'wanted': 'class'})
        source = 'let inspect(node, name) = { match functionDecl(hasName(name)).bind("function") in node }'
        data = service.request(dict(source=source, cursor=len(source), directory=str(self.root), library=str(self.root), parametersFor='inspect'))
        self.assertEqual(data['parameterRoles'], {})
        marker = self.root / 'executed'
        source = f'let inspect(node, cpp = unknownDangerousFunction()) = {{ save "ran" to "{marker}"; parse cpp }}'
        data = service.request(dict(source=source, cursor=len(source), directory=str(self.root), library=str(self.root), parametersFor='inspect'))
        self.assertEqual(data['parameterRoles'], {'cpp': 'path'})
        self.assertFalse(marker.exists())

    def test_literals_are_inferred_using_console_member_metadata(self):
        self.assertIn('push', self.names('let xs = [1, 2]\nxs.'))
        self.assertIn('strip', self.names('let name = "hello"\nname.'))
        self.assertIn('name', self.names('let obj = {name: "x"}\nobj.'))
        self.assertNotIn('push', self.names('let obj = {name: "x"}\nobj.'))

    def test_list_destructuring_and_clause_functions_have_offline_completion(self):
        self.assertIn('strip', self.names('let [name] = ["hello"]\nname.'))
        self.assertIn('push', self.names('let head : tail = [1, 2]\ntail.'))
        items = self.names('let classify = { ([]) 0; (head : tail) head }\nclassi')
        self.assertIn('classify', items)
        self.assertIn('classify([])', items['classify']['detail'])

    def test_user_function_signature_and_nested_argument_position(self):
        source = 'let scale(value, factor = 2) = { value * factor }\nsca'
        item = self.names(source)['scale']
        self.assertIn('scale(value, factor = 2)', item['detail'])
        self.assertIn('Definition', item['documentation'])
        data = self.complete(source[:-3] + 'scale(other("a,b"), ')
        self.assertEqual(data['call'], {'name': 'scale', 'parameter': 1})
        self.assertEqual(data['functions']['scale']['signature'], 'scale(value, factor = 2)')

    def test_multiline_earlier_line_and_existing_parenthesis_are_preserved(self):
        source = 'emit match functionDecl(\n  isDef()\n).bind("fn");'
        cursor = source.index('isDef') + len('isDef')
        item = self.names(source, cursor)['isDefinition']
        replaced = source[:item['start']] + item['text'] + source[cursor:]
        self.assertEqual(replaced, source.replace('isDef', 'isDefinition'))
        self.assertIn('Matcher<FunctionDecl> isDefinition()', item['documentation'])

    def test_comments_and_strings_do_not_offer_matchers(self):
        self.assertEqual(self.names('// functionD'), {})
        self.assertEqual(self.names('emit match hasName("functionD'), {})
        self.assertIn('functionDecl', self.names('// comment\nemit match functionD'))

    def test_library_and_import_bodies_never_run(self):
        marker = self.root / 'executed'
        (self.root / 'lib.ctk').write_text(f'let helper(value, count = 2) = {{ save value to "{marker}" }}\nlet effect = unknownDangerousFunction()')
        item = self.names('help')['helper']
        self.assertIn('helper(value, count = 2)', item['detail'])
        self.assertFalse(marker.exists())
        self.assertIn('helper', self.names('import "lib.ctk"\nhelp'))

    def test_grammar_filters_root_and_nested_matchers(self):
        self.assertNotIn('isDefinition', self.names('match '))
        self.assertIn('functionDecl', self.names('match '))
        self.assertIn('isDefinition', self.names('emit match functionDecl(isDef'))

    def test_filesystem_paths_in_multiline_scripts_and_function_bodies(self):
        (self.root / 'source file.cpp').write_text('int value;')
        (self.root / 'source dir').mkdir()
        (self.root / 'source dir/nested.cpp').write_text('int nested;')
        prefixes = ['parse "sou', 'let scale(x) = x * 2\nparse "sou',
                    'let analyze() = {\n  let tree = parse "sou',
                    'let analyze() = {\n  match varDecl() in "sou',
                    'let analyze() = {\n  import "sou',
                    'let analyze() = {\n  let data = read "sou']
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                items = self.names(prefix)
                self.assertIn('source file.cpp', items)
                self.assertEqual(items['source file.cpp']['detail'], 'file')
                self.assertIn('source dir/', items)
                item = items['source file.cpp']
                self.assertEqual(prefix[:item['start']] + item['text'], prefix[:prefix.rfind('"')] + '"source file.cpp"')
        self.assertIn('nested.cpp', self.names('parse "source dir/'))
        self.assertEqual(set(self.names('set cache_dir to "sou')), {'source dir/'})

    def test_path_completion_preserves_existing_quotes_and_later_lines(self):
        (self.root / 'source file.cpp').write_text('int value;')
        source = 'let scale(x) = x * 2\nlet tree = parse "sou"\nprint scale(21)'
        cursor = source.index('sou') + 3
        item = self.names(source, cursor)['source file.cpp']
        self.assertEqual(source[:item['start']] + item['text'] + source[cursor:], source.replace('"sou"', '"source file.cpp"'))
        self.assertNotIn('source file.cpp', self.names('print "sou'))
        self.assertNotIn('source file.cpp', self.names('// parse "sou'))
        self.assertNotIn('source file.cpp', self.names('match varDecl(hasName("sou'))

    def test_import_paths_use_script_directory_and_paths_share_console_candidates(self):
        from clang_toolkit.cli.path_completion import path_completions
        from prompt_toolkit.document import Document
        directory = self.root / 'scripts'
        directory.mkdir()
        (directory / 'local.ctk').write_text('let local() = 1')
        source = 'let scale(x) = x * 2\nimport "loc'
        data = service.request(dict(source=source, cursor=len(source), directory=str(self.root), scriptDirectory=str(directory), library=str(self.root)))
        self.assertIn('local.ctk', {item['label'] for item in data['items']})
        for prefix in ['parse "loc', 'import "loc', 'read loc', 'set cache_dir to "']:
            with self.subTest(prefix=prefix):
                expected = {item.display_text: item.text for item in path_completions(Document(prefix), directory)}
                actual = service.request(dict(source=prefix, cursor=len(prefix), directory=str(directory), library=str(self.root)))
                self.assertEqual({item['label']: item['text'] for item in actual['items'] if item['detail'] in {'file', 'directory'}}, expected)

    def test_helper_file_arguments_offer_paths_without_changing_the_other_arguments(self):
        helpers = Path(__file__).parents[2] / 'skills/ctk-script/scripts/ctk_helpers.ctk'
        (self.root / 'helpers.ctk').write_text(helpers.read_text())
        (self.root / 'source file.cpp').write_text('struct Order {};')
        (self.root / 'source dir').mkdir()
        for helper in ['classByName', 'classInfo', 'classTemplateInfo', 'ancestors', 'functionInfo', 'callSites']:
            with self.subTest(helper=helper):
                source = f'let node = {helper}("sou", "Order")\nprint node'
                cursor = source.index('sou') + 3
                items = self.names(source, cursor)
                self.assertIn('source dir/', items)
                item = items['source file.cpp']
                self.assertEqual(source[:item['start']] + item['text'] + source[cursor:], source.replace('"sou"', '"source file.cpp"'))
        self.assertNotIn('source file.cpp', self.names('classByName("source file.cpp", "sou'))
        self.assertNotIn('source file.cpp', self.names('classByName(other("sou'))
        self.assertNotIn('source file.cpp', self.names('// classByName("sou'))
        self.assertNotIn('source file.cpp', self.names('classFields("sou'))
        self.assertIn('source file.cpp', self.names(f'classByName("{self.root}/sou'))
        self.assertIn('source file.cpp', self.names('classByName(sou'))
        commented = 'classByName(\n  // target file\n  "sou", "Order")'
        self.assertIn('source file.cpp', self.names(commented, commented.index('sou') + 3))

    def test_user_function_file_arguments_follow_direct_and_forwarded_parameters(self):
        (self.root / 'source.cpp').write_text('int value;')
        source = 'let readTree(input) = parse input\nlet lookup(name, cpp) = readTree(cpp)\nlookup("not a path", "sou'
        self.assertIn('source.cpp', self.names(source))
        self.assertNotIn('source.cpp', self.names('let label(target) = target\nlabel("sou'))
        self.assertNotIn('source.cpp', self.names('let readTree(input) = parse input\nlet readTree(input) = input\nreadTree("sou'))

    def test_helper_path_inspection_never_executes_bodies_or_defaults(self):
        marker = self.root / 'executed'
        (self.root / 'source.cpp').write_text('int value;')
        source = f'let load(input = unknownDangerousFunction()) = {{ save "ran" to "{marker}"; parse input }}\nload("sou'
        self.assertIn('source.cpp', self.names(source))
        self.assertFalse(marker.exists())

    def test_class_name_context_uses_the_first_argument_without_executing_it(self):
        helpers = Path(__file__).parents[2] / 'skills/ctk-script/scripts/ctk_helpers.ctk'
        (self.root / 'helpers.ctk').write_text(helpers.read_text())
        source = 'let node = classByName("source file.cpp", "demo::Or")\nclassFields(node)'
        cursor = source.index('demo::Or') + len('demo::Or')
        context = self.complete(source, cursor)['symbols']
        self.assertEqual(context['file'], str((self.root / 'source file.cpp').resolve()))
        self.assertEqual(context['prefix'], 'demo::Or')
        self.assertEqual(source[context['start']:cursor], '"demo::Or')
        self.assertEqual(context['quote'], '"')
        self.assertFalse(context['close'])
        for first in ['unknownFunction()', '"{unknownFunction()}"']:
            self.assertIsNone(self.complete(f'classByName({first}, "Or')['symbols'])
        self.assertIsNone(self.complete('classByName(other("source.cpp"), "Or')['symbols'])
        self.assertIsNone(self.complete('classByName("source.cpp", other("Or')['symbols'])

    def test_class_name_context_resolves_literal_variables_and_selected_file(self):
        helpers = Path(__file__).parents[2] / 'skills/ctk-script/scripts/ctk_helpers.ctk'
        (self.root / 'helpers.ctk').write_text(helpers.read_text())
        for prefix in ['let cpp = "source.cpp"\nclassByName(cpp, ', 'let tree = parse "source.cpp"\nclassByName(tree, ']:
            with self.subTest(prefix=prefix):
                self.assertEqual(self.complete(prefix)['symbols']['file'], str((self.root / 'source.cpp').resolve()))
        source = 'classByName(arg.FILE, "'
        data = service.request(dict(source=source, cursor=len(source), directory=str(self.root), library=str(self.root), targetFile=str(self.root / 'selected.cpp')))
        self.assertEqual(data['symbols']['file'], str(self.root / 'selected.cpp'))


if __name__ == '__main__':
    unittest.main()
