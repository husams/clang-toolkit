# Multi-file scripts and batches

## Discovery location

Console `glob("src/**/*.cpp")` discovers relative paths on the **client**, returning File/Directory values; it rejects absolute patterns. Direct console match targets accept directories, absolute/relative globs, and lists using client expansion. `files "PATH"` discovers/fixes serving-side input and compiler-profile metadata without parsing. For remote servers, use serving-side discovery or explicit server-accessible targets.

```text
let inputs = files "/project/src/**/*.cpp";
print $inputs.length;
file list discovered in $inputs;
```

Inspect diagnostics/profiles when parsing fails. Supply the correct compilation database/flags before interpreting empty results. `set` compiler/output configuration persists overrides; do not change it merely to demonstrate syntax.

## Foreground console batch

```text
let inputs = files "/project/src/**/*.cpp";
let run = batch part in $inputs size 2 do {
    let rows = match functionDecl(isDefinition()).bind("f") in $part.inputs;
    let names = foreach row in $rows do { $row.f.qualified_name; };
    $names;
};
print $run.status;
print $run.results_complete;
let names = flatten($run.results);
foreach name in $names do {
    print $name;
};
```

- Choose `size N` or `count N`. `jobs` defaults to configured `pool_size`; `jobs J` overrides parallel file work for this batch. The body is serial, group indices one-based.
- `$part.inputs`, `.paths`, `.index`, `.length` expose the group. Inputs freeze before execution; acknowledged resource cleanup precedes the next group.
- Assigned batches suppress automatic body/report output; progress defaults to on, with one-second running updates even in `let`. Use `progress off` for quiet execution. Explicit writes still occur. The body's final value is detached and collected.
- Inspect status, completeness and failed/skipped groups. Earlier successful values may coexist with failure. `on error continue` still reports a failed run.
- Collection is bounded across the run to 10,000 items/1,000,000 estimated bytes. Large tasks may need per-group exports instead of collecting every row.
- Detached results support inspection/export, not continuation. Continue matching inside the group while values are live.
- Extract requested fields while rows are live, as above. Flattened detached row envelopes do not expose the live `$row.f` shortcut; do not assume identical field paths after detachment. Inspect copied envelopes when full rows are actually needed.
- Foreground nesting and legacy acquisition commands are restricted. Check current help before using scoped yielding blocks inside a batch; historical documentation differs on this boundary.

When the user requests exports, add `save $rows to "/output/batch-${part.index}.json" as json;`. End with a small collectable scalar such as `$part.index;` to avoid retaining all rows. File/tree handles cannot be collected.

## Durable server batches

Use asynchronous execution when the task calls for it; bodies use native syntax:

```text
background batch part in $inputs size 2 request "functions-v1" do {
    let rows = match functionDecl(isDefinition()).bind("f") in $part.inputs;
    $rows;
}
```

Capture the returned run ID/report. Consult current help for `batch status|cancel|resume|retry` and `batch promote`. `let run = batch status $run` refreshes a report. Lifecycle mutations use the last report revision. Reuse the same request key to recover an uncertain StartBatch response; a new key starts a new run. Do not blindly retry unknown outcomes after restart. Retry revalidates frozen inputs/profiles/dependencies; promotion copies detached results without restoring native handles. Native nested groups share parent ownership and validate input/profile subsets and budgets.

Narrow queries or reduce groups after resource failures; do not claim absence. File leases and independent cursors can pin the same snapshot: closing a lease need not release every owner. Preserve requested output destinations and avoid service restarts as a debugging side effect.

## Sources

- `docs/console-command-reference.md`
- `docs/expression-values.md`
- `docs/durable-batches.md`
- `~/workspace/wiki/pages/manuals/clang-toolkit-console-resource-management.md`
- `~/workspace/wiki/pages/planning/clang-toolkit-open-files-and-batches.md`
