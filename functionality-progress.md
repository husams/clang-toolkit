# Remaining Clang Toolkit functionality

Final aggregate validation completed on 7 October 2026 for the remaining native
analyses, project facade, enhanced snapshot reuse/persistence, Python/console
integration, tests, documentation and manual launcher. The human authorized
committing and pushing this complete scope. The serializer and SDK foundation is
already published; console commit `aa3a924` is included in this publication.
Only the pre-existing cache swap-file deletion is excluded.

Earlier component counts and resume notes below are historical milestones.
The final aggregate verification section supersedes their delivery state.

| Component | State | Evidence / next step |
| --- | --- | --- |
| Typed semantic serialization | Delivered | `query-engine-progress.md`, `docs/semantic-serialization.md`; genuine native/schema limits remain explicit. |
| Result cursors / Match / CloseSession | Delivered | Owned latest-row bindings, atomic guarded revisions, selection/scopes, expiry/close and Python/CLI. macOS LLVM 22.1.8 and RHEL LLVM 21.1.8: full serial 175 CTests and 143 Python/BDD pass. |
| Standalone AST traversal | Delivered | Dedicated native visitor, typed preorder/parents, explicit options and atomic limits; API/server/Python/CLI/unit/BDD. macOS/RHEL: 179 native + 150 Python/BDD tests pass; Clang-only 131 pass; Clang-disabled 93 pass and live RPC returns FAILED_PRECONDITION. 1,227 implementation files match the RHEL image. |
| CFG operations | Delivered | Native typed blocks/edges, all 15 element and 11 construction kinds in dedicated files, native options/version checks, shared executor and API/Python/CLI. macOS 185 native + 159 Python/BDD; RHEL 185 CTests + 159 Python/BDD; Clang-only 131 and disabled 93 plus real disabled RPC pass. |
| Call-graph operations | Delivered | Native root/declarations, repeated typed calls, visitor options, static/indirect-call semantics, bounded atomic results; API/server/Python/CLI/unit/BDD. macOS/RHEL 193 C++ and 166 Python/BDD pass; Clang-only 133 and disabled 93 plus disabled RPC pass. C++ project match/CFG/callgraph facade stubs replaced and compilation database flags verified. |
| Server scripting DSL | Delivered | ANTLR 4.13.2, immutable typed values, lexical loops, branching native composition, one pinned AST/shared worker and atomic quotas; API/server/Python/Lark CLI/unit/BDD. macOS/RHEL 204 native and 172 Python/BDD pass; Clang-only 138, disabled 100, live disabled/pure RPC probes pass. |
| Header/PCH/module reuse and persistence | Delivered | Complete filesystem/reader closure capture, strong native input hashes, tracked AST serialization, named/transitive module restoration, pinned generations and safe fresh-parse fallback. macOS/RHEL: 214 C++ and 177 Python/BDD tests pass; Clang-only 148 and disabled 101 pass. |

Cursor source decisions: `~/workspace/wiki/pages/planning/clang-toolkit-result-cursors.md`
and `clang-toolkit-matching-engine.md`; API target fields retain their existing tags.

Cursor validation logs: `/tmp/ctk-cursors-full-native.log`,
`/tmp/ctk-cursors-final-match-tests.log`, `/tmp/ctk-cursors-final-units.log`,
`/tmp/ctk-cursors-final-bdd.log`, `/tmp/ctk-cursors-rhel-final-run.log`.
`api/check.py`, the 251-serializer/923-field source gate and `git diff --check`
pass. Three native persistence assertions fail when CTest processes share one
storage root concurrently: the store deliberately takes an exclusive root
lock, and losing processes fall back to parsing. Their serial reruns pass;
required full serial CTest passed. This is test storage isolation, not
a matcher result failure. Default rootless Podman storage was unusable;
RHEL validation succeeded with the machine's separate rootful storage.

Traversal verification: `/tmp/ctk-traversal-full-native.log` (179 GoogleTests in
one process), `/tmp/ctk-traversal-final-units.log` (137),
`/tmp/ctk-traversal-bdd.log` (13), `/tmp/ctk-traversal-rhel-run.log` (179 CTests,
150 Python/BDD), `/tmp/ctk-traversal-clang-only-all.log` (131), and
`/tmp/ctk-traversal-noclang-tests.log` (93). Schema/source gates and Clang-header
boundary checks pass. Clang-only serial CTest also passed all 131 tests.

CFG logs: `/tmp/ctk-cfg-full-native-final.log` (185),
`/tmp/ctk-cfg-native-final.log` (all six CFG tests, including all element/context
kinds), `/tmp/ctk-cfg-python-units-final.log` (144), `/tmp/ctk-cfg-bdd.log` (15),
`/tmp/ctk-cfg-rhel-run.log` (185 serial CTests and 159 Python/BDD),
`/tmp/ctk-cfg-clang-only-tests.log` (131), `/tmp/ctk-cfg-noclang-tests.log` (93),
and `/tmp/ctk-cfg-disabled-probe.log`. Native full-suite refresh uses separate
storage and temporary-input roots to prevent collisions with concurrent CTest
processes; all 185 pass with isolation. The local serial CTest baseline refresh passed all 184 original cases; the final six CFG cases and complete 185-case native suite pass. Clang 21 rejects the Clang 22-only reachable
switch-default option explicitly; all other native build flags remain supported.
The final Python public-export refresh passed all 159 Python/BDD tests in the refreshed image.

Call graph verification: `/tmp/ctk-call-graph-full-native.log` (193),
`/tmp/ctk-call-graph-native-final.log` (six call graph and two facade fixtures),
`/tmp/ctk-call-graph-unit.log` (149), `/tmp/ctk-call-graph-bdd.log` (17),
`/tmp/ctk-call-graph-rhel-run.log` (193 serial CTests and 166 Python/BDD),
`/tmp/ctk-call-graph-clang-only-tests.log` (133),
`/tmp/ctk-call-graph-noclang-tests.log` (93) and
`/tmp/ctk-call-graph-disabled-probe.log`. Schema/serializer/Clang-boundary and
diff checks pass. Native contexts are isolated for simultaneous suite runs.

Scripting verification: `/tmp/ctk-script-native-final.log` (204),
`/tmp/ctk-script-units-final.log` (153), `/tmp/ctk-script-bdd-final.log` (19),
`/tmp/ctk-script-rhel-run-final.log` (204 serial CTests and 172 Python/BDD),
`/tmp/ctk-script-clang-only-tests-final.log` (138),
`/tmp/ctk-script-noclang-tests-final.log` (100),
`/tmp/ctk-script-disabled-probe.log`, `/tmp/ctk-script-no-clang-probe.log`.
The first endpoint checks were sandbox-blocked; authorized reruns passed. RHEL's
older protobuf requires oneof case enums for scalar presence; that portable fix
passes the full matrix. All 1,444 implementation/test files matched the tested
RHEL image before this tracker update. Schema/serializer/boundary/diff gates pass.


Native snapshot verification, completed 7 October 2026:
`/tmp/ctk-closure-mac-native-final-authorized.log` (214),
`/tmp/ctk-closure-python-final.log` (155 unit and 22 BDD),
`/tmp/ctk-closure-rhel-run5.log` (214 GoogleTests, 214 serial CTests and 177 Python/BDD),
`/tmp/ctk-closure-clang-only-final-tests2.log` (148), and
`/tmp/ctk-closure-noclang-tests-final-authorized.log` (101).
The macOS serial run in `/tmp/ctk-closure-mac-ctest-final.log` passed 209 cases;
five local-socket cases were sandbox-blocked and all five passed the authorized
CTest rerun in `/tmp/ctk-closure-mac-ctest-socket-rerun.log`. The complete authorized
214-case GoogleTest run also passed. These endpoint restrictions were environment
limitations, not product failures.

LLVM 21/22 portability was verified for native module-cache ownership and ASTWriter
construction. Directory observations use canonical keys on Linux. Metadata read
by serialization is captured before freezing and copying the complete proof.
PCH/module native content hashes detect equal-size preserved-time edits; imported
declarations are tracked during parsing so persisted roots reload correctly.
Unsupported views stay fresh and preserve native source semantics.

Schema, 251-serializer/923-field source coverage, Python lint, Clang-header boundary
and diff checks pass. `/tmp/ctk-closure-source-parity-final.log` confirms all 1,450
implementation and test files match the validated RHEL image
`0bc6d0555c95abe60ea139a8d668731fdf8c5f8935f1fac3c6efdc12a6c9192c`.
See `docs/native-snapshot-reuse.md` for supported precompiled inputs and limits.
All agreed functionality is delivered; no implementation story remains open.


Resume audit, 7 October 2026: the serialization chat is idle after its integration
commit. All 1,450 implementation and test files remain byte-identical to the
verified source manifest; no agreed component is missing. The linked overall
implementation Page still describes historical scaffolds and is stale compared
with this implementation record. Additional work needs a new scope.

## Final aggregate integration verification — 7 October 2026

The frozen candidate combines published SDK commit `59e8ad7`, console commit
`aa3a924`, and every remaining approved implementation file. Whole shared
grammar/client/runtime/server versions include AST traversal, CFG, call graph
and compilation-database project operations alongside the reviewed SDK.

Independent native-analysis and Python/console reviews found no actionable
functional issues. Snapshot review reproduced one defect: successful fresh
parses with more than 16,384 loaded headers failed snapshot admission. A
non-reusable owner now keeps its complete native buffers while recording only
the main-buffer fingerprint for admission; reuse and persistence remain disabled
for that owner. A regression queries a function from the last of 16,385 headers.
The CFG documentation now describes the public all-statement-kinds boolean.

| Final gate | Result |
| --- | --- |
| macOS, Clang 22.1.8, full dev build and native suite | 249/249 passed |
| Rocky Linux 9, Clang 21.1.8, full dev build and native suite | 249/249 passed |
| Full Python unit and live BDD suites, each platform | 390/390 passed: 344 unit + 46 BDD |
| macOS Clang-only / network disabled | 151/151 passed |
| macOS Clang disabled | 109/109 passed |
| TypeScript | Strict compilation, lint, build, 41 unit and 20 live Unix/TCP tests passed |
| Python source and extracted-wheel strict consumers | 0 errors; invalid fixture produced the expected 5 errors |
| Python wheel parity | All 643 package files matched; py.typed included |
| Schema / serializer / Clang include boundary | 256 protobufs, 251 payloads/serializers, 923 field paths; passed |
| Source parity after testing | All 2,572 frozen source hashes matched on host and Rocky |

Native suites ran as one CTest-managed test-binary process with separate writable
storage and temporary-input roots. All persistence regressions passed. Making a
storage root a regular file independently reproduces the six failures recorded
in the console review, confirming unavailable storage can cause those assertions;
the historical console root's precise cause was not established. Rocky's slow
per-test runner was intentionally interrupted after 185 passing cases and
superseded by the complete 249-case monolithic run.

The final wheel SHA-256 is
`296bd1d84cc8ccfd032f5597c730d1fbd9a702fd6e54ff246cc0fc4c04ddb74f`.
Source-preservation and exact publication audits use an isolated Git index;
the existing `server/src/cache/.snapshot_cache.cpp.swp` deletion remains unstaged.

Local evidence: `/tmp/ctk-full-integration-plan.json`,
`/tmp/ctk-full-integration-macos-native.log`,
`/tmp/ctk-full-integration-macos-python.log`,
`/tmp/ctk-full-integration-clang-only-logs/ctest.log`,
`/tmp/ctk-full-integration-noclang.log`,
`/tmp/ctk-full-integration-ts-live.log`,
`/tmp/ctk-full-integration-rhel-n3f5vubc/validation-report.json`,
and `/tmp/ctk-full-integration-python-package/`.
