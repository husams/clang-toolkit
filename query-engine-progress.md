# Query engine implementation progress

## Scope

Implement the query-engine integration in slices while preserving the existing
dirty API/protobuf worktree. Standard Clang AST matcher expressions execute in
session analysis; there is no independent planner. Semantic bindings must cross
from Clang as completed, owned protobuf payloads, with a concrete serializer
class for every supported schema node kind.

## Stories

| Story | State | Evidence / next step |
| --- | --- | --- |
| Confirm wiki decisions, worktree boundaries and current component contracts | Done | Wiki: `pages/planning/clang-toolkit-query-engine.md`; existing Cache, Storage, Network and AnalysisSession APIs inspected. |
| Define protobuf binding ownership across Clang, application and Network | Done | Additive typed `MatchResult` accompanies legacy summaries; app/network copy owned protobuf values. |
| Connect snapshot acquisition to Cache/Storage and keep AST access serialized | Done | `SnapshotCache` loader parses/reloads validated AST artifacts and runs query work in the cache execution lane; corruption/staleness falls back to reparsing. |
| Implement concrete node serializers and generated coverage map | Partial | 251 concrete dispatch classes are checked against catalog/schema; rich field writers cover shared declaration/expression metadata, functions, variables, integer/string literals and call/member-call data. Other kinds remain explicitly incomplete with unavailable fields. |
| Integrate serialization with callback rows, cancellation and retained publication | Done | Clang callback values are owned protobufs, copied into app events and then into typed Network rows; existing stream cancellation/terminal tests pass. |
| Validate native, Python, BDD, macOS and RHEL paths | Done | Final review fixes: macOS C++ 106/106 and Python+BDD 129/129 passed; Rocky 9 C++ 106/106 and Python+BDD 129/129 passed. |

## Remaining work

- Complete field-level semantic writers for the remaining catalog nodes; those
  bindings are currently explicitly marked incomplete.
- Resolve the existing `api/check.py` conflict with generic `Any` fields in the
  AST semantic schema before claiming a fully typed nested contract.

## Review fixes

| Finding | State | Verification |
| --- | --- | --- |
| Trigraph directives bypass cache freshness safeguards | Done | Include-search shadowing passes for `??=include`, a backslash-spliced digraph, and a trigraph-spliced digraph. Escapes and indirect preprocessing arguments conservatively disable reuse. |
| Object type serialization desugars aliases | Done | Exact native types are preserved: Clang 22 alias/direct payloads remain TypedefType/RecordType; Clang 21 ElaboratedType wrappers report explicit UnsupportedValue with a deferred-contract reason. |
| Temporary AST paths collide between processes | Done | Atomic owner-only temporary directories replace predictable artifact filenames; ownership, permissions and cleanup checks pass. |
| Corrupt stored artifacts fail valid source queries | Done | Corruption after store initialization falls back to source parsing; the regression restores the damaged test blob. |
| Snapshot retention reporting disagrees with owned memory | Done | The engine pins the latest snapshot per file/compilation context for the session. Fresh non-reusable parses and loaded-artifact survival past LRU eviction are verified. |
| Clang-only build depends on enabled networking | Done | Match protobuf generation is independent of gRPC; a full Clang build with networking and the API option disabled succeeds. |

Each parsed or reloaded AST now owns an independent physical VFS working
directory. The multi-directory regression caught shared process filesystem state
on Clang 21; all three directive cases pass after isolation, including after an
earlier fixture directory is removed.

Final Clang-only build and tests passed: 79/79 with networking and the API option
disabled. API-only and network-only CMake configurations also succeed.
Independent review found no remaining blocker in
the fixes. Existing field-level serializer work and the generic Any contract
conflict listed above remain outside these review fixes.
