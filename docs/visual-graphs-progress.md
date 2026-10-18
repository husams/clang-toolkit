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
- Full existing VS Code host regression succeeded (`CTK_EXTENSION_HOST_PASS`, `CTK_LARGE_AST_HOST_PASS`, owned test processes closed).
- Python units: 3,046 passed against worktree sources.
- Existing native build: 439/440 cases passed after retrying seven storage cases with private storage. `ProjectIndexServiceTest.SharedHeaderPayloadIsStoredOnceWithEveryTuProvenance` still fails independently of this extension change (zero symbols instead of 20). No native/server source was changed; this is a baseline verification limitation, not a green complete native suite.
- Native demo capture: 302 distinct functions, 307 edges, five CFG blocks and one parse. Browser interaction verified all 302 functions stay loaded across drill/back navigation and the previous pan/zoom returns unchanged; font size stays at least 11px. State tests cover 3,001 nodes, shared callees, recursion, hidden-path reveal and collapse/reopen persistence.

## Try it

From `vscode/`, run `node scripts/preview-graphs.mjs`. It discovers the shared native build and Python environment (or honors `CTK_SERVER` / `CTK_PYTHON`), generates a real C++ fixture and opens an isolated development host. Use **CTK: Show Call Graph**, **Expand downstream**, then **Fit graph**. Select a function or statement and use **CTK: Show CFG** for its native CFG.

The preview server uses a short private `/tmp/ctk-vscode-graphs-*` socket/profile directory to stay below macOS IPC path limits. Process metadata, launch logs and the C++ fixture are in ignored `vscode/artifacts/graph-preview/`. Stop only that server with `node scripts/preview-graphs.mjs --stop`.

Installable package: `vscode/artifacts/clang-toolkit-prototype.vsix` (0.3.0). It includes the pinned local ELK layout engine and needs no webview network access. The graph covers one translation unit and non-system headers, with incomplete native results reported in the view.
