# CTK console

The interactive console opens a full-screen workspace by default. It uses the existing prompt_toolkit command buffer, language validation, completion, history, and native analysis client.

## Launch

From the repository, launch CTK console with its own temporary native server:

```bash
cd /Users/husam/workspace/clang-toolkit
scripts/manual_console.sh
```

Before launching, run `uv sync --frozen`, `cmake --preset dev`, and `cmake --build --preset dev` first. Exiting the launcher stops its private server and removes its temporary storage.

For an existing server, use the normal connection settings:

```bash
uv run ctk --server unix:///tmp/ctk.sock
```

## Controls

| Control | Action |
| --- | --- |
| F2 / click Actions | Open the single action menu; use arrows, Page Up/Down, mouse wheel, and Enter or click |
| F3 | Open or close the local file explorer |
| F4 / Help in toolbar | Open or close formatted command help |
| F5 | Refresh the focused inventory or local file listing |
| F7 / Outline in toolbar | Open or close the binding/property tree |
| F8 / Resources in toolbar | Open or close open-file and retained-session inventory |
| F9 / Server in toolbar | Open or close full, periodically refreshed server details |
| F6 / Shift+F6 | Move between input, results, visible files, and the active right panel |
| Up / Down / Enter in files | Select entries; expand/collapse folders; prepare a file's `parse` command |
| Escape | Close completion/menu, the focused right panel, or file explorer; return to input |
| Enter in input | Continue incomplete syntax; submit a complete command |
| Ctrl+R | Search command history, or results when results have focus |
| Ctrl+C | Clear a draft; request cancellation for a supported active batch |
| F1 | Show shortcuts in the results pane |
| F10 / Ctrl+D on empty input | Quit; finish an active command before closing |
| Click a file / click again | Select it, then expand its folder or prepare its `parse` command |
| Wheel / Page Up/Down | Scroll the focused file list, action menu, or results |
| Ctrl+End in results | Jump to the latest output and resume following |
| Right / Left in trees | Expand or enter a branch / collapse or select its parent |
| Ctrl+Left/Right in outline / horizontal track | Pan long properties |
| Enter on Next/Previous page in outline | Load the selected 50-item page with absolute indexes |

Use Fn with function keys if your keyboard reserves them for system controls.

The title **CTK console** appears at the left of the top bar, followed by one Actions entry and direct Help, Outline, Resources, and Server panel toggles; each right panel also has a clickable × close control. Its menu includes files, hidden-file visibility, following, search, wrapping, clearing displayed results, command help, and exit. The bottom bar shows session state, outcome, elapsed time, input position, follow state, server resident memory, and retained-session count instead of repeating all shortcuts. Scrolling results pauses following so new output cannot pull you away from the content you are reading.

Wide terminals use the right side for relevant command help, a binding outline, resources, or server details. The pane starts hidden when it would leave too little input width; explicitly opening it in a narrow terminal creates a closable overlay. Help uses Rich Markdown for colored headings, bullets, inline code, and grammar-colored CTK examples. Executed `help COMMAND`, `COMMAND?`, bare `help`, and F1 use the same rendering in the results pane: Markdown markers stay hidden and examples have a dark code background. The plain console keeps its original text help. The completion popup has a matching dark theme with short command, matcher, and field descriptions. Input, submitted command blocks, and errors are colored; the workspace explicitly uses 256-color rendering so inherited monochrome settings do not flatten the interface.

## Multiline input

Input starts at one row. New logical lines and wrapped text expand the command area upward, reducing the results pane. Every logical input line has a number in the left gutter; wrapped continuations leave that number blank. Submitted commands render as numbered code blocks with their original indentation, grammar-aware CTK syntax colors, and a distinct dark background across each row. They have no CTK command label or decorative border. Long source lines wrap to the result pane width with a blank continuation gutter; changing pane width or the wrap setting rerenders them without changing retained source/search text. Keywords are pink, node matchers blue, traversal/combinator matchers purple, predicate matchers green, strings gold, variables/references teal, numeric/boolean literals orange, and operators a brighter gray than punctuation. These syntax roles share one palette across input, results and help examples; surrounding colors and panels are unchanged. Neither area uses `ctk>` or `...>` markers. The editor stops growing at half the usable terminal height and scrolls to keep the cursor visible; results retain at least three rows when the terminal has sufficient space. Submitting clears the editor back to one row.

Typing `(`, `[`, `{`, or a quote inserts its closing partner and leaves the cursor inside. Accepting a completion ending in an opener also inserts a fresh closer, preserving all following text and outer brackets anywhere in a multiline draft. Typing the existing closer moves past it; Backspace between an empty pair removes both. Enter after an opener creates an indented line and keeps the closing bracket on its own line. Further lines preserve indentation, and a closing bracket on an empty line returns to its opener’s indentation. Pasted text retains its original characters and spacing. Pair insertion is one undo step and also works in a next-command draft while analysis runs.

Try typing this one line at a time. The first three Enter presses add lines; the final Enter submits one command and records one history entry:

```text
let inputs = [
    "one",
    "two"
]
```

Then enter:

```text
print "INPUT_COUNT=${inputs.length}"
```

The result is `INPUT_COUNT=2`. You can also paste a multiline command as a single draft before submitting it.

## File explorer

Files belong to the local client working directory. Selecting a file prepares an escaped absolute-path `parse` command and returns focus to input. It preserves an existing draft and never executes a file selection automatically. Paths still need to exist on the configured server for remote parsing.

Folders load on demand in a worker thread. Hidden files, build folders, and dependency folders are initially omitted; Actions can show them. Scans and visible rows have explicit bounds, and symlink directories remain leaves. At widths below 80 columns, the explorer becomes a closable overlay so it does not squeeze command input.

## Bindings and resources

F7 lists local `let` bindings. Enter toggles expansion of selected lists, match rows, bindings, and readable node properties. Right expands a branch or enters its first child; Left collapses it or selects its parent. Click a triangle to toggle a branch in one click; clicking another part of a row selects it. Ctrl+Left/Right and the horizontal scrollbar pan long property values. The outline loads only expanded branches and is bounded to 300 visible rows and eight levels. Long lists load only the selected page of 50 children. Select Next page or Previous page and press Enter, or click the pager row, to reach later items without expanding the entire collection. FileSet pages group inputs under expandable directory branches; expanding one file reveals its frozen compilation details. Duplicate paths with different compilation profiles retain their own absolute indexes. Binding rows show the qualified declaration name (or declaration name when available) and declaration type, with `(unnamed)` as the fallback. `p` prepares `print` for the selected reference, including the existing `$files.inputs[index]` path for file entries. No RPC or mutable operation runs during rendering, and local property reads finish before Runtime cleanup.

Standalone matches, `print` of match values or FileSets, `file list`, and `bindings` also display expandable trees within the existing results pane. Focus results with F6 or click a row, then use the same arrows or Enter. Match rows expand into named bindings and their readable properties. File listings group the selected page under directories. Source blocks, formatted help, the editor, pane placement, and theme remain unchanged. Tree previews are searchable and bounded; their property labels show up to 512 characters, while F7 retains longer labels. The most recent 20 tree previews remain interactive; earlier previews retain their displayed text. Print a value again to inspect it anew. Basic prompt output and file exports keep their textual format.

F8 groups server-owned open-file leases and retained analysis sessions under expandable roots. Expand a file or session to reveal its details. Select a row with arrows or the mouse; `a` prepares attachment of the selected session into a free `$attachedN` binding, and `c` prepares closure of the selected lease or cursor. The buttons beneath the inventory perform the same preparation. The command appears in the editor for review and runs when you press Enter there. Existing drafts are preserved. Listings are bounded to 100 files and 100 sessions.

The underlying language already supports these controls:

```text
file list
session list
bindings
server status
session attach "SESSION_ID" into $tree
session close "SESSION_ID"
file close $source
```

The serving-file and session ownership rules are documented in the [resource management guide](file-output-resource-management.md); the console runtime and real-server checks verify the existing commands used by the panels. Closing a cursor invalidates its aliases; closing a file lease does not discard independent cursor ownership.

While the workspace is open, live native cursors owned by its client receive metadata-only lease renewal every 30 seconds and before commands. Renewal creates no aliases, changes no result revisions, and stops when the owner is closed or released. The server retains its existing five-minute idle expiry and independent-source fork behavior. A cursor already expired, explicitly closed, or lost during server restart still needs a fresh parse or a live session attachment.

F9 contains every process, retained-memory, limit, cache, and disk field exposed by `server status`, refreshed every two seconds without filling the transcript. RSS is a separate process measurement from retained/cache estimates. Unsupported RSS is shown as unavailable. Refresh failure marks the last footer sample stale and exposes the error in the panel; refresh resumes on the next attempt. The normal command remains available for a full transcript snapshot.

## Repository match failure

The reported `analysis_service.cpp` failure was a compiler-profile problem: the AST builder could not find `ctk/net/analysis_service.hpp`. Automatic discovery searched `compile_commands.json` and `build/compile_commands.json`, while this checkout's CMake preset writes `build/dev/compile_commands.json`.

Discovery now also checks the project's `build/dev` and `build/release` preset paths, preserving explicit database precedence and compiler working-directory/profile identity. Against a private server, copying the reported source outside the project reproduced the missing-header error; matching the original repository source with its automatically selected profile returned 21 main-file functions in 4.47 seconds. The repository target was verified against a private native server. This corrects compilation context; unavailable matcher names still require a valid Clang matcher.

For a different build layout, use `ctk --compile-commands PATH` or `set compile_commands "PATH"`. A database explicitly selected for another project cannot supply a missing source entry.

Rich integration follows its [Markdown](https://rich.readthedocs.io/en/stable/markdown.html) and [Console capture](https://rich.readthedocs.io/en/latest/console.html) APIs. Captured ANSI is converted into prompt_toolkit styled fragments inside a scrollable buffer, using the existing Lark-based CTK lexer for fenced examples. The [prompt_toolkit text-editor example](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/main/examples/full-screen/text-editor.py) is the referenced editor-style layout; the console retains the console's existing editing keys.

## Menu focus and large-match errors — 11 October 2026

Actions now restores focus only to a panel still visible in the current layout. Switching or hiding Help while the menu is open cannot restore the removed help Window; a current panel or the command editor receives focus instead.

The 100,000-row limit is a server query budget. Display pagination does not bypass it. `unless(isImplicit())` still includes declarations from headers; filtering system headers can leave many third-party declarations. For functions in the selected source file, use:

```ctk
let file = parse "./server/src/net/match_service.cpp"
let x = functionDecl(
    isExpansionInMainFile(),
    unless(isImplicit())
)
let y = match $x in $file
```

A row-budget failure publishes no partial cursor. The source cursor's independent idle expiry explains why a later retry can report `cursor unavailable`; the screenshot alone does not establish its expiry timestamp. Workspace keepalive prevents ordinary editing pauses from expiring still-owned cursors. Failures now include the relevant narrower-matcher or reparse/Resources recovery guidance.

A private-server check parsed the exact `match_service.cpp` target once, then matched the main-file/nonimplicit expression above: 28 functions returned with the original tree and independent result both retained. This query was verified against a private native server.

Script errors with valid line/column coordinates are underlined in red inside the submitted block, with a caret below. Unknown-variable errors mark a unique grammar-token reference. The explanation remains below the block, without a duplicate plain source/caret excerpt. Ambiguous references and native C++/matcher diagnostics retain their message without inventing a script location.

Restart the existing console with the Launch command to load the new code.


## Limits

Use `ctk --ui prompt` to select the basic prompt; interactive `ctk` opens the workspace. One-shot queries and script/redirected input keep their existing execution behavior. A name filter, manual pane resizing, searchable action palette, and dedicated jobs view remain future options. Cancellation uses existing batch resource controls; other commands finish before the application closes. The displayed transcript is bounded to 200,000 characters; use the existing output/save commands for retained results.

## Merge validation — 11 October 2026

After integration with the current main branch, 972 Python unit tests, 116 acceptance scenarios (26 + 26 + 64 private-server cases), and 336 native tests passed. The acceptance suite includes two real-terminal scenarios covering the title, menus, mouse controls, panels, multiline editing, syntax colors, formatted help, and smart pairs during completion. Twelve workspace/highlighting modules passed type checking; focused lint and launcher syntax checks passed.

The default-launch correction was revalidated with the same complete suites: 972 Python unit tests, 116 acceptance scenarios, and 336 native tests. The real-terminal workspace scenario now omits `--ui`, while unit coverage verifies default workspace selection and the explicit basic-prompt option.

## Isolated tree preview — 11 October 2026

The expandable-tree changes are isolated on `codex/console-expandable-trees`. Launch this checkout to try them:

```bash
cd /Users/husam/.claude/worktrees/clang-toolkit/console-expandable-trees
scripts/manual_console.sh --ui workspace
```

Use `print $rows`, `file list`, `file list discovered in $files`, or `bindings` to display a tree in results. Select a branch, then press Right to expand, Left to collapse, or Enter to toggle. F3 and F7 use the same branch navigation. F8 exposes collapsible file/session roots and details. Ctrl+Left/Right still pans long values in F7/F8. Layout, colors, smart pairs, and automatic indentation are preserved.

Validation: 985 Python unit tests and all 336 freshly built native tests pass. The combined acceptance run passed 115 cases, including both real-terminal workspace cases; automatic query-session startup timed out once at 30 seconds alongside gRPC fork/event-loop warnings. That case passed on two isolated reruns, including one with the original interpreter and configuration, giving passing coverage for all 116 scenarios. Six workspace modules pass type checking; focused lint, launcher syntax, and whitespace checks pass. Evidence remains in this worktree's ignored `build/tree-*.log` files. All edits in this change are confined to the isolated worktree.
