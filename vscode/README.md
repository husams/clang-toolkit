# Clang Toolkit VS Code prototype

Semantic Analysis has two tabs: **Symbol Search** and **Actions**. Symbol Search finds declarations by name, with scope and kind filters under Options. Actions run YAML-described CTK functions on a retained file root or a selected match binding. Both use the real native server. Ordinary console scripts remain available from the editor and file menu.

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

The Activity Bar hexagon opens Semantic Analysis. Server connection state and running work appear in the status bar; click the running task there to cancel. Clicking a result opens source and the **CTK Result** AST inspector. Plain script runs open **CTK Output** with the console's rendered output and diagnostics. Search file/result limits are explicit.

CTK Result shows the selected node's actual Clang kind, name/signature, source link and preview, readable AST properties, direct children and a collapsible source range. Click a child to inspect it; **Back** restores the previous node and **Selected result** returns to the original binding. Source links open the current inspected node in the editor. Properties adapt to declarations, records, expressions, casts and literals. Internal cursor/USR values, protobuf wrappers/enums, availability flags, supported scopes and whole-match dumps are excluded. Unknown or unrequested properties are omitted; they are not interpreted as empty values or false flags.

Actions inspect the original retained native nodes without reparsing. Symbol Search owns a separate bounded inspector context because its search worker has already released its cursors; selecting a new search result releases the previous inspector context. C++ edits or changed settings require refreshing/reselecting a result. Direct children load lazily from the native visitor, including implicit/type-location nodes, rather than from JSON or name-based reconstruction. Some auxiliary AST kinds have a Clang kind and child navigation but no additional serialized properties. Navigation is bounded to 1,000 direct neighbours, 128 inspected nodes and 10,000 retained handles per context; limit/errors are reported explicitly. Loading appears in the status bar, and failed loads offer Retry while keeping the current AST facts visible.

Workspace scope searches the active file's workspace folder (or the first folder if none is active). **Open Output** exposes script emissions and error details directly from the shared panel.

Right-click a C++ file: **CTK → Select Action…** pins that file as the initial action target. **Run Script…** and **Run Predefined…** retain the original console-script and search commands. Semantic Analysis has its own icon, with no search entry in the file menu. CTK editors have a Run button. Syntax colors distinguish YAML front matter, commands, matcher categories, strings, numbers, variables and comments.

## Node actions

1. Open a C++ file, select **Actions**, and use the single **Select action…** picker. It lists predefined and workspace actions plus **Create action…**. Without an active C++ file, the first run asks for a file.
2. Expand **Options** for the action's arguments. Descriptions appear as input hints; required arguments expand automatically. Click **Run** to parse the file and execute the action.
3. Results form one outline: **file → Match [n] → bindings**. Each match starts collapsed; click its heading or focus it and press Enter/Space to expand or collapse only that match. Bindings appear as compact, indented child rows with tree guides; snippets are available on hover and in CTK Result after selection. Each match keeps its caller, callee and other bindings together, including nodes located in another file. The automatic `root` binding determines the match's file and line; without it, the first binding supplies the location. Bindings remain independently selectable, and nodes from another file show that file beside their line number. File counts count matches, not individual bindings.
4. Select a binding, then **Run action on selected node…**. The same picker chooses the follow-up action; supply its options and click **Run**. The original native node is passed directly, without reparsing or reconstructing it from displayed JSON. **Back** restores earlier results; **File root** changes the next action's input back to the parsed translation unit.
5. Source/header edits and CTK configuration changes mark the context stale. Save edits, click **Refresh**, and run again. **Close** releases the context so another active file can be used. Failed or cancelled actions keep the preceding successful results. History is held in memory for at most 32 successful runs; refreshing/closing releases it.

`examples/caller-callee.ctk-action` displays one caller and one callee per call. Copy it into `.ctk/actions/` and run it on `examples/caller-callee.cpp`: Match [1] is `firstCaller → firstTarget`, and Match [2] is `secondCaller → secondTarget`. An automatic `root` that exactly duplicates a named binding is hidden from the outline; its native handle remains retained. Unique roots and all explicit binding names remain visible.

**Create action…** immediately opens a saved, editable template in a pinned editor tab and selects it in Actions. The file is named `my-action.ctk-action`, `my-action-2.ctk-action`, and so on, without overwriting existing files or colliding with action names. Edit its YAML name, description, arguments and CTK body directly. Creating from **Run action on selected node…** keeps that node as the input. Expired native contexts show a Refresh message; **Refresh**, then **Run** reparses the same C++ file even while the action editor is active.

The selected action's name, description and Options update as you edit its YAML, including unsaved changes. Added/removed arguments and changed hints, types or defaults appear automatically. Explicitly entered values survive compatible edits; untouched defaults follow the YAML. Incomplete metadata keeps the last valid fields visible and disables Run until repaired. Reopening the picker also uses unsaved action names. Editing metadata does not rerun an action or discard its retained nodes/results.

String arguments in **Options** offer suggestions automatically while typing or on focus; **Ctrl+Space** requests them manually. Use **Up/Down** to choose, **Enter/Tab** to accept, and **Escape** to dismiss. Selecting a folder continues into its contents. Paths stay literal, including spaces and quotes. Relative paths use the analysis workspace directory, with absolute paths and `~/` also supported. Class names come from the current analysis C++ translation unit, including headers, using the same compiler/server settings as editor completion. Save C++ edits before requesting class suggestions.

The console parser infers path arguments used by `parse`, `read` and file-taking helpers, and class arguments passed to `classByName` or class-name matchers. Forwarding through named helpers is supported when the dependency can be inspected statically. For ambiguous or dynamic code, an optional YAML `completion: path`, `file`, `folder` or `class` sets the provider explicitly; it requires a string argument. Completion inspects definitions without executing bodies or defaults and leaves the action's retained context/results alone. See `examples/argument-completion.ctk-action`.

Create workspace actions as `.ctk/actions/*.ctk-action` (other workspace folders are discovered too):

```yaml
---
name: find-function
description: Find function definitions under the selected node.
arguments:
  - name: name
    description: Exact function name; leave empty to find all.
    type: string
    default: ""
---
if name == "" then {
    match functionDecl(isDefinition()).bind("function") in node
} else {
    match functionDecl(isDefinition(), hasName(name)).bind("function") in node
}
```

This is the bundled **Find function** example; use a different unique name for a workspace copy. The extension translates it into an ordinary console function:

```ctk
let find_function(node, name = '') = {
    if name == "" then {
        match functionDecl(isDefinition()).bind("function") in node
    } else {
        match functionDecl(isDefinition(), hasName(name)).bind("function") in node
    }
}
```

`node` is implicit and must not be declared in `arguments`. Action names may contain hyphens, which become underscores in the callable; collisions are rejected. Arguments have a CTK identifier, description, optional type (`string`, `number`, `boolean`) and optional typed default. Required arguments precede defaulted ones. Values are passed as literal runtime bindings, without inserting user text into source. The body must return retained CTK matches; scalar/text/JSON/detached-list returns are rejected. Each match binding becomes a selectable live node. Preloaded console helpers and action-local functions/imports are available; helper libraries are loaded once per retained session.

Action files use the same CTK editor completion and signature providers in their bodies, with offsets mapped across the YAML header. The editor Run button uses current unsaved action text. Required arguments are collected in Options before execution. Actions currently start from one translation unit; matches may span its included files, and follow-up actions stay in that parsed context. Symbol Search separately supports workspace scope.

Autocomplete uses the console's actual grammar-aware completion engine. Suggestions appear while typing and after `.`, `$`, `(`, comma and space. Match results, strings, lists, dictionaries and parsed trees receive console member suggestions inferred from their declarations. Local functions and helpers in `~/.ctk/lib` (or `ctk.libraryDirectory`) show signatures, default parameters and Markdown definitions. Function calls display argument hints. Earlier-line edits preserve later text and existing parentheses. Drafts and helper bodies are inspected without execution; members requiring unknown runtime values cannot be inferred.

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

Version 0.2.1 bundles the merged console pipe/tuple implementation, so the current default `~/.ctk/lib/ctk_helpers.ctk` loads without changes. The default-library regression executes `classByName`, `classFields`, a user-defined pipe function and another action on the returned field while keeping the parse count at one. Run it with `CTK_TEST_DEFAULT_LIBRARY=1 pnpm test:live`. The regular console regression suite also covers pipelines, tuple callbacks, cancellation and imports. `examples/order-fields.ctk-action` demonstrates returning live field matches through a console helper.

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
