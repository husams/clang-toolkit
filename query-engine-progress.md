# Query engine implementation progress

## Scope

Implement the query-engine integration and native semantic serialization while
preserving unrelated worktree changes. Standard Clang AST matcher expressions execute in
session analysis; there is no independent planner. Semantic bindings must cross
from Clang as completed, owned protobuf payloads, with a concrete serializer
class for every supported schema node kind.

## Stories

| Story | State | Evidence / next step |
| --- | --- | --- |
| Confirm wiki decisions, worktree boundaries and current component contracts | Done | Wiki: `pages/planning/clang-toolkit-query-engine.md`; existing Cache, Storage, Network and AnalysisSession APIs inspected. |
| Define protobuf binding ownership across Clang, application and Network | Done | Additive typed `MatchResult` accompanies legacy summaries; app/network copy owned protobuf values. |
| Connect snapshot acquisition to Cache/Storage and keep AST access serialized | Done | `SnapshotCache` loader parses/reloads validated AST artifacts and runs query work in the cache execution lane; corruption/staleness falls back to reparsing. |
| Implement concrete node serializers and generated coverage map | Done | 251 dedicated source/header pairs populate native fields; the strengthened gate checks 923 direct payload extraction/availability paths. Current family fixtures and platform checks are tracked below. |
| Integrate serialization with callback rows, cancellation and retained publication | Done | Clang callback values are owned protobufs, copied into app events and then into typed Network rows; existing stream cancellation/terminal tests pass. |
| Validate native, Python, BDD, macOS and RHEL paths | Done | Current macOS and Rocky 9 C++ 158/158, Python/unit/BDD 132/132; Clang-only CTest 131/131. |

## Current validation and native limits

- Genuine absent native data, unsupported version-specific nodes, contract gaps
  and expansion limits remain explicit availability reasons; these bindings are
  never advertised as complete. See `docs/semantic-serialization.md`.
- The previous generic `Any` conflict is resolved by the typed recursive schema
  assembly, with draft migration details in `api/README.md`.

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

Earlier integration Clang-only build and tests passed: 79/79 with networking and the API option
disabled. API-only and network-only CMake configurations also succeed.
Independent review found no remaining blocker in
the fixes. Those results describe the earlier query-engine integration; the
6 October implementation below supersedes its partial field writers and schema.

## Complete semantic serialization (6 October 2026)

Live baseline: `38176d7`; pre-existing deleted `.snapshot_cache.cpp.swp` is unrelated.
Historical checks above do not validate this implementation.

| Story | State | Evidence / next step |
| --- | --- | --- |
| Resolve typed recursive AST contract | Done | Compile-time assembly preserves dedicated schema sources and stable typed wrapper tags; strict AST checker passes; migration is documented. |
| Dedicated declaration field serializers | Done | 66 dedicated pairs; finite names/symbols/templates and source-backed declaration metadata; 23 family fixtures pass. |
| Dedicated expression field serializers | Done | 104 dedicated pairs; exact constants and separate call/cast/constructor metadata; 12 family fixtures pass. |
| Dedicated statement and type field serializers | Done | 29 statement and 52 type pairs; owned children, qualifiers and exact native subtype dispatch; 6 statement and 11 type fixtures pass. |
| Field/family fixtures and strengthened coverage gate | Done | API checker and 251-node/923-field source gate pass; native fixtures verify actual values/presence, independent roots, ownership, truncation and transport. |
| Current macOS/RHEL, native/Python/BDD and Clang-only verification | Done | Full results below; version-specific fixture assertions preserve exact native wrappers and explicit availability. |

### Verified results

| Check | Result |
| --- | --- |
| Strict API/schema checker | Pass: 256 source protos, 251 self-contained payloads, concrete recursive wrappers, stable tags, presence, exact bits, finite symbols and JSON round trips; Any/Struct prohibition retained. |
| Dedicated serializer field gate | Pass: 251 dedicated serializers and 923 direct payload extraction/availability paths. This is source coverage, not a claim that every rare native alternative was instantiated. |
| macOS arm64, LLVM 22.1.8 | Build succeeds; CTest 158/158. Final rebuilt fixture binary also passes all 158 tests together. |
| Rocky/RHEL 9, LLVM 21.1.8 | Required container build/run succeeds; CTest 158/158, strict schema/coverage gates pass. Container/host SHA256 parity verified for 787 implementation/schema/test/build files. |
| Python and BDD, both platforms | 132/132: 124 unit tests and 8 BDD scenarios, including complete typed native initializer/type transport. Only existing pytest-bdd deprecation warnings. |
| Clang-only, networking and API option disabled | Build succeeds; serial CTest 131/131; final rebuilt fixture binary also passes all 131 tests together. |
| Native compatibility preflight | Actual LLVM 21 syntax checks pass for all 104 expression and 52 type serializers plus their shared helpers; all declaration/statement sources compile in the full build. |
| Diff whitespace | `git diff --check` passes. |

Cache regression tests use serial execution and isolated validation cache roots;
parallel test processes share an exclusive default cache store. The two cache
regressions pass when run serially. Fixture corrections preserve native matcher
cardinality, unregistered matcher limitations and exact ParenType/ElaboratedType
wrappers instead of flattening types or weakening semantic assertions.

Serializer integration targets `main` from baseline `38176d7`, using the verified
6 October snapshot. Later analysis/scripting work and the unrelated pre-existing
deleted swap file remain separate worktree changes.
See `docs/semantic-serialization.md` for extraction boundaries, genuine native
and schema limits, expansion bounds and runtime evidence; `api/README.md`
documents draft wire/descriptor migrations and client regeneration requirements.
