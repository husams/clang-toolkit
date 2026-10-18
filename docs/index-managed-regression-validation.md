# Managed Indexing Regression Validation

**Status: qualified fresh run passed.** Timings describe the archived benchmark patch; the later pre-merge skip-window correction is documented separately below. The final Release server and worker indexed all 628 compile-database entries with no failures or skips. The run used a fresh isolated database and the same 2,291 pinned C++ input hashes as the completed baseline. It is a matched-input validation; elapsed-time differences from the earlier managed run do not establish a causal speedup because storage state and host conditions differed.

## Qualification run

The fresh run started at 2026-10-18 09:39:33.083 UTC and completed at 09:44:53.457 UTC. The completion bracket was 319.371–320.376 seconds. The final status was `INDEX_STATE_COMPLETE`, revision 628, 628/628 indexed, 0 failed, 0 skipped. There were 453 foreground RPCs across 65 bursts, with no RPC failures and no indexing-control calls. The isolated service used the final private-worktree Release pair: server SHA-256 `d75f78eafb34f70a302c1ecdbd46e5d1d6b93c645dced7e28b747da53515f9d5`; worker SHA-256 `57bf4b31c39f0da6f02c73fbb04798b83edb37556752e1b83dbf846533d507d4`.

The copied compile database hash matched its pinned value, `25a9cd8f183165ac9ec204a278e0cf7d4f14b0681b3d646c9de2c1360532d139`. All 2,291 input files still matched their pre-run hashes; the baseline and candidate input manifests were identical. The read-only storage audit found the same three user tables and schema version 2, 628 ready main-TU rows across 627 source paths, and 1,604 header-cache groups. It matched all 145,382 symbol rows against the baseline with bidirectional SQLite `EXCEPT` counts of zero. Main TU contexts were paired one-to-one using source path, working directory, and all compile arguments, removing only the build-specific extractor fingerprint. All 1,604 header groups retained the same synthetic IDs and full symbol-row fingerprints.

The main-TU index contained 24,142 definition rows and zero nondefinitions, standard-qualified definitions, SDK/LLVM-path definitions, outside-project definitions, or nonempty signatures. A separate audit across all symbol rows, including cached headers, also found zero definitions from standard C++ library headers, SDK headers, or compiler builtins. It retained 61,668 definitions from nonstandard installed Clang/LLVM and related APIs, plus 21 project-owned `std` specializations. There were 39 total `std`-qualified specializations; namespace membership alone is not a standard-library-header test.

The host's sampled load averages ranged from 8.98 to 20.63 (1 minute), 15.13 to 21.91 (5 minutes), and 23.33 to 28.39 (15 minutes). The controller reached 587,184 KB sampled RSS; the largest sampled worker was 503,568 KB, with a peak sampled concurrent worker-RSS sum of 1,454,928 KB. The sampled worker concurrency peaked at four. Of 206 worker process snapshots, 200 showed nice 15 and six single-snapshot observations showed nice 0; the snapshot cadence cannot establish how long those six processes remained at that priority.

The process CPU audit recorded raw `proc_pid_rusage` counters from about ten seconds after indexing began through the last sample before completion: controller user+system delta 509,781,800 raw units and cumulative child user+system delta 22,597,573,220 raw units. A three-trial calibration on this host measured 0.024014 raw units per `time.process_time_ns` nanosecond. Any converted CPU seconds are therefore a host-specific estimate, not a portable interpretation of Apple's counter units.

## Foreground behavior

The first exact, prefix, and USR cross-TU results were positive at revision 16, with definitions attributed to both `ANTLRFileStream.cpp` and `ANTLRInputStream.cpp`. Exact lookup was cross-TU positive in 63/67 samples; prefix and USR lookup were positive in all 63 samples each. The initial exact probes preceded the first indexed publication. The out-of-line lookup found `ctk::platform::current_executable_sibling` in the actual `server/src/platform/index_worker.cpp` source in 8/65 samples, first at revision 576.

| Probe | Samples | p95 | Maximum |
|---|---:|---:|---:|
| Exact definition lookup | 67 | 19.739 ms | 40.688 ms |
| Prefix lookup | 63 | 11.638 ms | 25.782 ms |
| USR lookup | 63 | 7.388 ms | 12.892 ms |
| Out-of-line definition lookup | 65 | 5.761 ms | 8.260 ms |
| Fresh parse and match | 65 | 73.855 ms | 731.249 ms |
| Index status | 65 | 2.719 ms | 6.153 ms |
| Server status | 65 | 17.673 ms | 27.262 ms |

After indexing, six idle bursts over 30 seconds made 42 RPCs with no failures or control calls; every status result remained complete at revision 628. Idle p95 latencies were 12.447 ms exact, 8.464 ms prefix, 4.743 ms USR, 5.078 ms out-of-line lookup, 53.039 ms fresh parse/match, 1.504 ms index status, and 16.899 ms server status.

An unchanged revalidation used Cancel followed by Start while retaining the persistent database. It finished in 9.103–9.209 seconds with all 628 entries skipped, zero failures, revision still 628, and no new or modified unit request files. Starting again while the job was already registered was idempotent. The zero request-file count alone does not prove workers were absent; the reported result is that all compile entries were skipped without changing the indexed revision. A separate control smoke test exercised cancel, pause, resume, and a lookup while paused; the lookup took 5.172 ms and returned 10 definitions from 10 TUs, and the resumed run again skipped all 628 entries with revision 628. The separately paused managed service was restored by the controller at 09:53:05 UTC; Resume completed in 0.500 ms.

## Change and comparison limits

The final candidate adds bounded batching of planning and unchanged/skipped validation work up to 16 TUs. The 16-TU changed-publication batch was already present in PR74. The pipeline retains fresh content hashing, validates expected dependencies before publication, keeps at most four extraction workers, and lowers their priority after startup. The archived timed six-file source/test patch relative to base `4351794` has 617 insertions and 97 deletions; it predates the separately verified pre-merge correction below. The target main branch later advanced to `4b3ded8` (#77) with Python/docs-only changes; all 2,291 pinned C++ inputs remained identical. The managed service remained on revision `4351794` during this qualification.

The earlier managed run took 440.252 seconds with existing storage and a Debug compile database. The qualified fresh run took 320.376 seconds on the same pinned inputs, an observed difference of about 120 seconds. This does not establish a 27% speedup: the storage state and host conditions were not matched. The older 228.112-second run used 623 contexts from 622 source files, different compile flags, and empty storage, so it is not a direct comparison either. The original managed run's host load and historical storage snapshot are unavailable.

A bounded controller snapshot showed directory inventory work in 2,405 of 2,438 sampled frames for the old watch budget and 10 of 1,612 for the candidate. In a separate paired-process benchmark over the same 55 roots, the old 2,048-watch cap failed 2,740 watch registrations and repeated all 55 walks (median 806.9 ms); the candidate 4,096 cap had no failed registrations and reused all 55 roots on the repeat pass (median 1.53 ms). This is a bounded inventory result, not a full-index speedup claim. See the [watch-budget benchmark](benchmarks/index-managed-regression-20261018/watch-budget-benchmark.md).

After process-group signaling fails, cleanup waits up to 10 ms for `waitpid` to confirm that the launched child exited; if it does not, the original error remains visible. The failing PID's actual exit delay was not instrumented. The upstream [Apple XNU process-group signal source](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/bsd/kern/kern_sig.c) describes a possible explanation for `EPERM` when there are no eligible processes, but does not confirm the exact running-kernel mechanism.

## Test results

The qualified native suite passed 511/511 tests in 164.158 seconds. The focused worker-process suite passed 16/16 tests in 1.464 seconds after the final deadline-poll ordering change. The four-test indexing E2E subset passed in 25.07 seconds before that final ordering change. The final Python unit suite passed 3,262 tests in 709.74 seconds.

## Pre-merge integration

The branch was brought forward to main `d8271b2`; upstream changes touched Python, VS Code, and documentation, with no changes to the server, API, or CMake inputs. Review found that a changed TU late in a planned skip window could force an unchanged predecessor to be extracted. The correction preserves each TU's fresh validation result and retries an unchanged prefix through the normal final-validation/commit path. The admission-mutation regression now covers both the first and sixteenth TU, requiring exactly five re-extractions, nineteen skips, five revision increments, and at most four live workers. Its initial adapter is destroyed before the second controller starts, keeping the concurrency assertion scoped to one controller.

The reviewed source commit is `8044a5a9ff201d579199c3e61f31ec4c42444f9c`. All 3,287 Python unit tests passed in 314.43 seconds; the three gRPC indexing scenarios passed in 44.21 seconds and the PCH invalidation scenario passed in 3.66 seconds. These four integration checks ran after the final review correction.

The 628-entry timing above was not repeated after this correction; its original source patch and binary hashes remain archived as benchmark provenance.

## Evidence

- [Final input, schema, and symbol-equivalence audit](benchmarks/index-managed-regression-20261018/audit.json)
- [Run completion and start records](benchmarks/index-managed-regression-20261018/final-result.json)
- [Initial index status](benchmarks/index-managed-regression-20261018/start.json)
- [Pinned run and shared CDB metadata](benchmarks/index-managed-regression-20261018/case.json)
- [Shared input and binary metadata](benchmarks/index-managed-regression-20261018/shared-metadata.json)
- [Baseline and qualified run comparison metadata](benchmarks/index-managed-regression-20261018/run-comparison.json)
- [Resource, priority, CPU, and foreground probe audit](benchmarks/index-managed-regression-20261018/resource-audit.json)
- [Raw sampled foreground probes](benchmarks/index-managed-regression-20261018/probes/samples.jsonl.gz)
- [Raw host and process samples](benchmarks/index-managed-regression-20261018/resources.jsonl.gz)
- [Raw process CPU counters](benchmarks/index-managed-regression-20261018/case-rusage.jsonl.gz)
- [All-symbol and header qualification](benchmarks/index-managed-regression-20261018/all-symbol-header-audit.json)
- [Idle foreground probe](benchmarks/index-managed-regression-20261018/idle-probes/summary.json)
- [Raw idle foreground samples](benchmarks/index-managed-regression-20261018/idle-probes/samples.jsonl.gz)
- [Unchanged revalidation](benchmarks/index-managed-regression-20261018/revalidation/result.json)
- [Idempotent start record](benchmarks/index-managed-regression-20261018/revalidation/idempotent-start.json)
- [Control smoke test](benchmarks/index-managed-regression-20261018/control-smoke/result.json)
- [Managed-service pause and resume records](benchmarks/index-managed-regression-20261018/managed-resume.json)
- [Raw CPU counter calibration](benchmarks/index-managed-regression-20261018/rusage-calibration.json)
- [Baseline-to-qualified input hash comparison](benchmarks/index-managed-regression-20261018/baseline-qualified-input-comparison.json)
- [Six-file source patch](benchmarks/index-managed-regression-20261018/source.patch.gz) ([base and file list](benchmarks/index-managed-regression-20261018/patch-base.txt))
- [Qualified native test log](benchmarks/index-managed-regression-20261018/tests/native-qualified.log.gz)
- [Python unit test log](benchmarks/index-managed-regression-20261018/tests/python-clean.log.gz)
- [Index E2E test log](benchmarks/index-managed-regression-20261018/tests/e2e-final.log.gz)
- [Worker-focused test log](benchmarks/index-managed-regression-20261018/tests/worker-focused.log.gz)
- [623-context implementation validation](benchmarks/index-io-623-20261018/README.md)

### Pre-merge evidence

- [Reviewed source patch](benchmarks/index-managed-regression-20261018/pr-source.patch.gz)
- [Pinned reviewed source/test hashes](benchmarks/index-managed-regression-20261018/pr-validation-inputs.json)
- [Integrated Python unit log](benchmarks/index-managed-regression-20261018/tests/pr-python.log.gz)
- [gRPC indexing scenarios](benchmarks/index-managed-regression-20261018/tests/pr-e2e.log.gz)
- [PCH invalidation scenario](benchmarks/index-managed-regression-20261018/tests/pr-pch.log.gz)
- [Non-head stale skip negative/positive regression proof](benchmarks/index-managed-regression-20261018/skip-window-regression-proof.md)
