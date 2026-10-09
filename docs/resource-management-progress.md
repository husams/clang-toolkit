# File output and resource management

- [x] Variable/interpolated paths for save/load/output and per-print overwrite/append.
- [x] Versioned binary protobuf snapshots with lossless primitive types.
- [x] Server status: uptime, process memory, retained resources, cache disk usage.
- [x] Owner-scoped session list/attach/close and local binding list/drop/rename.
- [x] Memory/disk cache pruning that preserves pinned ASTs and leases.
- [x] Help, completion, API/client methods, unit and BDD coverage.
- [x] Full C++/Python checks and an isolated live-server smoke test.

Existing unrelated edits in semantic field handling and matching are preserved.

## Verified on 9 October 2026

- C++ debug build and all 281 GoogleTest cases passed with an isolated store.
- All 519 Python unit tests passed.
- All 69 BDD scenarios passed across the full initial run (50 network scenarios)
  and the final 19 console scenarios rerun after fixing optional-keyword completion.
- Unix and TCP resource controls passed through sync/async SDKs; real console
  exports round-tripped JSON, YAML and protobuf and verified overwrite/append.
- API schema checks and the 251-node serializer source gate passed.
- TypeScript schema regeneration/build passed; 51 tests passed (24 optional
  integration cases remain skipped in the default TypeScript test command).
- A running server must be restarted to expose the added RPCs. Existing user
  sessions were not restarted or pruned during validation.

The initial CTest run collided with an existing server's storage lock. An isolated
full GoogleTest run passed. A full E2E run exposed an automatic optional `to`
completion interfering with Up/Down history; implicit grammar continuations are
now suppressed after complete commands, preserving explicit Tab and path navigation.
