# Native snapshot reuse and persistence

All native query, cursor, traversal, CFG, call-graph and script operations acquire
owned AST generations through the same snapshot adapter. Warm acquisitions repeat
content validation. A fresh engine can load a persisted native translation unit
and its complete precompiled dependency graph; it does not replay serialized
query rows.

## Captured inputs

Each parse uses a private filesystem instance. The adapter records the file bytes
actually supplied to Clang, include/config/module-map lookups, missing earlier
search candidates, `__has_include` probes, real paths and equivalent lookup
spellings. Enumerated directories retain sorted namespace proofs. Compiler
selection environment variables participate in the compilation profile.

Regular buffers are copied into snapshot ownership. Imported AST reader buffers,
input-file proofs, loaded source buffers and metadata read by AST serialization
are captured before the filesystem is sealed. The AST, native module/PCH buffers, staged root and persistent lease live
until their last snapshot owner releases them. A pinned cursor continues to use
its generation after a source, header or precompiled file is replaced; a new file
query acquires a validated generation.

Native artifact freshness uses content digests rather than modification times.
For PCH and module input files, the adapter additionally checks the native stored
content hash against the captured source bytes. Same-size edits with preserved
modification times therefore invalidate reuse. Reader imports become explicit
artifact graph edges. Named-module mappings are restored from the validated
module observations when loading the stored root.

## Building reusable precompiled inputs

Clang must have recorded content hashes when creating a precompiled input:

```sh
clang++ -std=c++20 -Xclang -fvalidate-ast-input-files-content \
  -x c++-header values.hpp -o values.pch
clang++ -std=c++20 -Xclang -fvalidate-ast-input-files-content \
  --precompile numbers.cppm -o numbers.pcm
```

Pass `-include-pch values.pch` or `-fmodule-file=numbers=numbers.pcm` through the
existing Python `compile_arguments` or CLI `extra_args` settings. Native flags
and compatibility still govern whether Clang can consume an artifact. The server
does not force a detailed preprocessing record into a user's compilation.

## Fallback and limits

Persistence is optional. Missing, corrupt, incompatible or stale stored artifacts
are retired and the requested source is parsed again with its original flags.
A stale *explicitly supplied* PCH/module that fails its native input proof requires
rebuilding that input; deleting the cache cannot repair the supplied compiler
artifact.

Inputs without native content hashes, response/opaque preprocessing options,
plugins and explicit VFS overlays remain fresh native parses without reusable
cache admission or persistence. Virtual source semantics are preserved. Direct
and nested expansions of `__DATE__`, `__TIME__` and `__TIMESTAMP__` are observed
through native preprocessing callbacks and are also kept fresh.

Filesystem capture is bounded to 16,383 observations and 256 MiB of regular-file
buffers. An incomplete capture disables reuse; it does not turn a valid native
query into a cache hit. Native memory figures are estimates and include owned
filesystem buffers and serialized root capacity. Existing operation, cursor and
response bounds still apply.

## Verification

`server/tests/test_snapshot_closure.cpp` covers header persistence, missing lookup
candidates, equal-size preserved-time edits, PCH source validation and pinned
buffers, an unhashed PCH, nested volatile macros, symlink retargeting, VFS fallback
and transitive named modules. Existing storage regressions cover corrupt-root
fallback and lease lifetime. Python unit tests verify formal CLI/client flag
preservation; BDD scenarios exercise header/PCH/module generations through the
actual local gRPC server.
