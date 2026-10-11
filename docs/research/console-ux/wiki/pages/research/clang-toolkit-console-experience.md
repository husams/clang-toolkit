---
name: Clang Toolkit console experience proposal
type: research
status: draft
last_updated: 2026-10-11
sources: 8
tags: [clang-toolkit, console, prompt-toolkit, user-experience]
---

# Clang Toolkit console experience proposal

Editable Page: [Clang Toolkit console experience proposal](https://chatgpt.com/space/page_bf6289c8e8a48191a3c5b4bf61e98f8e).

Keep prompt_toolkit and add two console experiences: improve the existing prompt with a live status bar first, then offer an optional workspace with menus, a collapsible file explorer, and searchable results. This keeps familiar command entry while making files, work in progress, and results easier to discover.

This exploration records the proposed direction and original baseline, dated 10 October 2026. The subsequent optional CTK console workspace is implemented with one scrollable Actions menu, mouse controls, closable Rich Markdown help, dark completion, a binding/property outline with declaration names/types and direct FileSet paths, file/session resource management, live server status, numbered source blocks with distinct syntax roles shared by Rich-formatted executed help, automatic indentation and closing bracket/quote pairs, a distinct dark background, wrapping and inline error markers, a left-aligned title, horizontal outline scrolling, lazy list pagination, safe menu focus restoration, and lease keepalive for owned native cursors; see [the launch and verification guide](../../../../../console-workspace.md). The feature tables below describe the broader proposal; filters, a command palette, manual resizing, and a dedicated jobs panel remain future work.

## Current console

The inspected worktree already has multiline input, syntax highlighting, validation on submission, contextual completion, persistent history, and reverse history search. It runs asynchronous prompts and sends command evaluation to a worker thread. Query events and ordinary results currently go through printed output. The prompt configuration has no bottom toolbar, application menu, or file explorer.

The dependency lock and installed package both use prompt_toolkit 3.0.53. The versioned official documentation below describes 3.0.52; the key APIs were also checked against the installed 3.0.53 package.

The existing wiki console design concentrates on language and result access. It does not supply an advanced layout proposal, so this exploration adds one. Its older interactive runtime page contains historical transport claims that the inspected application has superseded. See the saved baseline and wiki context snapshots in the worktree.

## Choices

| Direction | Experience | Effort and tradeoffs | Recommendation |
| --- | --- | --- | --- |
| Enriched prompt | Existing terminal flow with status, history suggestions, and clearer completion hints | Smallest change; retains terminal scrollback. A PromptSession toolbar alone does not create a persistent explorer | Start here |
| Optional prompt_toolkit workspace | Menu, closable sidebar, results area, command editor, and fixed footer | More layout, focus, output, and cancellation work. A full screen view needs its own searchable transcript | Preferred destination |
| Workspace as the default | Every interactive launch enters the richer layout | Strong consistency, but adoption depends on paste, terminal selection, narrow screens, and remote use working well | Reconsider after a pilot |
| Framework migration | Rebuild the console in another terminal framework | Would require separate evidence and a new integration effort; no requested feature currently requires it | Defer |

Effort is a relative assessment, not a delivery estimate. The [prompt guide](https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/asking_for_input.html) supports a callable bottom toolbar; the [application guide](https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/full_screen_apps.html) supplies the layout and focus primitives for a workspace.

## Features worth adding

| Feature | User benefit | Proposed behavior | Priority |
| --- | --- | --- | --- |
| Bottom status bar | See what the console is doing | Connection state, current scope, last command outcome, elapsed time, and shortcut hints | First |
| File explorer | Find and select inputs without typing long paths | Toggle open or closed; expand folders lazily; filter names; show selected inputs separately | Next |
| Application menu | Discover available actions | File, View, Session, Help; actions share the same handlers as shortcuts | Next |
| Command palette | Find an action quickly | Search actions by name; show shortcut and whether the action is available | Next |
| Results viewer | Inspect large output without losing the prompt | Search, wrap toggle, follow or pause scrolling, copy, and explicit export | Next |
| Context help | Reduce syntax memorization | Show the selected command or matcher signature and a short example | Later |
| Variables and bindings panel | Discover retained values | List variable names and types; expand fields within explicit bounds | Later |
| Work and diagnostics panel | Find progress and failures | Show acknowledged jobs, progress, errors, and supported cancellation actions | Later |
| History suggestions and themes | Make daily typing more comfortable | Optional history suffix suggestions, configurable colors, keyboard first controls | Small parallel improvement |

The [reference](https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/reference.html) includes MenuContainer, MenuItem, TextArea, ConditionalContainer, and history suggestion APIs. A file tree and searchable command palette require CTK controls built from these primitives; they are not turnkey widgets.

## Proposed workspace layout

**Single line input** — the command editor starts compact, leaving most of the main pane for results.

```text
 Actions [F2]        CTK workspace
+----------------------+----------------------------------------------------+
| Files                | Results                                            |
| > src                | Search results   Follow on                         |
|   alpha.cpp          | previous command output                            |
|   beta.cpp           |                                                    |
|                      |                                                    |
|                     |                                                    |
|                      +----------------------------------------------------+
|                      | ctk> let inputs = [                                |
+----------------------+----------------------------------------------------+
 Session open | Editing | Ln 1, Col 1 | Follow on
```

**Multiline input** — additional lines move the divider upward. The results viewport becomes shorter; the existing output remains in its scrollback.

```text
 Actions [F2]        CTK workspace
+----------------------+----------------------------------------------------+
| Files                | Results                                            |
| > src                | Search results   Follow on                         |
|   alpha.cpp          | previous command output                            |
|   beta.cpp           +----------------------------------------------------+
|                      | ctk> let inputs = [                                |
|                     |        "src/alpha.cpp",                            |
|                      |        "src/beta.cpp"                              |
|                      |      ]                                             |
+----------------------+----------------------------------------------------+
 Session open | Editing | Ln 1, Col 1 | Follow on
```

**At the height limit** — the editor scrolls internally to keep the cursor visible. The menu, file pane, and bottom status bar stay in place.

```text
 Actions [F2]        CTK workspace
+----------------------+----------------------------------------------------+
| Files                | Results                                            |
| > src                | Search results   Follow on                         |
|   alpha.cpp          | previous command output                            |
|   beta.cpp           +----------------------------------------------------+
|                      |      [earlier lines above; scroll to view]         |
|                     |        "src/gamma.cpp",                            |
|                      |        "src/delta.cpp"                             |
|                      |      ]                                             |
+----------------------+----------------------------------------------------+
 Session open | Editing | Ln 1, Col 1 | Follow on
```

The implemented command editor occupies the width of the main pane. `ctk>` labels only the first logical line; subsequent lines use a blank gutter, preserving the code’s indentation. The draft and submitted command blocks both have syntax coloring. Logical lines and wrapped visual lines expand the editor upward to half the usable workspace, with at least three result rows when space permits; longer drafts scroll with the cursor, and submission returns to one row. Closing the explorer restores width without losing the draft. Manual resizing remains a proposal item.

Enter keeps the current console behavior: it inserts a newline while input is incomplete or the cursor is within the draft, and submits complete input when the cursor is at the end. Submission returns the editor to its compact height.

The file pane starts closed. Opening it gives the file list focus; closing it restores the command editor and its draft. On narrow terminals, replace the sidebar with a temporary picker and keep the command editor usable. Treat roughly 100 columns as an initial design assumption to validate, rather than a framework requirement.

The results area retains a bounded display transcript. Follow mode stays active until the user scrolls back; new results then show an unread indicator. Large output goes to explicit export instead of growing an unlimited widget buffer.

The footer always fits one row. Hide secondary fields as space shrinks, preserving activity and available shortcut hints. Memory and progress fields appear only when a supported API supplies them; unknown or stale values stay visibly unknown.

## File explorer behavior

Separate **project files** from **selected analysis inputs**. Browsing a file must not automatically parse it or acquire server resources. Enter on a file should prepare the existing parse command in the editor; the user can inspect and submit it. An explicit action can select files for a later operation.

Use lazy directory loading and bounded filtering. Avoid recursive scans on every redraw, skip bulky generated directories by default with an explicit override, and retain a stable selection when folders change.

Label filesystem scope clearly. Local browsing reads the client filesystem. Analysis paths belong to the serving machine. For a remote endpoint, a server backed listing or preview needs a verified API; do not assume a local path names the same remote file. Start with local browsing and already known server inputs. A read only source preview is a later feature once retrieval and limits are defined.

## Menus and keyboard behavior

Proposed shortcuts are F1 Help, F2 Menu, F3 Files, F4 Actions, F6 Next pane, and Shift F6 Previous pane. Escape dismisses the topmost overlay and returns to its prior focus. Leave Tab for completion and Ctrl R for history search. Retain the current multiline Enter behavior.

Ctrl C needs a clear context rule: clear an idle draft, or request cancellation of the active foreground operation. Display cancelling until the runtime acknowledges the outcome. An explorer or menu callback must not manipulate server resource ownership directly.

Menu actions and palette actions use one registry containing a name, shortcut, availability condition, and handler. File actions prepare commands; View toggles panels; Session exposes verified status and cleanup actions; Help offers commands, matcher guidance, and shortcuts. Disabled actions explain what is missing.

Mouse interaction can follow keyboard support. It should remain optional because selection and copy behavior need testing in the actual terminal.

## Integration approach

Keep the existing language parser, completer, lexer, validator, history store, and runtime. Add a view layer that observes command and session events and owns display state. Rendering callbacks read cached snapshots; they must not perform filesystem scans or network requests.

For the enriched prompt, add a callable bottom toolbar and use prompt_toolkit output coordination for events arriving during input. For the workspace, render events inside the results view and coalesce status redraws with Application.invalidate. Do not print ordinary background events directly into the managed screen.

Run the workspace with Application.run_async within the existing event loop. The [asyncio guide](https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/advanced_topics/asyncio.html) documents this integration. Preserve the current separation between asynchronous session events and worker based command evaluation; the UI should receive safe snapshots rather than traverse mutable runtime values while a worker changes them.

A footer is presentation work and should not require a protobuf change. Remote browsing or unavailable counters are separate contract work and must start at api/. Preserve script, one shot, and piped input behavior when adding a proposed --ui workspace option.

## Suggested delivery order

1. **Status and output coordination.** Add connection and command lifecycle state, a responsive footer, and safe background output while keeping the current prompt.
2. **Optional workspace shell.** Add a bounded transcript, command editor, menus, shared action registry, and basic focus handling.
3. **Closable file explorer.** Add local lazy browsing, filtering, selected input indicators, command preparation, and narrow terminal fallback.
4. **Discovery and inspection.** Add action search, contextual help, variables, and supported work status after the basic workflow feels stable.

Begin with the footer and output coordination. The explorer should follow the workspace shell because its value depends on reliable focus, result display, and task state.

## Evidence and acceptance

A synthetic layout probe using prompt_toolkit 3.0.53 passed five checks: F3 opened the sidebar, F3 closed it and preserved the draft, the footer read updated state, a menu action used the same toggle, and the asynchronous application exited cleanly. It used pipe input and DummyOutput, so it establishes widget composition and focus feasibility, not terminal appearance or CTK integration.

Before implementing the proposal, use these acceptance criteria:

- Preserve a multiline draft, cursor position, completion, and history search across opening and closing panels.
- Keep the editor responsive while queries stream; show failures and cancellation acknowledgment accurately.
- Submit prepared commands through the existing history path exactly once.
- Bound file listings, transcript size, and value inspection; label truncation and make export discoverable.
- Check small and large terminal sizes, resize, Unicode widths, paste, copy and selection, macOS terminals, and a RHEL or SSH session.
- Preserve noninteractive output and exit status; run the required C++ and Python suites once application changes exist.

The main assumptions to validate are whether users prefer terminal scrollback or an in app transcript, whether the file pane helps their real input selection workflow, and whether the proposed shortcuts survive their terminal and SSH setup.

## Sources and worktree record

Official sources:

- [Prompt and toolbar documentation](https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/asking_for_input.html).
- [Application layout and focus documentation](https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/full_screen_apps.html).
- [Asyncio integration documentation](https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/advanced_topics/asyncio.html).
- [Widget and application API reference](https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/reference.html).

The source snapshots, baseline audit, and reproducible probes are saved under docs/research/console-ux/ in the Git worktree at /Users/husam/.claude/worktrees/clang-toolkit/console-ux-exploration, branch codex/console-ux-exploration, baseline ed20acf. Your uncommitted work in the main checkout is excluded from that baseline.

The wiki research page, index additions, and log entry are staged in that worktree. The canonical personal wiki is not a Git repository, so it has not been modified under the requirement that all work stay in a Git worktree.


Related wiki pages: [[pages/planning/clang-toolkit-console-design]], [[pages/planning/clang-toolkit-interactive-runtime]], [[pages/manuals/clang-toolkit-console-resource-management]].

## Sources

- [2026-10-10-ctk-console-ui-baseline.md](../../raw/2026-10-10-ctk-console-ui-baseline.md).
- [2026-10-10-ctk-console-wiki-context.md](../../raw/2026-10-10-ctk-console-wiki-context.md).
- [2026-10-10-prompt-toolkit-api-probe.md](../../raw/2026-10-10-prompt-toolkit-api-probe.md).
- [2026-10-10-prompt-toolkit-asyncio.md](../../raw/2026-10-10-prompt-toolkit-asyncio.md).
- [2026-10-10-prompt-toolkit-layout-probe.md](../../raw/2026-10-10-prompt-toolkit-layout-probe.md).
- [2026-10-10-prompt-toolkit-layout.md](../../raw/2026-10-10-prompt-toolkit-layout.md).
- [2026-10-10-prompt-toolkit-prompts.md](../../raw/2026-10-10-prompt-toolkit-prompts.md).
- [2026-10-10-prompt-toolkit-reference.md](../../raw/2026-10-10-prompt-toolkit-reference.md).
