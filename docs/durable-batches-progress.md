# Durable batches delivery

Authorized 2026-10-10: complete remaining batch features through publication.
Baseline: e0095fe; main and live origin/main agreed; checkout initially clean.
The independently authorized offset commit ed20acf was merged into main during
validation; all batch edits were preserved and the combined implementation is checked.

| Story | Acceptance | State |
| --- | --- | --- |
| Registry | Server-owned background runs; persisted manifests/results; ownership/revision guards; restart recovery; safe export receipts; acknowledged cleanup | Verified |
| Native language | ANTLR batches and typed collection expressions; scoped ownership; detached final values; list iteration | Verified |
| Console and SDK | Sync/async lifecycle methods; background/status/cancel/resume/retry; bounded explicit promotion | Verified |
| Verification | Full suites, restart/failure controls and real repository/console acceptance | Passed |
| Publication | Committed and pushed; matching remote and clean-main evidence recorded in the wiki and published spec | Published |

| Gate | Result |
| --- | --- |
| Native C++ suite | 335 passed; private storage root; configured dev build passed |
| Python unit suite | 896 passed after final SDK changes |
| Full real-server BDD suite | 114 distinct scenarios passed in three isolated 38-case shards |
| Final durable acceptance | All eight affected scenarios passed after the temporary-file ownership fix |
| TypeScript | Check/build and 52 default tests passed; all 24 live integration tests passed |
| API contract | 256 protos and 251 semantic payloads passed |
| Semantic serializer | 251 classes and 923 extraction paths passed |
| Python lint/help | Owned Ruff checks and 106 help/durable unit cases passed |

The live SDK acceptance parsed three real repository translation units with a
one-file server admission limit and three single-input groups. Batch and serial
matching each found 17 main-file function definitions. Native bytes, reserved
bytes, active work, file leases and result cursors were all zero after the batch.
The actual Lark runtime also completed background/status/promote with a detached
fixture match result. Sync start/status and promotion were verified directly;
control operations have async SDK and raw-wire lifecycle coverage.

Durable scenarios verify client disconnect/idempotence, stale revisions, native
expression values, committed exports surviving restart without replacement,
repair/retry of a known directory export failure, changed-header rejection,
cancel/resume/retry, and hard-stop recovery that refuses unknown outcomes.
Native tests also cover post-rename journal failure and normal quota rejection.
They do not simulate power loss or kernel/filesystem fault injection.

The final implementation fixes scope-key identity consistently, releases the
cursor operation lock before rollback close, excludes private AST restoration
directories from dependency observations, and removes failed temporary files only
while this writer owns them. Real source/header/lookup guards remain enforced.
Detached match rows preserve binding locations but do not encode their originating
input; their source_file is None. Native admission is not an RSS guarantee.

Independent reviewers approved all three stories, with zero open findings.
A bounded Cidx refresh indexed only server/src/script/engine.cpp and resolved
Engine::run and Engine::contains_batch definitions/declarations and signatures.
Database verification reported 845 files and zero missing files. The refresh
used --no-graph: relationship resolution is unavailable, freshness metadata is
null/unverifiable, and cross-TU semantic coverage is not established. Registry,
resource and native safety were independently reviewed against named code and
compiled/live evidence; this check does not claim a comprehensive fresh index.
