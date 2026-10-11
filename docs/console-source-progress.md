# Workspace batch progress and source navigation

Implementation branch: `codex/console-source-progress`, in the isolated `console-expandable-trees` worktree.

## Progress

- [x] Foreground batches publish immutable file counters and update one bar in place.
- [x] The existing status row keeps live counters visible during long body output.
- [x] Durable batches use frozen input totals and refresh once per second while active.
- [x] Failed files count as done; cancelled, unknown, skipped and unattempted inputs do not count as successful work.
- [x] Cancellation uses the existing resource scope or revision-checked durable run controls.
- [x] `progress off`, ordinary prompts and redirected output retain their existing behavior.

## Source window

- [x] Match, binding, location and range rows link to valid physical AST coordinates.
- [x] Click a linked label or select it and press **O**; triangle clicks and Enter still expand trees.
- [x] A separate window overlays the console with numbered C++ on the left and file matches on the right.
- [x] Each named binding navigates to its own range; macro links use expansion coordinates.
- [x] The outline pages all matches in the file from current bindings and retained result previews, 50 matches per page.
- [x] **Tab/F6** changes focus, **N/P** navigates matches, **Escape/Close** restores the originating selection and draft.
- [x] Source reads occur off the UI thread; missing and oversized files show a recoverable message. The viewer reads local files up to 8 MB.
- [x] Existing console layout, theme, pair closing and indentation are preserved.

## Verification

- [x] Focused existing workspace and batch checks: 135 passed before adding new feature coverage.
- [x] New event-loop and real-terminal checks cover source links, numbered highlighted C++, outline navigation, focus restoration, cancellation, progress coalescing, paging, expired results and large-output trimming.
- [x] Full suites: **1,032 Python unit tests**, **116 acceptance cases** in one run, and **336 native tests** pass; the native build also succeeds.
- [x] Seven workspace/progress modules pass type checking; all changed Python files pass focused lint and the diff passes whitespace checks. The evaluator retains exactly the same 26 type diagnostics as the baseline, verified with a shadow-file comparison.

Validation evidence is retained under this worktree's ignored `build/source-progress-*.log` files. The native suite used private storage and temporary directories; acceptance tests used isolated servers. The real-terminal acceptance case verifies the unchanged console toolbar, numbered command editor, existing pairing/indentation behavior and source-view syntax colors. Durable file counters are derived from the frozen inputs of completed/failed groups; the server's durable status API does not expose finer per-file outcomes.

Restart the isolated console with:

```sh
/Users/husam/.claude/worktrees/clang-toolkit/console-expandable-trees/scripts/manual_console.sh --ui workspace
```

Try:

```ctk
let tree = parse "examples/parse_match.cc"
let rows = match functionDecl(isExpansionInMainFile()).bind("f") in $tree
print $rows
let inputs = files "examples/*.cc"
batch part in $inputs size 1 do { let found = match functionDecl(isExpansionInMainFile()).bind("f") in $part; }
```

Expand a match or binding, then click its underlined label or press **O**. For a running bar, click **Cancel**, or select its row and press **C**. Foreground **Ctrl+C** retains its existing cancellation behavior. Body output remains available; completion leaves one final bar and an expandable batch report. A completed batch can have fewer done files than discovered files when its body deliberately targets only a subset.
