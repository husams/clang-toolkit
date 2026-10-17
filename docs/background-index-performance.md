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
