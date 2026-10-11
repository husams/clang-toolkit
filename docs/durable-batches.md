# Durable batch runs

Durable runs execute native ANTLR script bodies on the serving machine. The server
stores the frozen manifest, per-group outcome, detached results and export
receipts, and keeps working when the initiating client disconnects. The console
foreground `batch` expression remains available with its established Lark body
language and automatic display rules.

```text
let inputs = files "src/*.cpp"
let run = background batch part in $inputs size 2 jobs 2 do {
    let rows = match functionDecl(isExpansionInMainFile()).bind("f") in $part.inputs;
    save $rows to "/tmp/functions-${part.index}.json" as json;
    $rows;
}
let current = batch status $run
let collected = batch promote $current
```

`durable batch` selects the same server-owned execution path. The returned run
has a stable `run_id` and monotonic `revision`; status accepts either a run value
or its ID after reconnect. Mutating controls require a current revision. The
server checks the authenticated caller's ownership before returning a run or
acting on it. Local unauthenticated transports retain the established
`local-user` ownership domain.

The synchronous and asynchronous clients provide `start_batch`, `batch_status`,
`cancel_batch`, `resume_batch` and `retry_batch`. Start accepts a `FileSet` or
typed descriptor sequence and a native body string, plus the group variable,
size or count, jobs, memory budget, continue-on-error and optional `request_id`.
Reuse that request ID with the exact original request after a lost Start reply;
the server returns the existing run. A changed payload for that key is rejected.

```python
run = client.start_batch(
    client.discover_files(["src/*.cpp"]),
    'let rows = match functionDecl() in $part.inputs; rows;',
    size=2,
    request_id="function-scan-2026-10-10",
)
current = client.batch_status(run.run_id)
# AsyncClient exposes the same operations with await.
```

Each group reserves its inputs and native memory before parsing, keeps work in
the admitted scope and releases its native ownership before scheduling the next
group. Main-file content is fingerprinted when the durable manifest is created.
Consumed source/header/lookup observations and the frozen compilation profile
are recorded when the group is first acquired. Retry revalidates those inputs;
changed sources or profiles require a new run. Changes to guarded compiler lookup
directories also invalidate that closure, so keep retryable exports outside those
lookup roots. Native admission is separate from
detached result and durable metadata limits; no RSS ceiling is promised.
Private directories used to restore cached ASTs are excluded from dependency
observations; real consumed headers and compiler lookup directories remain guarded.

`batch cancel` stops new work and cooperatively cancels current work. The status
report records whether cleanup was acknowledged. `batch resume` schedules pending
groups; `batch retry` also considers known failed or cancelled groups. Completed
groups keep their results and exports. A process restart does not automatically
replay an interrupted body: a running group's outcome becomes unknown. An
unknown outcome must never be presented as an ordinary retryable failure.

Durable JSON and protobuf exports contain the typed native `ScriptValue`
envelope. Paths are interpreted on the serving machine. The registry records an
intent and output digest before publishing a complete file, then records a
committed receipt. Journal and output replacements synchronize their file and
parent directory chain, including newly created ancestors. A journal write error
closes the registry to status and control requests until restart, so an uncertain
publication cannot create duplicate runs or expose stale success. A repeat of an already committed identical export verifies its
digest and skips the write; altered or unresolved output is rejected. Separate
groups must use distinct canonical destinations. Append exports are unsupported.
An existing directory destination is rejected before an intent is recorded, so
repairing that known failure can permit retry when the frozen input closure still
matches. A failure after a publication attempt retains the conservative unknown
outcome rules.
On restart, an intent is reconciled only when the existing complete output
matches its recorded digest; other outcomes stay unknown.

Group results contain copied semantic values without native cursor identities.
`batch promote` explicitly copies successful detached values into the local
runtime. Promotion does not recreate an AST or a live continuation cursor.
Detached match rows preserve their binding locations but do not encode the
originating input, so `source_file` is `None`; a header or macro binding location
must not be mistaken for that missing identity.
Native `files`, batch expressions, scalar/list/object values, member/index access
and collection functions are parsed and evaluated through ANTLR and C++; see
[server-scripting.md](server-scripting.md) for the final language surface.

Implementation and validation evidence is tracked in
[durable-batches-progress.md](durable-batches-progress.md).
