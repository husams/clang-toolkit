# Opened files and bounded batches — implementation progress

Authoritative scope: [wiki plan](/Users/husam/workspace/wiki/pages/planning/clang-toolkit-open-files-and-batches.md), first three phases; background/resumable/native-script parity deferred.

Baseline: HEAD `7d3cb87`, existing console collections/imports/matcher-catalog edits preserved. Tracked baseline diff and status saved outside the checkout at `/tmp/ctk-open-files-baseline/`.

| Story | Owner | State | Acceptance |
| --- | --- | --- | --- |
| F1 additive wire/resource contract and generated SDKs | coordinator | complete | 256-proto gate; Python/TypeScript generation and TS checks |
| F2 serving-side discovery, file leases, cursor/work inventory | server_resources | complete | identity, aliases, independent pins, refresh, owner-scoped work-only rows |
| F3 atomic scopes, provisional ownership, expiry and cleanup acknowledgment | server_resources | complete | failed replies, cancellation, transient accounting |
| F4 typed Python API and partition helpers | python_resources | complete | sync/async parity, profile preservation and native acceptance |
| F5 Lark file/batch commands, controls, escape/output bounds | console_batches | complete | real console, help/completion, stop/continue, SIGINT cleanup |
| F6 integration, full gates and wiki/manual updates | coordinator | complete | native/Python/BDD, API/serializer/TS, controlled and repository scans |

## Validation

Fresh verification on 2026-10-10:

- Full native suite passed 312/312 using `/tmp/ctk-server-resources-build/` and private `CTK_STORAGE_ROOT=/tmp/ctk-resource-final-storage`; includes database-relative script paths, lexical source identity, owner-scoped work-only inventory and work snapshot admission.
- Full Python unit suite passed 821/821 after the final interruption, status-classification and rejected-input/skip-accounting changes.
- Full real-server E2E BDD suite passed 103/103 against the current native binary; includes the preserved preexisting console features and new opened-file/batch acceptance.
- API gate: 256 compiling protos, 251 self-contained semantic payloads. Serializer gate: 251 dedicated classes, 923 extraction paths.
- Generated TypeScript check/build and default test suite passed: 52 passed, 24 optional integrations skipped.
- Controlled real-server BDD checks cover frozen manifests, independent leases, aliases/attachments, refresh, atomic admission, borrowed pins, a reply lost after cursor publication, detached native analyses/scripts, and saved output before stop/continue failure.
- Repository acceptance: 13 `server/src/application/*.cpp` inputs, server `max_files=1`, size 1/jobs 1/memory 768 MiB, 13 completed scopes, 13 successful JSON saves, 558 main-file function definitions equal to serial SDK results. Every terminal scope acknowledged cleanup with zero native/reserved/cursor/file/work ownership, and final global native/cache accounting returned to zero. Peak accounted bytes: 496,061,945; peak reservation: 16,777,216. Evidence: `/tmp/ctk-repository-batches-evidence.json` and `/tmp/ctk-repository-batches-bpw168ij/`. Earlier 548-count acceptance preceded added inventory functions; each batch/serial pair agreed on its contemporaneous source.
- Real first-SIGINT: observed active native work, exit 130, next group skipped, cleanup acknowledged, Released tombstone and zero live counters; independent reusable cache baseline preserved. A one-shot parse/match/save also exited 0. Evidence: `/tmp/ctk_batch_sigint_final_evidence.json`.
- Lost scope-admission reply: a one-byte client receive limit returned RESOURCE_EXHAUSTED after the server committed two inputs and 33,554,432 reserved bytes. The console now treats framework reply-size rejection as unknown cleanup, stops later groups, and never retries the body; only explicit server admission-rejection details prove no work was admitted. Evidence: `/tmp/ctk_scope_open_receive_limit_evidence.json`.

All delivery gates are green on the final frozen source. The lost-reply fixture uses a 60-second deadline so concurrent cold native work does not replace its intended reply-size failure; it still requires RESOURCE_EXHAUSTED and a server-published cursor before cleanup. Native binary timestamps are newer than every changed native source, header and protobuf contract.

## Adopted defaults and boundaries

Batch jobs inherits the effective configured `pool_size` through the same resolver as direct multi-file matching; an explicit positive jobs override is local to the batch. Group bodies execute serially, and physical server concurrency remains bounded by its executor/admission limits.

Discovery caps: 10,000 inputs, 16 MiB metadata, 100,000 visited entries. Initial parse reservation: max(16 MiB, 64 × main-source bytes). Group output cap: 1,000,000 characters. Final report cap: 4,000 characters with at most eight sampled unknown-cleanup groups. Export counts describe successful `save` calls.

Resource scopes default to five-minute TTL, permit shorter positive TTLs, and retain terminal acknowledgment for a bounded five-minute/512-record history. Native global accounting deduplicates shared snapshots; per-scope attribution may overlap. Legacy query-input admission remains a separately reported domain. Admission estimates do not guarantee an RSS ceiling.

The full validation above ran before publication on baseline HEAD `7d3cb87`, preserving the existing console edits. On 2026-10-10 the user authorized committing and pushing all pending changes together, including collections/imports and matcher-catalog support. No shared-server restart was performed. RHEL packaging, background/resumable batches, and ANTLR native-script batch-language parity are deferred.

## Expression extension — 2026-10-10

User-authorized follow-up: evaluate operations as values, return batch status and
detached final group values, suppress automatic display in consumed expressions,
and expose standalone `progress on|off` (default on).

| Story | Owner | State | Acceptance |
| --- | --- | --- | --- |
| E1 common expression grammar/evaluator and foreach block values | python_resources | complete | operations in let/list/dict/grouped contexts; one evaluation; assigned silence |
| E2 batch report/results, detachment and progress control | console_batches | complete | final group values survive cleanup; bounded collection; failed reports inspectable |
| E3 independent expression/batch unit and native BDD coverage | scope_review | complete | 860 units and 11 affected native BDD scenarios; effects, failure/cap/cancellation and cleanup regressions |
| E4 spec/help/docs and full verification | coordinator | complete | wiki/published spec, 312 native/860 Python/104 BDD tests and real console probes |

The earlier delivery totals describe the published `ed1d55e` baseline.

### Extension verification

- Full native suite: 312/312 passed with private `CTK_STORAGE_ROOT`; log `/tmp/ctk-expressions-native.log`. This extension changes no C++ source or wire contract.
- Full Python unit suite: 860/860 passed; log `/tmp/ctk-expression-capture-full-units.log`. Covers command/list/dictionary/grouped values, exactly-once effects, final foreach/batch values, typed responses, silent assignments and preserved match-do captured text.
- Full real-server E2E BDD suite: 104/104 passed; log `/tmp/ctk-expressions-e2e-final.log`. The separately repeated 11 affected native scenarios also passed, including sync/async SDK match-do capture and detached batch persistence after cleanup.
- Actual TTY console acceptance against an isolated native server with `max_files=1`: two one-input groups returned detached matches of lengths 2 and 1, saved each group as JSON and the combined values as protobuf, and returned `completed`. Assigned `progress on` emitted no body/progress/report output; a standalone `progress off` kept body/final output, while default standalone progress emitted group-started/completed events. File leases and result cursors were zero after the collected match run. Fixture/artifacts: `/tmp/ctk-expression-console-_q1y6k9g/`.
- Failure/cap/cancellation tests preserve successful earlier values, expose bounded diagnostics/partial cancelled reports, preserve interrupted assignment bindings and acknowledge cleanup before another group. Legacy unscoped acquisitions are rejected recursively before admission.
- Ruff and diff whitespace checks passed; generated command reference equals live help. The wiki plan/manual/design and published specification have been updated and read back.

Native match copies remain usable for local inspection/export, while native continuation requires a live owner. Aggregate collection limits are 10,000 retained items and 1,000,000 estimated bytes. RHEL packaging, background/resumable batches, legacy ownership migration and native ANTLR batch-language parity remain deferred.

## Functional flatten — 2026-10-10

User-authorized follow-up: introduce `flatten($run.results)` after verifying all
previous changes are already committed on clean local/remote main `2fbcec2`.
One-level concatenation preserves order and row identity, skips empty children,
does not mutate/requery inputs, rejects noncollection children by index and
caps output at 10,000 items. `join` retains string semantics. Grammar, editor
tokenization, dedicated help and generated reference are updated.

Verification complete: all 878 Python unit tests and 105 full real-server E2E
BDD scenarios passed, along with seven separately repeated native batch
scenarios. The new real-server scenario flattens silent batch collections,
prints three function names, saves/reloads the flat protobuf list, and confirms
zero native ownership/accounting counters. No native source or wire contract
changed; the native suite's existing 312/312 result applies to the unchanged
native implementation.

Evidence: `/tmp/ctk-flatten-full-units.log`, `/tmp/ctk-flatten-native.log`,
`/tmp/ctk-flatten-e2e-final.log`. Actual TTY examples confirmed local flatten
assignment, nested-list preservation, standalone rendering and `help flatten`.
Ruff, whitespace and generated-help consistency checks passed; the wiki
plan/manual and published specification include the functional API.
