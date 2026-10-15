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

Scripts run in a cancellable worker using the native ANTLR DSL. The CTK editor supplies TextMate syntax scopes plus offline matcher completion and hover. Compilation flags, compilation database, endpoint and shared configuration are configurable. Workspace scope covers the selected workspace folder. Execution is disabled in untrusted workspaces, and file/result limits are explicit.

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

This is a runnable prototype rather than a released extension. It runs the server's native DSL; Python-console-only helpers and runnable declarations are not implemented. Matcher completion covers the checked-in offline catalog and local `let` names; arbitrary user-defined function signatures are not yet inferred. The custom block opens in the native CTK editor for highlighting/completion; its sidebar preview is plain text. Native server and extension host must share source paths. No VS Code marketplace publication or global extension installation was performed.

The real host confirms webview rendering and language providers. Pixel-level mockup parity and manual picker/color acceptance remain to be reviewed; no screenshot-based visual acceptance is claimed.
