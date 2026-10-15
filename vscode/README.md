# Clang Toolkit VS Code prototype

One Semantic Analysis view runs predefined analyses, saved scripts and custom CTK blocks. Find symbols is the default action; the function, class and variable actions are presets. Changing actions changes the inputs while preserving scope, execution, results and source/details. This executable prototype uses the existing TypeScript SDK and native server; search results are real.

## Run

Requires Node 22+, pnpm, VS Code 1.100+ and a running native `ctk-server`. From `vscode/`:

Script execution and autocomplete need Python 3.14 with the CTK console dependencies. The extension discovers a nearby `.venv`, the uv-installed CTK environment, or `python3`; set `ctk.pythonPath` to the console's interpreter if needed. The console package from this checkout is bundled in the VSIX.

```sh
pnpm --dir ../typescript install --frozen-lockfile
pnpm --dir ../typescript build
pnpm install
pnpm build
code .
```

Press F5 and select **Run CTK Prototype**. Set `ctk.server` to an endpoint such as `unix:///tmp/ctk.sock`, or leave it empty for shared YAML discovery. Compilation databases are discovered by the server; `ctk.compilationDatabase` and `ctk.compileArguments` override defaults.

Alternatively, run `pnpm package` and use **Extensions → Install from VSIX…** with `artifacts/clang-toolkit-prototype.vsix`.

The Activity Bar hexagon opens Semantic Analysis. Choose an analysis, set inputs and scope, then run. Results group by file; clicking a row opens source and the **CTK Result** bottom panel. Raw semantic fields remain inspectable. Script runs open **CTK Output** automatically with the console's rendered output and diagnostics. Failed files stay visible beside partial results. File/result limits are explicit. Stop requests console cancellation and cleanup; an unresponsive worker is terminated after ten seconds.

Workspace scope searches the active file's workspace folder (or the first folder if none is active). **Open Output** exposes script emissions and error details directly from the shared panel.

Right-click a C++ file: **CTK → Run Script…** or **Run Predefined…**. These use the same catalog and parameter collection. Semantic Analysis has its own icon, with no search entry in the file menu. CTK editors have a Run button. Syntax colors distinguish commands, matcher categories, strings, numbers, variables and comments.

Autocomplete uses the console's actual grammar-aware completion engine. Suggestions appear while typing and after `.`, `$`, `(`, comma and space. Match results, strings, lists, dictionaries and parsed trees receive console member suggestions inferred from their declarations. Local functions and helpers in `~/.ctk/lib` (or `ctk.libraryDirectory`) show signatures, default parameters and Markdown definitions. Function calls display argument hints. Earlier-line edits preserve later text and existing parentheses. Drafts and helper bodies are inspected without execution; members requiring unknown runtime values cannot be inferred. The sidebar block is a preview; **Edit in CTK editor** opens or reuses the editor with these features.

Filesystem suggestions use the console's path-role provider for commands such as `parse`, `read`, `import`, `load`, `save … to` and `match … in`. They appear while typing quoted paths, after quotes and `/`, or with **Trigger Suggest**. Files and folders have distinct icons; selecting a folder continues into its contents. Paths containing spaces are quoted, and an existing closing quote and later script lines are preserved. This also works inside function bodies and after function definitions. File operands use the workspace directory (the script's folder when no workspace is open); imports use the saved script's own folder. Ordinary strings, matcher names and comments do not receive filesystem suggestions.

Helper file arguments also complete paths: for example, type inside the first argument of `classByName("", "demo::Order")`. The editor inspects helper definitions to identify parameters used as file inputs, including simple forwarding through other helpers or user-defined functions. It uses those argument positions with the same filesystem provider, quoting and folder navigation. Function bodies and defaults remain dormant during completion. Analysis follows only the called function's dependencies and caches the result; complex or unavailable definitions conservatively receive normal completion.

The second argument of `classByName` automatically suggests fully qualified class/struct names from the first argument's C++ translation unit, including included headers: type `classByName("demo.cpp", "demo::Or` and select `demo::Order`. A short typing pause opens the popup even when normal string suggestions are disabled or an inline completion provider suppresses quick suggestions. Set `ctk.automaticClassSuggestions` to `false` to use manual invocation instead. Suggestions carry a class icon and source location, preserve existing closing quotes and later script text, and use the same native server/compiler settings as analysis. The first argument can be a literal path, a safely inferred path/tree variable, or `arg.FILE` after selecting a C++ target. Save C++ edits first; native completion reads files on disk. Queries run in a separate worker with bounded, briefly cached results; file/header/settings changes invalidate the cache. Dynamic first-argument expressions are not evaluated for completion.

## Console scripts and parameters

All script entry points use the same **compiled console batch runner** as `ctk SCRIPT.ctk`: saved scripts, the editor Run button and custom blocks. Console helpers, `let` functions, defaults, closures, inline callbacks, imports, error/exit handlers and `print` use the console implementation. Each run starts a fresh console session and preloads `~/.ctk/lib` (or `ctk.libraryDirectory`). Definitions persist within a run; subsequent runs load them again. The native DSL remains available through the console's explicit `script` command.

```ctk
// @ctk {"title":"Class fields","parameters":[{"name":"CLASS_NAME","label":"Class name","kind":"text","required":true}]}
let node = classByName(arg.FILE, arg.CLASS_NAME)
classFields(node)
```

Picker parameters arrive as literal strings in `arg.NAME`; `arg.FILE` is the selected C++ file (empty when none is selected). Legacy unquoted `${NAME}` placeholders become `arg.NAME` references, without inserting user text into executable source. Parameters support `text`, `choice` (with `choices`), `file`, `folder`, defaults and optional values. Cancelling a picker does not execute. Unsaved editor contents run directly. Saved scripts resolve relative imports against their own directory; untitled/custom blocks use the workspace directory. Pure local scripts can run without C++ input or a native connection. Workspace scripts execute once with all selected files configured as default matcher inputs. Printed/returned match values and helper symbol summaries with source coordinates populate the shared results list; other values stay in console output. Try `examples/console-demo.ctk` with `examples/demo.cpp` active.

The server and extension host must share filesystem paths. Untrusted workspaces cannot execute analyses.

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

`test:host` uses an isolated VS Code profile and temporary fixture workspace; set `VSCODE_EXECUTABLE_PATH` when VS Code is installed elsewhere. It checks actual webview result rendering, source navigation, matcher completion, hover, predefined analyses and console scripts. Validation outcomes and repository-wide limitations are recorded in repository file `docs/vscode-prototype-progress.md`.

Design: https://chatgpt.com/space/page_befdeedd156081919409f24942e91485.

References: [Webview security](https://code.visualstudio.com/api/extension-guides/webview), [language providers](https://code.visualstudio.com/api/language-extensions/programmatic-language-features), [contributions](https://code.visualstudio.com/api/references/contribution-points), [ESM support](https://code.visualstudio.com/updates/v1_100#_esm-support-for-extensions).
