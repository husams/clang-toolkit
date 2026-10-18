# CTK 623-TU project-index performance validation

## Result

Revision `1588fd0` completed the isolated fresh index of 623 compile-command entries (622 distinct source files) in 228.112271666 seconds, with 623 completed, zero failed, and zero skipped. Completion was bracketed by 227.609215833 and 228.112271666 seconds. Run artifacts: `/tmp/ctk623-profile-20261018-ofgwx7u_/result.json` and sibling logs/resources.

This run was 57.085 seconds (20.016%) shorter than the previous completed 285.197-second run. Host load for the previous run is unknown, so this is an elapsed-time comparison, not a controlled speedup claim. The prior non-batched candidate took 1,002.119787 seconds and had an initial lookup failure (`no such table`); its recorded load average was about 58 on a 10-core host. The final run's 1-minute load average was 8.42 at start and 10.02 at end (10-core host). Do not attribute the timings causally.

The PCH inputs in the 285.197- and 1,002.119787-second runs matched: 121,531,908 bytes per PCH across 322 TUs, about 39.13 GB aggregate. Weighted-byte and microbenchmark records: [weighted dependencies](benchmarks/index-io-623-20261018/weighted-dependency-bytes.json), [reader microbenchmark](benchmarks/index-io-623-20261018/microbench-results.json). The final audit passed for all 623 TU contexts, normalizing only the changed extractor fingerprint. Per-TU definitions and header provenance matched after excluding definitions in 19 modified source/generated input paths; macro arguments and environment were compared unchanged.

## Bottleneck and fix

The controller repeatedly opened and hashed dependency files after extraction. The prior manifests contain 852,533 references to 4,016 unique dependency paths, representing about 49.99 GiB of repeated reads by current file size. A 121.5 MB PCH used by 322 TUs accounts for 39.13 GB of that weighted total. Profiles placed roughly 90% of sampled controller frames in manifest validation.

The fix validates shared dependencies once per publication batch of up to 16 ready TUs, reuses bounded open readers while still freshly hashing bytes, and shares include inventories with workers. Four background workers continue extracting while publication stages. Fresh hashes, macro contexts, negative include checks, transaction rollback and single-TU fallback preserve correctness. Standard-library definitions remain excluded; dependency hashes still detect changes to compiler inputs.

## Correctness and integrity

- Compile database: SHA-256 `2b1a78fa8475cd79d45a74997caf94a205e0f5028811a44d79733c7e9ba11ec9`; 1,984 input hashes recorded. Source/build inputs were unmodified during the run. Server and worker binary hashes matched before/after: `57182f0aeebc9398af2277482b92e1a17590660b624ce4b2e7e7912d9b285b36` and `1f5538d8a2d1f4241c5641f598471a2ccc6e906f0c2f06b2d916055c41b5e93f`.
- SQLite has exactly the three expected user tables: `metadata`, `symbol`, and `translation_unit`. Audit: 145,344 definitions, 1,603 header groups, zero non-definitions, zero standard-header paths, zero anonymous-namespace names, and zero nonempty signatures.
- The run verified a cross-TU lookup of `antlr4::ANTLRInputStream` across 10 TUs. During indexing, 132 genuine cross-TU checks and 18 published out-of-line definition checks succeeded. There were no changed project inputs and no probe errors.
- Current implementation batches changed-TU publication (up to 16 ready units) and fresh-validates a union of dependency hashes; conflicting expected hashes fall back to singleton publication. Unchanged-TU manifest skip/revalidation remains per TU, outside this batch path. The pause/cancel, generation, input-freshness, macro/include-context, and atomic-publication checks passed in the native suite.

## Foreground responsiveness

All probes completed without errors. Counts are exact/prefix/USR/out-of-line/fresh-parse-and-match/index-status/server-status; inactive phases do not contain every probe kind.

| Phase | Checks | p95 / max (ms) |
|---|---:|---|
| Before indexing | 50 | exact 4.975 / 4.975; parse+match 29.208 / 29.208; index status 0.699 / 0.699; out-of-line 1.258 / 1.258; server status 5.110 / 5.110 |
| During indexing | 318 | exact 19.618 / 28.487; prefix 17.322 / 27.567; USR 8.790 / 14.901; parse+match 53.638 / 56.112; index status 2.783 / 3.724; out-of-line 6.207 / 7.640; server status 10.009 / 10.824 |
| After indexing | 98 | exact 6.409 / 6.409; prefix 8.061 / 8.061; USR 4.332 / 4.332; parse+match 49.110 / 49.110; index status 2.478 / 2.478; out-of-line 5.388 / 5.388; server status 9.567 / 9.567 |

Fresh parse/match averaged 23.970 ms before indexing, 41.247 ms during, and 43.241 ms after. These observations show fast, nonblocking requests, not zero latency overhead. The run includes 46 exact checks during indexing; exact/prefix/USR/native parse and match remained within the 2-second request timeout, with zero errors. (Values above are measured p95 and max, not timeout budgets.)

## Resource use and design

The run used at most four workers. The full-run sampler recorded 949 worker observations at nice 15 and 77 at nice 0; every nice-0 observation was that process's first observation, with no later nice-0 samples. Peak server RSS was 657,408 KiB; peak single-worker RSS 570,656 KiB; peak combined worker RSS 1,278,464 KiB; peak combined process RSS 1,858,544 KiB. The FD counts below are a mid-run snapshot, rather than full-run maxima. `lsof` observed 1,290 directory FDs and 2,060 regular FDs (3,356 total); directory FD counts include non-watcher descriptors. The 2,048 directory-watch budget was not filled at that snapshot.

The final design batches up to 16 completed changed TUs in one transaction, with no more than four live workers and extraction prelaunch during staging. It freshly validates the common expected dependency-hash union after admission; input changes or generation changes prevent commit. Per-TU revision bumps remain inside the transaction, and the three-table schema remains unchanged. Missing or pre-schema lookups return empty/stale. Content hashes are freshly read on each manifest pass; no digest-value cache is used. Reader/watch optimizations are filesystem-guarded, with fresh-open/tree-walk fallback elsewhere.

## Tests and remaining qualification

- Native C++: 504 passed in 72.822 seconds ([native log](benchmarks/index-io-623-20261018/tests/native.log.gz)).
- Python: 3,069 passed and one timed out in the full run; all four parameterizations passed on isolated retry ([retry log](benchmarks/index-io-623-20261018/tests/python-console-retry.log.gz); [full run](benchmarks/index-io-623-20261018/tests/python-full.log.gz)).
- E2E, executed elevated: 197 passed and 12 failed ([full log](benchmarks/index-io-623-20261018/tests/e2e-full.log.gz)). All 12 failed node IDs passed targeted reruns from `/tmp` using the isolated worktree Python/server and Homebrew Clang where needed; the [Unix](benchmarks/index-io-623-20261018/tests/e2e-callgraph-unix-retry.log.gz), [TCP](benchmarks/index-io-623-20261018/tests/e2e-callgraph-tcp-retry.log.gz), and [remaining retry](benchmarks/index-io-623-20261018/tests/e2e-remaining-retry.log.gz) logs preserve exact results. Only two callgraph cases were reproduced on baseline `560b076` and traced to `/O1` compile-database discovery. Keep full-suite and targeted-run results separate.
- Final index-specific E2E subset: four passed in 25.52 seconds.
- The final 623-context definition/provenance audit passed with the 19 modified input paths explicitly listed. Host load for the 285.197-second prior run is unknown, so the observed elapsed-time difference remains non-causal.

Permanent evidence: [result](benchmarks/index-io-623-20261018/result.json), [correctness audit](benchmarks/index-io-623-20261018/final-correctness-audit.json), [resources](benchmarks/index-io-623-20261018/resource-audit.json), and test logs in the same folder. Prior report: [parallel baseline](index-parallel-623-validation.md). The benchmark used a private server, stopped after completion; the managed main server was not replaced or restarted.

## PR integration validation

After integrating main `52a7daf`, the final source revision `b9b0a505ee39cda004ec15701c0850af22b4ca9e` passed all 507 native tests (77.873 seconds), all 3,243 Python unit tests (221.40 seconds), and 43 indexing/cross-TU/foreground integration cases (139.85 seconds). Both independent code reviews approved. [Integration summary](benchmarks/index-io-623-20261018/integration/summary.json) and compressed logs preserve the exact outcomes.

Pre-merge review closed the partial-schema race by requiring both forced SQLite name indexes in the reader snapshot. Integration also exposed an unchanged upstream memory-test fixture comparing cold and stored AST estimates; the same failure reproduced with the main-checkout native test binary. Pinning one backend snapshot for both controllers preserved every assertion and passed 20 consecutive runs. An initial Python workspace timeout passed all three isolated parameterizations and then the complete clean suite; the initial E2E import-path collection error and original failure logs remain available alongside successful runs. The 623-TU timing above remains attributed to its measured revision.
