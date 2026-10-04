# In-memory cache implementation

Source designs: [cache](https://chatgpt.com/space/page_2e571754ca3081919967899081ebaf73), [radix data model](https://chatgpt.com/space/page_77f518388f748191b08749f838b780fa), and `~/workspace/wiki/pages/planning/clang-toolkit-{ast-cache,radix-binding-model,result-cursors,server-architecture,persistence}.md`.

- [x] Inspect wiki designs and current scaffold; preserve unrelated working changes.
- [x] Explicitly raise the server build standard from C++20 to C++23.
- [x] Implement and verify compressed radix storage, iterators and prefix ranges.
- [x] Implement canonical path/profile identity and immutable snapshot boundary.
- [x] Implement acquisition, weak reverse invalidation and token LRU retention.
- [x] Verify race, cancellation, eviction and container contracts.
- [x] Run existing C++/Python checks and record unavailable platform gates.

Scope: cache library with an injectable Clang-free loader/validator. Transport,
matcher services, cursor registry and disk persistence remain separate work.

## Delivered

- `RadixTree<T>`: compressed byte storage, stable payload references, forward
  iterators, immutable keys, mutable/const traversal, nonowning prefix views,
  move support, split/merge allocation rollback, boundary-aware iterator equality.
- Explicit path policy and versioned canonical UTF-8 JSON compilation identity;
  full identity comparison after every digest hit, collision bypass and uncaptured
  environment eligibility flag.
- Immutable snapshots with consumed-input/lookup manifests and opaque native
  ownership; shared acquisition, independent cancellation, publication epoch
  fences, weak reverse invalidation, generation/token LRU and separate limits.
- Metadata limits still permit existing-path invalidation; empty profiles reclaim
  capacity; input copying/deduplication happen outside metadata locking.
- Native validation shares the snapshot execution lane; retirement retains native
  ownership until metadata locking ends.
- [API and container contracts](cache.md) document concurrency, iterator lifetime,
  supported range algorithms, loader responsibilities and practical limits.

## Verified gates (2026-10-04)

- macOS / Homebrew Clang 22.1.8: dev build and 52/52 CTest cases pass.
- macOS Clang-free dev-noclang: build and 52/52 CTest cases pass.
- macOS Python 3.14: 91/91 unit tests and 1/1 BDD E2E scenario pass.
- Rocky Linux 9 / Clang 21.1.8: final image build, server build, 52/52 C++ cases
  and 92/92 Python tests pass. No required platform gate remains unavailable.
- Formatting of new C++ cache/tests and `git diff --check` pass. The unchanged
  legacy LRU's pre-existing style is outside the formatting gate.
- Independent review examined collision identity, concurrency, native release,
  metadata pressure, and publication rollback; identified issues were corrected
  with focused regression cases.

The native loader is an injectable boundary, not a production parser or matcher
service. Input freshness depends on its complete, stable capture and validation.
Reusable native bytes are estimates; cursor pins and parser allocations need
caller budgets. Builds and completed-flight waiters can conservatively retry on
unrelated invalidation; the configured retry bound reports sustained churn.

## Acquisition maintainability correction (2026-10-04)

- [x] Replace the oversized public acquisition function with an identity wrapper.
- [x] Separate internal metadata operations from acquisition coordination.
- [x] Use short named selection, validation, wait, load and publication methods.
- [x] Explain locking, retirement ownership and flight finalization in comments.
- [x] Review the refactor and rerun required C++/Python/platform checks.

The public acquisition wrapper is nine lines including its signature. The retry
coordinator has a ten-line body; the largest acquisition phase has a 21-line body.
Private `acquisition.hpp` contains explicit request/attempt/prepared-result records;
`snapshot_acquisition.cpp` contains the phases; `cache_state.cpp` owns metadata
operations, with `_locked` methods documenting caller-held locking. This replaces
the original multi-page function without changing the public API.

Independent review found no flight, cancellation, publication or owner-lifetime
regression. After the refactor, macOS dev/dev-noclang and Rocky Linux 9 each pass
52/52 C++ cases; macOS and Rocky Linux each pass 92/92 Python tests. Formatting and
`git diff --check` pass.
