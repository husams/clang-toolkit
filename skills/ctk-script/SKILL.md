---
name: ctk-script
description: Write, run, explain, and debug clang-toolkit scripts using the compiled console DSL, legacy console DSL, or native server language. Use for .ctk files, parse/match/foreach workflows, native node navigation, inheritance queries, binding-field extraction, named or inline executable blocks, classInfo, ancestor trees, ready-made matchers, indexed foreach with .index, while, repeat until, break/continue, and script or batch execution; use the SDK reasoning skill for Python API tasks.
---

# Write and use CTK scripts

Produce runnable CTK statements that answer the user's question and verify them against the requested target when execution is authorized. Prefer direct binding fields and requested scalar output over dumping AST JSON.

## Choose the language

- **Console DSL:** `ctk` (including `uv run ctk`) defaults to the compiled engine. It supports arithmetic, Boolean logic, value-producing conditions, mutation, value predicates, and loop control. Read [console.md](references/console.md). `python -m clang_toolkit.cli.app` and `scripts/manual_console.sh` retain the legacy default; pass `--script-engine compiled` there when using the compiled syntax. `--script-engine tree` selects the reference evaluator, and `legacy` selects the previous parser.
- **Loops and indexes:** use `foreach item in items do BODY` and access its zero-based ordinal as `item.index`; use `item.value` for colliding data fields. Read [loops.md](references/loops.md) for complete executable examples, `while`, `repeat … until`, `break`, `continue`, and collection/scope rules.
- **Executable blocks:** read [runnables.md](references/runnables.md) for `let name(params) = expression`, brace bodies, inline `(params) = body`, defaults, closures, optional `on error`/`on exit`, and `break`/`continue`. Both body forms compile to Python; invoke through a bound name.
- **Ready-made utilities:** read [utilities.md](references/utilities.md), then import [ctk_helpers.ctk](scripts/ctk_helpers.ctk) using its resolved absolute skill path. It supplies live `classByName` bindings, `ancestors`, `classInfo`, `classTemplateInfo`, member/function/call summaries, collection callbacks and reusable matchers. These are imported functions, not server commands.
- **Named script arguments:** `ctk FILE.ctk x=value` runs the file and exposes the literal string as `arg.x`; `--script`, `--execute`, and piped runs accept the same arguments.
- **Text and CSV inputs:** `read` returns text lines or CSV records; trim strings explicitly with `.strip()`. See the complete input example in [console.md](references/console.md).
- **Native node navigation and inheritance:** read [navigation.md](references/navigation.md) for `traverse` from any retained node, filtered `peek`/`step`, matcher scopes, direct base bindings, and streaming versus explicit collection.
- **Native server DSL:** the console's `script "SOURCE" [in "TARGET"]`, SDK `run_script`, or a `background batch`/`durable batch` body. Read [native.md](references/native.md). This language uses explicit `emit` statements.
- For multi-file discovery, batching, resource cleanup, and exports, also read [batches.md](references/batches.md).

`--script FILE.ctk` and `script "SOURCE"` are different execution paths. Do not mix their comments, functions, field methods, loop terminators, or output conventions. Compiled-console arithmetic, conditions, mutation, value predicates, and new loop forms do not add those features to native server scripts or server-side batch bodies.

## Work through the language

Use the supplied target and endpoint; `ctk` without an override uses its configured server. Use `help match`, `help foreach`, `help loops`, `help predicates`, or the relevant topic to confirm syntax, and `server status` to check readiness. Do not install packages, restart the user's service, change persistent settings, or substitute Python SDK calls merely to make a script example run.

When the user requests console-only exploration or forbids file reading, use a real TTY-backed `ctk` session, bounded statements, console help, `.keys`, and `inspect`; do not inspect target source, configuration, or implementation files. For ordinary script authoring, use bundled references first and read target source only when the user asks. Follow applicable wiki-first instructions for project/design context; historical proposals do not prove runtime support.

Verify in small steps: one target, one matcher, row count, one binding's fields, then iteration or continuation. Use `let rows = match ...`, including `match`; `let predicate = functionDecl(...)` only constructs a matcher. Avoid indexing until a nonempty result is established.

The interactive console accepts whole scripts with newline/semicolon-separated top-level statements, just like `--script` or `--execute`. In the workspace, paste the script and press Ctrl+Enter or Ctrl+J; use Alt+Enter or Shift+Enter to type additional lines. Execution stops at the first error or exit, and history keeps the whole submission once. For a multi-file continuation, `source_match_index` is local to the originating file's match result, not a global index into the combined parent collection; use `source_file` and per-file parents for attribution.

Use `row.f.qualified_name`, `row.f.decl_name`, and other discovered direct properties. Preserve explicit bindings and implicit `root`. Keep headers included unless the user requests main-file-only analysis. Query AST children through follow-up matching rather than treating unrequested fields as empty.

## Evidence and boundaries

- Check field availability, query completion, provenance, and limits before interpreting missing data. Errors or limits do not establish symbol absence.
- Retain live values for native continuation. Exported, loaded, batch-collected, and server-returned values are detached data.
- Default traversal includes implicit nodes. Overlapping roots and repeated rows preserve multiplicity; deduplicate deliberately when needed.
- `foreach ... select ... where ... group by ... having ... do { ... }` is a **draft proposal in the checked 2026-10-11 baseline**. Confirm current console support before presenting it as executable. When discussing the proposal, preserve clause order, direct dot access, and the single-stream design. Proposed helpers such as `collect` and `row_info` also require verification.
- Use supported `.unique`, `.filter`, `.sort`, ordinary `foreach`, and local collections for current tasks when sufficient. State remaining DSL gaps plainly.

Return the exact script and observed output or an explicit unverified boundary when details are requested. Follow the user's response-length preference. Parsing syntax or reading a manual is not live verification.

Console guidance and bundled libraries were verified on 2026-10-13 against the compiled engine with named/inline runnables and indexed foreach, while/repeat and loop control. Use bare names, `//` comments and `{expression}` interpolation in new console scripts. Native server-language guidance retains its 2026-10-11 baseline; each reference lists maintained sources for refresh. Check `ctk --version` and server capabilities when installed behavior differs.
