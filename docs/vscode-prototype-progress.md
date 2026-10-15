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

The sidebar's custom block is explicitly a read-only preview; its editor button reuses the existing CTK document. Python 3.14 with console dependencies is discovered or configured through `ctk.pythonPath`. Completion never evaluates user drafts, calls helper bodies, or sends native queries. Members of unknown runtime return values are not invented.

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
