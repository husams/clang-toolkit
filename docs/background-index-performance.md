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
service policy would avoid throttling the request-serving process while keeping
indexing's per-thread/per-worker limits. Automatic approval rejected that
service-wide change as outside the indexing authorization; user approval is
pending, and the existing service policy remains in place. Proposed configuration:
`/tmp/ctk-server-reviewed.plist`. Reference:
[Apple launchd manual](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5).

A separate SQLite compiler-optimization experiment measured 6.04 versus 5.85
seconds on a native storage probe; this was not a meaningful improvement and the
build-setting change was discarded.

## Verification

- Final server/worker/native-test build succeeds.
- Ten focused native checks pass, including migration with a concurrent old-schema reader.
- Four live indexing E2E checks pass, including foreground parsing during extraction.
- Full isolated Python unit validation passed 2,493 tests. An initial run's
  configuration-sensitive console mock read the local compilation-database
  setting; the unchanged test passes in an isolated working directory.
- Full native regression validation is running at background CPU/I/O priority,
  with per-test storage isolation. An earlier normal-priority run was stopped
  because it distorted foreground latency measurements; no test limits changed.

The final full isolated Python unit run passed **2,493 tests** in 155.54 seconds
(`/tmp/ctk-index-throughput-unit-isolated.log`); test code and limits were unchanged.
The initial isolated collection needed the repository on PYTHONPATH for its
cross-test imports. Full native checks and the queued full BDD run remain in progress.
