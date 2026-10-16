# VS Code prototype progress

Branch: `codex/vscode-extension-prototype`.

Worktree: `/Users/husam/.claude/worktrees/clang-toolkit/vscode-extension-prototype`.

Base: `2ef4baec833ccd5caa28ce4cef2ae95a0d2d7fc5`. The original checkout's unrelated CFG changes were preserved.

Design source: [normal proposal Page](https://chatgpt.com/space/page_befdeedd156081919409f24942e91485).

- [x] Create an isolated worktree from committed HEAD.
- [x] Implement one shared action catalog, parameter picker and Semantic Analysis view.
- [x] Connect predefined analyses and native scripts to the TypeScript SDK and native server.
- [x] Add CTK highlighting, matcher completion, hover and file context-menu execution.
- [x] Verify native results, real webview rendering, extension-host workflows and VSIX contents.
- [x] Run repository Python and C++ checks and record results, including failures.

## Implemented

The Activity Bar opens one Semantic Analysis panel. Find symbols, function/class/variable presets, class members, saved scripts and custom blocks use the same scope, execution and file-grouped results. Required parameters use VS Code input, choice or path pickers. File menus contain Run Script and Run Predefined. Results open their source location and CTK Result details. Script output and errors are reachable through Open Output.

Scripts now run in a cancellable worker using the compiled console batch entry point (version 0.1.2 correction below). The CTK editor supplies TextMate syntax scopes plus console completion and hover. Compilation flags, compilation database, endpoint and shared configuration are configurable. Workspace scope covers the selected workspace folder. Execution is disabled in untrusted workspaces, and file/result limits are explicit.

The committed native API advertises `BINDING_MATCH_SCOPE_CHILDREN`, but the vendored TypeScript schema omitted it. This prototype updates that enum in the SDK schema and generated type, with a real protobuf wire-decoding regression check; it does not loosen boundary validation.

## Validation on 2026-10-15

| Check | Result |
| --- | --- |
| Extension strict TypeScript and Biome | Passed |
| Extension model/unit tests | 6 passed |
| Extension native integration | 5 passed against the isolated binary |
| Real VS Code extension host | Passed: actual webview match/file-group rendering, source/details navigation, offline completion/hover, predefined analysis, native script and overlapping-run rejection |
| SDK strict TypeScript and unit tests | Passed; 52 passed, 24 separate integration tests skipped |
| Native C++ suite | All 363 covered and passed across runs; six storage tests failed during a shared-storage parallel run, then all six passed serially with a fresh isolated storage root |
| Python unit suite | 2,085 passed, 22 failed |
| Python end-to-end suite | 94 passed, 58 failed |
| VSIX package | Bundles SDK/dependencies, protobuf schemas, matcher catalog, grammar and examples; development tests and node_modules excluded |

The repository-wide Python checks are **not green**. The unit failures report a syntax error loading the existing user library `/Users/husam/.ctk/lib/ctk_helpers.ctk`. Most end-to-end failures show the same preload error; other console/native assertions and terminal timeouts also remain in the full report. No Python, C++ or global library source was changed for this prototype. These results are not evidence that the full repository is ready to release.

Raw validation output is retained locally under `vscode/artifacts/validation/` and excluded from Git/VSIX. The initial serial C++ run covered tests 1–119, the remaining run covered 120–363, and the six failed storage cases were rerun serially.

## Prototype boundary

This is a runnable prototype rather than a released extension. Predefined analyses use the TypeScript SDK; scripts use the bundled Python compiled console, including helpers and runnable declarations. Native server and extension host must share source paths. The prototype was subsequently installed locally for the user's trial; no marketplace publication was performed.

The real host confirms webview rendering and language providers. Pixel-level mockup parity and manual picker/color acceptance remain to be reviewed; no screenshot-based visual acceptance is claimed.

## Autocomplete correction, version 0.1.1

The initial matcher-only provider did not provide the console's member or user-function behavior. The editor now uses the same `ReplCompleter` and `PrototypeCompleter` as the console, with safe draft type inference and helper/header inspection. It supplies contextual matcher/keyword suggestions, match/list/map/string/tree members, local and library function signatures/defaults, Markdown definitions, and argument hints. CTK-specific defaults enable automatic suggestion popups even when global inline-completion settings suppress them. Existing parentheses and text after an earlier-line cursor are preserved.

The sidebar's custom block is explicitly a read-only preview; its editor button reuses the existing CTK document. Python 3.14 with console dependencies is discovered or configured through `ctk.pythonPath`. This version's completion never evaluates user drafts, calls helper bodies, or sends native queries; version 0.1.5 adds a separate native class-name query. Members of unknown runtime return values are not invented.

Seven focused Python regressions and the expanded real VS Code host test pass, covering member metadata, library and user-defined signatures, grammar contexts, strings/comments, earlier-line insertion, nested argument hints, actual source edits and CTK suggestion defaults. The previous repository-wide Python failures remain recorded above; no console/runtime or native-server source was changed by this correction.

Installed version 0.1.1 was also verified manually in the user's normal VS Code profile: typing `.` after `x` in `autocomplete-demo.ctk` automatically opened the suggestion list containing `filter`, `isEmpty`, `length`, `one`, `root`, `sort`, `symbol` and `unique`, with console method descriptions. This worked with the user's inline completion provider still active. The existing unsaved user script was preserved, and isolated extension-test instances exited after validation.

## Console execution correction, version 0.1.2

Saved scripts, custom blocks and Run Current Script now invoke the actual `cli.app._run` compiled-console batch entry point in a separate Python process. The bridge supplies workspace compiler settings and literal `arg` inputs, observes visible results for source navigation, and leaves parsing, helper preloading, imports, function execution, output routing, recovery/exit handlers, session commands and cleanup to the console. The configured helper directory is shared with autocomplete. Each run starts a fresh session, like `ctk SCRIPT.ctk`.

Editor runs use current unsaved text without a save prompt. Script-relative imports retain the real source path; untitled blocks use the workspace directory. Scripts without C++ inputs can run locally. Workspace scope executes once with all files as default matcher inputs. `arg.FILE` is the selected/first input; unquoted legacy placeholders become argument references, never interpolated user code. Console output opens automatically. Returned/printed match bindings and helper symbol summaries retain file grouping and source navigation. Stop requests console cancellation, with a ten-second termination fallback.

Focused validation: 11 extension unit/console-worker tests passed, seven autocomplete adapter tests passed, six native integration tests passed, and the real VS Code extension-host test passed with an unsaved script calling `scale`, `classByName` and `classFields`. Strict TypeScript, Biome and whitespace checks passed. The exact `console-demo.ctk` artifact also ran in a real TTY through `uv run ctk` with the user's default helper preload: `42`, `fields: 1; methods: 1`, and the real `demo::Order::quantity` summary at `demo.cpp:3`. Previous repository-wide Python failures remain documented above; no Python console/runtime or C++ implementation was changed.

Version 0.1.2 was packaged, installed and reloaded in the user's existing VS Code trial window. Clicking the editor Run button for `console-demo.ctk` visibly produced the same console output and a clickable `demo::Order::quantity` result at line 3. The normal default `~/.ctk/lib` preload was used. The demo remains open for trial, the user's existing unsaved script was preserved, and no isolated extension-test processes remained after validation.

## Filesystem completion correction, version 0.1.3

The editor now offers the console's actual filesystem path candidates inside command operands, including quoted paths after compiled function definitions and inside function bodies. The adapter obtains command starts from the console's own completion catalog, then lets its existing path-role grammar choose files or directories; it does not evaluate drafts. Saved-script imports resolve against the script directory, while other operands use the workspace directory. Earlier-line edits retain closing quotes and later text. File/folder icons, quote/slash triggers and CTK string suggestions are enabled; selecting a folder requests its children.

Validation: all 10 adapter tests passed, all 92 focused console filesystem/completion/editor tests passed, and all 11 extension unit/console-worker tests passed. Strict TypeScript, Biome, whitespace checks and the real VS Code extension-host workflow passed, including actual file insertion, folder continuation, script-relative import suggestions and the CTK string-suggestion setting. Native query integration and full repository suites were not repeated for this editor-only change; the earlier suite results remain above.

Version 0.1.3 was packaged, installed and reloaded in the normal trial window. Typing `dem` inside the quoted `parse` operand after a function definition automatically displayed `demo.cpp` with file metadata; Tab inserted `"demo.cpp"` without altering the closing quote or following `print scale(21)` line. The separate `path-completion-demo.ctk` remains open and saved. All three pre-existing unsaved drafts were preserved; isolated test windows exited.

## Helper argument filesystem completion, version 0.1.4

Filesystem completion now applies to helper file arguments, including the first parameter of `classByName`, `classInfo`, `classTemplateInfo`, `ancestors`, `functionInfo` and `callSites`. The editor parses dormant function definitions to identify direct native file inputs and follows unchanged parameters forwarded through helper or user-defined calls. It analyzes only reachable function dependencies and caches syntax facts. Class-name arguments, unrelated nested calls and parameters requiring semantic fields retain normal completion. Unknown or complex data flow is treated conservatively. Bodies and defaults are never executed for completion.

The lexer tracks the active argument through nested calls and multiline comments. The existing console path provider supplies files, directories, absolute/relative paths, quoting and suffix preservation. An explicit execution override also clears any previously associated draft, preventing an earlier editor script from replacing the newly selected action's source.

All 13 adapter tests, all 11 extension unit/console-worker tests, strict TypeScript, Biome and whitespace checks passed. The real VS Code host passed file insertion into `classByName`, preservation of the class-name argument and later source, folder suggestions, user-defined file parameters and successful execution of the completed call against the native fixture. Previous repository-wide suite results remain above; native and console implementations were unchanged.

Version 0.1.4 was packaged, installed and reloaded in the user's existing trial window. Typing `dem` inside `classByName("", "demo::Order")` automatically suggested `demo.cpp`; Tab inserted it, and Run Current Script returned the real `demo::Order::quantity` field at line 3. The saved `helper-path-demo.ctk` remains open with its output. All three existing unsaved drafts were preserved, and isolated test windows exited.

## File-dependent class-name completion, version 0.1.5

The second `classByName` argument now offers fully qualified class/struct names found by the native server in the first argument's translation unit, including headers. The Python adapter supplies only safely inferred target/context metadata; literal paths, literal path variables, parsed-tree variables and the selected `arg.FILE` are supported. It never executes a draft, helper or default to resolve a file. Dynamic expressions receive no semantic suggestions.

A separate Node worker uses the existing class matcher and compiler/database/server settings. Results are deduplicated, source-located and bounded; completed query results expire after two seconds, at most eight entries are retained, and narrower prefixes reuse complete broader queries. Source/header/settings changes invalidate pending/cached queries. Dirty C++ buffers require saving before native suggestions. The completion provider checks cancellation and document versions, preserves existing quotes and later source, and reports native failures in CTK Completion output.

Focused validation: all 15 Python adapter regressions, 11 extension unit/console-worker tests, seven native integration tests, strict TypeScript, Biome and whitespace checks passed. Native tests cover qualified class names, included headers, duplicate declaration filtering, switching the first file, source edits and missing files. The real VS Code host passed second-argument completion, applying the actual edit without changing later source, selected-file completion and successful execution of the completed `classByName`/`classFields` script. Earlier repository-wide suite limitations remain recorded above; the native server and console runtime implementations are unchanged.

Version 0.1.5 was packaged, installed and reloaded in the existing trial window. In the normal profile, Ctrl+Space inside the second argument displayed `demo::Order` with a class icon, `demo.cpp:2` and the actual struct declaration. Automatic popup behavior was not confirmed in this profile; its global string quick-suggestion preference is disabled. Existing user preferences were preserved.

Tab inserted the qualified class name while retaining both quotes and the following `classFields(node)` line. Running the saved `class-name-demo.ctk` returned the real `demo::Order::quantity` field at `demo.cpp:3`. The completed demo remains open, all three existing unsaved user drafts were preserved, and no isolated extension-test instances remained.

## Automatic class-name popup, version 0.1.6

The normal profile reproduced a missing automatic popup while Ctrl+Space returned the correct native classes. A CTK-specific workspace quick-suggestion override did not restore it and was removed. The installed VS Code implementation also allows inline completion providers to suppress normal quick suggestions independently of the editor setting.

The extension now opens the standard completion popup after a 160 ms pause in class-name typing. It resolves the actual `classByName` second-argument context through the existing safe adapter before opening suggestions, so ordinary strings, comments, first arguments and other helpers do not receive this extra trigger. It coalesces edits, waits for the editor's updated cursor, rejects stale document/cursor/focus changes and cancels when switching editors or disposing the extension. Completion insertion and undo/redo do not reopen the popup. The optional `ctk.automaticClassSuggestions` setting defaults to true; global editor preferences and inline completion providers remain available.

Validation: 14 extension unit/console-worker tests passed, including three new automatic-trigger regressions for rapid typing, delayed cursor updates, non-class contexts, stale lookups, cancellation and disposal. The focused trigger tests passed again after the cursor-update guard changed; strict TypeScript, Biome, whitespace checks and the complete real VS Code host workflow passed. Native server, console runtime and semantic queries were unchanged; their earlier results remain above.

Installed version 0.1.6 was reloaded in the normal trial profile with the original workspace settings. Typing the individual keys `d`, `e`, `m` in the second argument automatically displayed the real `demo::Order` class suggestion with `demo.cpp:2` and its struct declaration; no completion shortcut was used. The inline completion provider remained active. Tab accepted the suggestion and the completed demo was saved. All three pre-existing unsaved drafts were preserved, and isolated test instances exited.

## YAML node actions, version 0.2.0 (2026-10-16)

Semantic Analysis now has Symbol Search and Actions tabs. Actions use one native picker for predefined/workspace definitions and creation. YAML front matter supplies the unique name, description and typed/defaulted arguments; the CTK body becomes a function with an implicit first `node` argument. Required arguments expand Options, and argument descriptions appear as input hints. `.ctk-action` files have YAML highlighting and the existing console completion/signature providers in their CTK bodies, including source-offset mapping across front matter.

A persistent compiled-console worker owns parsed roots and result collections. Opaque binding handles reference real retained native selections; serialized data is used only for display. Bindings outline and file/match/binding groups preserve every binding and match association. Select a binding, choose another action with the same picker, and run on that exact node without reparsing. Back restores earlier results; File root restores the original translation-unit input. Refresh/Close releases session handles. Source edits and settings changes invalidate the context; errors and cancellation preserve earlier successful results. At most 32 successful runs are retained. Actions start from one translation unit; Symbol Search retains workspace scope. Connection/task state and cancellation are in the status bar.

Validation:

| Check | Result |
| --- | --- |
| Strict TypeScript, Biome, whitespace | Passed |
| Extension unit/worker suite | 20 passed |
| Python editor adapter regressions | 15 passed |
| Native extension integration | 9 passed; ambient-library check is opt-in |
| Real VS Code host | Passed: both actual webview result views, source navigation, selected-node follow-up, parse count staying 1, Back, workspace YAML discovery, current unsaved action execution, completion edits preserving YAML/later CTK, stale-buffer rejection and overlapping-run protection |
| Native build and C++ suite | 363 passed; initial serial tests plus remaining tests with a separate storage root per process |
| Repository Python units | 2,085 passed, 22 failed; same external helper-library preload failures recorded for the original prototype |
| Repository Python end-to-end | 93 passed, 59 failed, 649 warnings; includes external helper preloads and remaining native/console assertions |
| VSIX | Version 0.2.0, with bundled action definitions, persistent host and YAML grammar/parser |

The user's current default `/Users/husam/.ctk/lib/ctk_helpers.ctk` also fails the compiled-console action preload at line 16 because it uses unsupported pipe (`|`) syntax. This was reproduced by the opt-in ambient-library native test; the two isolated retained-action scenarios still passed. Configuring `ctk.libraryDirectory` to this checkout's `skills/ctk-script/scripts` passes the real editor and native workflows, including helpers/user functions. An existing empty directory is usable when helpers are unnecessary. The user's helper library and main checkout were preserved. No broad console language update is claimed by this prototype.

Validation logs are retained under `vscode/artifacts/validation/actions-20261016/` and excluded from Git/VSIX. Isolated extension-host windows exit after their checks; the user's existing trial installation is unchanged by this implementation. Screenshot-based visual acceptance is not claimed.
