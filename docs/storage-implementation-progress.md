# Native AST storage implementation

Current native-adapter delivery and platform verification are tracked in [functionality progress](../functionality-progress.md) and [native snapshot reuse](native-snapshot-reuse.md). The storage record below preserves its original delivery state.

Design contract: [persistence specification](https://chatgpt.com/space/page_3e89aff64e2c819194fe8ea862c459cd), [schema v1](https://chatgpt.com/space/page_864e098739988191b7bbc19a5adc0dea), [C++ technical design](https://chatgpt.com/space/page_3f75548a9ba08191b70bcd533c5212e7), [cache design](https://chatgpt.com/space/page_2e571754ca3081919967899081ebaf73), and [radix/binding model](https://chatgpt.com/space/page_77f518388f748191b08749f838b780fa).

## Original storage requirements and status

| Requirement | Status | Evidence |
| --- | --- | --- |
| Public typed domain API; backend hidden from callers | Implemented | `store.hpp`; SQLite types remain private |
| Exact schema v1: 9 tables, 48 fields, 8 indexes, 3 guards | Implemented | Migration compares all stored schema definitions against the v1 DDL |
| Per-connection SQLite settings and ordered transactional migrations | Implemented | `sqlite_raii.cpp`, `schema_migrations.cpp` |
| Versioned canonical identities, SHA-256 and full-byte collision checks | Implemented | `canonical_encoder.cpp`, collision/version tests |
| Durable content-addressed blob staging/publication | Implemented | `blob_store.cpp`; existing-blob reuse now fsyncs file and directories |
| Complete input observations and dependency closure validation | Implemented | `snapshot_validation.cpp`; main/absent/directory/DAG cases |
| Runtime leases, stale/retirement/GC and race safety | Implemented, limited coverage | Lease/shared-blob cases and concurrent recovery/publication test; broader crash stress remains |
| Bounded recovery, unique-byte quota, pins and access coalescing | Implemented, limited coverage | Recovery scans/cleanup are budgeted; pinned snapshots are skipped by quota retention |
| Native TU/PCH/module adapter with safe unsupported fallback | Pending | Native adapter evidence; simple TU roundtrip is insufficient |
| macOS + RHEL 9 build/test validation; independent design/lifetime review | Pending | Recorded commands and review findings |

## Original starting state

- Checkout HEAD: `5702f26c653fb694a219648c3eba6880a4b2115e` (`main`, one commit ahead of `origin/main`).
- Existing unrelated user file preserved: `docs/cpp-technical-design.md` (untracked before this work).
- Existing `ctk::storage::Store` is only string `load`/`save`; no server persistence caller or production Clang loader exists.
- Existing Clang entry points in `server/src/clang/tooling.cpp` are empty stubs.
- Host has SQLite 3.51.0 and OpenSSL 3.6.4; native format probe evidence covers a simple TU roundtrip only. PCH/module relocation, lazy dependency capture and stable VFS views are not established.

## Original implementation log

Implemented the typed Store API, v1 metadata repository, canonical profile/toolchain/manifest encoding, durable content-addressed blob store, ownership lock, validation, leases, retention, quota and bounded recovery. Recovery waits for active publications; non-reusable profiles cannot be published or acquired. macOS dev and dev-noclang pass 66/66 C++ tests; Python unit (91) and E2E (1) pass. RHEL validation is blocked because the local Podman socket is unavailable. Independent review confirms there is still no production native-artifact adapter or server integration; safe cache fallback therefore remains necessary. Broader crash-boundary tests are still outstanding.
