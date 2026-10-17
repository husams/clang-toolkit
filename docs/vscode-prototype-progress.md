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

## Helper compatibility correction, version 0.2.1

The extension bundled a console older than the user's pipe-based helper library.
The prototype now includes the existing merged console pipe/tuple implementation
from PR #33 (0410df4), without changing the user's helper file. Execution,
completion and scripts all receive this runtime in the rebuilt VSIX.

The default-library native regression now calls `classByName` and `classFields`,
uses a user-defined pipe function, returns a live field match and runs another
match on that binding with the parse count remaining 1. All three retained-action
scenarios pass against the unchanged default helper library. The real VS Code
host also passes its complete script, completion and two-tab Actions workflow
without a library-directory override. Version 0.2.1 contains an editable
`order-fields.ctk-action` example and `actions-demo.cpp` trial fixture.

Validation: 84 pipe/tuple unit checks, 20 extension checks and 15 Python editor
adapter checks pass. Full Python units: 2,169 passed, 22 failed; those remaining
failures use the legacy console engine, which cannot import the modern console
library. Selected native console end-to-end checks: 14 passed, 9 failed for that
same legacy-engine preload. No native C++ code changed; the preceding 363 native
cases remain the applicable C++ verification. Logs are in
`vscode/artifacts/validation/helper-fix-20261016/`.

After fresh user confirmation, the verified VSIX was installed in the normal
VS Code profile; the extension listing confirms version 0.2.1. A new normal trial
window is open on `vscode/artifacts/try-it/actions-demo.cpp` with Actions selected.
Running the workspace Order fields action through the unchanged default helper
library displayed `demo::Order::quantity` in the bindings outline and a connected
server status. Existing user windows were preserved, and isolated test windows
closed after verification.

## Custom action creation correction, version 0.2.2

Create action now opens a saved, pinned template directly and keeps editor focus,
without a second naming prompt. Unique names avoid existing files, invalid action
files and equivalent callable names. Creating from the selected-node picker keeps
that exact live input. The owning workspace folder receives the new file.

Manual testing also found that running a custom action after the native cursor
expired showed `cursor unavailable` without marking the context stale. The
extension now offers a clear Refresh message and preserves the C++ target when
refreshing from an action editor. It does not automatically retry user code.

Validation: 21 extension tests, four native action tests (including unchanged
default helper loading and closed-context recovery), type checking, Biome and the
complete real VS Code host passed. The host creates two distinct action files,
runs a new action on a selected function without reparsing, and refreshes/reruns
while its editor is active. An initial extended host check encountered a delayed
source-save invalidation; creation checks now precede the existing dirty-source
scenario so they do not depend on that event timing.

Installed version 0.2.2 in the normal profile and reloaded the existing trial
window. A mouse click on Create action opened `my-action-2.ctk-action` immediately,
with editor focus and the correct C++ input. Clicking Run returned five function
matches and connected status. Existing user windows were preserved; isolated test
windows closed after verification. The VSIX passed ZIP validation; SHA256 is
`48cc04ce732a445bca42b507b7162b5cf3926735a95576f8bdd7f1cee3678dbc`.

## Live YAML metadata, version 0.2.3

Editing the selected action updates its picker label, description and Options
directly from the current editor buffer, including unsaved changes. Added and
removed arguments, descriptions, types and defaults refresh without reselecting
the action. Compatible entered values survive; untouched defaults follow the
updated YAML. Reopening the catalog reads unsaved names and omits the old name.

Incomplete metadata retains the last valid controls, shows an editing message and
disables Run until repaired. Reverting/closing an editor reloads its saved
definition. Metadata changes do not execute code or discard the retained AST or
results. Running code keeps its own definition/value snapshot for history even
if the editor changes while it runs.

Validation: TypeScript, Biome, 22 extension tests and the complete isolated VS Code
host passed. The host verifies actual rendered labels, fields and defaults after
unsaved edits, preserves a user value across invalid YAML and argument additions,
checks argument removal and catalog names, then executes without saving or
reparsing C++. The shared Python and native C++ implementations did not change;
the existing repository-wide limitations recorded above remain.

Installed v0.2.3 in the normal profile and reloaded the existing trial window.
Manual edits in a new example renamed the selected action, added and changed its
Options, preserved `demo::adjust` while adding a numeric argument, and returned
one match for that function before saving. The example was saved afterward and
left open with Options and results. Isolated test windows closed normally.
The VSIX passed ZIP verification; SHA256 is
`557e2398396d7884476e73cc6c27ec4591ce8777ab3ca230fb285843b854b630`.

## Options argument autocomplete, version 0.2.4

String fields in Options now provide automatic suggestions on focus and while
typing. The console's syntax inspection identifies file operands, class-name
matcher operands and parameters forwarded through known helpers. No action body
or default is executed for inference. Optional string-argument metadata
`completion: path | file | folder | class` handles ambiguous definitions.

Paths are completed as literal values without adding CTK quotes. Relative paths,
absolute paths, home paths, spaces, quotes, and folder continuation are supported;
folder-only metadata filters out files. Class suggestions use the current analysis
translation unit and the existing bounded native class lookup, including headers
and compiler/server settings. Dirty C++ inputs request saving rather than querying
outdated disk contents. Requests/results are bounded and stale field/revision
responses are ignored. Completion has its own workers and does not change the
retained action context or results.

The popup supports Up/Down, Enter/Tab, Escape and Ctrl+Space, with combobox/listbox
roles and VS Code suggestion colors. Selecting a folder requests its children.
The example `vscode/examples/argument-completion.ctk-action` demonstrates inferred
class-name and source-file roles.

Validation: TypeScript, Biome, 24 extension tests, 16 console adapter checks and the
complete real VS Code host passed. The host checks native class suggestions and
literal file/folder candidates before an action has run, verifies that a marker
file has not been written and retained parse count remains zero, then runs the
action and observes the marker and field result. Shared console/native sources
were unchanged; the preceding repository-wide limitations still apply.

Installed v0.2.4 in the normal profile and reloaded only the existing trial window.
Manual typing opened class and filesystem popups without Ctrl+Space. Tab accepted
`demo::Order`; a direct mouse click and Enter accepted `actions-demo.cpp`. Tab on
`.ctk/` immediately listed its `actions/` child. Running those completed values
returned `demo::Order::quantity`. The new example was saved and left open with
Options/results; isolated test windows closed normally. The VSIX passed ZIP
verification; SHA256 is
`4d62106dfeea5307e5fac4ecedae36cad38f6181f9046b8a68e4e62fe6470938`.

## Preserve related bindings per match, version 0.2.5

Actions now use one outline: file → match → bindings. The binding-name view and
redundant view switch are removed. Match IDs keep related callers, callees and
other bindings together, including bindings in other files and repeated nodes
shared by multiple matches. The automatic `root` binding supplies the owning file
and line; the first binding is the fallback for results without `root`. File counts
count matches. Cross-file bindings display their own file/line and retain their
independent source navigation and native handles. Match order and binding order
are preserved. Back restores the earlier complete match outline.

Added a caller/callee example and regression coverage for interleaved bindings,
cross-file relationships, identical locations in distinct matches, missing roots,
and empty results. TypeScript, Biome, 27 extension unit tests, 16 console adapter
checks and the complete isolated VS Code host passed. The host rendered two
caller/callee matches sharing a header callee under one source-file group,
asserted every match's exact binding handles, navigated to that header and ran
another action on the selected callee with parse count still one, then restored
the original rows with Back. Native/shared console code was unchanged; previously
recorded repository-wide test limitations still apply. Logs are in
`vscode/artifacts/validation/match-groups-20261016/`.

Installed v0.2.5 in the normal profile and reloaded the existing trial window.
Selected the new Caller callee example through the actual action picker and ran
it against `actions-demo.cpp`. The installed UI showed one file, one match at
line 8, and its call/callee/caller/root bindings together. The old Bindings/Files
switch is gone. The example/result remain open for trying; isolated host windows
closed normally. VSIX ZIP verification passed; SHA256 is
`8b4acf6cd7dc9beffd8bf18e6f1a34b70e12ea7194790529594ed75bd935bb50`.

## Explicit collapsible match rows, version 0.2.6

The previous outline kept match IDs together but its binding rows visually lined
up with match headings, and expanded code snippets made it read like a flat list.
Each `Match [n]` now starts collapsed and expands independently through its native
disclosure heading (mouse or Enter/Space). A separate indented child group with
tree guides contains compact binding rows. Source excerpts remain in tooltips
and CTK Result after selection. Selecting bindings and publishing new state do
not recreate unchanged results or reset open/closed match state.

TypeScript, Biome, 27 extension tests and the complete isolated VS Code host
passed. The host now also asserts that each caller/callee match starts collapsed
while retaining every exact binding handle, and still verifies cross-file source
navigation, follow-up without reparsing and Back. Shared backend sources are
unchanged. Logs: `vscode/artifacts/validation/collapsible-matches-20261016/`.

Installed v0.2.6 and reloaded only the existing trial window. A separate
`match-groups-demo.cpp` fixture produced two matches through the real action
picker and Run button. Both began collapsed. Clicking Match [1] revealed only
its four indented bindings; clicking it again hid them. Expanding Match [2]
revealed only its own bindings while Match [1] stayed closed. The trial remains
in that state. Isolated test windows closed normally. VSIX ZIP verification
passed; SHA256 is
`cb578d67bbbc345fea50fe4a4a13ae37ee520c1d8152d8d4101dcfdd542ca244`.

## Caller/callee example clarity, version 0.2.7

The two fixture calls have different callers (`firstCaller` and `secondCaller`)
and the same callee (`sharedTarget`). The earlier example also explicitly bound
the call-expression node, whose label displayed the same target name, and showed
the automatic root alias of the caller. This made the related rows look duplicated.
The example now binds only `caller` and `callee`. The outline hides a `root` alias
only when its complete native binding payload exactly equals a named binding in
that same match. Root handles remain retained, unique roots remain visible, and
all explicit binding names and matches remain distinct. Identical symbol names
or source locations alone never cause bindings to be hidden.

TypeScript, Biome, 29 extension tests and the complete real VS Code host passed.
The host executes the shipped caller/callee example and asserts exactly four
displayed nodes across two matches: `firstCaller → sharedTarget` and
`secondCaller → sharedTarget`. It separately asserts both root handles remain
retained and verifies header navigation and follow-up without reparsing. Native
server and console sources are unchanged. Logs are under
`vscode/artifacts/validation/caller-callee-20261016/`.

Installed v0.2.7 and reloaded the existing trial window. Ran the corrected action
through its actual picker and Run button, then expanded both matches. The native
UI shows exactly `callee: sharedTarget` and `caller: firstCaller` in Match [1],
and exactly `callee: sharedTarget` and `caller: secondCaller` in Match [2]. Both
remain open for comparison. ZIP verification passed; VSIX SHA256 is
`5cffc1312fea7d3a7fda8fe32b6fc96a043b72f174f12a3ca55a2c782743c490`.

## Distinct callees in the trial example

Added `vscode/examples/caller-callee.cpp` and updated the existing trial fixture
so `firstCaller` calls `firstTarget`, while `secondCaller` calls `secondTarget`.
Updated the README's expected pairs. The installed v0.2.7 extension is unchanged.
In the actual trial window, Refresh and Run returned exactly two matches, each
with one caller and its distinct callee. Both groups were expanded for comparison;
selecting the second caller refreshed source navigation and CTK Result to the
current `secondTarget` call. This fixture-only change was verified with the real
native parser and installed UI; extension/backend code was not changed.

## Readable AST inspector, version 0.2.8

Replaced the CTK Result JSON dump with the selected node's actual Clang kind,
name/signature, source link and preview, readable Properties, navigable Children
and a collapsible Source range. The property model explicitly selects AST facts
for declarations, records, expressions, casts, literals and calls. It excludes
protobuf wrappers/enums, cursor/session/USR values, availability flags, supported
scopes and complete match payloads. Unknown or unrequested properties are omitted;
an empty direct parameter list does not imply that the function has no parameters.
Some auxiliary nodes expose their true Clang kind and children without additional
serialized properties.

Children load through the public native `peek` visitor. Actions reuse their
retained node handles and parsed file. Symbol Search opens a separate bounded
inspection context and resolves one exact kind/source location because its search
worker has already released its native handles; ambiguous selections are rejected.
Changing source/settings invalidates inspection. Back restores the exact cached
node and Selected result returns to the original binding. Loading appears in the
status bar, and failed loads preserve the current properties with a Retry button.
Limits are explicit: 1,000 direct neighbours, 128 inspected nodes and 10,000
retained handles per context. Closing/resetting a worker releases its inspection
collections. Only the sanitized AST model is posted to the webview.

Validation logs: `vscode/artifacts/validation/ast-inspector-20261017/`.

| Check | Result |
| --- | --- |
| TypeScript and Biome | Passed |
| Extension unit suite | 34 passed, 12 native opt-in cases skipped |
| Console adapter suite | 16 passed |
| Native action/inspection integration | 5 passed with the default helper library |
| Complete isolated VS Code host | Passed, including rendered AST properties, child/source navigation, Back, selected-result restoration and unchanged parse count |
| Repository C++ suite | All 363 distinct tests passed; three snapshot-cache cases failed during the parallel segment and passed on isolated serial retry |
| Repository Python units | 2,169 passed, 22 failed; existing external helper preload and CLI failures remain, so the full repository suite is not green |

No shared server, SDK, console runtime or API source was changed. The native
integration follows FunctionDecl → CompoundStmt → ReturnStmt → CallExpr, checks
readable call properties and confirms the original action parse count remains one.
The host also covers Symbol Search inspection, safe visible fields, source links,
and the existing metadata/autocomplete/follow-up/history flows.

Installed v0.2.8 in the normal VS Code profile and reloaded the existing trial
window. In the actual installed Actions tab, Caller callee returned the two
distinct caller/callee matches. Selected `secondCaller`, verified its signature,
return type and definition property, then clicked CompoundStmt → ReturnStmt →
CallExpr. The inspector displayed `int`, `prvalue`, Direct dispatch, callee
`secondTarget` and caller `secondCaller`, with native child buttons. Back restored
ReturnStmt and Selected result restored secondCaller. The trial remains open on
that function with readable properties and children; isolated host windows closed
normally. Final VSIX ZIP verification passed; SHA256 is
`5ccb5f4b629940c663b42430b563b3a1bc0bb242474ec7ffa0e14075376a3fcf`.

## Actions on the inspected AST node, version 0.2.9

Added **Run action on this node…** to CTK Result. The button opens the existing
predefined/workspace action picker for the exact node currently displayed,
including navigated children, Back and Selected result. Choose or create an
action, edit its script-defined arguments under Options, then Run in Actions.
The chosen input is labelled with its readable AST kind/name, and keeps that
label after execution. Cancelling the picker leaves the existing action/input
unchanged. The webview sends only an action intent; the extension resolves the
current retained node itself rather than accepting an arbitrary target ID.

Action-backed inspection reuses the action worker and exact native handle.
Symbol Search transfers its live inspection worker into Actions only after a
choice is confirmed; it retains the parsed-file root separately from the child
input. Repeated actions reuse that context, File root returns to the true file
root, and action history retains earlier result groups. Transfer also reassigns
worker diagnostics/invalidation to Actions. A new search cannot dispose a worker
already owned by Actions. Closed or changed contexts reject old handles rather
than reparsing and running on a different target. Disposed workers reject further
requests without starting another process.

Validation logs are under
`vscode/artifacts/validation/inspector-actions-20261017/`. TypeScript, Biome,
34 extension unit tests (12 native opt-ins skipped), 16 console adapter checks
and five native integration tests passed. The real VS Code host verifies both
origins: a Symbol Search class → method → body transfers its exact child and
returns zero function definitions in that body, while restoring File root finds
definitions again; an action result → body → return → call runs Find calls on
that exact CallExpr and returns the expected call. Both paths keep parse count
one, readable input labels, repeated follow-ups and closed-context rejection.
Shared server/SDK/console runtime sources are unchanged; repository-wide Python
limitations recorded for v0.2.8 still apply.

Installed the final v0.2.9 package in the normal VS Code profile and reloaded only
the existing trial window. In the installed UI, searched for `secondCaller`,
navigated FunctionDecl → CompoundStmt → ReturnStmt, and clicked the inspector's
new button. The picker title identified ReturnStmt. Cancelling left the Symbol
Search/inspector selection unchanged; choosing Find calls switched to Actions
with the ReturnStmt input. Run returned exactly one `call: secondTarget` match,
and the input label remained ReturnStmt after execution. The final package was
rerun through the same workflow after the label/cleanup corrections, and remains
open on that ReturnStmt with its result match expanded. Isolated host windows
closed normally. VSIX ZIP verification passed; final SHA256 is
`0ad13ce8cd94bb4968e5de3dfcc2fa6dd0d2f8d7ee744efeaf11498541036d53`.

## Automatic AST source-range highlighting, version 0.2.10

Selecting an inspector child now reveals and selects its complete C++ source
span automatically, with a theme-aware highlight while focus stays in CTK
Result. Cached children, Back and Selected result update the editor in the same
way. Source links and initial match selections use the same range handling.
Navigation reuses an already visible source editor and reveals off-screen spans.
Only one AST highlight is retained; selecting a source-less node clears the
previous decoration and any still-matching AST selection. Editing its document
clears the decoration, and dirty documents do not receive stale highlights.
Generation/version checks discard superseded or edited document loads.

The frontend reads the existing native expansion range. It uses the explicit
exclusive end, including the final token and complete macro invocation, rather
than guessing from Clang's legacy final-token start. UTF-8 byte offsets and
byte-based columns convert to VS Code's UTF-16 positions. Invalid, out-of-file,
reversed and split-codepoint spans cannot produce an arbitrary selection;
missing exclusive ends fall back to a valid source point. Raw node metadata
remains private to the extension host.

TypeScript and Biome checks and 41 extension unit tests passed (12 native opt-in
tests skipped), including seven focused range cases for final-token inclusion,
Unicode/CRLF, byte columns, macro expansion, different files and unavailable
coordinates. The complete real VS Code host asserts selected editor text after
class-method/body and function/body/return/call navigation, Back, Selected result,
source-less children when present, and a header body. It also retains the prior
Actions, Symbol Search, follow-up, metadata and autocomplete coverage. No server,
SDK, console worker or API implementation changed; previous repository-wide
Python limitations remain recorded above. Logs:
`vscode/artifacts/validation/ast-highlight-20261017/`.

Installed v0.2.10 in the normal VS Code profile and reloaded the existing trial
window. Searched for secondCaller and clicked its CompoundStmt, ReturnStmt and
CallExpr children without using the source link. The installed editor selected
the corresponding 27-, 22- and 15-character spans, including the final closing
token; accessibility focus stayed in CTK Result throughout. Visual inspection
confirmed only `secondTarget(2)` highlighted for the CallExpr. The trial remains
open there, and isolated test windows closed normally. VSIX ZIP verification
passed; SHA256 is
`cc792e83323cbd783e41619087d3cea529d41dbe3a80479bf17960f6e59cf6f3`.

## Editor selection to AST inspector, version 0.2.11

With an analysis open in CTK Result, selecting saved C++ source now navigates the
inspector to its smallest enclosing AST node. It keeps the editor's exact text
selection and focus. Lookup trims surrounding whitespace and a final statement
semicolon, converts UTF-16 editor offsets to UTF-8 byte spans, and prefers explicit
nodes over implicit expression wrappers sharing the same range. It can find
unvisited nodes in other functions and included headers of the current parsed
translation unit. The selected native handle supports children, Back, Selected
result and further actions without reparsing.

The worker lazily indexes native source declarations in each selected file, then
navigates retained children of the smallest covering declaration. All inspection
collections remain owned by the same action/search context and close with it.
Bounds are explicit: 16 indexed files, 5,000 declarations per file, 128 visited
nodes and 64 levels per lookup, plus existing inspector limits. No partial lookup
is published on failure. No matching node produces a visible notice and disables
actions on the previous displayed node; it does not silently switch parsed files.

Mouse/keyboard/selection-command events are debounced for 180 ms. Programmatic
inspector highlights are ignored, preventing a feedback loop. Pending requests
cancel on editor changes; document version, dirty state, active editor and exact
selection are checked before dispatch and again before applying a reply. Native
operations serialize with other inspection requests, and newer selections
supersede older work. Dirty/untrusted/non-C++ documents do not trigger lookup.

Validation logs: `vscode/artifacts/validation/editor-ast-sync-20261017/`.
TypeScript, Biome, 44 extension tests (14 native opt-ins skipped), 16 console
adapter tests and seven native integration tests passed. Native checks cover
calls, references instead of implicit casts, return statements, a different
function, repeated handle reuse, follow-up execution, no-match/closed contexts,
UTF-8 source and a path containing spaces/regex metacharacters. The real VS Code
host exercises actual editor selection commands from both Symbol Search and
Actions, partial identifiers, statement terminators, editor focus/selection
preservation, unmatched selection guards, outdated replies and included headers.
One header assertion was corrected to compare physical paths because preserving
the user's editor also preserves its `/var` alias; the diagnostic is retained in
`host-path-alias.log`. Shared server, SDK and console runtime implementations are
unchanged; the repository-wide Python limitations above remain applicable.

Installed v0.2.11 in the normal profile and reloaded only the existing trial
window. Opened secondCaller through Symbol Search, then used the C++ editor's
Go to Line and Shift+Right to select the argument `2` at line 5, column 42.
Without clicking an AST child or running a command from the inspector, CTK Result
changed from FunctionDecl to IntegerLiteral with Type int, prvalue and Literal
value 2. The editor retained its one-character selection and keyboard focus.
The trial remains open in that state; isolated host test windows closed normally.
The VSIX includes the native lookup adapter and passed ZIP verification. SHA256:
`37d9fc819cb51eb67ef56eb023bbb38f8e5c719c0a101d00e948e03ecd70785c`.

## Cursor movement to AST inspector, version 0.2.12

Clicking or moving the caret in saved C++ source now updates the visible CTK
Result inspector without selecting text. The existing 180 ms debounce,
document/context guards and stale-response checks apply to both cursor and
selection events. The editor keeps keyboard focus and its exact empty selection.
Inspector-created highlights remain excluded from reverse lookup.

The first VS Code run exposed a previously hidden feedback race: collapsing an
owned highlight emits an asynchronous Command selection event, which the new
cursor lookup initially treated as user navigation. It cleared ownership before
the replacement highlight completed. Source highlighting now records and
consumes its own pending collapse events, with a bounded eight-entry queue;
mouse/keyboard input clears pending entries for that editor. Source-less AST
children still clear the previous selection and remain displayed after debounce.

Zero-length source spans now carry cursor positions through the extension and
native adapter, including byte offset zero. Native lookup uses half-open ranges
for points: a token's exclusive end belongs to an enclosing node or the next
token, never to the token on its left. Nonempty text selections keep their
existing containment and whitespace/statement-terminator normalization. Nodes
remain native and support child navigation and actions without reparsing;
unmatched positions show a notice and disable actions on the previous node.

Validation logs: `vscode/artifacts/validation/cursor-ast-sync-20261017/`.
TypeScript, Biome, 45 extension tests (14 native opt-ins skipped), 16 console
adapter tests and seven native integration tests passed. The cursor regression
first failed on the old empty-selection behavior. Native checks cover file
start/EOF, identifier interiors, exclusive token boundaries, UTF-8 positions,
stable handle reuse and unchanged parse counts. The real VS Code host passed
cursor commands from Symbol Search and Actions, references/calls/literals,
included headers, exact caret/focus preservation, actions on cursor-selected
nodes, unmatched positions and source-less/forward-highlight feedback guards.
The original diagnostic runs are retained in `host.log` and `host-trace.log`;
the passing run is `host-fixed.log`. The isolated test window and server closed.
Shared server/SDK/console runtime implementations are unchanged; the previously
recorded repository-wide Python baseline limitations still apply.

The v0.2.12 VSIX passed ZIP verification and was installed in the normal profile.
SHA256: `821290da6c76ef09c96a7902999aea6d061b113be535bf912d4a82b822d11b20`.

Reloaded only the existing normal-profile trial window and opened secondCaller
through Symbol Search. A single mouse click on its argument `2` selected
IntegerLiteral in the inspector, with Literal value 2 and the editor at line 5,
column 42 with no text selected. Right moved to column 43 and displayed the
enclosing CallExpr for secondTarget, including caller secondCaller; Left returned
to IntegerLiteral at column 42. Keyboard focus stayed in the C++ editor throughout.
The trial remains open at that cursor position; custom action tabs were preserved.

## Automatic file AST and unloaded child fetching, version 0.2.13

Opening saved C/C++ source activates the extension and loads CTK Result without
running a search or action. The native adapter matches the parsed tree's actual
TranslationUnitDecl, retains it as a selectable native handle and fetches only
its direct declarations in the main file. Clicking a previously unvisited child
loads its actual direct children using the same native visitor and cached pages;
descendants are not fetched recursively at file-open time. File AST replaces
Selected result as the root navigation label for this context. Actions can use
the file inspector's exact selected native child without another parse.

Automatic loading preserves the editor's focus, caret and text selection. File
switches are debounced, and version/generation checks suppress stale loads.
Saving the active file or changing CTK settings reloads the file context.
Inspector-driven source navigation pauses automatic file loading, so navigating
into a header does not replace the selected node or its original translation
unit. Trust and saved-source guards remain in force; load errors are shown with
Retry. A newer file/context cannot claim a worker created by an older pending
Python-runtime lookup.

The real VS Code checks exposed two lifecycle races. A delayed file-create
notification could dispose a worker while the newly opened file was loading;
source invalidation now schedules a fresh automatic load with generation guards.
Also, VS Code can hold `/var` and `/private/var` editors for one physical file.
Automatic loading resolves physical paths before replacing a context, preserving
cursor synchronization and header navigation across those editor aliases.

Validation logs: `vscode/artifacts/validation/auto-file-ast-20261017/`.
TypeScript, Biome, 45 extension tests (15 native opt-ins skipped), 16 console
adapter tests and eight native integration tests passed. Native checks open a
file without an action, run an action on its real TU binding, lazily inspect
unvisited function/body children, reuse child handles and parsed roots, and
reject closed handles. The real VS Code host activates from the C++ language
event without calling extension.activate or any CTK command, opens the file AST
with no search results, navigates unvisited namespace/class children, switches
files and automatically replaces stale handles after saving changed C++ source.
The existing search/actions, cursor sync, source highlighting, header navigation,
completion and history checks also passed. Initial failures are retained in
`host.log` and `host-restart.log`; the passing run is `host-final.log`. Isolated
test windows and servers closed normally. Shared server/SDK/console runtime
implementations are unchanged; previously recorded repository-wide Python
baseline failures remain applicable.

Packaged and installed v0.2.13 in the normal VS Code profile; ZIP verification
passed. VSIX SHA256:
`9a20ba50a579ce833cda72c80ca70e2e364400f00db1419f5bfa6b52fd7a707b`.

Reloaded only the existing normal-profile trial window. Its already-open
match-groups-demo.cpp loaded TranslationUnitDecl and the four function children
automatically while Symbol Search remained empty. The editor kept focus and its
caret at line 5, column 42 with no selection. Clicking the unvisited secondCaller
node fetched its function properties/type/body children; clicking CompoundStmt
fetched ReturnStmt, with the expected source highlights. No search or action was
run. The trial remains open at that body node with File AST navigation available;
custom action tabs were preserved.

## Expandable AST tree and cursor reveal, version 0.2.14

CTK Result now keeps a hierarchical AST outline beside the selected node's
properties. Chevron expansion fetches unloaded children without changing the
selection or source highlight; collapsing and reopening keeps cached children
and their exact native IDs. Row selection loads properties, expands that node and
highlights its source. The tree has ARIA levels/selection/expanded state, roving
focus, sibling positions and Up/Down/Left/Right/Home/End/Enter/Space navigation.
Horizontal/vertical scrolling keeps deep nodes usable in a narrow panel.

Cursor lookup now walks the same retained TU child graph used by the outline,
returning a validated, connected root-to-selected-node path. The client merges
those pages, expands every ancestor and scrolls the selected row into view
without moving focus or the editor caret. Other expanded branches remain open.
This replaces disconnected matcher-result handles and the old declaration index;
native IDs in cursor paths are exactly the IDs displayed by the tree. Included
header declarations are fetched as actual TU children only when that header is
selected. Limits remain explicit: 16 source files, 1,000 direct neighbours,
128 inspected/visited nodes, 64 cursor-path levels and 10,000 retained handles.
An unmatched source position clears tree selection and disables actions while
keeping the previous facts and notice visible. Branch-load errors preserve the
tree and Retry repeats that branch load.

Validation logs: `vscode/artifacts/validation/ast-tree-20261017/`.
TypeScript, Biome, 48 extension tests (15 native opt-ins skipped), 16 console
adapter tests and eight native integration tests passed. New tree-model checks
cover unloaded versus leaf state, collapsed branch caching, preserved sibling
expansion, selection reveal on Back, and rejection of disconnected native paths.
Native tests verify actual TU-to-function-to-body-to-return-to-call child edges
and stable IDs shared with the file root, alongside existing UTF-8, source-point
and follow-up-action checks. The real VS Code host verifies rendered tree rows,
expansion without changing the selected node, unloaded grandchildren, collapse
and cached reopening, and automatic expansion from a fully collapsed tree for
every tested editor cursor move. Exact editor selection and focus remain intact;
source lookup into an included header also expands the real TU path without
reparsing. The full existing search/action/history/completion suite passes;
`host-final.log` is the final successful run. Isolated test windows and servers
closed normally. Shared server/SDK/console runtime implementations are unchanged;
the previously recorded repository-wide Python baseline failures still apply.

Packaged and installed v0.2.14 in the normal VS Code profile. The VSIX includes
the tree renderer and passed ZIP verification. SHA256:
`fcb315df1a4b48642f142190f4d4c23bc1b0a6f13546e4352a44fee7c0457088`.

Reloaded only the existing normal-profile trial. The file AST appeared as an
outline with four collapsed function branches. Clicking the root chevron hid
the branches; Right reopened them, and Down selected firstTarget, fetched its
unvisited children and highlighted its full source while focus stayed in the
tree. After collapsing the entire root again, moving the C++ caret to line 5,
column 42 automatically reopened TU → secondCaller → CompoundStmt → ReturnStmt
→ CallExpr and selected IntegerLiteral value 2. The earlier firstTarget expansion
was retained. Right in the editor selected the containing CallExpr at column 43;
Left returned to IntegerLiteral. The selected row scrolled into view and the C++
editor retained keyboard focus with no text selected. The trial remains in that
state, with custom action tabs preserved; no search or action was needed.

## AST node context actions and inspector tabs, version 0.2.15

CTK Result now has full-width **AST** and **Properties** tabs in place of the
split layout. Switching tabs keeps the native node, loaded children and expanded
branches. Editor cursor updates respect the current tab; returning to AST reveals
the latest selection. The tab list supports Left/Right and Home/End navigation,
with ARIA selection and a single visible panel.

Each AST row contributes a native VS Code **Run Action…** context-menu entry.
The existing predefined/workspace/create action picker receives that clicked
row's retained native ID, including an unselected node with unloaded children.
Opening or cancelling the picker keeps the inspector selection unchanged.
Choosing an action sets that exact node as its input; arguments and Run remain
in Actions. Context changes, unknown node IDs and busy inspection reject old
menu requests, including a context change while the picker is open. The existing
native session and changed-source checks remain in force. The Properties tab's
action button continues to use its selected node. The menu follows the official
[VS Code webview context-menu API](https://code.visualstudio.com/api/extension-guides/webview#context-menus).

Validation logs: `vscode/artifacts/validation/ast-menu-tabs-20261017/`.
TypeScript and Biome pass, along with 48 extension unit tests (15 native opt-ins
skipped), 16 console adapter tests and eight native integration tests. The native
server, Python SDK and console runtime are unchanged; previously recorded
repository-wide Python baseline failures still apply.

The final real VS Code host run (`host-final.log`) passed the existing
search/action/history/completion suite and the new context-menu/tab cases.
It invokes the registered menu command with the DOM context of an unselected,
unloaded namespace row, activates the resulting action target and verifies its
exact native ID while the inspector remains on the TU root. Unknown IDs and
activation after changing files reject. Tab switching preserves all tree rows
and the native selection; cursor movement while Properties is active keeps that
tab active and returning to AST shows the updated tree. Isolated test windows
and servers closed normally.

Packaged and installed v0.2.15 in the normal VS Code profile; ZIP verification
passed. VSIX SHA256:
`d6b676eb89781d24baf1f34ee560990846cc0400e2321e3ffb2124765c5abf8f`.

Reloaded the existing normal-profile trial and used its real native menu.
With the TU root selected, right-clicking the collapsed, unloaded firstCaller
opened **CTK · Action on firstCaller**. Choosing Find calls set
**Input: FunctionDecl: firstCaller**; Run returned one match containing
**call · firstTarget · line 4**. Properties still showed the TU root, confirming
that right-clicking and choosing an action did not silently change selection.
Left/Right switched the tabs with only one panel visible. With Properties active,
moving the C++ caret to line 5, column 42 updated it to IntegerLiteral value 2
and kept editor focus and the Properties tab. Returning to AST revealed the
expanded secondCaller → CompoundStmt → ReturnStmt → CallExpr path and selected
literal. Right-clicking the unselected nested CallExpr opened
**CTK · Action on secondTarget**; cancelling kept both the literal selection and
the prior firstCaller action/results. The trial remains open on AST with the
one-match result, the editor caret at 5:42 and custom-action tabs preserved.

## Double-click Properties and node-specific semantics, version 0.2.16

Double-clicking an AST row selects that exact native node and opens Properties;
Enter offers the same keyboard behavior. Returning to AST keeps its selection,
expanded branches and cached children. Tree rows keep their DOM identity across
loading/selection updates so the first click cannot destroy the double-click
target. A double-click during that node's initial load opens Properties and lets
the same request finish. The Properties tab receives focus without moving the
source caret again. Navigation keeps a fixed place even at the file root, and
loading uses the status bar and tree's busy state; neither inserts a row above
the tree between clicks. Tree text selection is disabled. Chevron clicks still
only expand/collapse a branch.

Properties now includes collapsible sections based on the selected node:

- Records: own declared methods, fields, static members, aliases and nested
  types grouped by public/protected/private access. Class/struct default access
  and explicit access declarations determine the groups; implicit members are
  omitted. Member links open that exact retained child in Properties.
- Inheritance: the selected class and direct/transitive base paths, showing
  access and virtual edges. The native base matcher resolves aliases to actual
  declarations, with no name-based lookup or reparsing. Dependent/unresolved
  bases are marked. Display is bounded to 16 levels and 128 base edges.
- Functions/methods: ordered parameter names and types, with explicit unnamed
  parameter labels. A root-only function match and exact declaration-context
  comparison exclude parameters belonging to nested lambdas/callables. Native
  FunctionProtoTypeLoc wrappers do not hide the signature's parameters.
- Enums: evaluated enumerator values and underlying type. Aliases: underlying
  type. Existing call/expression/cast/operator/literal properties remain; method
  and field qualifiers include const/static/virtual/pure-virtual/mutable when
  present. Statements and auxiliary nodes omit empty semantic/property groups.

`vscode/examples/semantic-inspector.cpp` demonstrates multiple inheritance,
an alias to a base, virtual transitive inheritance, all three member access
groups, typed and unnamed parameters, a nested lambda, an enum and a type alias.

Validation: `vscode/artifacts/validation/ast-semantics-20261017/`.
TypeScript and Biome pass; 50 extension unit tests pass (16 native opt-ins
skipped), along with 16 console adapter tests and nine native integration tests.
The native fixture verifies the actual base paths and access/virtual labels,
private class defaults, static fields, member types, method constness, ordered
named/unnamed parameters, nested-lambda exclusion, enum values, alias types,
empty statement semantics, cached facts and a single parse. Boundary tests
reject disconnected inheritance paths and oversized inheritance/parameter lists.
The real VS Code host (`host-final.log`) verifies Properties opening during a pending child load,
rendered class groups/base paths/parameter tables, and exact tree state after
returning to AST, alongside its existing search/action/history/completion suite.
Its isolated test window/server closed normally. No shared native server, Python
SDK or console runtime changed; the earlier repository-wide baseline still applies.

Packaged and installed v0.2.16 in the normal VS Code profile. ZIP verification
passed and the new renderer, native adapter and fixture are included. SHA256:
`67341699e44275cca8df5b0a4c6e7d989dd456190b481cbfe726fa636e3f8aeb`.

Used the normal-profile extension with the new example. A first double-click
on the unloaded Widget row opened Properties, focused its tab and displayed
MidAlias → virtual public Root, protected Hidden, and all three member groups.
Returning to AST kept Widget selected with its direct children expanded. A
double-click on its unloaded check method opened the method's Properties with
limit:int and label:const char *, return type bool and Const:Yes. The sample is
open in the existing trial window; custom action tabs are preserved. The shared
managed CTK server was neither restarted nor replaced.

## Selectable base declarations and collapsible sections, version 0.2.17

Resolved base classes in Inheritance are now links to retained native class
declarations. Clicking one loads its Properties, selects the actual declaration
in the AST tree and highlights its full source range, including definitions in
headers. Aliases select the underlying declaration. Base links also offer the
native Run Action context menu; the selected base works with the existing
Properties action button. Dependent/unresolved bases remain plain text.

The adapter keeps the base matcher collections alive and assigns declaration
handles from the same registry as TU/header navigation. Identity includes the
owning parsed file, serialized declaration facts and its exact source range.
This keeps related links and native tree rows on the same handle. Following a
base uses its native range to walk the retained TU and validates the exact
expected handle before returning a connected ancestry path. It never substitutes
a same-named class or reconstructs a node from display JSON. Other expanded
branches stay open; Back restores the derived selection. Cached ancestry pages
retain semantic sections too. Inspection, history, source-file, depth, result
and retention limits still apply; closing or refreshing invalidates old links.

AST, Source, Inheritance, member groups, Parameters, Properties and Source range
now have full-width collapsible headers with VS Code-style chevrons and native
Enter/Space disclosure behavior. Open/closed choices persist by section title
across nodes, tabs and webview reloads, storing only UI booleans. Collapsing AST
keeps its selection and expanded branches; source synchronization updates the
retained tree without forcing the section open. Reopening reveals the selection.

Validation logs: `vscode/artifacts/validation/ast-base-navigation-20261017/`.
TypeScript and Biome pass. Fifty extension unit tests pass (17 native opt-ins
skipped), 16 console adapter tests pass, and all ten native integration tests
pass (`native-final.log`). New native checks cover alias/transitive-base handle
identity, forward declarations in a header, a same-named unrelated class, real
TU/namespace ancestry, exact one-match field actions, a single parse and expired
references. The final real VS Code host run (`host-final.log`) passes the full
existing suite plus rendered section headers, selected-base source highlighting,
preserved derived/base expansion, Back, invalid-link rejection and an action
targeted at the selected base. Test windows and isolated servers closed normally.
No shared server, Python SDK or console runtime changed; the earlier repository
baseline still applies.

Packaged and installed v0.2.17 in the approved normal VS Code profile; ZIP
verification passed. VSIX SHA256:
`65fb0b6cb16c3c0b3e3483eeed613907de04add5b37c43bcb06757efa4e69494`.

Reloaded the existing normal-profile trial and used the extension directly.
Clicking Widget's transitive Root base selected Root's declaration, highlighted
its complete four-line source and opened its Properties. The AST tab showed
Root selected/expanded while Widget's expanded branch remained intact. Folding
Public members kept it folded when selecting Root and returning to Widget;
folding AST kept it closed across a Properties/AST round trip. Reopening kept
the native selection. The Properties action picker was titled Action on Root;
Find classes ran with Input: CXXRecordDecl: Root and returned one Root match at
line 1. Right-clicking the MidAlias link opened Action on Middle, confirming the
alias targets its actual class. The picker is closed, the one-match result and
sample remain available, and custom-action tabs are preserved. The user's
managed server was not restarted or replaced.

## Explorer sidebar AST Inspector, version 0.2.18

Moved the complete inspector from the contributed bottom-panel container into
Explorer as **AST Inspector**, alongside native sections such as Outline and
Timeline. Its native header folds the whole view, including the **AST** and
**Properties** tabs. Removed the redundant disclosure around the AST tab's
tree; semantic property groups retain their individual disclosure controls.
The sidebar uses the sidebar theme background and tighter horizontal spacing.

The webview retains its context while hidden. Automatic file loading and
cursor lookup update the retained model without focusing the view or forcing
it open; visibility changes publish the latest state when reopened. The
selected tab, loaded tree branches and native selection survive hiding and
reopening. Explicit result selection still reveals the inspector.

Validation: TypeScript and Biome pass; 50 extension tests pass with the 17
native opt-ins skipped. The full isolated VS Code extension-host suite passes,
including an actual hidden sidebar, opening another C++ file while hidden,
moving the cursor onto its IntegerLiteral, preserving the exact caret and
Properties tab, reopening with the same tree/native selection, and all existing
action, source navigation and semantic/base checks. The isolated test window
and server closed normally. Logs are in
`vscode/artifacts/validation/ast-sidebar-20261017/`.

Packaged and installed v0.2.18 in the approved normal VS Code profile; archive
verification passed and the installed extension reports 0.2.18. VSIX SHA256:
`91efba84e68dde45bfc13d6aad13220dc18cfb57835521c4c0cc10967b821cc8`.

Reloaded the existing normal-profile trial and verified the native Explorer
section directly. **AST Inspector** appears beside Outline, Timeline and
AST Match Bindings; the old contributed CTK Result panel is absent. Expanding
its header shows both tabs inside it. Double-clicking Widget opened Properties;
collapsing the native header hid both tabs and all content. Moving the C++ caret
to the `check` method kept it collapsed. Reopening restored Properties showing
`Widget::check` and its two parameter types; returning to AST showed that method
selected with its Widget/TU ancestors expanded. The trial remains open with
the AST tab visible; custom action editor tabs were preserved. The user's
managed server was not restarted or replaced.

## Fixed inspector tabs, version 0.2.19

Moved the AST/Properties tab strip to the top of the inspector's fixed header,
with Back/File AST beneath it. The view fills its native sidebar section;
the AST tree and Properties are bounded, separate scrolling areas. Removed
the tree's minimum viewport-height calculation and the outer document's scroll
so tree/property scrolling cannot move the tabs out of view. The tree keeps
its existing scroll position and selected-node reveal behavior, and Properties
retains its collapsible semantic sections. The native sidebar header still
collapses the entire inspector.

TypeScript and Biome pass. The first two host attempts reached the original
20-second initial AST deadline while the native worker was still loading;
an isolated worker/server diagnostic completed successfully in 19.253 seconds.
The host's automatic-file wait now allows 45 seconds, covering the existing
30-second RPC deadline plus worker startup and error-reporting overhead.
No production RPC timeout or server behavior changed. Validation logs are in
`vscode/artifacts/validation/ast-fixed-tabs-20261017/`.

The extension unit run passes: 50 tests, with 17 native opt-ins skipped. The
final full host run passed initial AST loading and continued, then stopped on
`Console completion timed out`; it is not a green full-host result. That log
is retained as `host-completion-timeout.log`. No console/runtime code changed.
The test window and its disposable server closed after the failure.

Packaged and installed v0.2.19 in the approved normal VS Code profile; archive
verification and installed-version checks pass. VSIX SHA256:
`6aee2ced4f058fdfa11f733f5a26bddefe94816c058c02d944b4fa4536c3d6eb`.
Reloaded the existing normal-profile trial and verified scrolling directly:
scrolling the AST to later declarations leaves AST/Properties and navigation
in place. Double-clicking Widget opens Properties; scrolling from the class
facts through Inheritance down to the final Source range keeps the tabs fixed
at exactly the same position. Returning to AST preserves Widget's selection
and expanded branch. The trial remains open on AST; custom action editor tabs
are preserved and the user's managed server was not restarted or replaced.

## Completion recovery and test cleanup, version 0.2.20

The earlier full-host completion timeout did not repeat during an instrumented
run: the same default-library argument inference completed in about three
seconds, and that traced run passed. A standalone reproduction completed in
2.197 seconds. Temporary request tracing was removed after diagnosis.

The completion bridge nevertheless had two confirmed lifecycle defects: its
30-second request clock included cold Python imports, and timing out removed
only the waiting request while leaving the worker and its queue alive.
The worker now acknowledges readiness before draft processing starts. Startup
and request processing have separate 30-second bounds. Identical in-flight
requests share one operation; completed results are not cached. Timeout,
interpreter failure or invalid protocol replies terminate the owned worker,
reject its waiting requests and allow the next attempt to start a fresh one.
Late messages/exits from an old worker cannot invalidate its replacement;
disposing the service also closes a worker that is still starting.

The real-host test launcher now owns its VS Code process and disposable server
directly. It uses separate profile and extension directories and closes its
owned process groups, including descendants, before removing the workspace.
Success, failure, SIGINT, SIGTERM and the ten-minute overall deadline all reach
cleanup; unresponsive children receive a forced shutdown. Cleanup cannot
launch another window if interruption happens during setup. The user's
normal VS Code profile and managed server are outside these process groups.

Validation logs are in
`vscode/artifacts/validation/completion-timeout-20261017/`. TypeScript and Biome
pass. All 75 extension tests pass, including all 17 native opt-ins and eight
new lifecycle regressions. All 17 Python console-adapter checks pass, including
the real readiness protocol. Six cleanup checks pass on macOS, covering
successful/failed launchers with surviving descendants, forced shutdown,
failed launch, macOS process-group liveness probes and interruption of the
actual harness using stand-ins that
open no windows. The cold-start regression keeps startup and processing below
their individual limits while exceeding the old combined limit; timeout
regressions verify worker termination and a successful retry.

The complete final real VS Code run (`host-final-clean.log`) passes all
existing scenarios, including editor/Options completion, YAML actions,
semantic properties, native AST/source navigation, follow-up actions and
preserved tabs. The runner exits successfully and prints
`CTK_TEST_PROCESSES_CLOSED`; an independent process audit reports zero test
processes remaining. The preceding run passed the scenarios but reported
EPERM while probing an already-closed server process group. Cleanup now
confirms actual group membership with `ps` when that macOS probe is denied;
the sixth cleanup regression covers this case. No test window is left open.

Packaged and installed v0.2.20 in the approved normal profile; archive and
installed-version checks pass. VSIX SHA256:
`68b4289f7310f17fbfdaa54542853dfd818408353efbbe179733d9e567927d2c`.
Installation opened no window and did not reload the user's current editor;
reload that existing window to activate the updated extension. No shared
native server, user helper library or custom action draft was changed.

## Restore the collapsible inspector to CTK Result, version 0.2.21

Corrected the earlier placement change: AST Inspector belongs in the separate
CTK Result bottom panel, not in Explorer. Its full-width AST Inspector header
now folds the whole inspector, including the AST and Properties tabs. Folding
uses the existing persisted section state; background file/cursor inspection
continues without reopening the section or a hidden panel. Expanding it
restores the current tab, selected node and expanded tree branches. The tabs
and navigation remain fixed above the independently scrolling tree/Properties
body. No Explorer view is contributed by this extension.

The first real scrolling check exposed an incorrectly sized details content
wrapper, which allowed the header and tabs to scroll away. The inspector body
is now bounded beneath its header rather than relying on percentage sizing
through that wrapper. Manual verification in the existing normal-profile
trial confirms both tree and Properties scroll under fixed tabs. Folding
hides both tabs and all content; moving the cursor to Widget::check while
folded keeps it folded. Reopening preserves Properties and shows the selected
method and its typed parameters. Switching to AST retains the expanded Widget
branch and selected check declaration. Explorer no longer contains AST
Inspector; unrelated extensions' views were left alone.

Validation logs: `vscode/artifacts/validation/ctk-result-collapse-20261017/`.
TypeScript and Biome pass; all 58 extension unit tests pass (17 native opt-ins
were not enabled in that run). The final complete real VS Code extension-host
suite passes against the final layout, including default helper-library
completion, YAML actions, grouping, native AST/semantic properties, source
highlighting, follow-up actions, preserved tabs/tree and hidden-panel updates.
The host launcher exits successfully and reports CTK_TEST_PROCESSES_CLOSED;
an independent process audit confirms zero temporary test processes remain.

Packaged and installed v0.2.21 in the approved normal profile, then reloaded the
existing trial window to activate it. The VSIX archive verifies successfully;
SHA256: `747c6cc0b486594b2a3e3b1ca9628be98f1df73c1c22e56c8c1c160e63d66d04`.
Custom action editor tabs and the managed native server are preserved. No
additional manual trial window was opened.

## Run Action in the node header, version 0.2.22

Moved the selected-node action into the Properties header beside the node's
name and Clang kind, renamed it Run Action, and aligned it to the far right.
The header stays visible while Properties scrolls. Long names/kinds shorten
visually with their full values available on hover, leaving the action on the
same row. The existing action target, disabled-state handling and picker flow
are reused.

TypeScript, Biome and the complete real VS Code extension-host suite pass.
Logs: `vscode/artifacts/validation/inspector-header-action-20261017/`.
The temporary host exited successfully with CTK_TEST_PROCESSES_CLOSED; a
separate process audit found zero remaining temporary test processes.

Packaged and installed v0.2.22 in the approved normal profile, then reloaded
the existing trial window. Archive verification and installed-version checks
pass. VSIX SHA256:
`19899599bcd0f08c0c2c112b3df70fba7854931c5fe9a7656ae20e996b8b8858`.
The real UI shows Run Action at the right of both the translation-unit and
Widget::check headers, on the same row as their name and type. Clicking it
opens the predefined/workspace action picker for the displayed native node;
cancelling preserves the analysis. The trial is left on Widget::check in
Properties with the user's existing section-fold choices and custom action
editor tabs preserved. No additional manual window was opened.

## Run Action beside the fixed tabs, version 0.2.24

Moved Run Action from the node header to the far right of the fixed
AST/Properties tab bar. The button is separate from the tablist and uses the
current selected native node from either tab. It remains visible as the tree
or Properties scroll, and the whole-inspector fold still hides it with both
tabs. The existing action picker and target validation are unchanged.

TypeScript, Biome and the complete real VS Code extension-host suite pass.
Logs: `vscode/artifacts/validation/inspector-tab-action-20261017/`.
The temporary test host exits with CTK_TEST_PROCESSES_CLOSED; an independent
audit confirms zero temporary test processes remain.

Packaged and installed v0.2.24 in the approved normal profile. Archive and
installed-version checks pass. VSIX SHA256:
`e715e77d0a4df31d714297c839e984fec66d5980579321621010862b65d65c98`.

Reloaded the existing normal-profile trial. Manual checks show the button on
the far right of the tab bar in AST and Properties; scrolling the AST leaves
the tabs and button fixed. Clicking it from AST after selecting Root opens
the picker titled Action on Root; cancelling preserves that selection. The
final installation was reloaded in the existing window and its Properties tab
placement checked again. No additional manual trial window was opened, and
custom action editor tabs and the managed native server remain intact.

## Compact inspector and expired-session recovery, version 0.2.25

Removed the redundant AST Inspector disclosure/title and the entire
Back/File AST navigation row. CTK Result now starts with the fixed
AST/Properties tabs and right-aligned Run Action. The tree or Properties uses
the remaining height. Per-property section folding remains available; the
native panel Hide control hides the whole inspector.

Inspection errors and unmatched-source notices now use the existing status
bar item instead of consuming rows above the node. Expired/closed cursor
errors are described as an expired or closed analysis session. Clicking
CTK · reload AST, or invoking CTK: Reload File AST, creates a fresh automatic
file-inspection context rather than retrying the unavailable handle. Actions
on the failed node remain disabled until a live node is selected. Reload
requires a saved C/C++ editor; it preserves existing action results.

A fresh native inspection of Root::Root succeeds with zero children and an
empty inheritance list. Closing a reproduction-owned native handle causes a
retained-value-closed error. The original trial's cursor-unavailable state was
also observed before installation. These are native analysis-lifetime errors,
not AST properties. The server's default cursor idle lifetime is five minutes;
no server lifetime setting or managed server was changed.

TypeScript and Biome pass, as do all 58 extension unit tests (17 optional
native tests were not enabled in that unit run). The complete real VS Code
extension-host suite passes, including a new unavailable-cursor regression:
the raw error/navigation/title text is absent from the inspector, the status
item offers Reload File AST, failed-node actions are blocked, and reloading
then inspecting the real Root::Root succeeds with actions enabled. Existing
completion, search/actions, grouping, semantic sections, source sync,
highlighting and tab/tree preservation checks also pass.

Logs: `vscode/artifacts/validation/compact-inspector-20261017/`. The test host
reports CTK_TEST_PROCESSES_CLOSED and an independent process audit reports zero
temporary test processes. Packaged and installed v0.2.25 in the approved
normal profile; archive and installed-version checks pass. VSIX SHA256:
`08be9aa9e6accb53a4300862c1b4b23f0365b6b36e8e5226e2372c219237119c`.

Reloaded the existing normal-profile trial and selected Root::Root through
the AST tree. Its Properties load successfully, Run Action is enabled, and
the inspector begins directly with the tabs and node content. The redundant
title, Back/File AST, raw cursor error and Retry rows are absent. Custom
action editor tabs and saved Properties-fold choices are preserved; no
additional manual trial window was opened.

## Inspector session lifetime, version 0.2.26

Renamed the bottom panel CTK Inspector while preserving its contribution IDs
and saved placement. Activating a saved C/C++ editor automatically parses it
and follows the cursor. Switching C/C++ files replaces the automatic context;
non-C++ tabs and hiding the inspector retain the last context. This is one
active automatic context, not a per-file AST cache.

Retained native cursors are renewed every minute without reparsing or changing
node identities. Renewal pins only this Python client's live CursorOwners;
server-wide session listings must not be used because they can include another
client's sessions. Foreground operations wait for in-flight renewal, busy work
skips overlapping heartbeats, and disposal stops renewal. A genuinely expired
automatic context is refreshed; an initial failed parse does not restart in a
loop. Action-owned workers renew their retained cursors too.

Closing the last related source/header tab releases its inspector and action
contexts. Split copies and inspected headers keep their translation unit alive;
inspector navigation pins source tabs instead of replacing their previews.
Closing a stale tab cannot clear a newer context. Reopening the same source
loads a new context even when VS Code retains its TextDocument internally.

TypeScript and Biome pass; 63 extension unit tests and 19 console-adapter tests
pass (17 optional native unit cases were not enabled). The complete real VS
Code extension-host suite passes with the console helper library enabled,
including live-session renewal, file switching, related-header navigation,
split ownership, source-tab release, stale targets and same-file reopening.
Earlier host runs exposed preview replacement, related-header ownership and
delayed-close/reopen races; these were repaired before the passing final run.

A native managed-server probe confirms eight owned session deadlines extend,
the selected node identity remains unchanged and parse_count stays one. A
separate client's sentinel session remains unchanged and usable; closing the
probe releases all eight owned sessions without closing that sentinel.

Logs: `vscode/artifacts/validation/inspector-lifetime-20261017/`.
The test harness reports CTK_TEST_PROCESSES_CLOSED and an independent process
audit finds zero temporary test processes. Packaged and installed v0.2.26 in
the approved normal profile; archive and installed-version checks pass.
VSIX SHA256:
`58916e500025345e53127c4ec16482b97c6337b723e5da963a05e77c216fc07f`.

Reloaded the existing normal-profile trial without opening another window.
The renamed CTK Inspector panel is visible; selecting actions-demo.cpp and
semantic-inspector.cpp automatically changes the file root. Selecting Root
opens its readable Properties with actions available after background renewal.
Custom action tabs remain open and the managed server was not restarted.

## Independent open-file inspector sessions, version 0.2.27

Replaces the single automatic context with a cache keyed by each file's
canonical filesystem path. Each visited open C/C++ file owns its native worker,
minute-by-minute renewal and saved inspector state. Switching back restores the
same selected native node, loaded children, expanded/collapsed branches,
navigation history and AST/Properties tab without reparsing. Restoring an
in-flight inspection waits for its worker before allowing another request.

Actions borrow retained file sessions instead of taking ownership. Refreshing
or closing Actions detaches its callbacks and results while the file retains
its AST; running on another file does not close the earlier inspector worker.
Action results use the worker that actually owns their handles. Shared observers
preserve both file-lifetime recovery and action diagnostics. Disposal is safe
when both the file and Actions close the same worker.

Closing the file's last tab disposes its cache entry and native resources;
split copies and filesystem aliases count as the same file. Closing an inactive
file leaves the active file's context intact. Reopening a closed file starts
a fresh native context. Source edits invalidate that source's cached session;
headers and CTK settings invalidate cached sessions conservatively. Unrelated
source-file changes no longer reset the active automatic inspector through the
transient search-result owner. The inspector remains in CTK Inspector.

Validation logs: `vscode/artifacts/validation/per-file-inspector-20261017/`.
The first full-host run identified action handles being routed through an
unrelated cached worker; ownership routing was corrected. The next run reached
the new final close/reopen checks and revealed that the test must close both
the /var and /private/var aliases before asserting last-tab release.

TypeScript and Biome pass, along with all 65 extension unit tests (17 optional
native unit cases remain opt-in). The final complete real VS Code extension-host
suite passes with the console helper library enabled. New checks retain two
independent files, restore exact node/context IDs, complete loaded trees and
per-file AST/Properties tabs, run actions with parseCount still one for each
file, detach Actions without closing either AST, close all aliases of one file
without disturbing the other, reject closed targets, and reopen with fresh IDs.
The harness reports CTK_TEST_PROCESSES_CLOSED; an independent process audit
reports zero remaining temporary test processes.

Packaged and installed v0.2.27 in the approved normal VS Code profile. Archive
and installed-version checks pass. VSIX SHA256:
`3a659cd472aea0aec099536530ceb0a305d2af4519b8e9278617e2d282ee0bab`.

Reloaded the existing normal-profile trial, expanded Middle and selected Root
in semantic-inspector.cpp, then opened actions-demo.cpp. Switching back restores
Root and its Properties tab immediately; opening AST shows both Root and Middle
still expanded, including Middle::weight. No extra manual VS Code window was
opened, custom action editor tabs were preserved, and the managed server was
not restarted.

## Save refresh with AST state restoration, version 0.2.28

Saving an open C/C++ file creates fresh native handles and rebinds the inspector
to its surviving selection and expanded/collapsed branches. Bookmarks retain
declaration identity, kind, source context and structural paths. Editor changes
rebase UTF-16 ranges before matching refreshed Clang UTF-8 source ranges. Undo
can revive a removed anchor. Unchanged header nodes use their own native ranges;
unique auxiliary nodes without source ranges use their enclosing structural
role. Ambiguous matches are not guessed. Removing a selected node falls back
to the nearest identifiable surviving parent.

The inspector keeps its AST/Properties tab, and refreshing does not reveal a
hidden panel or move the editor caret. Native action targets from the previous
parse are invalidated; new targets and restored branches share the new parse.
Saving an inactive open file refreshes its cached session without replacing the
active inspector. Returning restores that already refreshed native selection.
Unrelated dirty source buffers no longer prevent a retained file from refreshing;
dirty headers and that file's own unsaved changes still block unsafe reuse.
Per-file renewal, split/alias ownership and last-tab release remain in place.

Validation logs: `vscode/artifacts/validation/save-restore-inspector-20261017/`.
The first full-host run preserved the changed literal as intended and exposed
an older test expectation that saving should reset to the file root. Updating
that expectation allowed the full native suite to pass, including shifted and
changed literals, overload identity, expanded sibling branches, deleted-node
fallback, stale target rejection, one parse for restored actions and background
saves. Final unit coverage adds undo, header-range and source-less-node cases.

TypeScript and Biome pass. All 75 extension unit tests pass (17 optional native
unit cases remain opt-in), and the final complete real VS Code host suite passes
with the console helper library enabled. The harness reports
CTK_TEST_PROCESSES_CLOSED, and an independent audit confirms zero remaining
temporary test processes.

Packaged and installed v0.2.28 in the approved normal VS Code profile. The
archive integrity and installed-version checks pass. VSIX SHA256:
`40818ab273d299099034c47e6af2bf18c8f9651b1500098641a1ae99b22a543a`.

Reloaded the existing normal-profile trial on its current match-groups-demo.cpp
tab. CTK Inspector loads the file's native declarations and enables Run Action;
the three custom action tabs remain open. No manual test window was added and
the managed server was not restarted. Save/edit behavior was exercised through
real VS Code documents in the isolated host suite above.

## Failed saved-file refreshes retain the last valid AST, version 0.2.29

Saved-file refreshes now build and restore a replacement AST offscreen before
committing it to the inspector. A failed parse preserves the preceding valid
node, readable properties, selected AST/Properties tab and all expanded branches.
The old native handles are detached from inspector navigation and actions, and
the failed replacement worker is released. No parse-error rows are inserted in
the inspector. The status bar reports AST refresh failed with the affected file,
error and a save-again hint. Returning to a failed file restores that snapshot
without reparsing or triggering a retry loop.

The next save retries automatically using the rebased selection/branch bookmarks.
A successful replacement clears that file's error and restores native navigation
and actions. Inactive saves use the same transaction and error reporting while
preserving the foreground inspector. Multiple files retain independent errors;
recovering or closing a file clears only its own status. Closing its last tab
still disposes its session and snapshot. Superseded refreshes cannot overwrite
another file's current inspector.

Validation logs: `vscode/artifacts/validation/failed-save-inspector-20261017/`.
Focused tests cover retained facts throughout a failed replacement, stale-handle
blocking, next-attempt success, late-error cancellation and independent background
errors. The real VS Code suite inserts an actual C++ #error, checks exact retained
tree/properties and selected-node identity, confirms errors appear only in the
status bar, switches away/back without retrying, repairs and saves to recover,
runs an action through the replacement parse, repeats failure/recovery in an
inactive tab, and closes a failed file's last tab. The first host run reached
recovery and exposed stale diagnostic text left on the hidden status item; the
cleared status now resets its text and tooltip as well.

TypeScript, Biome and all 78 extension unit tests pass (17 optional native unit
cases remain opt-in). The final complete real VS Code extension-host suite passes
with the console helper library enabled, including actual Clang error/recovery
and failed-file close checks. The harness reports CTK_TEST_PROCESSES_CLOSED and
an independent audit confirms zero remaining temporary test processes.

Packaged and installed v0.2.29 in the approved normal VS Code profile. Archive
integrity and installed-version checks pass. VSIX SHA256:
`db6b403fec90c8f5fe745ea88cd4145c10ac5972972fecb4b53142fbcea93c2d`.

Reloaded the existing normal-profile match-groups-demo.cpp trial. CTK Inspector
automatically displays the native file tree (Base, Sample, another and the four
caller/callee functions) with Run Action enabled; all three custom action editor
tabs remain open. No additional manual window was opened, user fixture contents
were preserved, and the managed server was not restarted.

## Clickable compiler errors in Problems, version 0.2.30

Automatic inspector parse failures now publish native Clang errors in VS Code's
Problems panel with source CTK. Each marker carries the real source file and
line; Clang's UTF-8 byte column is converted to VS Code's UTF-16 character
position, including non-ASCII text and CRLF source. Clicking a marker uses VS
Code's standard error navigation. Included-header errors target the header.
The open main document URI is retained when Clang reports its canonical alias.

Compiler error locations come from the existing native parser RPC failure;
no second compiler run, server restart, or guessed source position is required.
Errors without source coordinates remain in the status bar. The last valid AST
and saved selection/branches retain their previous failure/recovery behavior.

Diagnostics belong to retained translation units. A successful parse or closing
the file's last tab clears its contribution. Shared-header errors are deduplicated
and remain while another retained file still reports them. Superseded reads,
closed sessions and extension disposal cannot republish obsolete errors. Both
active and background saves publish/clear their errors without replacing another
file's inspector.

Validation logs: `vscode/artifacts/validation/parse-problems-20261017/`.
Unit coverage includes native-message extraction, paths with spaces/colons,
invalid/missing locations, Unicode conversion, source URI aliases, shared-header
ownership and cancellation/close/disposal. A real native worker check preserves
the exact diagnostic for an undeclared identifier after Unicode text, then an
error in an included header. The full VS Code test suite additionally checks
the actual diagnostic URI, severity, message, exact #error location, and clearing
after active/background recovery and last-tab close.

TypeScript, Biome and all 86 extension unit tests pass (18 optional native cases
remain opt-in). The focused native diagnostic test passes for both Unicode
source and an included header. The complete real VS Code host suite also passes
with the console helper library enabled; its harness reports
CTK_TEST_PROCESSES_CLOSED, and an independent audit finds zero temporary test
processes remaining.

Packaged and installed v0.2.30 in the approved normal VS Code profile. Archive
integrity and installed-version checks pass. VSIX SHA256:
`233af5febb88cbe0dfc2a87dc9b6096d51cea26600167b444fc85232fcc6e572`.

Verified a real Problems click in the existing normal-profile trial. A disposable
C++ file first parsed successfully, then saving an undeclared identifier after
λ and emoji text produced one CTK diagnostic at line 1, column 34 (native byte
column 37). Double-clicking that CTK row opened the source at the missing
identifier. Repairing and saving removed the marker; Problems reported no
workspace problems. Closed and removed the disposable fixture, restored the
original match-groups-demo.cpp and CTK Inspector panel, and preserved all three
custom action editor tabs. No manual test window was opened and the managed
server was not restarted.

## Deduplicate CTK and clang Problems entries, version 0.2.31

Problems now keeps another provider's diagnostic when CTK reports the same
physical source file, start position, error severity and message. Initial
capitalization, whitespace and curly/straight quote differences are normalized;
C++ identifier spelling and case remain significant. The other provider's
marker, source range and associated actions remain available. Unrelated errors
at the same location, warnings and errors at different positions stay distinct.

The extension observes diagnostic changes, including providers that publish
after CTK. A matching CTK marker is withdrawn while the other marker exists;
the cached CTK marker returns if that provider removes it. CTK-only errors remain
visible when no language server is available. Filesystem aliases resolve to
the same physical file for comparison, and shared-header CTK markers are also
deduplicated across aliases. Other providers' collections are never modified.
Unchanged output does not rewrite the CTK collection, preventing diagnostic
notification loops. Disposal removes the listener and ignores pending alias
lookups. Existing AST preservation and Problems navigation remain in place.

Validation logs: `vscode/artifacts/validation/deduplicate-problems-20261017/`.
Focused coverage includes an existing clang error, delayed publication,
withdrawal/fallback restoration, distinct messages/locations/severities,
case-sensitive C++ names, filesystem aliases and notification-loop prevention.
The real VS Code host suite adds a separate clang diagnostic collection after
a genuine parse error, verifies exactly one matching Problems entry, then removes
that collection and verifies the CTK fallback returns without replacing the AST.

The first complete host run passed deduplication but exposed an existing save
retry race: a late filesystem notification could invalidate a replacement while
the previous failure still suppressed retries. Starting a new saved-file attempt
now clears that suppression, allowing invalidation to schedule its replacement.
The last valid AST and previous status-bar error remain available until success.
The final run passes the background save/recovery checks as well.

TypeScript, Biome and all 93 extension unit tests pass (18 optional native cases
remain opt-in). The final complete real VS Code extension-host suite passes with
the console helper library enabled, including live diagnostic handoff/fallback.
The harness reports CTK_TEST_PROCESSES_CLOSED; an independent audit confirms
zero remaining temporary test processes.

Packaged and installed v0.2.31 in the approved normal VS Code profile. Archive
integrity and installed-version checks pass. VSIX SHA256:
`b366d57d85d99541a0a6ab90bb0df4efc02b6f8cc14d9fbe82615510ee9cfc9f`.

Verified with both CTK and the real clang extension in the existing normal
profile. Saving an undeclared identifier after Unicode text produced exactly
one Problems entry, attributed to clang at line 1, column 34; CTK still reported
its parse failure in the status bar. Double-clicking the remaining entry selected
the identifier in C++. On repair, the CTK fallback appeared while reparsing,
then the successful parse cleared it and Problems reported no workspace issues.
Closed and removed the disposable fixture, restored match-groups-demo.cpp and
CTK Inspector, and preserved the three custom action tabs. No extra manual VS
Code window was opened and the managed server was not restarted.
