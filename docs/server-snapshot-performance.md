# Server snapshot reads and AST persistence

The server now reads native snapshot blobs in 64 KiB blocks with an initial
capacity reservation. Publication uses the original draft rather than copying
all AST buffers to normalize its timestamp, reuses the incoming digest computed
before reserving publisher leases, and normalizes the main source path once.

These changes preserve synchronous Clang serialization and durable publication:
existing/colliding blob verification, file and directory syncs, publisher leases,
atomic metadata publication, rollback, retention, exact-size checks and SHA-256
verification remain enabled. The public API and storage schema are unchanged.

## Repeated Clang measurements on linux-dev

Measured on 2026-10-11 with three native workers and the same 2 GiB snapshot
admission limit for both binaries. This complete repeated comparison replaces
the earlier incomplete single-pass measurements. Both binaries include the
earlier batch stall and progress fixes. Machine settings stay fixed.

Each cell is the median of three runs, in seconds, from 60 fresh server sessions
and 114 measured batches. Each session performs the same three-file startup
warm-up before timing. Setting order is shuffled each round, and version order
alternates across paired settings. Cold means CTK cache pruning with OS caches
retained. Cached measurements follow a successful cold run or complete priming
through safe smaller groups when the cold setting fails.

| Dataset | Batch size/jobs | Cold before | Cold after | Cached before | Cached after |
|---|---:|---:|---:|---:|---:|
| Basic, 46 files | 1/1 | 71.28 | 69.80 | 34.06 | 31.77 |
| Basic, 46 files | 4/2 | 46.64 | 45.65 | 22.42 | 20.94 |
| Basic, 46 files | 4/4 | 37.51 | 36.07 | 17.19 | 16.78 |
| Basic, 46 files | 16/4 | 29.78 | 28.96 | 14.70 | 13.88 |
| Basic, 46 files | 16/8 | 29.41 | 28.92 | 14.62 | 13.88 |
| Basic, 46 files | 32/8 | 17.72† | 17.21† | 14.51 | 13.70 |
| CodeGen, 4 files | 1/1 | 48.54 | 47.55 | 20.71 | 19.14 |
| CodeGen, 4 files | 2/2 | 30.81 | 30.16 | 13.08 | 12.09 |
| CodeGen, 4 files | 4/4 | 21.67† | 28.71† | 9.38 | 8.80 |
| Clang, 1,003-file pressure test | 32/8 | 23.77† | 24.42† | N/A | N/A |

† All three runs fail at the memory-admission limit with acknowledged cleanup.
These values measure time to failure and cleanup, not completed-work throughput.
The 1,003-file pressure test stops at its first failed group; full cached
throughput is intentionally excluded. Successful Basic batches return exactly
870 definitions and successful CodeGen batches return 259. Three samples limit
claims of statistical significance; raw triplets and ranges are retained.

All 114 measured reports acknowledge cleanup with zero external pins and unknown
outcomes. Progress gaps stay below 1.002 seconds. All 3,753 concurrent status
probes succeed: before median/p95/max 3.72/8.21/381.35 ms, after
3.72/6.95/193.92 ms. All owned servers stopped and test storage was removed.
The separate earlier cancellation check returned the prompt in 2.06 seconds,
and the next batch succeeded.

The 54 complete final status dumps show no active work, cursors, explicit leases
or reservations. Six Basic 1/1 final dumps exceeded the console display budget;
their full batch cleanup reports and concurrent status samples are retained.

## Validation

- Full Linux native suite: 340 tests pass.
- Full Python unit suite: 1,022 tests pass.
- Full console acceptance suite: 116 tests pass.
- macOS native build and all 18 storage tests pass.
- New storage regressions cover 64 KiB boundaries, multi-megabyte binary data,
  appended/truncated/corrupt/missing blobs, caller buffer preservation, timestamp
  normalization and corrupt existing blobs during prehashed publication.

Implementation: `server/src/storage/blob_store.cpp`,
`server/src/storage/store_publication.cpp`,
`server/src/storage/metadata_repository.cpp`,
`server/src/storage/storage_internal.hpp`, and
`server/src/clang/cached_query_engine.cpp`.

Complete repeated matrix, sample triplets, ranges, cleanup/progress checks,
concurrent server status measurements and hashes:
[fair comparison report](benchmarks/2026-10-11/report.md) and
[individual measurements](benchmarks/2026-10-11/measurements.csv).
Full test logs and timestamped console evidence are retained locally.

Applied in the local checkout and an isolated linux-dev build. The ordinary
remote checkout and separate cloud VM have not been deployed.
