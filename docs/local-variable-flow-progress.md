# Local variable tracking implementation

Scope: the CFG Page's first milestone for a retained function and direct non-volatile integer or Boolean local: usage sites, reaching assignments, initialization, liveness and unused assignments. Declaration identity and the pinned native snapshot are authoritative. Unsupported effects produce explicit incomplete results.

- [x] Add streaming API and bounded native event/dataflow analysis.
- [x] Connect retained-node validation, transport, Python and console syntax.
- [x] Verify branches, loops, short circuit, shadowing, ordering, unsupported effects and resource lifecycle.
- [x] Run the exact Page example in a real CTK terminal and capture actual output.
- [x] Document the implemented scope and validation.

Validation complete: all 381 native tests passed in one run, including 16 variable-flow regressions. All 2,129 Python unit tests passed. The full E2E run passed 155 cases with two existing console-editor/server-startup timeouts; both passed in isolation, covering all 157 cases. The final two variable-flow scenarios passed again over Unix sockets and TCP with a 4 KiB message limit: the aggregate stream exceeds one message while every individual event fits. They also verify retained source removal, stale/closed/foreign inputs, provisional ordering, cancellation and resource limits.

The API contract check, serializer coverage gate, TypeScript contract check and 52 TypeScript unit tests passed (24 optional integration cases skipped). The exact example ran in a real terminal against a private server from the final native build; its output exactly matches `examples/local_usage.output.txt`. The managed user server was unchanged. Independent review approved the implementation, including C++23 return casts, unbraced statement bodies and reference-result escapes; unmodeled lvalue uses remain explicitly incomplete. `git diff --check` and formatting checks pass.

Python acceptance used the external test-only startup-library isolation harness at `/private/tmp/ctk_cfg_isolation.py`, preserving explicit test library directories while excluding the ambient user library from legacy-engine cases. Production startup behavior was unchanged.
