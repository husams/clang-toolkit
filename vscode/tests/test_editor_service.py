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


if __name__ == '__main__':
    unittest.main()
