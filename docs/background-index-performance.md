# Background index throughput

The live clang-toolkit run initially committed one TU roughly every 30–40 seconds
while the persistent index WAL reached 5.9 GiB after only a small fraction of 623
compile entries. Two CPU samples distinguish repeated include-tree validation
from the dominant insertion cost: the second sample spends 800 samples inside
SQLite insertion, including 435 reading WAL frames. Standalone extraction of the
first actual TU takes 1.633 seconds and emits 53,342 symbols.

The original symbol table used WITHOUT ROWID with a long composite primary key.
SQLite duplicated that key into five secondary lookup indexes. The writer also
used its default small page cache and deferred passive checkpointing until an
entire project pass completed.

The symbol table now uses SQLite's ordinary internal rowid: the public columns,
uniqueness constraint and three-table schema stay the same, but secondary indexes
store compact integer references. A background transaction migrates existing
symbols without clearing them. Cancellation/foreground admission interrupts the
migration; pause gates publication. WAL readers retain their previous snapshots.
The writer uses a 32 MiB page cache and passive checkpoints after each changed TU.
Checkpoints run outside the status mutex and never wait on readers. The 64 MiB
journal retention target is not a hard limit when readers pin a WAL snapshot.

## Isolated measurement

The benchmark inserts the same 53,342 extracted symbols into three TU contexts.
It uses the host Python SQLite library, so timings show the storage effect and
are not an end-to-end server throughput claim.

| Layout | Insertion seconds | Observed WAL MiB |
| --- | ---: | ---: |
| Original layout and settings | 4.378 | 468.3 |
| Original layout, 32 MiB cache, per-TU checkpoints | 4.750 | 206.3 |
| Rowid layout, 32 MiB cache, per-TU checkpoints | 2.451 | 66.8 |

Measurements and CPU samples: `/tmp/ctk-index-db-before-after.log`,
`/tmp/ctk-index-profile-before.log`, `/tmp/ctk-index-slow.sample.txt` and
`/tmp/ctk-index-slow2.sample.txt`. Existing wiki resource-management material
predates this index; these findings come from the live server and checkout.

## Live validation

After migration, a 86.5-second observation completed eight further TU entries
(about 10.8 seconds/TU), versus recent original commits around 30–40 seconds/TU.
This is an observed sample of successive ANTLR TUs, not a controlled whole-project
benchmark; some of the interval overlapped the final build. Index status probes
in the steady portion took about 1–3 ms. The WAL was observed at 261 MiB rather
than multiple GiB. Log: `/tmp/ctk-index-throughput-live-after.log`.

The dedicated controller thread now uses utility QoS on macOS and a lower
per-thread nice level on Linux. The extractor remains a separate lower-priority,
resource-bounded process. No foreground request uses the indexing executor or
waits for its AST extraction/database work.

The managed macOS server was launched as a submitted job with no ProcessType.
Apple documents CPU and I/O throttling for this default. A proposed Interactive
service policy avoids throttling the request-serving process while keeping
indexing's per-thread/per-worker limits. After explicit user approval, the policy
was installed at `/Users/husam/.local/state/ctk/server.plist`; launchctl reports
`spawn type = interactive (4)`. The server was restarted and indexing resumed.
Reference:
[Apple launchd manual](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5).

A separate SQLite compiler-optimization experiment measured 6.04 versus 5.85
seconds on a native storage probe; this was not a meaningful improvement and the
build-setting change was discarded.

## Coverage-query correction

Live cross-TU verification exposed another bottleneck once the index reached
about 100 contributions: coverage counts read status/indexed_at fields stored
after large dependency manifests in each translation_unit overflow record.
The 250 ms lookup budget could therefore expire before the symbol query ran.
A covering index on (status,indexed_at) makes both counts independent of those
manifests without adding a table. Query-plan regression checks require covering
index scans for both counts. After applying it, the previously failing lookup
returned 100 matches in a mean 25.38 ms (maximum 47.70 ms over five requests)
while indexing remained active. The final code includes automatic creation of
this index for new and existing projects; all ten focused native and four live
indexing checks passed again.

## Verification

- Final server/worker/native-test build succeeds.
- Ten focused native checks pass, including migration with a concurrent old-schema reader.
- Four live indexing E2E checks pass, including foreground parsing during extraction.
- Full isolated Python unit validation passed 2,493 tests. An initial run's
  configuration-sensitive console mock read the local compilation-database
  setting; the unchanged test passes in an isolated working directory.
- Full native validation passed 427 unique checks across the full run and two
  unchanged isolated timing reruns, with per-test storage isolation.
- Full BDD validation passed 195 scenarios in three batches of 65.

The final full isolated Python unit run passed **2,493 tests** in 155.54 seconds
(`/tmp/ctk-index-throughput-unit-isolated.log`); test code and limits were unchanged.
The initial isolated collection needed the repository on PYTHONPATH for its
cross-test imports. Background validation scheduling affected an existing 200 ms
cursor-expiry test and a shutdown-drain timing check; remaining validation returned
to normal scheduling after the approved server policy was active. Both checks
passed unchanged in isolation.

Full native coverage is complete: **425/427 passed in the full run**, and the two
background-scheduling-sensitive checks passed unchanged on isolated normal-priority
reruns (**2/2 passed**). Total unique native checks passing: **427**. No test
limits or expectations were relaxed. Logs:
`/tmp/ctk-index-throughput-ctest-final.log` and
`/tmp/ctk-index-throughput-ctest-retries.log`.
Full BDD validation passed **195/195** in three batches after the native suite.
Log: `/tmp/ctk-index-throughput-bdd-complete.log`; detailed batch logs are
`/tmp/ctk-index-throughput-bdd-{0,1,2}.log`.
Final live verification: the Interactive service is running, indexing is active,
and the latest status reports zero failed TUs. The first full 623-entry pass is
still in progress; stored contribution counts can include retained older contexts
until that pass retires them.

## Populated symbol lookup follow-up

Subsequent live checks reproduced `UNAVAILABLE: interrupted` for populated exact
and prefix searches during indexing. An empty-result probe had not exercised the
expensive response path. The old query joined TU metadata before sorting and
limiting matches; `status` follows the potentially large dependency manifest in
its overflow record. Repeated matching declarations amplified those reads.

The lookup now materializes a bounded set of narrow symbol keys before fetching
payloads, then materializes metadata once per distinct returned TU. A new covering
`translation_unit_lookup(id,main_file,arguments,status)` index avoids manifest
pages entirely. Reads explicitly select that index when present because SQLite
sometimes chose the primary key instead. Stores without the index remain readable;
the background writer adds it without rebuilding symbol contributions or adding
a table.

Prefix searches bound the name and qualified-name arms independently before
merging and deduplicating them. Prefix ordering now uses SQLite NOCASE to match
its existing case-insensitive matching and let the qualified-name prefix index
stop early; exact and USR ordering remain unchanged. Literal LIKE wildcard
escaping, distinct TU variants, truncation, and snapshot revision/staleness remain
supported.

A remaining first cold-page read exceeded the previous 250ms server cutoff even
after the query changes. The server budget is now one second, still bounded by an
earlier client deadline and cancellation. This allows cold disk reads without
relaxing result limits or serializing other RPCs. It is separate from the SQL
work reduction and must not be interpreted as a fourfold performance gain.

A new native regression exercises 3,000 contributions across three TU variants
with 2MiB manifests, exact and qualified matches, both prefix arms, a 1,000-row
USR response, deduplication, literal wildcard escaping, and a pre-upgrade store.
The plan guard requires the response metadata query to use a covering index.

Immediate post-restart live verification passed **40/40 populated lookups**
(exact names, a roughly 97,000-match prefix, and USRs) while indexing was active
and status/parse requests ran concurrently. Results included up to **64 distinct
TUs**. Lookup mean was **47.11ms**, maximum **495.69ms** including the first cold
read; all 40 status requests passed with a **2.87ms mean / 37.97ms maximum**.
Four parse calls succeeded; the first cold client/parse call took 8.63 seconds,
so their aggregate must not be described as uniformly fast. The real console
also returned populated `ANTLRInputStream` results at index revision 182.
Logs: `/tmp/ctk-symbol-lookup-live.log` and `/tmp/ctk-symbol-console.log`.

Full native validation passed **428/428 checks** in one isolated GoogleTest
process (102.38 seconds), including the new populated-lookup regression. The
initial per-test CTest invocation was stopped after 31 passing cases to avoid
repeating process startup for every check; it is not claimed as a complete CTest
pass. Full isolated Python unit validation passed **2,493/2,493** (369.47 seconds).
Logs: `/tmp/ctk-symbol-lookup-native-all.log` and `/tmp/ctk-bounded-python.log`.
Formatting and `git diff --check` also pass.

A separate concurrent run used **eight distinct source files** after explicitly
recording client/parse warmup (585.62ms). All fresh parses succeeded at **293.52ms
mean / 365.75ms maximum**, all 20 populated cross-TU lookups succeeded at
**26.90ms mean / 131.50ms maximum**, and all 20 server-status requests succeeded
at **117.09ms mean / 221.89ms maximum**. This ran while the BDD suite was also
active, so it is an observed responsiveness check rather than an isolated
throughput benchmark. Index revision had advanced from 181 to 185; indexing was
still active with zero reported failures. Log: `/tmp/ctk-symbol-lookup-fresh.log`.

Full BDD coverage verified **195 unique scenarios**: **194/195** passed in the
three-batch run, and the remaining unchanged multiline-console scenario passed
in isolation in **7.18 seconds**. Its batch failure was a 30-second CLI subprocess
startup timeout; no symbol-index operation was involved and no timeout or test
expectation was changed. The first isolated retry needed the same repository
PYTHONPATH as the full driver to collect cross-test imports. Logs:
`/tmp/ctk-symbol-lookup-bdd.log`, `/tmp/ctk-symbol-lookup-bdd-{0,1,2}.log`, and
`/tmp/ctk-symbol-lookup-bdd-retry.log`. This is not a claim that all BDD scenarios
passed together in one run.

Final managed-server check: PID 28071 remains running, indexing is active at
revision **195**, **609 current-pass TUs remain pending**, and **zero TUs have
failed**. Stored contribution counts still include retained older contexts until
this pass retires them. The full 623-TU project pass is not yet complete.

## Remaining publication bottleneck (17 October 2026)

The pending count was repeatedly reset by rebuilds: the TU key included a hash
of the complete worker executable, including unrelated link/build metadata.
The live store contained 211 contributions for 64 distinct source files, with
147 older contributions sharing the same source and arguments. Older contexts
remain readable until the existing completed-pass cleanup retires them.

The worker now supplies an extraction-specific source fingerprint, configured
compiler/resource paths and Clang version alongside the existing command and
environment context. Unrelated executable-byte changes retain TU identities;
changes to extraction inputs still invalidate them. An executable timestamp
guard rejects publication if the worker changes during a pass. This identity
upgrade requires one initial refresh of legacy contributions.

A live process sample found publication waiting on SQLite index-page reads.
Extraction of ANTLRFileStream.cpp produced 53,347 symbols in 1.832 seconds, but
publication into an identical checkpointed copy of the populated store took
22.999 seconds, with 190,640 cache misses and 171,861 page writes. Removing the
two redundant BINARY name indexes reduced publication to 16.473 seconds, with
136,685 misses and 127,336 writes: about 28% less publication time and 26% fewer
writes in this controlled single-TU comparison. The benchmark used the server's
bundled SQLite, actual extracted rows, the same insertion order and 32MiB cache.
Larger caches and sorted insertion did not produce a reliable improvement and
were not adopted.

Exact name lookups explicitly seek the remaining NOCASE indexes in separate
UNION arms with an additional BINARY equality filter, preserving case-sensitive
results and deduplication. The BINARY column uses unary + to keep that equality
as a residual rather than an access constraint. Validation caught a full scan
with the initial OR form in the bundled SQLite; the final plan regression
requires both index seeks. USR and prefix indexes stay
available; the schema still has three tables. Existing stores drop the redundant
indexes in the background without rebuilding their symbol rows.

Foreground activity previously discarded a partially staged publication and
forced the same TU to be extracted again. Publication and dependency hashing now
yield to foreground work while retaining their progress. WAL readers continue
to see the last committed snapshot. Dependencies, compilation commands and the
worker timestamp are checked again before committing, so edits during a yield
cannot publish stale results. Cancellation, pause, foreground extraction
preemption, low worker priority, resource limits and the 32MiB cache remain in
place.

Regression coverage exercises unrelated worker-byte changes, foreground bursts
during publication, header edits while yielded, exact-case matching and indexed
query plans. Python unit validation passed 2,500 tests (343.62 seconds).
The final complete native run passed all 433 checks (78.34 seconds), including
the query-plan guard. Formatting and whitespace checks passed; independent
review found no remaining blockers.

The final managed server (PID 7485) resumed the same persisted index and skipped
five unchanged contributions instead of restarting extraction at the first TU.
During concurrent foreground work, all 20 populated cross-TU lookups passed at
25.01ms mean / 122.91ms maximum; eight distinct-file parses passed at 307.33ms
mean / 369.01ms maximum, after separately recording a 7.70-second cold warmup.
All 20 server-status calls passed at 120.27ms mean / 220.33ms maximum. A second
run exercised 40 populated exact, prefix and USR lookups at 92.90ms mean /
587.79ms maximum, with no errors. Indexing advanced to revision 232 and 617
pending TUs, with no reported failures. These live runs overlapped the full BDD
suite and are responsiveness observations, not isolated throughput comparisons.
The entire 623-TU pass remains incomplete.

All 199 end-to-end scenarios passed in three isolated batches (67/66/66,
569.20/585.49/562.48 seconds). That run overlapped the query-plan corrections;
the four index-specific end-to-end scenarios were additionally rerun against the
final UNION build and all passed (36.04 seconds). Logs:
`/tmp/ctk-publication-bdd.log`, `/tmp/ctk-publication-bdd-{0,1,2}.log` and
`/tmp/ctk-publication-index-bdd-final.log`.

## Exclude system symbols and retain unchanged header rows (17 October 2026)

The remaining write volume was mostly the standard library, repeated for each
translation unit. The captured ANTLRFileStream.cpp extraction contained 53,347
symbols across 877 files; only 280 symbols belonged to project files. Its
largest contributors were libc++ string, unordered_map, hash-table and other
standard headers. A TU contribution is not an appropriate place to replicate
the entire standard library.

The extractor now prunes declaration subtrees classified by Clang as system
headers, with a second spelling-location check before USR generation. It still
parses those includes for correct project types and keeps their input hashes
for invalidation. Project headers and macro-dependent TU variants remain
indexed. A per-extraction USR/location/kind set also removes repeated visits
before serialization.

TU refreshes no longer delete and reinsert every symbol. Conditional UPSERTs
leave unchanged rows and their secondary indexes intact; a connection-local
temporary key set identifies removed declarations for deletion. The existing
transaction publishes all changes atomically and keeps pause/cancel and input
revalidation gates. There are still only three persistent tables. Project
header contributions retain each TU's provenance and compile context; they are
not incorrectly merged across macro variants.

The identical real TU now emits 280 symbols (99.5% fewer) in 1.227 seconds.
The previous extraction took 1.832 seconds. Publishing the new emitted rows
with the same insert benchmark, populated-store snapshot, three secondary
indexes and 32MiB cache took 0.153 seconds versus 16.473 seconds for the previous
53,347 rows. Page writes fell from 127,336 to 899. This benchmark measures the
reduced row set; the full service also performs manifest checks and differential
publication, so this is not an end-to-end 107-fold speedup claim.

All 435 initial native checks passed (85.95 seconds), including standard vector/string
headers, an explicitly marked system header, project-header macro variants,
and database triggers that reject physical rewrites of unchanged header rows.
All 2,500 Python unit checks passed (235.48 seconds). Independent review found
no blockers; formatting and whitespace checks passed.

A follow-up live sample placed the controller in repeated include-directory
inventory scans rather than symbol insertion. The shared inventory walker now
derives ordinary directory paths from their resolved parent and calls
`weakly_canonical` only for symlink directories. It retains cycle/alias
detection, file-name output and limits. A paired comparison on the actual SDK
framework tree produced identical 850,544-byte output in 0.245 seconds before
and 0.216 seconds after. A regression compares the full encoded output with
the original canonical walk across nested directories, aliases and a cycle.
This change preserves include-shadowing invalidation rather than skipping SDK
dependency checks.

All 436 final native checks passed (113.98 seconds), as did all four index
end-to-end scenarios rerun against the final build (57.85 seconds). Independent
review also approved the inventory change. The initial complete BDD run overlaps
the rebuild; its final result is recorded separately below.

During the full managed-project pass, 20 populated cross-TU lookups passed at
15.69ms mean / 18.50ms maximum; eight distinct-file parses passed at 346.22ms
mean / 464.37ms maximum after a separately recorded 8.66-second cold warmup.
Twenty status calls passed at 134.77ms mean / 316.68ms maximum. The full BDD suite
was running concurrently, so these are loaded responsiveness observations.

Evidence: `/tmp/ctk-project-only-extraction.log`,
`/tmp/ctk-project-only-publication.log`, `/tmp/ctk-project-only-native.log`,
`/tmp/ctk-project-only-unit.log`, `/tmp/ctk-project-only-foreground.log`, and
`/tmp/ctk-project-only-progress.log`.

Evidence logs: `/tmp/ctk-real-extraction.log`,
`/tmp/ctk-publication-three-indexes.log`,
`/tmp/ctk-publication-native-union.log`, `/tmp/ctk-publication-unit.log`,
`/tmp/ctk-publication-live-union.log` and
`/tmp/ctk-publication-live-running.log`.

### Shared project-header payloads

System-header exclusion alone was insufficient. The real batch.pb.cc contribution
still contained 110,087 project symbols, including 80,992 from the same generated
semantic.pb.h header. Repeating those payloads through secondary indexes remained
expensive and one preliminary live lookup exceeded its budget during that write
load. That preliminary run is not a successful final responsiveness result.

The final publisher groups each header's exact serialized symbol records in
sorted order and hashes that content together with its file path. Identical
payloads are stored once; differing macro-dependent payloads receive different
owners. Membership changes update one header owner rather than rewriting every
declaration in that header. Main-file rows remain private to their TU and use
the differential update described above.

This preserves the three persistent tables and their columns. Header owners
use translation_unit rows with indexed_at=0, whose dependencies_json is a JSON
array of referring real TU IDs. Real TU rows retain positive timestamps, ordinary
file-dependency manifests, a reserved layout marker and reserved group references.
Dependency validation excludes only those reserved bookkeeping fields. A partial
covering index contains the header membership arrays; actual TU counts continue
to count only positive timestamps.

Lookups materialize bounded physical candidates, include every physical owner
tied at the candidate boundary, expand header memberships, and sort/limit by
the real TU IDs before fetching payloads and covering TU metadata. The boundary
step preserves logical ordering for small limits across macro variants; review
caught this edge case and a deliberately inverse-order, three-variant regression
now covers it. Callers still receive each TU's actual file and compilation
context, not a synthetic header owner.

Unchanged flat contributions whose IDs match the current extractor and whose
inputs still validate are migrated from their stored rows without running Clang
again. Publication still rechecks dependencies, commands and worker identity
before committing. Refresh/removal releases memberships and removes unreferenced
header owners. A large obsolete cohort is retired by atomically copying retained
owners, dropping the old symbol table and rebuilding the smaller indexes; WAL
readers retain the previous snapshot. SQL progress callbacks yield to foreground
requests and honor pause/cancel. The private populated-snapshot benchmark spent
147.24 seconds dropping the old approximately 10GB symbol table, rather than
performing per-symbol secondary-index deletions; that one-time cost is separate
from ordinary TU publication.

The 20-TU regression stores 200 physical header declarations for 4,000 logical
contributions, while exact lookup returns all 20 TU provenances and prefix lookup
honors its limit/truncation flag. Trigger guards confirm unchanged header rows
are not physically rewritten. All 440 final native checks passed (70.07 seconds).
Independent review approved shared ownership, logical ordering and fast migration.

### Final verification

Before the memory-guard adjustment below, the shared-header build passed
all 440 native checks, all 2,500 Python unit checks,
and all 199 end-to-end scenarios. The latter ran in three isolated batches
(67/66/66 scenarios, 627.57/644.52/613.32 seconds).

The oversized old symbol cache was preserved by renaming its directory to
`31f15246fed0bcde30334e9a53a0e0a94ea31ef5c4d498f9cc42cce4330f2830.before-shared-20261017T135742Z`
under `~/.cache/clang-toolkit/storage/symbol-index/`. A clean full-project
pass started at 2026-10-17 13:57:42 UTC. This measures a clean index rather
than hiding the separately reported old-cache migration cost. The backup
remains available for rollback.

During this pass, simultaneous foreground probes measured eight fresh-file
parses at 130.45ms mean / 153.66ms maximum, 20 populated cross-TU lookups at
6.57ms / 7.97ms, and 20 server-status calls at 39.87ms / 68.51ms. A separate
40-request exact/prefix/USR cross-TU probe passed with zero errors at 8.13ms
mean / 17.58ms maximum. The client and initial parse warmup took 3.99 seconds
and is reported separately from the steady-state requests.

A brief paused comparison used eight other fresh files and the same request
mix: parses 150.06ms / 187.77ms, lookups 10.04ms / 15.40ms, status 58.19ms /
85.01ms. These bounded samples show no observed foreground regression under
indexing; they are not a claim of zero scheduling overhead in every workload.
Indexing was resumed immediately after the comparison.

At 204 indexed TUs, the live database contained zero symbol rows from libc++
include paths, SDKs, system `/usr/include`, or Clang resource includes. The
generated semantic.pb.h had two genuine payload variants: one shared by 47
TUs and one by a single TU, each stored once rather than copied per TU.

The clean pass reached 622/623 TUs at 14:19:42 UTC, exactly 22 minutes after
starting, with all 129 populated cross-TU lookup probes successful (10.54ms
mean / 68.76ms maximum). One test TU, `serialization/testing/test_cached_values.cpp`,
hit the existing 1GiB worker guard. A separate low-priority, 2GiB-guarded
diagnostic completed that TU in 7.53 seconds, emitting 213,102 project symbols
with a measured peak of 1,080.19MiB. The production guard was therefore raised
to a still-bounded 1.5GiB; worker priority, foreground yielding and time/output
limits remain unchanged.

After rebuilding/restarting with that adjustment, the server reused the 622
stored TUs and filled the missing contribution. It reported COMPLETE at
14:24:00 UTC with 623 completed, 623 skipped on its final reconciliation,
zero pending and zero failed. The elapsed wall time from the clean start was
26 minutes 18 seconds, including the brief pause comparison, diagnostic,
rebuild/restart and foreground interruptions. This is substantially below
the previous 4–5 hour estimate, which was an estimate rather than a completed
baseline measurement.

Final read-only inspection found exactly three persistent tables, all 623
real TUs, 531,276 physical symbol rows and zero system-include-path symbol rows.
The shared semantic.pb.h payload had 98 members in one variant and one member
in its other variant, with 80,992 physical declarations per variant. The main
database occupied 574MiB with 58MiB of WAL at inspection; the old backup is
retained. No standard-library/system-header declarations are indexed, while
their dependencies remain validated for correct invalidation.

During the final retry, with regression suites also running, eight fresh-file
parses completed at 254.56ms mean / 545.35ms maximum, 20 populated lookups at
15.28ms / 90.27ms, and 20 status calls at 106.71ms / 325.91ms. A separately
recorded cold client/parse warmup took 5.10 seconds. The retry/reconciliation
monitor made another 16 successful populated lookups at 21.59ms / 45.78ms.
These loaded samples remain responsive but are not directly comparable with
the quieter paused baseline. Forty generated-header exact/prefix/USR lookups
also passed during the clean pass (6.72ms mean / 15.38ms maximum).

After the memory-guard adjustment, all 440 native checks passed again
(162.89 seconds) with a dedicated `CTK_STORAGE_ROOT`, as did all 2,500 Python
unit checks (435.07 seconds). Initial native reruns without that isolation
failed storage expectations because the managed server owns the default cache;
the sandboxed attempt also denied local socket binding. Those attempts are
retained in their logs and are not counted as successful checks. Independent
review approved the bounded guard adjustment.

The final end-to-end rerun passed 198/199 scenarios initially. The remaining
PCH scenario required `CTK_TEST_CLANG`, which was absent from that runner;
it passed separately in 2.92 seconds with the server's LLVM compiler and the
repository import path configured. Thus all 199 scenarios were verified
against the final build; the initial environment failure is retained in
`/tmp/ctk-shared-memory-bdd-2.log` rather than reported as a clean first pass.
The two clean batches passed 67 and 66 scenarios in 926.55 and 947.55 seconds.

A final steady-state probe, with all 623 TUs stored and background
reconciliation still enabled, passed another 20 populated cross-TU lookups
at 8.80ms mean / 11.92ms maximum and 20 status calls at 61.09ms / 160.45ms.
Eight fresh-file parses passed at 177.45ms mean / 234.22ms maximum, with a
separate 299.93ms client/parse warmup.

Evidence: `/tmp/ctk-shared-final-native.log`,
`/tmp/ctk-shared-migration-focused.log`, `/tmp/ctk-project-only-unit.log`,
`/tmp/ctk-shared-final-bdd.log`, `/tmp/ctk-shared-final-bdd-{0,1,2}.log`,
`/tmp/ctk-shared-clean-progress.log`, `/tmp/ctk-shared-clean-foreground.log`,
`/tmp/ctk-shared-clean-lookups.log`, and
`/tmp/ctk-shared-paused-foreground.log`. Additional final evidence:
`/tmp/ctk-heavy-index-profile.log`, `/tmp/ctk-shared-memory-progress.log`,
`/tmp/ctk-shared-final-memory-foreground.log`, and
`/tmp/ctk-shared-generated-lookups.log`, plus
`/tmp/ctk-shared-memory-native-private.log` and
`/tmp/ctk-shared-memory-unit.log`, `/tmp/ctk-shared-memory-bdd.log`,
`/tmp/ctk-shared-memory-pch-configured.log`, and
`/tmp/ctk-shared-final-steady.log`.
