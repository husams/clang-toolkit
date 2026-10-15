# Clang Toolkit VS Code prototype

One Semantic Analysis view runs predefined analyses, saved scripts and custom CTK blocks. Find symbols is the default action; the function, class and variable actions are presets. Changing actions changes the inputs while preserving scope, execution, results and source/details. This executable prototype uses the existing TypeScript SDK and native server; search results are real.

## Run

Requires Node 22+, pnpm, VS Code 1.100+ and a running native `ctk-server`. From `vscode/`:

Console autocomplete also needs Python 3.14 with the CTK console dependencies. The extension discovers a nearby `.venv`, the uv-installed CTK environment, or `python3`; set `ctk.pythonPath` to the console's interpreter if needed.

```sh
pnpm --dir ../typescript install --frozen-lockfile
pnpm --dir ../typescript build
pnpm install
pnpm build
code .
```

Press F5 and select **Run CTK Prototype**. Set `ctk.server` to an endpoint such as `unix:///tmp/ctk.sock`, or leave it empty for shared YAML discovery. Compilation databases are discovered by the server; `ctk.compilationDatabase` and `ctk.compileArguments` override defaults.

Alternatively, run `pnpm package` and use **Extensions → Install from VSIX…** with `artifacts/clang-toolkit-prototype.vsix`.

The Activity Bar hexagon opens Semantic Analysis. Choose an analysis, set inputs and scope, then run. Results group by file; clicking a row opens source and the **CTK Result** bottom panel. Raw semantic fields remain inspectable. Non-location output appears in **CTK Output**. Failed files stay visible beside partial results. File/result limits are explicit. Stop terminates the worker immediately; server handles follow the native cancellation/expiry policy.

Workspace scope searches the active file's workspace folder (or the first folder if none is active). **Open Output** exposes script emissions and error details directly from the shared panel.

Right-click a C++ file: **CTK → Run Script…** or **Run Predefined…**. These use the same catalog and parameter collection. Semantic Analysis has its own icon, with no search entry in the file menu. CTK editors have a Run button. Syntax colors distinguish commands, matcher categories, strings, numbers, variables and comments.

Autocomplete uses the console's actual grammar-aware completion engine. Suggestions appear while typing and after `.`, `$`, `(`, comma and space. Match results, strings, lists, dictionaries and parsed trees receive console member suggestions inferred from their declarations. Local functions and helpers in `~/.ctk/lib` (or `ctk.libraryDirectory`) show signatures, default parameters and Markdown definitions. Function calls display argument hints. Earlier-line edits preserve later text and existing parentheses. Drafts and helper bodies are inspected without execution; members requiring unknown runtime values cannot be inferred. The sidebar block is a preview; **Edit in CTK editor** opens or reuses the editor with these features.

## Native scripts and parameters

This prototype executes the **native ANTLR CTK DSL** through `Client.runScript()`. Python-console-only helpers and runnable declarations are outside this initial slice. Use `emit` for script output.

```ctk
// @ctk {"title":"Class fields","parameters":[{"name":"CLASS_NAME","label":"Class name","kind":"text","required":true}]}
emit match fieldDecl(hasParent(cxxRecordDecl(hasName(${CLASS_NAME})))).bind("symbol");
```

Placeholders are unquoted: `${CLASS_NAME}` becomes an escaped string literal. `${FILE}` is reserved for the C++ target. Parameters support `text`, `choice` (with `choices`), `file`, `folder`, defaults and optional values. Cancelling a picker does not execute. Scripts must be saved; custom blocks can open in a native CTK editor for highlighting and completion. The server and extension host must share filesystem paths. Untrusted workspaces cannot execute analyses.

## Validate and package

```sh
pnpm check
pnpm test
pnpm test:console
CTK_SERVER=/absolute/path/ctk-server pnpm test:live
CTK_SERVER=/absolute/path/ctk-server pnpm test:host
pnpm package
```

The VSIX in `artifacts/` bundles the SDK, dependencies, schemas and matcher catalog. Build regenerates catalog metadata from the repository without network access.

`test:host` uses an isolated VS Code profile and temporary fixture workspace; set `VSCODE_EXECUTABLE_PATH` when VS Code is installed elsewhere. It checks actual webview result rendering, source navigation, matcher completion, hover, predefined analyses and native scripts. Validation outcomes and repository-wide limitations are recorded in repository file `docs/vscode-prototype-progress.md`.

Design: https://chatgpt.com/space/page_befdeedd156081919409f24942e91485.

References: [Webview security](https://code.visualstudio.com/api/extension-guides/webview), [language providers](https://code.visualstudio.com/api/language-extensions/programmatic-language-features), [contributions](https://code.visualstudio.com/api/references/contribution-points), [ESM support](https://code.visualstudio.com/updates/v1_100#_esm-support-for-extensions).
