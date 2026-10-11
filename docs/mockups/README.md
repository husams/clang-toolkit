# Batch progress and source navigation mockup

Interactive design preview with sample data; no console runtime changes.

Page: https://chatgpt.com/space/page_c81ba2c9195c8191b509e4c7ccad804b

The editable source is `batch-source-navigation.html` in this isolated worktree.

- Batch progress updates one bar and a completed/total counter. Failed files count as completed; success/failure counts remain separate. Cancellation preserves partial progress and reports unprocessed files.
- Matches, bindings, and locations are links. A source window shows C++ syntax highlighting, line numbers, the selected source range, and all three sample matches for the file.
- Outline links navigate between matches and bindings. A callee binding navigates to its declaration, while its enclosing call match navigates to the call site. Previous/next controls cycle through matches. Close and Escape return focus to the originating console link.
- The existing console chrome, dark palette, results/help panes, editor, and footer are retained. The source viewer is depicted as a separate window below the console so both mockups can be reviewed together.

Browser verification: completed counts advance from 14/24 to 24/24; cancellation preserves counts and disables advancement; restart restores the sample. Match and binding links select lines 5–7, 12, or 16 as appropriate. All 19 source lines are numbered and syntax colored. Previous/next navigation and close/focus restoration work. Layout fits the tested 500px, 736px, and 1024px widths without page overflow; code and outline sit side by side on the wide view and stack on narrower views. The identical source is embedded in the Page.
