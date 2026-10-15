"""Regressions for the VS Code adapter using the console's real engine."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('editor_service', Path(__file__).parents[1] / 'console/editor_service.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


class CompletionTests(unittest.TestCase):
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

    def test_literals_are_inferred_using_console_member_metadata(self):
        self.assertIn('push', self.names('let xs = [1, 2]\nxs.'))
        self.assertIn('strip', self.names('let name = "hello"\nname.'))
        self.assertIn('name', self.names('let obj = {name: "x"}\nobj.'))
        self.assertNotIn('push', self.names('let obj = {name: "x"}\nobj.'))

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


if __name__ == '__main__':
    unittest.main()
