# Clang Toolkit C++ Technical Design

This document describes the C++ server at commit `5702f26` and explains the implemented snapshot cache through UML class and sequence diagrams. The cache separates path metadata, reusable generations and immutable native ownership so that invalidation can prevent reuse while callers continue using snapshots they already acquired.

## Scope and implementation status

The server builds as C++23. `ctk_core` contains the cache and the transport, scripting and storage interfaces. Optional `ctk_clang` contains the Clang boundary, and `ctk-server` currently starts the transport scaffold. Only `server/src/clang/` includes Clang or LLVM headers.

| Module | Current behavior | Remaining integration |
| --- | --- | --- |
| `ctk::cache` | Radix path registry, canonical compilation identity, immutable snapshots, shared acquisition, validation, invalidation and bounded reuse | Production native loader and callers |
| `ctk::net::Server` | Stores an address; `run()` prints a message and returns | gRPC dispatch, UDS and TLS serving |
| `ctk::script::Engine` | `eval()` returns its source unchanged | Query composition and evaluation |
| `ctk::storage::Store` | Abstract `load()` and `save()` contract | Filesystem and SQLite implementation |
| `ctk::clang_layer` | `Project` and free functions for match, CFG and call graph; functions return empty results | Native parsing and query execution |

The earlier wiki architecture and cache pages describe the intended system; their C++20 and cache status statements predate this implementation. Cursor registries, binding rows, persistence and transport orchestration are future integration work and are not represented as existing cache calls below. The older generic `LruCache` is separate from snapshot retention.

## UML class diagrams

Class names below omit their namespace for readability. Public cache types are in `ctk::cache`; internal records and reuse policy are in `ctk::cache::detail`. `SnapshotCacheImpl` denotes the private `SnapshotCache::Impl` class.

A filled diamond means exclusive containment. An open diamond labeled `shared` means a strong shared pointer that extends lifetime. A dashed arrow labeled `weak` means a non-owning weak pointer. A plain arrow denotes use or a borrowed reference. Multiplicities describe objects retained by each source object.

### Public cache boundary

```mermaid
classDiagram
direction TB
class SnapshotCache {
  +acquire(path, context, cancellation) SnapshotPtr
  +invalidate_path(path)
  +invalidate_directory(path)
  +notify_path_change(path)
  +clear_reuse()
  +files() FileInfoVector
  +stats() CacheStats
}
class SnapshotCacheImpl
class CacheOptions {
  +max_snapshots
  +max_estimated_bytes
  +max_generations_per_profile
  +max_pending_builds
  +max_paths
  +max_profiles_per_file
  +max_inputs_per_snapshot
  +max_acquisition_attempts
}
class CompilationContext {
  +schema_version
  +arguments
  +toolchain_identity
  +environment
  +reusable
  +canonical_bytes() string
  +digest() string
}
class SnapshotLoader {
  <<abstract>>
  +load(path, context) LoadedSnapshot
  +validate(snapshot) bool
}
class LoadedSnapshot {
  +estimated_bytes
}
class SnapshotEntry {
  +generation
  +profile_identity
  +canonical_manifest
  +estimated_bytes
  +execution_mutex() mutex
}
class InputObservation {
  +path
  +kind
  +content_digest
  +validation_context
  +stat_hint
}
class NativeSnapshotOwner {
  <<polymorphic base>>
}
SnapshotCache "1" *-- "1" SnapshotCacheImpl : unique_ptr
SnapshotCacheImpl "1" *-- "1" CacheOptions : limits
SnapshotCacheImpl "1" o-- "1" SnapshotLoader : shared
SnapshotCache ..> CompilationContext : reads during acquire
SnapshotCache ..> SnapshotEntry : returns shared const handle
SnapshotLoader ..> LoadedSnapshot : produces
SnapshotLoader ..> SnapshotEntry : validates
LoadedSnapshot "1" *-- "0..*" InputObservation : captured inputs
LoadedSnapshot "1" o-- "0..1" NativeSnapshotOwner : shared
SnapshotEntry "1" *-- "1..*" InputObservation : immutable inputs
SnapshotEntry "1" o-- "1" NativeSnapshotOwner : shared const
```

`SnapshotPtr` is `std::shared_ptr<const SnapshotEntry>`. A caller retaining that handle pins the generation and its native owner independently of cache reuse. The class enforces immutable snapshot fields; its execution mutex serializes native operations because immutable ownership alone does not make a native AST thread safe. `LoadedSnapshot` is a transfer record, rather than a base class of `SnapshotEntry`.

`SnapshotLoader` supplies a stable native owner and a complete manifest of consumed file buffers, absent lookup candidates and relevant directory observations. It must validate content and lookup state; stat hints alone cannot establish freshness. The cache holds the execution mutex during `validate()`, so the adapter must not acquire that mutex again. Loads and validation of different snapshots can run concurrently. A production Clang implementation of these interfaces has not yet been supplied.

### Metadata and reuse ownership

```mermaid
classDiagram
direction TB
class SnapshotCacheImpl {
  -mutex metadata
  -invalidation_epoch
  -next_generation
  -pending_builds
  +select_attempt(request)
  +reuse_candidate(request, attempt)
  +join_flight(request, attempt)
  +build_generation(request, attempt)
  +publish_generation(request, attempt, prepared)
  +finish_flight(attempt, result)
}
class RadixTree {
  +find(path)
  +try_emplace(path, value)
  +erase(path)
  +prefix(path)
}
class FileEntry {
  +path_key
  +observation_hint
  +invalidation_epoch
}
class ProfileEntry {
  +canonical_context
}
class SnapshotRecord {
  +reusable
}
class SnapshotEntry
class Flight {
  +mutex
  +ready
  +done
  +publication_epoch
  +error
}
class ReusePolicy {
  +admit(record)
  +touch(record)
  +remove(record)
  +oldest()
  +estimated_bytes()
}
class ReuseToken {
  +estimated_bytes
}
SnapshotCacheImpl "1" *-- "1" RadixTree : path registry
SnapshotCacheImpl "1" *-- "1" ReusePolicy : LRU order
RadixTree "1" o-- "0..*" FileEntry : terminal shared values
FileEntry "1" o-- "0..*" ProfileEntry : shared digest map
ProfileEntry "1" o-- "0..*" SnapshotRecord : shared generations
ProfileEntry "1" o-- "0..1" Flight : shared pending build
SnapshotRecord "1" o-- "1" SnapshotEntry : shared const
Flight "1" o-- "0..1" SnapshotEntry : shared completed result
ReusePolicy "1" *-- "0..*" ReuseToken : list entries
ReuseToken ..> SnapshotRecord : weak
SnapshotRecord ..> ProfileEntry : weak
SnapshotRecord ..> FileEntry : weak dependencies
FileEntry ..> SnapshotRecord : weak reverse dependencies
```

The radix tree is the sole authoritative pathname registry. A file record can represent a main source, a dependency, an absent candidate or a directory namespace. Its observation hint is advisory; the snapshot manifest remains the authoritative record of the captured generation. Profile lookup uses a digest but compares the complete canonical context before reuse. A digest collision or `reusable=false` bypasses profile reuse and builds an ephemeral snapshot.

The profile owns reusable generation records. The LRU contains weak tokens and byte estimates, rather than another pathname index or native owners. Weak links in both dependency directions avoid ownership cycles. Retirement removes generation ownership, reverse membership and the LRU token; it does not invalidate an already acquired `SnapshotPtr`.

### Radix container structure

```mermaid
classDiagram
direction TB
class RadixTree {
  +begin() iterator
  +end() iterator
  +find(key) iterator
  +prefix(key) PrefixView
  +try_emplace(key, value)
  +erase(key)
}
class Node {
  +label
  +parent
}
class TerminalValue {
  +const string key
  +mapped_value
}
class Iterator {
  -tree
  -current
  -boundary
}
class PrefixView {
  +begin() iterator
  +end() iterator
}
RadixTree "1" *-- "1" Node : root
Node "1" *-- "0..*" Node : unique children
Node "1" *-- "0..1" TerminalValue : unique payload
Node --> Node : nonowning parent
Iterator --> RadixTree : borrowed tree
Iterator --> Node : borrowed current and boundary
PrefixView --> RadixTree : borrowed tree
```

`TerminalValue`, `Iterator` and `PrefixView` are diagram labels for the template's payload, iterator and prefix range types. The payload is `std::pair<const std::string, T>`. Compressed labels and children ordered by unsigned initial byte support lexicographic forward traversal. A terminal may also have children; the root label is empty. Prefix matching can end inside a compressed label.

Structural mutation or moving the tree invalidates iterators and views. References to surviving payloads remain stable across splits, merges and moves; erasing a payload ends its lifetime. The container has no internal locking. The cache serializes traversal and mutation under its metadata mutex and exposes copied `FileInfo` vectors to callers. Immutable keys and forward traversal support lookup, filtering and transformation, but not sorting or other algorithms requiring permutable keys or random access.

## Identity and resource policy

Paths use explicit absolute POSIX server spellings. Relative paths, NUL, dot components and repeated separators are rejected. A single trailing slash is accepted and removed, except for `/`. The cache does not resolve symlinks or fold case. Directory invalidation includes the exact namespace and descendants under a separator boundary, so `/src` does not match `/src-old`.

The versioned compilation identity captures input spelling, working directory, ordered arguments, toolchain and resource identities, target, sysroot, ordered overlays and environment entries sorted by name. Canonical UTF-8 JSON and full-byte equality determine compatibility. The ordered input manifest has a separate canonical representation and excludes stat hints.

Limits independently bound reusable generations, estimated reusable bytes, generations per profile, pending builds, path records, profiles per file, input observations and acquisition attempts. Oversized snapshots and zero reuse capacity can return valid ephemeral handles. External pins and native parsing allocations remain outside the reusable byte estimate. Capacity failures raise `ResourceExhausted`; repeated freshness rejection ends with an acquisition error after the configured retry bound.

## UML sequence diagrams

These diagrams describe cache calls that exist in the current source. Metadata lock notes refer to `SnapshotCache::Impl::mutex`. Slow native work, waiting and native-owner destruction occur outside that lock. Methods ending in `_locked` require a caller-held metadata lock.

### Cold acquisition and publication

```mermaid
sequenceDiagram
autonumber
actor Caller
participant Cache as SnapshotCache
participant State as SnapshotCacheImpl
participant Loader as SnapshotLoader
participant Snap as SnapshotEntry
participant Flight
Caller->>Cache: acquire(path, context, stop_token)
Cache->>State: acquire(canonical request)
State->>State: select_attempt()
Note over State: Metadata lock: select profile, reserve flight,<br/>capture epoch and generation, increment pending
State->>Loader: load(path, context)
alt Load and construction succeed
  Loader-->>State: LoadedSnapshot
  State->>Snap: construct immutable generation
  State->>Loader: validate(snapshot)
  Note over Loader,Snap: Snapshot execution lane held, metadata unlocked
  Loader-->>State: valid or stale
  alt Validation succeeds
    State->>State: prepare_snapshot()
    Note over State: Copy and deduplicate observations outside metadata lock
    State->>State: publish_generation()
    Note over State: Metadata lock: recheck epoch and file,<br/>register inputs, retain eligible generation, enforce limits
    State->>State: result.snapshot = accepted snapshot or empty
  else Validation rejects generation
    State->>State: result remains empty for retry
  else Validation or preparation or publication throws
    State->>State: result.error = current exception
  end
else Load or construction throws
  State->>State: result.error = current exception
end
State->>State: finish_flight(attempt, result)
State->>State: clear pending flight and decrement pending
Note over State: Release metadata lock before taking flight mutex
State->>Flight: store result, epoch, error and done
State->>Flight: notify_all()
State->>State: check leader cancellation
alt Leader cancelled
  State-->>Caller: AcquisitionCancelled
else Error recorded
  State-->>Caller: propagate exception
else Snapshot available
  State-->>Cache: SnapshotPtr
  Cache-->>Caller: SnapshotPtr
else Freshness rejected
  State->>State: retry within acquisition limit
end
```

The initiating caller performs the synchronous load. Its stop token is checked after completing the flight, so cancellation can still leave a reusable generation for other callers. A load or publication exception is recorded for joined waiters, and every completed build releases its pending slot. Publication and completed-flight reuse conservatively require the global epoch to match, covering dependencies discovered during parsing; unrelated invalidation can therefore cause a bounded retry.

### Warm reuse

```mermaid
sequenceDiagram
autonumber
actor Caller
participant State as SnapshotCacheImpl
participant Record as SnapshotRecord
participant Loader as SnapshotLoader
participant LRU as ReusePolicy
Caller->>State: acquire(canonical request)
State->>Record: select latest generation
Note over State,Record: Copy shared ownership under metadata lock
State->>Loader: validate(record.snapshot)
Note over Loader: Hold snapshot execution lane, metadata unlocked
Loader-->>State: valid or stale
State->>State: check caller cancellation
Note over State: Metadata lock: recheck reusable and same file record
alt Valid and still reusable
  State->>LRU: touch(record)
  State-->>Caller: shared const SnapshotEntry
else Invalid
  State->>State: retire_locked(record)
  Note over State: Release retired owners after metadata unlock
  State->>State: retry acquisition
else Concurrent retirement or replacement
  State->>State: retry acquisition
end
```

Warm acquisition uses the record's reuse state and file identity after validation. It does not reject a generation solely because an unrelated global invalidation epoch changed. Relevant invalidation reaches the record through its registered dependency links.

### Joining a build and independent cancellation

```mermaid
sequenceDiagram
autonumber
actor Leader
actor Waiter
participant State as SnapshotCacheImpl
participant Flight
participant Loader as SnapshotLoader
Leader->>State: acquire(path, profile)
State->>Loader: load(path, context)
Waiter->>State: acquire(same path and full profile)
State->>Flight: select existing flight
Note over State: Metadata unlocked before waiting
State->>Flight: wait(done, waiter stop_token)
alt Waiter cancelled while waiting
  State-->>Waiter: AcquisitionCancelled
  Note over Leader,Loader: Leader load continues for other callers
else Leader completes
  Loader-->>State: loaded inputs and native owner
  State->>State: validate and publish or record failure
  State->>State: release pending slot
  State->>Flight: store result and notify_all()
  Flight-->>State: waiter copies result or error
  alt Error
    State-->>Waiter: propagate loader or publication error
  else Snapshot available
    State->>Loader: validate completed snapshot again
    Loader-->>State: validation result
    State->>State: check waiter cancellation, epoch and file
    State-->>Waiter: SnapshotPtr or bounded retry
  else Empty result
    State->>State: retry waiter acquisition
  end
end
```

A waiter joins the existing full-identity flight before any new pending-build slot is reserved, including when the build limit has been reached. Waiter cancellation affects that waiter only. Each waiter revalidates a completed snapshot before returning it; a flight result is not a guarantee that disk state stayed unchanged until the waiter resumed.

### Dependency invalidation and pinned lifetime

```mermaid
sequenceDiagram
autonumber
actor Watcher
actor Caller
participant State as SnapshotCacheImpl
participant File as FileEntry
participant Record as SnapshotRecord
participant Snap as SnapshotEntry
Caller->>Snap: retain SnapshotPtr
Watcher->>State: notify_path_change(path)
Note over State: Metadata lock: advance global epoch once,<br/>find path and parent namespace without allocating records
State->>File: follow direct profiles and weak reverse links
File-->>State: affected generation records
State->>Record: mark nonreusable and detach reuse links
State->>State: remove profile generation and LRU token
Note over State: Keep temporary SnapshotPtr pins through lock release
State->>State: unlock metadata and release retired pins
Caller->>Snap: continue using acquired generation
Note over Caller,Snap: Existing caller pin keeps native ownership alive<br/>and native operations require execution_mutex
Caller->>Snap: release final external handle
Note over Snap: Destruction occurs when all strong owners are gone
```

Explicit path invalidation follows the same retirement policy. Directory invalidation visits the exact namespace and descendant paths, and reverse dependencies can retire a translation unit outside that directory. Eviction retires reuse ownership using the same lifetime discipline without being a watcher event. An unused path record cannot be erased while reusable generations, flights or live reverse dependencies still require it. Cache destruction requires all active cache operations to have finished.

## Implementation organization and validation

`SnapshotCache::acquire()` prepares identity and delegates. `snapshot_acquisition.cpp` separates retry coordination, selection, warm validation, flight waiting, native load, publication and completion into short named methods. `acquisition.hpp` carries request, attempt and prepared-result records. `cache_state.cpp` contains metadata policy. Keeping these responsibilities separate makes locking and owner lifetime visible without a multi-page acquisition function.

The recorded post-refactor checks pass 52 C++ tests in macOS `dev`, macOS `dev-noclang` and Rocky Linux 9, plus 92 Python tests on macOS and Rocky Linux. Coverage includes radix split and merge behavior, identity collisions, reverse invalidation, publication races, cancellation, metadata pressure, eviction with external pins and native destruction outside metadata locking. These are the existing implementation results; this document adds no production parser or transport implementation.

## Source references

| Source | Design evidence |
| --- | --- |
| [Cache contract](/Users/husam/workspace/clang-toolkit/docs/cache.md) | Identity, ownership, container and concurrency rules |
| [Public cache API](/Users/husam/workspace/clang-toolkit/server/include/ctk/cache/snapshot_cache.hpp) | Acquisition, invalidation, inspection and limits |
| [Snapshot boundary](/Users/husam/workspace/clang-toolkit/server/include/ctk/cache/snapshot.hpp) | Immutable snapshot, observations and loader contract |
| [Metadata records](/Users/husam/workspace/clang-toolkit/server/include/ctk/cache/cache_records.hpp) | Strong and weak ownership relationships |
| [Radix tree](/Users/husam/workspace/clang-toolkit/server/include/ctk/cache/radix_tree.hpp) | Compressed nodes, iterators and prefix ranges |
| [Acquisition phases](/Users/husam/workspace/clang-toolkit/server/src/cache/snapshot_acquisition.cpp) | Cold, warm, waiter and cancellation sequences |
| [Cache state policy](/Users/husam/workspace/clang-toolkit/server/src/cache/cache_state.cpp) | Publication eligibility, retirement and limits |
| [Reuse policy](/Users/husam/workspace/clang-toolkit/server/include/ctk/cache/reuse_policy.hpp) | Weak LRU tokens |
| [Validation record](/Users/husam/workspace/clang-toolkit/docs/cache-implementation-progress.md) | Existing build and test results |
| [Server architecture design](https://chatgpt.com/space/page_1abde7a65a14819196b0919a6311a5ba) | Intended integration; wiki mirror `[[pages/planning/clang-toolkit-server-architecture]]` |
| [Original cache design](https://chatgpt.com/space/page_2e571754ca3081919967899081ebaf73) | Design rationale; wiki mirror `[[pages/planning/clang-toolkit-ast-cache]]` |
| [Radix and binding design](https://chatgpt.com/space/page_77f518388f748191b08749f838b780fa) | Path registry rationale; wiki mirror `[[pages/planning/clang-toolkit-radix-binding-model]]` |
