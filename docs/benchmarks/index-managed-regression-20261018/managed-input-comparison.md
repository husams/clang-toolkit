# Managed versus isolated PR74 input comparison

Read-only comparison, 2026-10-18. Wiki consulted first: `/Users/husam/workspace/wiki/pages/research/clang-toolkit-index-dependency-io.md`. No managed-server or indexing control calls performed.

The 440.252s managed versus 228.112s isolated figures are not a controlled runtime comparison: the isolated run used a frozen 623-entry Release compile database and empty storage; managed used a 628-entry Debug compile database with existing storage. Both runtime server/worker builds are optimized Release, both LaunchAgents use Interactive process policy, and the worker executable hashes are identical (`1f5538d8a2d1f4241c5641f598471a2ccc6e906f0c2f06b2d916055c41b5e93f`). The elapsed ratio is 1.930x, but differences below are confounders, not a causal apportionment.

| Verified input | Managed | Isolated |
|---|---:|---:|
| CDB entries / unique sources | 628 / 627 | 623 / 622 |
| External fetched TUs | 141 (136 ANTLR) | 141 (136 ANTLR) |
| Principal CDB flags | `-O0 -g0`, no `-DNDEBUG` | `-O1 -DNDEBUG -g0`; ANTLR also `-O3 -DNDEBUG` |
| PCH references | 322 | 322 |
| Current PCH bytes | 124,806,524 | 121,531,912 |
| Current manifest dependency references | 876,170 | 871,137 |
| Current distinct dependency files | 5,684 | 5,677 |
| Current weighted dependency bytes | 54,767,494,514 | 53,675,533,167 |
| Current main TU rows / header groups | 628 / 1604 | 623 / 1603 |
| Current symbols | 145,382 | 145,344 |
| Index startup | 08:34 UTC | 07:33 UTC |

After normalizing only worktree root and build/release versus build/dev roots, managed has exactly five extra sources: `directory_watch.cpp`, `index_file_reader.cpp`, `index_filesystem.cpp`, `test_index_file_digest.cpp`, and `test_index_definition_reuse.cpp`. No old-cohort source is missing. The two CDBs also refer to distinct generated build outputs and distinct PCHs. Compile-database optimization flags describe the code being parsed; they do not establish the optimization level of the running indexer.

Current manifest-weighted dependency bytes are only 2.03% larger for managed; reference count is 0.58% larger. The PCH difference is 2.69%, accounting for 1,054,425,064 of the 1,091,961,347 extra weighted bytes. These size differences alone do not establish why observed elapsed time is 93.0% greater. The Debug preprocessor state can change assertion expansions and AST work; its cost is unmeasured. Existing context/DB replacement and host load can also change cost. The exact managed-start old-context row count needs its historical snapshot rather than today's cleaned-up 628-row snapshot.

The shell reports launchd maxfiles 256/unlimited. Neither inspected service definition contains a maxfiles override; actual per-process FD limits were not measured. Both service definitions use Interactive, and managed resource snapshots show four nice-15 workers; no cgroup difference applies to these native macOS processes. Actual QoS scheduling, launch-time load, and exact historical input sizes were not captured together, so they cannot be equated. The isolated server config explicitly set parse pool size 3; managed plist passes no config argument, so its resolved pool configuration remains unverified.

Recommended controlled A/B: use private servers with the same durable optimized binaries, first indexing the managed Debug CDB into empty temporary storage and then the frozen Release CDB into empty temporary storage, with the same parse pool/probe cadence and host-load/resource capture. Run sequentially and repeat in reversed order. A subsequent private run with a snapshot of the populated managed DB separates old-context replacement from input differences. Keep the managed service untouched. Comparing input flags with matched Release-compatible PCHs must preserve PCH correctness; simply editing `-DNDEBUG` is not a valid PCH experiment.

Raw quantified artifact: `/tmp/ctk-managed-input-comparison.json`. Extraction inputs: `/tmp/ctk-managed-dependencies.jsonl` and `/tmp/ctk-isolated-dependencies.jsonl`. Values use current manifest/current stat sizes, not reconstructed historical bytes. The historic isolated run's PCH was recorded as 121,531,908 bytes, four fewer than its current artifact; do not present today's sizes as exact run-time measurements.
