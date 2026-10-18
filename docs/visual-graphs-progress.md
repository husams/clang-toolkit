# Extension graph views

Worktree: `codex/visual-callgraph`, based on `a9e355b` (the current extension checkout).

- [x] Read existing inspector/session ownership and native graph contracts.
- [x] Native call graph and CFG display projections from the retained AST.
- [x] Directed visual graph, direct expansion/collapse, search, pan/zoom and readable names.
- [x] Breadcrumb camera restoration, retained branches, and fullscreen editor view.
- [x] Run verification, package version 0.3.0 and launch an isolated preview.

No matching extension graph implementation was present in the wiki index; current checkout code and the approved interactive mockup are the implementation references.

## Verification (2026-10-18)

- Type check, build, lint and VSIX packaging succeeded. Lint retains one existing informational suggestion in `inspector-bookmark.test.ts`.
- Extension units: 123 passed; editor-console checks: 20 passed.
- Live extension/native tests: 23 passed, one existing optional default-library test skipped.
- Focused real VS Code test: call graph and CFG webviews render under the actual webview CSP; native if-edges display True/False.
- Final worker-backed large-graph VS Code test passed with `CTK_TEST_GRAPHS_ONLY=1 CTK_TEST_GRAPHS_LARGE=1`: 302 native functions render in fullscreen and all 302 expansion flags return to the inspector. Layout runs in a local blob worker; bridge intersections are cached per layout. Pan/zoom changes made while arrangement is pending are kept.
- Full existing VS Code host regression succeeded (`CTK_EXTENSION_HOST_PASS`, `CTK_LARGE_AST_HOST_PASS`, owned test processes closed).
- Python units: 3,046 passed against worktree sources.
- Existing native build: 439/440 cases passed after retrying seven storage cases with private storage. `ProjectIndexServiceTest.SharedHeaderPayloadIsStoredOnceWithEveryTuProvenance` still fails independently of this extension change (zero symbols instead of 20). No native/server source was changed; this is a baseline verification limitation, not a green complete native suite.
- Native demo capture: 302 distinct functions, 307 edges, five CFG blocks and one parse. Browser interaction verified all 302 functions stay loaded across drill/back navigation and the previous pan/zoom returns unchanged; font size stays at least 11px. State tests cover 3,001 nodes, shared callees, recursion, hidden-path reveal and collapse/reopen persistence.

## Try it

From `vscode/`, run `node scripts/preview-graphs.mjs`. It discovers the shared native build and Python environment (or honors `CTK_SERVER` / `CTK_PYTHON`), generates a real C++ fixture and opens an isolated development host. Use **CTK: Show Call Graph**, **Expand downstream**, then **Fit graph**. Select a function or statement and use **CTK: Show CFG** for its native CFG.

The preview server uses a short private `/tmp/ctk-vscode-graphs-*` socket/profile directory to stay below macOS IPC path limits. Process metadata, launch logs and the C++ fixture are in ignored `vscode/artifacts/graph-preview/`. Stop only that server with `node scripts/preview-graphs.mjs --stop`.

Installable package: `vscode/artifacts/clang-toolkit-prototype.vsix` (0.3.0). It includes the pinned local ELK layout engine and needs no webview network access. The graph covers one translation unit and non-system headers, with incomplete native results reported in the view.

## 2026-10-18: native breadcrumb verification

Used macOS UI automation against the isolated VS Code development host, clicked `save_order`, and returned using the `submit` breadcrumb. The original navigation message added a 13-pixel row and shifted the returned graph by 8 pixels. Removed that redundant message; the breadcrumb already identifies the focused function, and native warnings now remain intact during navigation.

Retested against the user's original view: all 302 functions remained expanded, child focus zoomed to 50%, and the breadcrumb restored the original 2% overview. All 27 visible function buttons returned to identical screen coordinates and sizes. The graph was left on `submit` at the original pan and zoom. Evidence is in `vscode/artifacts/graph-preview/breadcrumb-verification.json` and `breadcrumb-verified.png` (local, ignored artifacts).

## 2026-10-18: reopen and saved view restoration

Native VS Code testing exposed two camera resets: revisiting a function outside the current breadcrumb trail ignored its saved camera, and the first ResizeObserver callback could replace the restored camera with a fitted view. Both now restore the existing camera. The new state regression covers revisits after serialization with 302 functions expanded.

Exited fullscreen from `submit → save_order → save_order_4`, confirmed all 302 functions and breadcrumbs returned to the Inspector, then reopened fullscreen. The three-level breadcrumb trail survived. Native UI comparisons before and after this cycle matched every visible function position, size and expanded control: `save_order_4` at 100% (10 visible function buttons), `save_order` at 40% (24), and `submit` at 3% (35). All 302 functions remained in the layout. The actual VS Code window was left on the submit overview. Evidence is in ignored `vscode/artifacts/graph-preview/reopen-verification.json` and `reopen-verified.png`.

Extension regression tests: 124 passed, 24 optional live tests skipped. Type checking and lint passed, retaining the existing informational template suggestion.
The rebuilt large native VS Code host regression passed with a three-function trail, distinct ancestor cameras, and an explicit 100% current camera; closing the editor returned the identical serialized state to the Inspector. One initial run timed out during AST loading before graph assertions; the isolated retry passed and closed all owned test processes. VSIX packaging succeeded (0.3.0, 5.43 MB), and the packaged graph sources contain both fixes.

## 2026-10-18: real VS Code restart persistence

Added validated workspace graph sessions with atomic file replacement, shutdown flushing, a `ctk.graph` webview serializer and **CTK: Reopen Last Graph**. Both Inspector and fullscreen changes update the saved session. Restored graphs retain their native display projection and keep AST actions disabled until a fresh native inspection supplies handles. The saved analysis can be refreshed with Show Call Graph or Show CFG.

Backed up the exact live graph, then quit preview process 42165 and launched process 98641 with the same profile and workspace, without the demo test driver. Reopen Last Graph restored all 302 expanded functions and `submit → save_order → save_order_4`. Every visible function position, size and expansion control matched before/after restart: submit at 3% (35 function buttons), save_order at 40% (24), save_order_4 at 100% (10). The serialized expansion flags and all three camera values also matched.

A second normal quit/restart (98641 → 6009), with no test driver and no reopen command, automatically restored the graph tab, the complete three-function trail, all 302 expansions and the same 100% child view. The exact saved ancestor cameras remained intact. Local evidence is in ignored `vscode/artifacts/graph-preview/restart-verification.json` and `restart-verified.png`.

Five new storage tests cover fresh-instance recovery of 302 expansions and cameras, overlapping saves, separate graph kinds, damaged storage and invalid payloads. The native large call graph/CFG host regression passed and closed its owned processes; type checking, lint, and the complete extension suite passed. Lint keeps one existing informational template suggestion.
Final verification: 130 extension tests passed, 24 optional live tests skipped. The additional Inspector regression confirms that restoring a saved graph cannot revive expired native AST handles. The rebuilt 0.3.0 VSIX packaged successfully (5.44 MB).
