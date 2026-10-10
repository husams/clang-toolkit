# Expression values

CTK evaluates operations as values. A standalone operation keeps its existing
display behavior; `let`, list/dictionary entries, and grouped expressions consume
the value without automatic display. Explicit writes and mutations still happen.
Commands that only perform an effect return null. `quit` and `exit` remain
console control flow.

```text
let state = resource status
let inventory = file list
let values = [server status, resource status]
let groups = foreach item in [1, 2] do {
    let value = $item;
    $value;
}
```

`foreach` and `batch` brace bodies contribute their final evaluated value.
An assignment contributes its assigned value; an empty body contributes null.
Assigned `foreach` blocks collect one final value per iteration. Standalone
blocks preserve their existing per-statement output. Match `do` blocks retain
their captured display text as the returned value; scoped analysis blocks keep
their explicit terminal `yield` contract.

## Batch values

```text
let inputs = files "server/src/"
let run = batch part in $inputs size 1 jobs 1 do {
    let matches = match functionDecl(isExpansionInMainFile()).bind("f") in $part.inputs;
    save $matches to "batch-${part.index}.json" as json;
    $matches;
}
print $run.status
print $run.completed_groups
save $run.results to "all-batches.json" as json
```

The report contains the existing resource, cleanup, file and group counters plus:

| Field | Value |
| --- | --- |
| `status` | `completed` or `failed`. |
| `results` | One detached final value per successfully completed group, in manifest order. |
| `result_group_indices` | The one-based group index corresponding to each result. |
| `results_complete` | Whether all manifest groups produced their complete collected values; failed, skipped or cancelled groups make it false. |

The report also includes aggregate result count/bytes and bounded group-error
samples. Interrupts expose a partial `status: cancelled` report on the raised
exception after cleanup; the interrupted assignment retains its previous value.

Match results become detached copies before their group's resources close.
They support local inspection and saving, while native continuation still
requires a live match result. File handles, parsed trees, and closures cannot be
collected. Scalars, lists, dictionaries and copied semantic values can be.
Collection is bounded across the run to 10,000 retained items and 1,000,000 estimated bytes;
exceeding a result bound fails the group
and preserves earlier successful values, rather than returning silent truncation.

An assigned or otherwise consumed batch is silent, including its body display
and progress events. Explicit `save` and `print ... to ...` writes remain effects.
A standalone batch retains its body output, default progress and final report:

```text
batch part in $inputs size 1 progress off do {
    let matches = match functionDecl(isExpansionInMainFile()).bind("f") in $part.inputs;
    save $matches to "batch-${part.index}.json" as json;
}
```

`progress off` suppresses lifecycle events; body output and the standalone final
report remain enabled. `progress on` is the default for standalone batches.
Consuming a batch value suppresses automatic output even with `progress on`.
The other `size`, `count`, `jobs`, `memory`, and `on error` controls are unchanged.
The compact standalone report displays collection counts/bytes; its separate
returned `results` array is available to consumed expressions.

An operational group failure returns an inspectable `status: failed` report in
value context. Standalone failure keeps its error/nonzero behavior. Invalid
syntax/options and interrupts still raise; assignment preserves its previous
binding if evaluation raises. Scope cleanup must be acknowledged before another
group starts, including after failures.

Batch bodies reject nested batches, yielding analysis blocks and legacy cursor
open/continue/restart, background and session start/add/match/resume operations
before admission. Those acquisition paths do not carry group ownership; use the
scoped `match`, `parse`, file and analysis operations inside a batch. The legacy
commands remain expressions outside batch bodies.
