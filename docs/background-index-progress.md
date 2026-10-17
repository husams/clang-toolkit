# Background symbol indexing implementation

Scope: the approved normal Page proposal, three SQLite tables, selective TU
refresh, isolated background extraction, and gRPC controls usable by any UI.

## Delivery

- [x] Define gRPC start, status, pause, resume, cancel, find and lookup contract.
- [x] Implement dependency manifests and atomic TU symbol replacement.
- [x] Run extraction in an independent background process with bounded resources.
- [x] Keep status/control and foreground queries independent of extraction.
- [x] Add Python API and console controls, including retained status values.
- [x] Verify incremental updates, persistence, pause/resume and failure recovery.
- [x] Run C++ tests, Python unit tests and BDD tests.

## Acceptance

Only affected compile entries are reparsed after source/header changes; unchanged
entries survive restart. Failed/cancelled extraction preserves committed data.
The database contains only metadata, translation_unit and symbol tables. UI
clients can poll status and pause/resume through gRPC while extraction is active.
Foreground operations do not wait for extraction or share its AST/executor.

## Verification evidence

The dev build succeeds. Python unit tests: **2493 passed**. New live gRPC/console
BDD scenarios: **3 passed**, including foreground parsing during active indexing.
The implementation preserves consumed-buffer digests, expands response files,
distinguishes compile configurations, and checks filename inventories for project
include roots. See [usage](background-symbol-index.md).

Full C++ regression validation: **423 passed**, with per-test storage isolation;
log `/tmp/ctk-index-ctest-parallel.log`. Full BDD regression validation: **194
passed** in three isolated batches without a competing native test workload;
log `/tmp/ctk-index-bdd-final.log`. No test timeouts were widened.

Final worker hardening uses CTK's configured compiler driver, preserves C language
mode for C inputs, fingerprints compiler environment settings, and captures PCH,
explicit module artifacts and their loaded source buffers. A real PCH regression
reproduced the prior driver mismatch before the fix. After rebuilding, **6 native
indexing checks** and **4 live indexing E2E checks** passed, including the new PCH
and mixed C/C++ selective-refresh case. This brings unique E2E coverage to **195**.
Logs: `/tmp/ctk-index-native-final.log`, `/tmp/ctk-index-pch-after.log`.

Pre-merge independent review fixed two additional refresh cases: a changed compile
command that fails now retains its last successful symbols as stale until repair;
attached include-path options are inventoried so new higher-priority headers
trigger refresh even when the directories are outside the project tree. Native
regressions cover both cases.
The extractor also checks Clang error diagnostics explicitly, preventing driver
errors from replacing committed symbols with an empty apparent success.
Final pre-merge rebuild of server, worker and native tests succeeded; **8 focused
native checks passed**, including all three new review regressions.
All **4 live indexing E2E checks passed** against the final build (3 control/
refresh scenarios plus the PCH case with `CTK_TEST_CLANG` set to the build's LLVM
compiler). Logs: `/tmp/ctk-index-pr48-e2e.log` and
`/tmp/ctk-index-pr48-pch.log`; the first PCH attempt lacked that required setting.
The 4 focused Python indexing unit checks also passed.
