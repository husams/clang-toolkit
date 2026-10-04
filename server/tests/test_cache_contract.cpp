#include "ctk/cache/snapshot_cache.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <atomic>
#include <future>
#include <memory>
#include <ranges>

namespace {
using namespace ctk::cache;

struct Owner final : NativeSnapshotOwner {};
class Loader final : public SnapshotLoader {
public:
  std::atomic<int> loads = 0;
  std::function<void(const SnapshotEntry &)> on_validate;
  LoadedSnapshot load(const std::string &path,
                      const CompilationContext &) override {
    ++loads;
    return {std::make_shared<Owner>(),
            {{path, InputKind::File, "buffer", {}, 1}},
            1};
  }
  bool validate(const SnapshotEntry &snapshot) override {
    if (on_validate)
      on_validate(snapshot);
    return true;
  }
};
CompilationContext context() {
  CompilationContext result;
  result.input_spelling = "/src/main.cpp";
  result.working_directory = "/src";
  result.toolchain_identity = "test-toolchain";
  return result;
}

TEST(CacheContract, ReclaimsEmptyProfileMetadataUnderPressure) {
  auto loader = std::make_shared<Loader>();
  CacheOptions options;
  options.max_profiles_per_file = 1;
  SnapshotCache cache(loader, options);
  const auto first = cache.acquire("/src/main.cpp", context());
  cache.clear_reuse();
  auto changed = context();
  changed.arguments = {"-DNEW_CONTEXT"};
  const auto second = cache.acquire("/src/main.cpp", changed);
  EXPECT_NE(first, second);
  EXPECT_EQ(cache.files().front().profiles, 1u);
  EXPECT_EQ(loader->loads, 2);
}

TEST(CacheContract, BoundsManifestBeforeAdmission) {
  auto loader = std::make_shared<Loader>();
  CacheOptions options;
  options.max_inputs_per_snapshot = 0;
  SnapshotCache cache(loader, options);
  EXPECT_THROW(cache.acquire("/src/main.cpp", context()), ResourceExhausted);
  EXPECT_EQ(cache.stats().pending_builds, 0u);
  EXPECT_EQ(cache.stats().reusable_snapshots, 0u);
}

TEST(CacheContract, ValidationRunsInsideSnapshotExecutionLane) {
  auto loader = std::make_shared<Loader>();
  SnapshotCache cache(loader);
  const auto snapshot = cache.acquire("/src/main.cpp", context());
  loader->on_validate = [&](const SnapshotEntry &value) {
    // Probe from another thread: try_lock by the owning thread is undefined.
    auto probe = std::async(std::launch::async, [&] {
      if (value.execution_mutex().try_lock()) {
        value.execution_mutex().unlock();
        return true;
      }
      return false;
    });
    EXPECT_FALSE(probe.get());
    EXPECT_EQ(cache.stats().pending_builds, 0u);
  };
  EXPECT_EQ(cache.acquire("/src/main.cpp", context()), snapshot);
}

TEST(CacheContract, ManifestExcludesStatHintsAndRetainsOrderedObservations) {
  const auto identity = context().canonical_bytes();
  LoadedSnapshot first{
      std::make_shared<Owner>(),
      {{"/src/main.cpp", InputKind::File, "main", {}, 1},
       {"/include/missing.hpp", InputKind::Absent, {}, "lookup-chain", {}}},
      1};
  auto second = first;
  second.inputs.front().stat_hint = 999;
  const SnapshotEntry a(1, identity, first);
  const SnapshotEntry b(2, identity, second);
  EXPECT_EQ(a.canonical_manifest, b.canonical_manifest);
  std::ranges::reverse(second.inputs);
  const SnapshotEntry reversed(3, identity, second);
  EXPECT_NE(a.canonical_manifest, reversed.canonical_manifest);
  EXPECT_EQ(std::ranges::distance(a.inputs), 2);
}
} // namespace
