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

## Deploy on RHEL 9

Check out the merged `main` branch on the RHEL machine, then run as
your normal VS Code user (not `sudo bash`):

```sh
bash vscode/scripts/deploy-rhel9.sh
code /path/to/cpp-project
```

RHEL 9, Rocky Linux 9, AlmaLinux 9 and CentOS Stream 9 are supported targets.
Internet access and sudo for missing system packages are required. The native
build needs the full AppStream and CodeReady Builder/CRB repositories, including
the Clang and GCC toolset packages used by `scripts/build-rhel9.sh`. Run from a
VS Code **Remote-SSH integrated terminal** when deploying to a remote extension
host; this lets the installer find that host's VS Code CLI. Otherwise it installs
desktop VS Code if `code` is missing. Use `--code /path/to/code` for another CLI;
VS Code 1.100 or newer is required. An existing older installation must be updated.

The script installs prerequisites, builds the native server and SDK, runs extension
type checks, lint and unit tests, and packages and installs the VSIX. The native
server and its indexing worker are installed together. It creates a
private Python 3.14 runtime, installs the shipped console helpers if absent, and
starts `ctk-vscode-prototype.service` in your systemd user session. Existing helper
files in `~/.ctk/lib` are kept, including user functions. A live check uses the actual
packaged worker to verify unsaved-buffer parsing, base-class navigation and an
action on the selected node before installing the extension. Its server, storage,
runtime and server configuration are under `~/.local/share/ctk-vscode`
(`$XDG_DATA_HOME/ctk-vscode` when set). The native binary and Python package are
copied/installed there; running the extension does not depend on keeping the build
checkout in place.

The extension is installed for your user, and the four CTK deployment settings
(`ctk.server`, `ctk.configPath`, `ctk.pythonPath`, `ctk.libraryDirectory`) are written
to VS Code's **user settings**. Open any trusted C++ project normally; there is no
required `.code-workspace` file, and deployment does not create a demo by default.
Desktop installs use `$XDG_CONFIG_HOME/Code/User/settings.json` (normally
`~/.config/Code/User/settings.json`); Remote-SSH installs use the remote user's
`$VSCODE_AGENT_FOLDER/data/Machine/settings.json` (normally under
`~/.vscode-server`). Named desktop profiles and Insiders are detected. Use
`--settings-file /absolute/path/to/settings.json` for a custom VS Code data directory
or CLI wrapper that hides its location.

Other settings, JSONC comments and trailing commas are preserved, and existing
settings are backed up beside the original as `settings.json.ctk-backup` when changed.
Malformed settings are left untouched and reported. Existing project settings
are kept and can override user settings. Rerunning updates the same deployment;
it removes the old installer's CTK deployment overrides from its own shortcut
workspace. Reload an existing VS Code window after an update. No editor window
opens during deployment.

```sh
# Preview without changes (also works before copying the checkout to Linux).
bash vscode/scripts/deploy-rhel9.sh --dry-run

# Optionally create the demo, or a shortcut for an existing project.
# Both still use user-level CTK settings.
bash vscode/scripts/deploy-rhel9.sh --demo
bash vscode/scripts/deploy-rhel9.sh --workspace /path/to/cpp-project

# Use a prebuilt portable VSIX matching this checkout; skip Node/pnpm entirely.
bash vscode/scripts/deploy-rhel9.sh --vsix /path/to/clang-toolkit-prototype.vsix

# Reuse an existing local CTK server instead of building/starting another one.
bash vscode/scripts/deploy-rhel9.sh --server unix:///tmp/ctk.sock --skip-deps

# Include the complete native and Python suites during the native build.
bash vscode/scripts/deploy-rhel9.sh --full-tests

systemctl --user status ctk-vscode-prototype.service
journalctl --user -u ctk-vscode-prototype.service -n 80 --no-pager
```

`--skip-deps` reuses a Node runtime installed by an earlier deployment, or assumes
prerequisites are otherwise installed; it still installs locked Python
and JavaScript dependencies and is not an offline mode. `--server` accepts only a
local Unix socket or loopback TCP endpoint; the server must share your filesystem.
Use `--profile NAME`, `--library-directory DIR` and `--prefix DIR` to select other
locations. A working systemd user session is required for the managed server; it
normally lasts for your login session. The installer does not enable lingering.
It never changes or restarts another CTK service. See `--help` for all options.

Installer regression checks: `pnpm --dir vscode test:deploy` (uses the checkout's
Python environment, or `CTK_PYTHON`). These simulate package installation and
systemd; actual machine deployment still needs validation on the destination.
Settings behavior: [VS Code user and workspace settings](https://code.visualstudio.com/docs/configure/settings),
[Remote-SSH settings](https://code.visualstudio.com/docs/remote/ssh), and
[remote settings location](https://github.com/microsoft/vscode/blob/main/src/vs/server/node/serverEnvironmentService.ts).
Prerequisite sources: [VS Code Linux setup](https://code.visualstudio.com/docs/setup/linux),
[Node 22 distributions](https://nodejs.org/dist/latest-v22.x/),
and [uv locked environment sync](https://docs.astral.sh/uv/concepts/projects/sync/).

## Use the extension

The Activity Bar hexagon opens Semantic Analysis. Server connection state and running work appear in the status bar; click the running task there to cancel. Clicking a result opens source and **CTK Inspector → AST Inspector** in the bottom panel. Plain script runs open **CTK Output** with the console's rendered output and diagnostics. Search file/result limits are explicit.

Opening a C/C++ file automatically activates the extension and loads **AST Inspector** in CTK Inspector, with keyboard focus and the caret kept in the editor. The panel starts directly with the fixed AST/Properties tabs and Run Action; there is no repeated inspector title or navigation row. Use VS Code's Hide Panel control to hide the whole inspector. The inspector belongs in CTK Inspector; it adds no section to Explorer. It stays hidden while files and cursor positions update; reopening restores the selected tab, expanded branches and latest node. Background loading does not switch away from your current sidebar or open a hidden result panel. The inspector loads the file's native TranslationUnitDecl and its direct declarations from that file. No search or action is required. Click any child to fetch its direct children on demand; loading appears in the status bar, repeated visits reuse retained native nodes, and failures appear in the status bar. Click **CTK · reload AST**, or run **CTK: Reload File AST**, to load a fresh file context; expired sessions do not leave raw cursor errors or retry rows in the inspector. The whole tree is not fetched upfront. First opening a file starts its own retained context; saving the active C++ file or changing CTK settings reloads it. Inspector-driven source navigation keeps the current node/context, including navigation into headers.

Each open C/C++ file keeps its own native AST session and inspector state. The first visit parses it; switching back restores its selected node, loaded children, expanded/collapsed branches and AST/Properties tab without reparsing. Split editors and filesystem aliases share the same file session. Switching to a script or another non-C++ editor leaves the last inspected AST available. Editing invalidates the source's native handles; saving refreshes its session automatically. Header changes and CTK settings conservatively invalidate cached sessions. Inspector-driven navigation into a header keeps its original translation unit and pins the source tab.

Saving a C/C++ file restores its selected node and expanded/collapsed branches in the refreshed AST, with AST/Properties kept on the same tab. Declarations use their semantic identities; other nodes use their structural context and source ranges adjusted for edits. The inspector never reuses expired native handles. A removed or ambiguous node falls back to its closest identifiable parent. Saves in inactive open files refresh their cached AST in the background without replacing the active inspector; returning uses that refreshed selection and tree. Refreshing does not move the editor caret or open a hidden inspector.

Retained native cursors are renewed once a minute while their owning context is open, including when the panel is hidden. Renewal uses only that worker's owned cursors; it does not reparse files or touch another client's sessions. Closing a file's last tab releases its worker, retained nodes and cached inspector state; closing one split keeps the remaining split's session. Closing an inactive file leaves the active inspector intact, and reopening a closed file starts a fresh context. Actions can share a retained file session; refreshing or closing Actions releases its borrowed reference while the file keeps its AST. Closing the window or unloading the extension stops renewal and releases its workers. A genuinely lost native session, such as a server restart, automatically refreshes the active file inspector; action results that no longer have valid native handles require Refresh.

AST Inspector has two full-width tabs: **AST** contains the expandable tree; **Properties** shows the selected node's Clang kind, name/signature, source link and preview, readable properties and source range. The tabs stay fixed at the top of the inspector, with Run Action at their right; the tree and Properties each scroll within the remaining height. **Double-click a tree row**, or press **Enter**, to select it and open Properties. Switching back to AST keeps the exact selection, expanded branches and loaded native children. Editor cursor changes update the selection without changing your tab; returning to AST reveals that selected row. Left/Right and Home/End switch focused tabs. Click a chevron to expand/collapse a branch without changing the inspected node; unloaded children are fetched on demand and reopening a branch reuses its native handles. Click a row to inspect and highlight it. Up/Down and Home/End move between visible nodes; Right expands or enters a branch, Left collapses or returns to its parent, and Space selects the focused node. Use the AST tree to select another node or the file root. Internal cursor/USR values, protobuf wrappers/enums, availability flags, supported scopes and whole-match dumps are excluded. Unknown properties are omitted.

Properties includes collapsible sections suited to the selected node. Classes/structs show their own declared methods, fields, static members, aliases and nested types grouped by **Public**, **Protected** and **Private** access; implicit compiler-generated members are omitted. **Inheritance** shows direct and transitive base paths with access and virtual inheritance, resolving aliases through native bindings; dependent/unresolved bases are marked. Functions/methods show an ordered **Parameters** table with names and types, including unnamed parameters; nested lambdas and other callables do not contribute parameters. Class-member names are links to that member's Properties. Enums show their enumerators and evaluated values; aliases show their underlying type. Existing expression/call/literal/operator facts remain available, with const/static/virtual/pure-virtual/mutable qualifiers when present. Statement and auxiliary nodes without extra facts do not display empty semantic sections. These facts reuse the retained AST and do not reparse the file.

Click a resolved **base class** in Inheritance to select its actual declaration, load its Properties and highlight its complete source range, including definitions in headers. Aliases select the underlying class. Its real TU/namespace ancestry expands in AST, while other branches stay open; select the derived class in AST to return to it. Use **Run Action** for the selected base, or right-click a base link for **Run Action…**. Both use the retained native declaration and reuse the parsed file. Unresolved/dependent bases remain plain text.

Base links also work with **unsaved C++ edits**. If edits made the displayed AST stale, following a base link rebuilds its context from private snapshots of the open source and dirty headers, then selects the same class by its semantic identity and highlights its current buffer range. Opening or explicitly reloading a dirty C++ file also uses its current buffer. Your files remain unsaved and their disk contents are untouched. The selected base can run actions against that same snapshot. Further edits invalidate it; a base link rebuilds it again on demand. A removed base reports that it changed instead of selecting another class with the same name. Snapshot files are released with the owning session.

In AST, base specifiers show their written type names. Expanding a resolved base or its TypeLoc children offers **Base declaration** to open the actual class, highlight its definition and run actions there. Properties includes the same link. These are explicit declaration references; the tree keeps Clang's actual child relationships. Aliases resolve to their underlying class through retained native bindings.

Selecting a declaration or member reference (`DeclRefExpr` or `MemberExpr`) offers **Referenced declaration** in Properties and **Declaration** in AST. Follow it to select the exact native declaration, expand its file ancestry and highlight its source, including methods and fields in headers. Local variables and overloaded methods remain distinct, and navigation reuses the parsed context.

Within Properties, **Source**, **Inheritance**, member groups, **Parameters**, **Properties** and **Source range** also have full-width collapsible headers. Click a header, or focus it and press Enter/Space, to fold it. These open/closed choices persist across node/tab changes and webview reloads. The AST tree appears directly in its tab, without an extra enclosing disclosure.

Selecting an AST child automatically reveals and highlights its complete source range in the C++ editor while keeping focus in the inspector. Selecting another tree node updates the highlight, including when it is in a header. The extension uses the server's exclusive end position and converts Clang's UTF-8 byte coordinates to VS Code's UTF-16 positions. Macro nodes highlight their expansion in the source. Missing ranges use a known source point without guessing a final token's length; nodes with no source clear the previous AST highlight. Editing the highlighted document clears the decoration; save and refresh analysis before navigating changed source.

With AST Inspector open, clicking or moving the cursor in a C++ editor, including one with unsaved edits, selects its smallest enclosing written AST node and automatically expands its ancestor branches in the file AST, including other functions and included headers. The selected row scrolls into view, while your exact caret, text selection and editor focus remain unchanged. Other expanded branches stay open. Selecting part of an identifier works too. A cursor position belongs to the token on its right; a node's exclusive end is outside that node. Outer whitespace and a trailing statement semicolon are ignored for nonempty selections. Events are debounced for 180 ms; inspector-created highlights do not trigger reverse lookup. A changed buffer rebuilds its retained AST from the current source and dirty headers; subsequent cursor moves reuse that snapshot. Superseded cursor requests cannot overwrite a later selection, and no source file is saved. Incomplete code keeps the last valid AST and reports a parsing error; another edit or save enables a fresh attempt. Native paths follow actual child edges and reuse the displayed tree's IDs, so further actions use the selected native node without reparsing. An unmatched position clears the tree selection, shows a status-bar notice and disables actions on the previously displayed properties. Lookup follows the retained TU tree, lazily adds declarations from an included header when needed, has no fixed source-file, visited-node or depth ceiling; failures are explicit.

Right-click any AST tree row and choose **Run Action…** to open the predefined/workspace action picker for that exact clicked node, including an unselected node whose children are still unloaded. Opening or cancelling the picker does not change the inspector selection. **Run Action** also appears at the far right of the fixed **AST / Properties** tab bar. It acts on the currently selected node from either tab and stays visible while the tree or properties scroll. Long node names are shortened visually with the full text available on hover. Choose an action (or create one), fill its arguments under **Options**, then press **Run** in Actions. The input label identifies that exact AST node. Cancelling the picker keeps the current action/input unchanged. Menus opened for an old file/context are rejected. Action results retain their original parsed context; a Symbol Search inspector transfers its live context to Actions when a choice is confirmed. Both paths reuse the native handle without reparsing or falling back to the file root. The **File root** control still returns to the actual parsed-file root, while action Back restores earlier results within that context.

Actions and Symbol Search inspect their original retained native nodes without reparsing. Symbol Search keeps its matched bindings and their parsed translation units alive; selecting a result sends its exact native node ID to the same inspector worker, without a second name or location lookup. Repeated selections and AST expansion reuse those IDs. A successful new search releases the previous search owner; a cancelled or failed search keeps the previous completed matches. Closing an editor tab does not discard the search result list's live matches. C++ edits or CTK settings changes invalidate the search context and require a new search; expired nodes fail explicitly instead of being relocated. Choosing an action transfers the live owner to Actions, so later searches cannot dispose that action's input. File opening has a separate inspector owner per file. Copied results from one-shot scripts retain the location-lookup path. Direct children load lazily through native child edges, including implicit/type-location nodes. File-root loading filters direct declarations to the requested file before collecting rows, so unrelated header declarations do not occupy that page. Some auxiliary AST kinds have a Clang kind and child navigation but no additional serialized properties. Matching and AST navigation have no fixed row, child, inspection or retained-handle count ceilings. Inheritance, parameters and source-selection paths also have no fixed display count ceilings. Configured server memory budgets, message limits, cursor admission, cancellation and idle expiry still apply. An explicit caller-selected navigation node budget remains available through the SDK; the inspector requests unlimited counts. Initial file inspection allows separate deadlines for parsing, root lookup and child loading; each RPC still uses ctk.rpcTimeoutMs. Limit/errors are reported explicitly. Loading appears in the status bar, and failed loads offer Retry while keeping the current AST facts visible.

Workspace scope searches the active file's workspace folder (or the first folder if none is active). **Open Output** exposes script emissions and error details directly from the shared panel.

Right-click a C++ file: **CTK → Select Action…** pins that file as the initial action target. **Run Script…** and **Run Predefined…** retain the original console-script and search commands. Semantic Analysis has its own icon, with no search entry in the file menu. CTK editors have a Run button. Syntax colors distinguish YAML front matter, commands, matcher categories, strings, numbers, variables and comments.

If parsing fails after a save, the inspector keeps the last valid AST, selected node, expanded branches and AST/Properties tab visible. **CTK · AST refresh failed** in the status bar names the file and shows the error on hover. Saved-file refreshes are transactional: the replacement tree appears only after parsing and state restoration succeed. Native navigation and actions on the old handles are disabled until a successful refresh. Fix the code and save again to retry automatically; tab switching and filesystem notifications do not repeatedly retry a failed save. Failed background saves keep that file's cached AST and report the error without replacing another file's inspector. The next successful save clears the error, restores surviving branches and enables native navigation/actions again. Closing the file's last tab clears its error and releases its session.

Compiler errors also appear under **CTK** in VS Code's **Problems** panel (View → Problems). Click an error to open its C++ file or included header at the compiler's exact line and column; Unicode positions are converted to VS Code coordinates. The next successful parse clears that file's errors, and closing its last tab releases them. Shared-header errors remain while another open file still reports them. Connection failures without compiler locations stay in the status bar.

When clang or another provider reports the same error at the same source position, Problems keeps that provider's entry and suppresses the matching CTK entry. Initial capitalization, whitespace and quote-style differences are ignored; C++ identifier spelling and case are preserved. CTK-only errors remain visible, and the CTK entry returns if the other provider removes its diagnostic. This updates automatically as providers publish results, including paths that refer to the same physical file.

Editing a C/C++ file immediately clears its stale parsing warning in the status bar and discards its CTK Problems entries, including cached entries hidden by clang and reports still being prepared. Removing a clang diagnostic while you type cannot bring back an old CTK error. Saving parses the new source and updates the status bar and Problems with only its current errors; a fixed file stays clear. Unrelated source files retain their errors. Header edits invalidate cached CTK errors conservatively, matching AST session invalidation. The last valid AST remains visible while you edit, and its stale native handles stay disabled until a successful save.

## Node actions

1. Open a C++ file, select **Actions**, and use the single **Select action…** picker. It lists predefined and workspace actions plus **Create action…**. Without an active C++ file, the first run asks for a file.
2. Expand **Options** for the action's arguments. Descriptions appear as input hints; required arguments expand automatically. Click **Run** to parse the file and execute the action.
3. Results form one outline: **file → Match [n] → bindings**. Each match starts collapsed; click its heading or focus it and press Enter/Space to expand or collapse only that match. Bindings appear as compact, indented child rows with tree guides; snippets are available on hover and in AST Inspector after selection. Each match keeps its caller, callee and other bindings together, including nodes located in another file. The automatic `root` binding determines the match's file and line; without it, the first binding supplies the location. Bindings remain independently selectable, and nodes from another file show that file beside their line number. File counts count matches, not individual bindings.
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

The completion worker acknowledges that Python has started before the 30-second request deadline begins; startup has its own 30-second limit. Identical requests share work while in progress. A timeout or broken worker closes that process, releases waiting requests and starts a fresh worker on the next completion attempt. Completed responses are not cached, so edits and filesystem changes remain visible.

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

`test:host` owns an isolated VS Code profile, extension directory, fixture workspace and server; set `VSCODE_EXECUTABLE_PATH` when VS Code is installed elsewhere. On macOS/Linux it closes its window and owned process groups on success, failure, interruption or the ten-minute overall deadline. `pnpm test:host-cleanup` verifies success/failure cleanup, forced shutdown and interruption using stand-ins that open no windows. The host suite checks actual webview result rendering, source navigation, matcher completion, hover, predefined analyses and console scripts. Validation outcomes and repository-wide limitations are recorded in repository file `docs/vscode-prototype-progress.md`.

Design: https://chatgpt.com/space/page_befdeedd156081919409f24942e91485.

References: [Webview security](https://code.visualstudio.com/api/extension-guides/webview), [language providers](https://code.visualstudio.com/api/language-extensions/programmatic-language-features), [contributions](https://code.visualstudio.com/api/references/contribution-points), [ESM support](https://code.visualstudio.com/updates/v1_100#_esm-support-for-extensions).
