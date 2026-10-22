# C/C++ reference navigation in VS Code

Opening a C or C++ source, header, or preprocessed `.i`/`.ii` file starts a background Clang scan. Resolved references to
variables, functions, members, types, aliases and namespaces are underlined.
Header declarations also receive links to their indexed definitions, even when the header contains no symbol usages.
Use Command-click on macOS or Control-click on Linux/Windows to follow a link.
Go to Definition and Peek Definition use the same reference bindings.

Hovering a symbol shows its signature, kind, indexed project, definition or declaration location, and a source preview. The hover includes Go to definition and Find all references actions. Hover metadata is cached for the current editor snapshot and is discarded after edits.

**CTK: Find All References Across Projects** and the normal References provider scan the translation units discovered by the server for every indexed project. They compare native USRs and include references from headers. The References section in Explorer collapses and expands like Outline. Its tree groups locations by project and file and shows the matching source line. A progress notification supports cancellation; file failures remain visible with incomplete coverage instead of being reported as a complete search. This is an on-demand native scan, so a large set of projects can take time. It does not add a result-count or elapsed-time cutoff.

The status bar shows the active file's symbol scan state and link count. Click it for retry, the actual failure message, or compiler settings. **CTK: Show Compiler Settings** displays the server's resolved arguments, working directory, compilation database, and whether the file has a direct command or an inferred context. **CTK: Select Header Translation Unit** chooses the translation unit whose frozen compiler profile is used for a header's symbol navigation. Choose Automatic compiler context to remove an override. Overrides are stored in `ctk.headerTranslationUnits`.

Highlight settings:

| Setting | Values |
| --- | --- |
| `ctk.symbolLinks.underline` | `always`, `modifier`, or `never`; modifier uses VS Code's Command/Control link emphasis; never keeps hover and definition commands available |
| `ctk.symbolLinks.style` | `solid`, `double`, `dotted`, `dashed`, or `wavy` |
| `ctk.symbolLinks.color` | `#RRGGBB`, or empty for text colour |
| `ctk.matchHighlight.style` | Selected single-line match underline style |
| `ctk.matchHighlight.color` | Selected-match underline colour, or empty for text colour |
| `ctk.matchHighlight.gutterColor` | Multiline gutter marker colour, or empty for amber |

**Pin results** in Symbol Search and Actions opens an independent query snapshot in an editor tab. Each tab retains its own matches, selection, expanded files, and scroll position, including across a window reload. Action snapshots include the currently displayed result page. Navigation verifies the source fingerprint before applying a saved range, so edits cannot send a pinned match to unrelated code. Native AST handles are not retained by pinned tabs. Close a tab to discard its snapshot.

Definition lookup searches every project indexed by the connected CTK server,
including projects outside the open VS Code workspace. Lookup uses the exact
Clang USR, preserving overloads and scopes. Available current definitions take
priority over declarations. Multiple definition locations open the references
picker. When no current indexed definition is available, navigation uses the
local definition or declaration found by Clang.

The extension uses the existing `ctk.server`, `ctk.configPath`,
`ctk.compilationDatabase`, `ctk.compileArguments`, `ctk.pythonPath` and
`ctk.rpcTimeoutMs` settings. `ctk.symbolNavigation` enables or disables the
feature and defaults to `true`. The workspace must be trusted, and the native
server must be running. Rebuild the server as well as the extension: type and
namespace references need source metadata for native location wrappers.

Scans include unsaved editor contents, including edited headers. Edits clear
old underlines and invalidate old clickable links immediately. Source edits
replace that file's scan; header edits also invalidate other open translation
units. Closing a document or disposing the extension cancels its background
work. Parser failures are reported in CTK Output. References that Clang cannot
resolve, and macro invocations that do not spell the referenced name, do not
receive guessed links.

## Validation

```sh
pnpm --dir vscode check
pnpm --dir vscode test
uv run python -m pytest tests/unit/test_vscode_symbol_navigation.py
cmake --preset dev
cmake --build --preset dev
ctest --preset dev
uv run python -m pytest tests/unit
uv run python -m pytest tests/e2e -m e2e
pnpm --dir vscode build
CTK_TEST_NAVIGATION_ONLY=1 pnpm --dir vscode test:host
```

The focused extension-host test creates two projects, indexes both, opens a
consumer file, checks native links and Unicode ranges, follows an exact
overload into the other project's implementation, and checks unsaved edits.
The host runner owns one disposable VS Code instance and closes its test
processes afterward.
