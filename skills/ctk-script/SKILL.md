---
name: ctk-script
description: Write, run, explain, and debug clang-toolkit .ctk scripts. Includes ready-made callgraph, CFG, local-variable and value-range analysis, class helpers, console queries, navigation, runnables, pipes, tuples and batches. Use the SDK reasoning skill for Python API tasks.
---

# Write and use CTK scripts

Produce runnable CTK statements that answer the user's question and verify them against the requested target when execution is authorized. Prefer direct binding fields and requested scalar output over dumping AST JSON.

## Start with a ready-made script

For static call graphs, read [callgraphs.md](references/callgraphs.md) and use [callgraph_project.ctk](scripts/callgraph_project.ctk) when its project/header boundary fits. It covers filenames, retained parsed files and matched functions; unlimited call depth and node counts; system-header exclusion; custom and optional strict filters; shallow graph structure; actual console output and root-site counts. Assigned graphs retain exact native callable references: `match ... in graph.nodes[i]` or `graph.function("qualified::name")` reuses their pinned AST without reparsing. Use [callgraph_match_nodes.ctk](scripts/callgraph_match_nodes.ctk) for the three-input matching example. The guide includes verified Linux output at merged revision `396306c` and a two-stage proof that closes the original handles and removes only a disposable source/header copy before matching nodes from all three graphs. A matched function selects reachable calls within its translation unit, not disconnected functions or a whole-project merge.

For CFGs, local usages or possible integer values, read [analysis.md](references/analysis.md) and run the matching bundled script with named arguments. It covers script selection, absolute skill paths, endpoints/build inputs, JSON exports, result interpretation and reuse of already parsed trees and matched nodes. Prefer these scripts when they cover the request; refine their selectors when an overload or shadowed declaration needs disambiguation.

Use `--script` for executable analysis scripts. Import the definitions-only helper library for reusable class, inheritance and matcher functions; the guide distinguishes these two workflows.

## Choose the language

- **Console DSL:** `ctk` (including `uv run ctk`) defaults to the compiled engine. It supports expressions, conditions, mutation, loops, pipelines and tuples. Read [console.md](references/console.md). `python -m clang_toolkit.cli.app` and `scripts/manual_console.sh` retain the legacy default; pass `--script-engine compiled` there when using the compiled syntax. `--script-engine tree` selects the reference evaluator, and `legacy` selects the previous parser.
- **Pipes, tuples and formatting:** read [pipes.md](references/pipes.md) for `value | filter(args)`, parameterized user filters, `zip`, tuple patterns in `foreach`, and `map((name, count) ...)` callbacks shared by `filter`, `sort_by` and `unique_by`. Leading `|` stages continue across newlines without outer parentheses. Prefer built-in filters for local transformations; use `json`, `pretty` or `table` for structured output. [pipe_report.ctk](scripts/pipe_report.ctk) is a complete runnable example.
- **Loops and indexes:** use `foreach item in items do BODY` and access its zero-based ordinal as `item.index`; use `item.value` for colliding data fields. Read [loops.md](references/loops.md) for complete executable examples, `while`, `repeat … until`, `break`, `continue`, and collection/scope rules.
- **List patterns:** `let [a, b] = xs` matches exactly two items; `let head : tail = xs` matches a non-empty list. Patterns also work in runnable parameters, inline callbacks and `foreach`. An ungrouped runnable-parameter colon introduces a public label, so group cons patterns as `let first((head : tail)) = head`, `map(((head : tail)) head)`, or `((head : tail))` in a clause. Standalone destructuring and `foreach` keep `head : tail`. See [list patterns](references/list-patterns.md).
- **Executable blocks:** read [runnables.md](references/runnables.md) for `let name(params) = expression`, brace bodies, inline `(params) body`, defaults, closures, optional `on error`/`on exit`, and `break`/`continue`. Both body forms compile to Python; returned and indexed callables can be invoked directly.
- **Ready-made utilities:** read [utilities.md](references/utilities.md), then import [ctk_helpers.ctk](scripts/ctk_helpers.ctk) using its resolved absolute skill path. It supplies live `classByName` bindings, `ancestors`, `classInfo`, `classTemplateInfo`, member/function/call summaries, collection callbacks and reusable matchers. These are imported functions, not server commands.
- **Named script arguments:** `ctk FILE.ctk x=value` runs the file and exposes the literal string as `arg.x`; `--script`, `--execute`, and piped runs accept the same arguments.
- **Text and CSV inputs:** `read` returns text lines or CSV records; trim strings explicitly with `.strip()`. See the complete input example in [console.md](references/console.md).
- **Native node navigation and inheritance:** read [navigation.md](references/navigation.md) for `traverse` from any retained node, filtered `peek`/`step`, matcher scopes, direct base bindings, and streaming versus explicit collection.
- **Native server DSL:** the console's `script "SOURCE" [in "TARGET"]`, SDK `run_script`, or a `background batch`/`durable batch` body. Read [native.md](references/native.md). This language uses explicit `emit` statements.
- For multi-file discovery, batching, resource cleanup, and exports, also read [batches.md](references/batches.md).

`--script FILE.ctk` and `script "SOURCE"` are different execution paths. Do not mix their comments, functions, field methods, loop terminators, or output conventions. Console pipelines, tuples, runnables, and loop forms do not add those features to legacy/native server scripts or server-side batch bodies.

## Work through the language

Use the supplied target and endpoint; `ctk` without an override uses its configured server. Use `help pipes`, `help match`, `help foreach`, `help loops`, `help predicates`, or the relevant topic to confirm syntax, and `server status` to check readiness. Do not install packages, restart the user's service, change persistent settings, or substitute Python SDK calls merely to make a script example run.

When the user requests console-only exploration or forbids file reading, use a real TTY-backed `ctk` session, bounded statements, console help, `.keys`, and `inspect`; do not inspect target source, configuration, or implementation files. For ordinary script authoring, use bundled references first and read target source only when the user asks. Follow applicable wiki-first instructions for project/design context; historical proposals do not prove runtime support.

Verify in small steps: one target, one matcher, row count, one binding's fields, then iteration or continuation. Use `let rows = match ...`, including `match`; `let predicate = functionDecl(...)` only constructs a matcher. Avoid indexing until a nonempty result is established.

The interactive console accepts whole scripts with newline/semicolon-separated top-level statements, just like `--script` or `--execute`. In the workspace, paste the script and press Ctrl+J to run; use Ctrl+Enter, Option+Enter (macOS), Alt+Enter, or Shift+Enter to type additional lines, including before another `|` stage. Execution stops at the first error or exit, and history keeps the whole submission once. For a multi-file continuation, `source_match_index` is local to the originating file's match result, not a global index into the combined parent collection; use `source_file` and per-file parents for attribution.

Use `row.f.qualified_name`, `row.f.decl_name`, and other discovered direct properties. Preserve explicit bindings and implicit `root`. Keep headers included unless the user requests main-file-only analysis. Query AST children through follow-up matching rather than treating unrequested fields as empty.

## Evidence and boundaries

- Check field availability, query completion, provenance, and limits before interpreting missing data. Errors or limits do not establish symbol absence.
- Retain live values for native continuation. Exported, loaded, batch-collected, and server-returned values are detached data.
- Default traversal includes implicit nodes. Overlapping roots and repeated rows preserve multiplicity; deduplicate deliberately when needed.
- `foreach ... select ... where ... group by ... having ... do { ... }` is a **draft proposal in the checked 2026-10-11 baseline**. Confirm current console support before presenting it as executable. When discussing the proposal, preserve clause order, direct dot access, and the single-stream design. Proposed helpers such as `collect` and `row_info` also require verification.
- Use pipes for local projection, filtering, sorting and formatting; native collection methods such as `.unique("f.symbol_identity")` remain useful for live query results. Do not replace a mutating traversal queue or native query with a local formatter. State remaining DSL gaps plainly.

Return the exact script and observed output or an explicit unverified boundary when details are requested. Follow the user's response-length preference. Parsing syntax or reading a manual is not live verification.

Pipe guidance and bundled helpers target the compiled and tree console engines from PR #33. The flow recipes also require the native CFG/reuse, variable-flow and interval support merged in PRs #31, #32 and #34. Use bare names, `//` comments and `{expression}` interpolation in new console scripts. Native server-language guidance retains its 2026-10-11 baseline; each reference lists maintained sources for refresh. Check console help and server capabilities when installed behavior differs.
