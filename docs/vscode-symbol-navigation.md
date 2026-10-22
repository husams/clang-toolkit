# C/C++ reference navigation in VS Code

Opening a C or C++ source, header, or preprocessed `.i`/`.ii` file starts a background Clang scan. Resolved references to
variables, functions, members, types, aliases and namespaces are underlined.
Header declarations also receive links to their indexed definitions, even when the header contains no symbol usages.
Use Command-click on macOS or Control-click on Linux/Windows to follow a link.
Go to Definition and Peek Definition use the same reference bindings.

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
