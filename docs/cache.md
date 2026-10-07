# In-memory snapshot cache

`ctk::cache::SnapshotCache` is the Clang-free cache library. The server scaffold
does not yet implement native parsing or matcher services; an adapter implements
`SnapshotLoader::load` and `validate` to supply owned native snapshots. Only
`server/src/clang/` may implement those operations using Clang headers. No disk
artifacts, protobuf payloads or matching results are cached by this module.

The implementation follows the [cache design](https://chatgpt.com/space/page_2e571754ca3081919967899081ebaf73)
and [radix data model](https://chatgpt.com/space/page_77f518388f748191b08749f838b780fa),
also stored at `~/workspace/wiki/pages/planning/clang-toolkit-ast-cache.md` and
`clang-toolkit-radix-binding-model.md`.

## Container contract

`RadixTree<T>` owns `std::pair<const std::string, T>` values. Its mutable and const
iterators are multipass forward iterators with real lvalue references. Keys cannot
be assigned through an iterator; mapped values can. Traversal uses unsigned byte
lexicographic key order, with an empty key before its descendants. The root has
an empty compressed label; every other label is nonempty and children have unique,
ordered initial bytes. Terminal payloads may also have children.

Use range-for, `std::ranges::find_if`, `for_each`, `distance`, `equal`, `copy`, and
`filter`/`transform` compositions. `prefix` returns a nonowning forward view and
can match a prefix ending inside a compressed label. Algorithms requiring random
access or mutable/permutable keys, including `sort`, `reverse`, and `remove`, do
not meet this iterator's requirements. The tree is sized; prefix distance walks
its terminal values. Prefix views and iterators require the tree to remain alive;
moving or structurally mutating the tree invalidates them. Iterator equality is
scoped to the same tree and traversal boundary, so full-tree and prefix iterators
at one payload can have different successors without violating multipass rules.
A named prefix view
can be passed to iterator-returning algorithms; algorithms on temporary views
may produce `std::ranges::dangling` according to the standard range rules.

References to surviving payloads remain stable across splits, merges and moves;
erasing that payload, clearing or destroying its owning tree ends their lifetime.
Insertion allocates the new branch completely before linking it. Deletion prepares
merged labels before removing a terminal; allocation failure leaves stored values
unchanged. Exceptions from payload destructors are unsupported, as with standard
containers.

The radix container has no internal synchronization. Serialize mutations against
all traversals; const concurrent reads are safe when the tree and mapped values
are unchanged. SnapshotCache never exposes tree iterators or mutable FileEntry
handles: `files` and `files_in_directory` return independent value vectors, safe
to iterate after mutation or cache destruction.

## Identity and ownership

Paths are explicit absolute POSIX server spellings. Reject dot components,
repeated separators, NUL and relative keys; do not realpath, lowercase or collapse
symlink-sensitive components. Directory operations include the exact namespace
and its trailing-separator prefix, excluding `/src-old` from `/src`. Root uses `/`.

A full versioned compilation identity includes input spelling, ordered arguments,
working directory, exact toolchain/resources, target, sysroot, ordered overlays
and sorted environment names. Canonical UTF-8 JSON has a versioned domain prefix.
FNV-1a digests are lookup aids; full bytes are compared on every hit. A collision
or `reusable=false` builds an ephemeral owner without replacing another profile.
The radix is the only authoritative pathname index, including dependency-only
files, absent candidates and directory namespaces.

Snapshots contain immutable ordered input observations and a canonical manifest;
stat hints are excluded from identity. Each loader must capture the actual
consumed buffers, failed lookup candidates and relevant namespace digests, and
preserve their stable view for lazy native access. Validation repeats those checks
before initial admission, every warm acquisition and each completed-flight waiter.
Freshness describes that captured generation, not an indefinitely unchanged disk.

Profile generation references retain reusable snapshots. The LRU stores weak reuse
tokens, and reverse dependencies are weak. Invalidation/eviction remove reuse
ownership and reverse membership; acquired SnapshotPtr handles still pin their
original AST and inputs. CacheOptions bounds retained snapshots, estimated reusable
bytes, generations, path records, profiles per path, input observations per
snapshot, concurrent builds and retries. Empty profiles are pruned under pressure.
Oversized snapshots are returned ephemerally. Estimates do not bound native memory
exactly, and externally pinned snapshots are outside the reusable byte budget.
Callers must bound cursor lifetimes and native parser allocations separately.

## Concurrency and cancellation

Acquisition is split into short selection, warm validation, shared-flight wait,
native load, publication and completion methods in `server/src/cache/snapshot_acquisition.cpp`.
Metadata policy lives in `cache_state.cpp`; methods with `_locked` in their names
require the caller to hold the metadata mutex. The public `acquire` method prepares
identity and delegates to the retry coordinator. Comments describe the ownership
and locking boundary at each phase.

One metadata mutex protects the radix, profiles, reverse links, flights and LRU.
Observation copying and path deduplication happen before locking; publication
performs bounded linear metadata work rather than quadratic deduplication.
Parsing, validation I/O, waiting, native execution and native-owner destruction
occur outside it. Admission checks unchanged file identity and an invalidation
epoch after validation. Builds and completed-flight waiters conservatively retry
even unrelated concurrent invalidations, covering dependencies discovered only
during parsing. Warm reuse checks registered reverse-link state and is unaffected
by unrelated watcher events. Sustained build churn returns an acquisition error
after the configured retry bound. Watcher events do not allocate new path records,
so metadata limits cannot prevent invalidating existing dependencies.

One flight serves a full path/profile identity. Waiters revalidate independently;
cancellation of one does not stop work needed by another. Waiting cancellation is
prompt; the initiating caller's synchronous native load finishes before its
cancellation is reported. A cancelled initiator can still publish a reusable owner.
Loader failures propagate to all joined waiters and release the pending-build slot.
Cache destruction requires callers to finish all active operations first, and
context arguments must remain unchanged during acquisition.

Native operations on one snapshot must hold its `execution_mutex`, acquired after
releasing cache metadata locking. The cache holds that lane when calling validate;
adapters must not lock it again. Native adapters may receive concurrent loads and
validation calls for different snapshots. Transport, cursor revisions and copied binding-row state are
separate responsibilities; no binding-state integration was needed for this cache.

## Validation

GoogleTests cover radix/container concepts and algorithms, split/merge rollback,
canonical identities, digest collision bypass, input/namespace reverse invalidation,
single-flight races, validation publication fences, cancellation, pinned eviction,
metadata limits, value-vector lifetimes and native destruction outside locking.
The root build explicitly requests C++23 for all server targets, including
`dev-noclang`. See `cache-implementation-progress.md` for actual gate results.

The integrated native adapter now captures header and precompiled dependency
closures; see [native snapshot reuse](native-snapshot-reuse.md) for its validation,
artifact ownership, supported proofs and fresh-parse fallback.
