# Workspace batch progress and source navigation

Implementation branch: `codex/console-source-progress`, in the isolated `console-expandable-trees` worktree.

## Progress

- [x] Foreground batches publish immutable file counters and update one bar in place.
- [x] Progress and done/total appear on the first result row; state, succeeded/failed counts and Cancel appear on the second.
- [x] The existing status row keeps live counters visible during long body output.
- [x] Durable batches use frozen input totals and refresh once per second while active.
- [x] Failed files count as done; cancelled, unknown, skipped and unattempted inputs do not count as successful work.
- [x] Cancellation uses the existing resource scope or revision-checked durable run controls.
- [x] `progress off`, ordinary prompts and redirected output retain their existing behavior.

## Source window

- [x] Match, binding, location and range rows link to valid physical AST coordinates.
- [x] Click a linked label or select it and press **O**; triangle clicks and Enter still expand trees.
- [x] A full-screen window overlays the console with numbered C++ on the left and the selected match on the right.
- [x] Only the clicked match, binding, location or range is marked and underlined inline, retaining C++ syntax colors and normal line spacing. The compact gutter uses red `▶` for selected lines; unrelated ranges remain unmarked.
- [x] Underlines use valid exclusive AST endpoint columns and UTF-8 byte coordinates; tabs expand to four spaces. Older results without exclusive columns mark through the end of the final line.
- [x] Each named binding navigates to its own range; macro links use expansion coordinates.
- [x] The outline contains only the selected link. Opening source does not traverse current bindings or retained result previews.
- [x] **Tab/F6** changes focus; **Escape/Close** restores the originating selection and draft. Open another result link to inspect a different match.
- [x] Source reads occur off the UI thread; missing and oversized files show a recoverable message. The viewer reads local files up to 8 MB.
- [x] Existing console layout, theme, pair closing and indentation are preserved.

## Verification

- [x] Focused existing workspace and batch checks: 135 passed before adding new feature coverage.
- [x] New event-loop and real-terminal checks cover source links, numbered highlighted C++, outline navigation, focus restoration, cancellation, progress coalescing, paging, expired results and large-output trimming.
- [x] Full suites: **1,032 Python unit tests**, **116 acceptance cases** in one run, and **336 native tests** pass; the native build also succeeds.
- [x] Seven workspace/progress modules pass type checking; all changed Python files pass focused lint and the diff passes whitespace checks. The evaluator retains exactly the same 26 type diagnostics as the baseline, verified with a shadow-file comparison.

### Source readability follow-up (initial version)

The compact gutter follow-up below replaces this version's separate rule rows and bracket markers.

- [x] Full-screen bounds at 48- and 100-column terminal widths; close restores the original draft and tree selection.
- [x] Multi-line ranges retain C++ syntax colors and original line numbers, with red gutter brackets and separate rule rows.
- [x] UTF-8 byte columns, tab expansion, mid-line expressions and exclusive end-at-next-line boundaries are covered.
- [x] Real-terminal native checks select `(value + 5) * 3` inside a longer statement and leave its semicolon outside the rule; multi-line function rules and gutter bounds are also verified.
- [x] Two-row batch progress and the second row's Cancel link are verified, including a real two-file batch.
- [x] **1,036 Python unit tests** and **336 native tests** pass; updated real-terminal acceptance cases pass.
- [x] Full acceptance suite: **116 cases passed** in 573.49 seconds. Combined with units and native tests, **1,488 tests passed**; the updated terminal cases were also rerun after the final range changes.
- [x] Seven changed presentation/script modules pass type checking, focused lint passes, and the diff has no whitespace errors.

### Link underline follow-up

- [x] Match and binding links underline their label text only; indentation, expand arrows, padding and newlines retain the ordinary tree style.
- [x] Outline padding and selection styles are preserved, so long rows still scroll horizontally.
- [x] Updated real-terminal checks verify link text is underlined and adjacent indentation/padding is not; both terminal cases pass.
- [x] All 1,036 unit tests pass; the two changed presentation modules pass type checking and focused lint.
- [x] All 116 acceptance cases and 336 native tests pass; **1,488 tests passed** across the full suites. Evidence is retained in `build/source-link-text-*.log`.

Validation evidence is retained under this worktree's ignored `build/source-progress-*.log` files. The native suite used private storage and temporary directories; acceptance tests used isolated servers. The real-terminal acceptance case verifies the unchanged console toolbar, numbered command editor, existing pairing/indentation behavior and source-view syntax colors. Durable file counters are derived from the frozen inputs of completed/failed groups; the server's durable status API does not expose finer per-file outcomes.

### Compact gutter follow-up

- [x] Gutter width follows the file's line-count digits: five columns for a two-digit file, reduced from ten.
- [x] Every selected line uses the same single red arrow, including blank lines inside a multi-line range.
- [x] Matched text is underlined on its own source row; no annotation rows are inserted. Source blank lines, indentation and syntax colors are retained.
- [x] Exact expression bounds still exclude adjacent operators and semicolons.
- [x] Updated source/terminal checks: 23 passed; all 1,036 unit tests, 116 acceptance cases, and 336 native tests pass (**1,488 total**). Type checking, focused lint and whitespace checks pass; evidence is retained in `build/source-compact-*.log`.

### All file matches and relative paths (historical; selection scope superseded below)

- [x] Every available match and named binding range remains marked, including collapsed and off-page outline entries; navigation changes the selected arrow without clearing other ranges.
- [x] Overlapping, nested and duplicate ranges merge into one underline; gaps between separate expressions remain unmarked unless another match covers them.
- [x] Selected lines use `▶`; other matched lines use `▷`, with the existing red marker color, gutter width, syntax colors and one row per source line.
- [x] The source window title shows paths relative to the current directory for files beneath it; outside files keep their absolute paths. File loading continues to use the original absolute path.
- [x] Focused checks: 25 passed, including real-terminal rendering, relative titles, persistent markers and source navigation; type checking and focused lint pass.
- [x] All 1,038 Python unit tests, 116 acceptance cases (502.32 seconds), and 336 native tests pass (**1,490 total**); evidence is retained in `build/source-all-matches-*.log`.

### Source horizontal scrollbar

- [x] The source pane shows a horizontal scrollbar only when a source line exceeds its available width, using the existing scrollbar colors and keeping the gutter fixed.
- [x] Click the arrows or track, or use **Ctrl+Left/Right** while the code pane has focus; scrolling leaves the source cursor and selected AST range unchanged.
- [x] Scroll extent uses terminal cell widths, including wide characters; resizing clamps the offset and vertical navigation retains it. Selecting another match resets horizontal scrolling and reveals its location; loading or missing files clear stale scrollbar state.
- [x] Short source files retain their existing layout; long files use one bottom scrollbar row within the code pane.
- [x] All 1,040 Python unit tests and 336 native tests pass; type checking and focused lint pass.
- [x] Focused checks: 27 passed, including real-terminal mouse and keyboard panning. All 116 acceptance cases pass (532.90 seconds), for **1,492 total** passing tests across the full suites; evidence is retained in `build/source-scroll-*.log`.

Restart the isolated console with:

```sh
/Users/husam/.claude/worktrees/clang-toolkit/console-expandable-trees/scripts/manual_console.sh --ui workspace
```

Submit each top-level command with **Ctrl+J**. The examples contain multi-line functions and classes; the call and multiplication occur in the middle of a statement.

```ctk
let tree = parse "examples/source_navigation/calculator.cc"
let functions = match functionDecl(isDefinition(), isExpansionInMainFile()).bind("f") in $tree
print $functions
let classes = match cxxRecordDecl(isDefinition(), hasName("Calculator")).bind("class") in $tree
print $classes
let calls = match callExpr(callee(functionDecl(hasName("scale")))).bind("call") in $tree
print $calls
let expressions = match binaryOperator(hasOperatorName("*"), hasAncestor(cxxMethodDecl(hasName("evaluate")))).bind("expr") in $tree
print $expressions
```

Expand a match or binding, then click its underlined label or press **O**. For a running bar, click **Cancel**, or select its row and press **C**. Foreground **Ctrl+C** retains its existing cancellation behavior. Body output remains available; completion leaves one final bar and an expandable batch report. A completed batch can have fewer done files than discovered files when its body deliberately targets only a subset.

The multiplication example selects `scale(bounded, 3) * 2`. Its exact text is underlined inline with its original syntax colors and a red marker in the gutter. Surrounding expressions and the semicolon remain unmarked, even when a retained function or class match covers the statement:

```text
▶19│         const int result = 7 + scale(bounded, 3) * 2;
```

The selected Calculator definition spans multiple lines, each marked with the same `▶` arrow. Other matches remain unmarked. Navigation uses original file line numbers, with one screen row per source line.

For a three-file batch:

```ctk
let inputs = files "examples/source_navigation/*.cc"
batch part in $inputs size 1 jobs 1 do {
    let found = match functionDecl(isDefinition(), isExpansionInMainFile()).bind("f") in $part;
    print "Group ${part.index}: ${found.length} functions";
}
```

For a larger batch, first run this from macOS Terminal before restarting the console:

```sh
/Users/husam/.claude/worktrees/clang-toolkit/console-expandable-trees/.venv/bin/python /Users/husam/.claude/worktrees/clang-toolkit/console-expandable-trees/scripts/create_source_navigation_examples.py
```

This creates 24 translation units with standard-library includes and 64 multi-line functions per file under the ignored `build/source-navigation-batch/` directory. It does not modify the three source-navigation fixtures.

```ctk
let large = files "build/source-navigation-batch/*.cc"
batch part in $large size 1 jobs 1 do {
    let found = match functionDecl(isDefinition(), isExpansionInMainFile()).bind("f") in $part;
    print "Group ${part.index}: ${found.length} functions";
}
```

A fresh private server makes the first run a cold parse. Later runs may use cached ASTs and finish faster; duration depends on the machine.

Expected progress presentation:

```text
Batch 61a5a9a6a7cc 14/24 files [━━━━━━━━━━━━━━──────────]
State: running · 14 succeeded · 0 failed · [Cancel]
```

Live verification found **6 functions, 1 Calculator class, 1 scale call, and 1 evaluate multiplication** in `calculator.cc`; the three-file and 24-file batches both completed with zero failed files. Each generated input produced 70 function definitions with the main-file matcher. Verification logs are `build/source-progress-refinement-*.log`.

### Selected match source scope

Clicking a result link or pressing **O** opens source for that exact link only. The code keeps its surrounding file context, while the outline and inline markings contain only the selected range. Current runtime bindings and earlier result previews are no longer collected, so an overlapping function match cannot obscure the bounds of a selected expression. Opening another link replaces the previous selection.

Validation for this change: 28 focused source/workspace checks pass, including exact expression bounds with an overlapping retained function, mouse and keyboard opening, and replacing a previous selection. The native build, focused lint and whitespace checks pass. The full Python unit run reports 3,661 passed and two unchanged server-lifecycle failures because the sandbox blocks the `ps` command used to recognize the server process. The real-server terminal scenario is blocked by Unix-socket bind permissions. Native validation also encounters socket permission errors, unavailable watcher notifications and index-worker failures; a fully green native/end-to-end run remains unverified in this environment.
