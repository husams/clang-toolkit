# Repeated before/after Clang server timings

All ten settings from the earlier comparison have three new measurements per version. Tables use medians in seconds; raw triplets and ranges appear below. These measurements replace the earlier incomplete, sequential single-run comparison.

| Clang inputs | Size/jobs | Cold before | Cold after | Cached before | Cached after |
|---|---:|---:|---:|---:|---:|
| Basic 46 | 1/1 | 71.28 | 69.80 | 34.06 | 31.77 |
| Basic 46 | 4/2 | 46.64 | 45.65 | 22.42 | 20.94 |
| Basic 46 | 4/4 | 37.51 | 36.07 | 17.19 | 16.78 |
| Basic 46 | 16/4 | 29.78 | 28.96 | 14.70 | 13.88 |
| Basic 46 | 16/8 | 29.41 | 28.92 | 14.62 | 13.88 |
| Basic 46 | 32/8 | 17.72† | 17.21† | 14.51 | 13.70 |
| CodeGen 4 | 1/1 | 48.54 | 47.55 | 20.71 | 19.14 |
| CodeGen 4 | 2/2 | 30.81 | 30.16 | 13.08 | 12.09 |
| CodeGen 4 | 4/4 | 21.67† | 28.71† | 9.38 | 8.80 |
| Clang 1003 pressure | 32/8 | 23.77† | 24.42† | N/A | N/A |

† A memory-admission failure, including cleanup, rather than completed-work throughput. The 1,003-file setting is an early-termination pressure test; N/A cached throughput is intentional. Failed cold small-dataset cases are followed by complete safe-batch cache priming before cached measurement, so cached results can complete even when cold groups exceed admission.

## Fairness controls

- Each setting/version/replicate gets a fresh isolated server, storage root and prompt console PTY. Only one benchmark server runs at a time.
- Before measurement, all sessions run the same three-file, three-job startup batch (`Version.cpp`, `Diagnostic.cpp`, `Builtins.cpp`) to exclude first-query initialization. That warm-up is not a measured sample.
- Cold batches run after CTK cache pruning; OS caches are retained. Cached batches follow a successful complete cold batch or safe full-dataset cache priming (Basic size 16/jobs 4; CodeGen size 2/jobs 2).
- Settings are shuffled deterministically per round. Each setting runs both versions consecutively, with first-version order alternated across pairs; the recorded schedule is reproducible.
- Native worker pool stays three, snapshot admission stays 2 GiB, same console/matcher/compiler database and source revision for both binaries. Machine settings were not changed.
- Three samples per condition describe observed variation; no statistical significance or general speed guarantee is claimed. Both binaries already include the stall/progress fixes.

## Individual samples and spread

| Inputs | Size/jobs | Cache | Before samples (s) | Before range | After samples (s) | After range | Median time reduction |
|---|---:|---|---|---|---|---|---:|
| Basic 46 | 1/1 | cold | 71.28, 71.26, 71.46 | 71.26–71.46 | 69.81, 69.80, 69.36 | 69.36–69.81 | 2.1% |
| Basic 46 | 1/1 | cached | 34.69, 34.06, 34.02 | 34.02–34.69 | 31.77, 32.04, 31.66 | 31.66–32.04 | 6.7% |
| Basic 46 | 4/2 | cold | 46.64, 46.82, 46.24 | 46.24–46.82 | 45.78, 45.60, 45.65 | 45.60–45.78 | 2.1% |
| Basic 46 | 4/2 | cached | 22.40, 22.49, 22.42 | 22.40–22.49 | 21.00, 20.83, 20.94 | 20.83–21.00 | 6.6% |
| Basic 46 | 4/4 | cold | 37.51, 37.35, 37.64 | 37.35–37.64 | 36.04, 36.07, 36.43 | 36.04–36.43 | 3.9% |
| Basic 46 | 4/4 | cached | 17.22, 17.19, 17.07 | 17.07–17.22 | 15.99, 17.22, 16.78 | 15.99–17.22 | 2.4% |
| Basic 46 | 16/4 | cold | 30.15, 29.78, 29.61 | 29.61–30.15 | 28.96, 29.10, 28.88 | 28.88–29.10 | 2.8% |
| Basic 46 | 16/4 | cached | 14.57, 14.94, 14.70 | 14.57–14.94 | 13.96, 13.88, 13.82 | 13.82–13.96 | 5.5% |
| Basic 46 | 16/8 | cold | 29.29, 29.70, 29.41 | 29.29–29.70 | 28.92, 28.41, 28.97 | 28.41–28.97 | 1.6% |
| Basic 46 | 16/8 | cached | 14.56, 14.62, 14.81 | 14.56–14.81 | 13.88, 13.99, 13.68 | 13.68–13.99 | 5.0% |
| Basic 46 | 32/8 | cold | 17.72, 17.67, 17.93 | 17.67–17.93 | 17.21, 17.29, 17.08 | 17.08–17.29 | N/A: failed runs |
| Basic 46 | 32/8 | cached | 14.51, 14.88, 14.33 | 14.33–14.88 | 13.70, 13.70, 14.20 | 13.70–14.20 | 5.6% |
| CodeGen 4 | 1/1 | cold | 48.35, 48.54, 48.61 | 48.35–48.61 | 47.55, 47.61, 47.01 | 47.01–47.61 | 2.0% |
| CodeGen 4 | 1/1 | cached | 20.66, 20.71, 20.78 | 20.66–20.78 | 19.26, 18.98, 19.14 | 18.98–19.26 | 7.6% |
| CodeGen 4 | 2/2 | cold | 30.81, 30.87, 30.58 | 30.58–30.87 | 30.16, 29.62, 30.24 | 29.62–30.24 | 2.1% |
| CodeGen 4 | 2/2 | cached | 13.29, 13.08, 13.04 | 13.04–13.29 | 12.23, 12.06, 12.09 | 12.06–12.23 | 7.6% |
| CodeGen 4 | 4/4 | cold | 21.67, 21.59, 21.68 | 21.59–21.68 | 28.71, 21.24, 29.06 | 21.24–29.06 | N/A: failed runs |
| CodeGen 4 | 4/4 | cached | 9.28, 9.60, 9.38 | 9.28–9.60 | 8.83, 8.51, 8.80 | 8.51–8.83 | 6.2% |
| Clang 1003 pressure | 32/8 | cold | 23.74, 25.18, 23.77 | 23.74–25.18 | 24.51, 23.99, 24.42 | 23.99–24.51 | N/A: failed runs |

## Correctness and feedback

All 114 measured reports acknowledge cleanup with zero remaining external pins, unknown file outcomes and unknown cleanup groups. Successful Basic batches return exactly 870 definitions; successful CodeGen batches exactly 259.
54 final resource-status dumps show released scopes and zero active work, result cursors, explicit leases and reservations. The six Basic 1/1 dumps exceeded the console automatic display budget and returned a truncation marker; their complete batch cleanup reports and concurrent status samples remain saved. Final process checks confirm all owned servers stopped and all 60 storage roots were removed.
Measured progress gaps are at most 1.0011s, including assigned batches and pressure cleanup. Unmeasured startup/priming reports are retained and checked for complete cleanup as well.

| Version | Status probes | Errors | Median (ms) | p95 (ms) | Max (ms) | Peak observed RSS (GiB) |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 1900 | 0 | 3.72 | 8.21 | 381.35 | 4.11 |
| optimized | 1853 | 0 | 3.72 | 6.95 | 193.92 | 4.02 |

## Reproduction and evidence

Only temporary owned benchmark servers/caches were used. The ordinary remote checkout, running services and separate cloud VM were not deployed or reconfigured. No implementation changes were made during this rerun; the preceding complete native/unit/acceptance test results remain recorded in the original optimization report.

Source revision: `a259ffb45c84f930d3ad810dd4ddde50c2667766`. Compilation database SHA-256: `31f9654123bca1887b1c849c017dbb83da0ad322068bef93d2f6bd45768a9668`.

Before SHA-256: `0a20c9e06e51286e2e5d54cbbf928f3871ac694a3ec35b26e0177f63ac553911`. After SHA-256: `369b68552157f52833564758b655e8ac836d22cb29076e91bbbd951146fb58f7`.

[Individual measurements](measurements.csv) contain all 114 timed batches. The tables above retain all sample triplets and ranges. Full console transcripts, status samples, configuration, binary hashes and test logs are retained in the local benchmark evidence archive.
