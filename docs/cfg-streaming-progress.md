# CFG streaming implementation

Scope: stream CFG blocks and reuse parsed trees, file handles and retained function bindings. Local-variable dataflow remains a proposal.

- [x] Add retained target and stream event API contracts.
- [x] Implement native block streaming, retained ownership and transport.
- [x] Add Python event iteration and compatibility collection.
- [x] Add console streaming and retained-target syntax.
- [x] Verify limits, cancellation, ownership and no reparsing; run full suites.
- [x] Update usage documentation and proposal status.

Validation complete: all 365 native tests passed in one run. The full Python unit run and focused reruns covered 2,119 cases, including 125 focused cases after fixing per-command completion ordering. All 155 E2E cases passed across the full run and isolated reruns, including three CFG scenarios over Unix sockets and TCP. The API contract check, serializer coverage gate, TypeScript contract check and 52 TypeScript unit tests passed. The exact example passed in a real terminal console with each completion before the next graph, then printed `1`, `5`, `1`. Incremental builds are clean and `git diff --check` passes.

Python validation excludes the ambient user startup library through an external test-only harness in `/private/tmp/ctk_cfg_isolation.py`; that library contains compiled-engine syntax while some existing tests explicitly use the legacy engine. The full unit run had 2,116 passes and two failures; the local batch startup timeout passed after compilation finished, and the completion expectation was corrected for the new `cfg in` form. The full E2E run had 153 passes and two timeouts in existing library-preload and workspace UI cases; both passed in isolation. The final CFG-specific rerun passed all three scenarios.
