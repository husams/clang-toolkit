# Dependency-I/O indexing evidence

Tested code: `1588fd03741a320ee2dd320064d163efb000b5c2`; fresh 623-TU run completed in 228.112271666 seconds. See [validation report](../../index-io-623-validation.md).

JSON files preserve the captured run/audits. Compressed JSON/JSONL files retain the exact compiler cohort, pinned input hashes, foreground probes, progress and resource samples. Original absolute paths identify the private run and original worktree; no database or build binaries are included. The derived correctness-audit script expects the original run databases and its original `/tmp` paths; it is saved as provenance, not a portable reproduction command. The full native suite passed; the full Python/E2E logs retain their failures separately from successful targeted retries.
