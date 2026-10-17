# Definitions-only indexing and conservative header reuse

Implementation: isolated worktree `index-definitions-context-reuse`, branch
`codex/definitions-header-reuse`, based on `ac0e7a6` (PR #55).
The managed server and its completed index are not changed by this work.

## What is indexed

Only definitions are emitted. Function prototypes, forward tags, declaration-only
variables, and function parameters are discarded before generating USRs. Defined
functions (including defaulted/deleted functions), defined variables and tags,
fields, aliases, concepts, enumerators, namespaces, and structured bindings remain
available for navigation. Template wrappers are omitted and their defining
underlying declarations are visited.

System headers, including standard-library headers, are excluded before declaration
traversal and USR generation. Clang still parses required includes to resolve C++
correctly. File paths are canonicalized once per FileID instead of once per symbol.

The persistent index still has exactly three SQLite tables: metadata,
translation_unit, and symbol. The extraction fingerprint changes automatically,
so upgrading makes old extractor contributions stale once; subsequent source/header
edits still refresh only affected TUs through the existing dependency mechanism.

## Header reuse

The optional derived cache reuses extracted definition records, not native ASTs or
Clang parsing. Each user-header snapshot binds its physical path and exact bytes,
compiler/toolchain/environment/options, normalized actual CC1 invocation, and the
complete preceding expanded token context through that header's exit. Token
spelling and expansion provenance are included. Nested headers can match even
when their outer wrapper headers differ.

Macro-expanded tokens participate in the context; changed macro results, prior
C++ declarations, include selection, same-size header edits, and symlink retargets
therefore miss rather than returning another context's definitions. Nullability
and explicit visibility pragmas enter the context. Macro stack pragmas are reflected in subsequent expanded tokens; diagnostic-only
deprecation pragmas and literal loop unroll hints are handled separately.
Unknown pragmas and volatile builtins conservatively disable later snapshots.

PCH/forced includes, modules, external ASTs, plugins, response/config files,
overlays, and unsupported compiler modes fall back to live extraction. A loaded
ASTReader is checked by its module count; an empty reader is normal on C++20 TUs.
Declarations completed outside their header, or with lexical parents spanning
files, are always extracted live. The visitor still recurses into cached files so
uncached nested declarations cannot disappear.

Files are checksummed, bounded, and atomically published. Invalid or unavailable
cache files fall back to live extraction. Budgets are 32 MiB per file, 64 MiB of
estimated native payload per TU, and 512 MiB / 4,096 files on disk. Only the eight
largest new header payloads per TU are saved, avoiding hundreds of tiny writes.
This derived cache adds no SQLite tables and can be discarded.

The prefix context is deliberately conservative. Different earlier semantic input
can prevent reuse even when a particular header would produce identical symbols.
In particular, cold batch.pb.cc/query.pb.cc did not share snapshots in the measured
sample. Their exact-context repeats under the final retention policy reused 45,901 and
43,670 definitions respectively; all serialized symbol fields matched fresh output.
These observations establish repeat reuse, not a general project-wide cross-TU
cache speedup. Focused tests separately verify cross-TU and nested-header hits.

## Background behavior

Extraction and cache I/O remain in the existing low-priority isolated worker.
Foreground parsing, status and symbol RPCs retain their independent execution and
read paths. No parallel TU scheduler or foreground lock is introduced. Existing
pause/resume/cancel controls and affected-TU dependency checks are retained.

## Verification

The 14 focused tests cover definition kinds, system-header exclusion, exact and
nested cross-TU reuse, macro contexts, prior declarations, header edits, include
selection, same-size edits, symlink retargets, volatile builtins, pragmas, forced
inputs, split declarations, and corrupt-cache fallback. Cache results are compared
against fresh extraction, including every stored symbol field.

The matched worker experiment uses twelve actual clang-toolkit TUs: two ANTLR
sources, batch/common/query generated protobuf sources, query_controller,
declaration_order, cxx_record_decl, binary_operator, test_cached_values,
index_service, and parser. The baseline extractor is from the base revision,
compiled with exactly the candidate's Release flags and libraries. Both use the
same compile database and source files. The candidate emits 303,390 definitions
versus 676,489 earlier rows (55.2% fewer); these are summed extraction rows, not
physical SQLite row counts. The final server measurements below include worker startup, extraction, derived
cache I/O, and SQLite publication.


## Measured results

On the twelve selected real TUs, cold indexing reached COMPLETE with zero failures
in 42.303 s with the old extractor and 40.161 s with the candidate (5.1% faster).
The backend/publication code and Release flags/libraries were held constant.
This modest end-to-end gain is distinct from the larger extraction-only gain seen
during development; no project-wide twofold speedup is established.

Physical symbol rows fell from 253,813 to 116,305 (54.2% fewer), with zero
non-definition rows and zero standard-header rows in the candidate. All three
SQLite tables remain unchanged. SQLite plus WAL at completion measured
287,248,384 versus 140,999,344 bytes; the optional derived cache used 65,090,214
additional bytes. Clang/LLVM API headers explicitly supplied as ordinary user
include directories remain indexed; they are distinct from standard headers.

During active indexing, all 20 probe iterations returned populated results from
multiple TUs. Exact-name/prefix/USR queries used `ctk::ast::v1::APArrayValue` and
`ctk::ast::v1::APArray`; the fresh parse probes each used a different source file.

| Request | Active: samples / mean / max | Idle: samples / mean / max |
| --- | --- | --- |
| Cross-TU exact, prefix and USR | 80 / 1.94 / 4.20 ms | 80 / 2.99 / 6.92 ms |
| Server status | 30 / 1.30 / 2.02 ms | 30 / 1.99 / 3.21 ms |
| Fresh parse and match | 8 / 22.95 / 27.47 ms | 8 / 34.12 / 40.87 ms |

No probe timed out. The private server completed all twelve TUs during the probe
run. These are sample measurements, not a measured completion time for all 623
TUs in the managed server's project.

Validation completed: 454/454 C++ tests, 2,500/2,500 Python unit tests, and all 199
E2E cases. The full E2E run passed 197 cases; its two version-command failures
were due to the fresh worktree lacking the normal ignored client build stamp.
Generating that installation metadata and rerunning both version cases passed
2/2; no product source change was needed. The E2E index cases cover pause/resume,
affected-TU refresh, failed-refresh recovery, standard exclusion, console status,
and foreground requests during extraction. The no-network protobuf target also
configured and built successfully; formatting and diff whitespace checks passed.

An additional copied-source incremental timing trial did not finish in the old
baseline and produced a partial worker response. It is excluded from speed claims;
selective refresh is established by the native and E2E tests, and exact-context
reuse by the successful real-worker output comparisons. No warm incremental
end-to-end speedup is claimed from that trial.

## Full-project measurement

The fresh full run completed all 623 TUs in 43m 43.467s, with zero failed TUs. Sampled cross-TU lookups stayed below 42 ms and foreground parse/match requests below 134 ms, with zero RPC failures or timeouts. This does not meet the desired indexing speed; see [the full measured report](index-full-623-validation.md) for build/load conditions, content checks and observer corrections.

## Initial optimized measurement before final review

The final fresh run completed **623/623 TUs in 17m15.916s**, with zero failed
TUs: an observed 2.53x speedup over 43m43.467s. The controller reuses directory
digests guarded by kernel change notifications. Foreground work now suspends
and resumes the isolated worker instead of discarding extraction and restarting
validation of completed TUs; publication also waits rather than rolling back
solely because a request arrived. CPU/I/O priority and worker resource limits
remain in place, with suspended time excluded from the worker wall deadline.

All 771 sampled active requests succeeded. Cross-TU exact/prefix/USR lookups
stayed below 9 ms, real out-of-line definition lookups below 4 ms, fresh native
parse/match below 36 ms, and status below 10 ms. All 202,255 physical definition
records and every one of the 623 TU/header-context memberships match the
intermediate completed index. There are still three SQLite tables, zero
non-definition rows and zero checked standard-header include rows.

All 462 native cases pass together; all 2,500 Python unit cases have passing
results (one startup timeout passed on retry); all 199 E2E cases pass together.
The measurements use the same frozen 623-TU compile database and Release flags,
with empty persistent/derived caches. OS caches and host activity are uncontrolled;
the older run also predates an edit to one test source. See the
[profile and fix](index-performance-profile.md) and
[final full measurement](index-full-623-optimized-validation.md) for evidence,
timing limits and the source-difference audit.

## Final admission validation and worker-exit race fixes

Current code is `4cfb528`. The final commit validator runs after foreground admission and rechecks dependency digests, compile-command contents, and worker identity before SQLite publication. If foreground or pause admission occurs partway through manifest validation, the validator clears the partial digest map and retries from the first dependency. This closes the stale-input gap without hashing under the status mutex or repeating hashes in the ordinary no-wait path. Deterministic tests cover edits during both final admission and an inner validation wait; both are red against the old implementation.

The worker controller reaps completed children and caches their exit status rather than signaling an exited child, including completion between polling and signaling. The console terminal progress-ordering correction is included separately and has no index-data effect.

Verification for this code: all 465 native tests passed (78.525s), all 2,817 Python unit tests passed (355.07s), and the full E2E run passed 206 cases with one workspace-ordering failure. After correcting it, that case and all three indexing cases passed together on the final build. The final build’s 32 focused native tests passed (32.206s), and its four focused E2E tests passed (37.18s). Linux was not run because Podman was stopped.

The final fresh 623-TU benchmark completed in **17m21.032s (1041.032s)** with zero failed, skipped or pending TUs. All 771 concurrent sampled requests passed: exact/USR below 6ms, prefix below 11ms, real separate-TU function-definition lookup below 4ms, fresh parse/match below 35ms, and status below 12ms. All 202,255 raw definition records and all 623 TU/header memberships match the previous completed index exactly; there are still only three SQLite tables and zero non-definition/checked standard-header rows.

The private run used the previously approved Interactive service policy with Utility indexing and nice-15 extraction workers. It retained empty private caches, the frozen original 623-TU compile database, the same Release flags and one-second status polling. The service was removed after verification, retaining `/tmp/ctk623-pr60-role-bgmli2s4`. The 43m43.467s, 35m06.108s and 17m15.916s runs remain historical; the final result separately verifies the corrected code. Host activity, OS cache warmth and historical source changes remain uncontrolled. See [the profile](index-performance-profile.md) and [full measurement](index-full-623-optimized-validation.md).
