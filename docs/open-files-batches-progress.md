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
