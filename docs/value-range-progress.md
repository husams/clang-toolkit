# Local value range implementation

Scope: the [CFG Page](https://chatgpt.com/space/page_ef2d38a1705c819196f51e0bc3fc4fc0)'s opt-in `variableflow ... values interval` proposal, reusing retained native nodes and reporting converged bounds before and after each usage. Unknown effects, arithmetic overflow and unsupported conversions must be explicit.

- [x] Read the Page contract and inspect the existing retained variable-flow path.
- [x] Extend the protocol, clients and compiled console.
- [x] Implement bounded native interval transfer, branch refinement and loop convergence.
- [x] Verify numeric soundness, failures, retained inputs and transport behavior.
- [x] Run the full script in the real CTK console and capture actual output.
- [x] Complete review and regression checks; update the Page with verified behavior.

Verification: all 397 native tests passed. The Python unit suite passed 2,140 cases with one batch-startup timeout; that case passed in isolation (2,141 cases covered). The full E2E suite passed 152 cases with seven server/REPL startup timeouts; all seven passed on isolated rerun (159 cases covered). Both value-range E2E scenarios passed again after the final native fix over Unix sockets and TCP with a 4 KiB event bound. TypeScript checks and 52 tests passed, with 24 optional integration tests skipped. API and serializer coverage checks passed. C++ formatting and whitespace checks passed.

The exact checked-in script was rerun in a real TTY-backed compiled console against the final disposable native server; its actual output matched `examples/value_ranges.output.txt` byte for byte after terminal CR normalization. User startup libraries were isolated using an empty library directory for the demo and a temporary test-only plugin for the Python suites; production startup behavior was unchanged. The Page labels the feature as implemented locally and includes this script, actual output and verification results.

Independent static review approved the signed-integer interval scope and the final fix. A late regression reproduced unsupported wide parameters and call results being misclassified as unreachable while reporting complete analysis. Both now produce explicit unsupported findings and unknown numeric facts. The test uses an explicit x86 target for wider integer support and exercises unsupported narrowing on older Clang versions. All native tests and the exact console example passed after this fix.

Before PR delivery, the feature was rebased onto main `0410df4`, including the pipe-filter and tuple-unpacking console changes. All 2,225 Python unit tests and all five combined value-range/pipe-filter E2E scenarios passed on the integrated tree. Independent review approved the integration. The previously verified native, API, TypeScript and numeric client/runtime code remained byte-identical during the rebase.

Limitations: conservative intervals for one signed integer local of at most 128 bits; unknown guards explore both edges and relationships with other locals are not retained. Unsupported numeric expressions or lossy conversions and possible signed overflow invalidate numeric facts and mark completion incomplete. Existing initialization and liveness results remain separate. Pull-request delivery is recorded in the repository history.
