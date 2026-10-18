# Directory-watch capacity benchmark

Date: 2026-10-18. Raw per-process results: [`watch-budget-paired-runs.txt`](watch-budget-paired-runs.txt). Both binaries ran in fresh processes over the same 55 roots from `/tmp/ctk-managed-inventory-roots.txt`, in identical order, with one DirectoryWatch/cache across roots and a cold inventory pass followed by a repeat pass. `old` uses HEAD's 2,048 cap; `candidate` uses the isolated worktree's 4,096 cap. Five alternating paired trials were run after the native suite ended. OS filesystem cache was not flushed, so “cold” means cold per-process watch/cache state. Priority lowering via `nice` and `taskpolicy` was denied by host policy; timings are normal priority.

| Measure (median of 5) | Old cap | Candidate cap |
|---|---:|---:|
| First inventory walk time | 844.4 ms | 902.6 ms |
| Repeat full walks / cache hits | 55 / 0 | 0 / 55 |
| Repeat pass elapsed | 806.9 ms | 1.53 ms |
| Add callbacks across both passes | 8,586 | 4,293 |
| Failed watch adds across both passes | 2,740 | 0 |

Median first-pass time is 58.2 ms higher with the candidate, reflecting registration of the additional watches. Median cold-plus-repeat time is 1653.5 ms old versus 904.0 ms candidate, a 749.5 ms (45.3%) reduction for this two-pass workload. Paired cold-plus-repeat savings were 785.1 ms at the median. All five candidate trials cached all 55 roots with zero failed adds; old-cap trials cached none and incurred 2,740 failed add callbacks across the two passes.

This bounded microbenchmark isolates watch-backed include-inventory reuse; it is not a full indexing speedup claim. Host priority could not be lowered, and concurrent unrelated work was absent during the trials.
