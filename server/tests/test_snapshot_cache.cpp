#include "ctk/cache/snapshot_cache.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <functional>
#include <future>
#include <memory>
#include <mutex>
#include <ranges>
#include <set>
#include <stop_token>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace {

using namespace std::chrono_literals;
using ctk::cache::CompilationContext;
using ctk::cache::InputKind;
using ctk::cache::InputObservation;
using ctk::cache::LoadedSnapshot;
using ctk::cache::SnapshotCache;
using ctk::cache::SnapshotLoader;
using ctk::cache::SnapshotPtr;

CompilationContext context_for(std::string spelling = "/src/main.cpp") {
  CompilationContext context;
  context.input_spelling = std::move(spelling);
  context.working_directory = "/src";
  context.toolchain_identity = "clang-22/test";
  context.arguments = {"clang++", "-std=c++23", context.input_spelling};
  return context;
}

InputObservation file_input(std::string path, std::string digest = "content") {
  return {std::move(path), InputKind::File, std::move(digest), {}, 1};
}

struct TestOwner final : ctk::cache::NativeSnapshotOwner {
  explicit TestOwner(std::function<void()> on_destroy = {})
      : on_destroy(std::move(on_destroy)) {}
  ~TestOwner() override {
    if (on_destroy)
      on_destroy();
  }
  std::function<void()> on_destroy;
};

class FunctionLoader final : public SnapshotLoader {
public:
  using LoadFn = std::function<LoadedSnapshot(const std::string &,
                                              const CompilationContext &)>;
  using ValidateFn = std::function<bool(const ctk::cache::SnapshotEntry &)>;

  explicit FunctionLoader(LoadFn load_fn, ValidateFn validate_fn = {})
      : load_fn_(std::move(load_fn)), validate_fn_(std::move(validate_fn)) {}

  LoadedSnapshot load(const std::string &path,
                      const CompilationContext &context) override {
    ++loads;
    return load_fn_(path, context);
  }
  bool validate(const ctk::cache::SnapshotEntry &snapshot) override {
    ++validations;
    return validate_fn_ ? validate_fn_(snapshot) : true;
  }

  std::atomic<int> loads{0};
  std::atomic<int> validations{0};

private:
  LoadFn load_fn_;
  ValidateFn validate_fn_;
};

LoadedSnapshot loaded(std::vector<InputObservation> inputs = {},
                      std::size_t bytes = 64,
                      std::function<void()> on_destroy = {}) {
  return {std::make_shared<TestOwner>(std::move(on_destroy)), std::move(inputs),
          bytes};
}

bool wait_for_waiting_acquisitions(const SnapshotCache &cache,
                                   std::size_t expected) {
  const auto deadline = std::chrono::steady_clock::now() + 2s;
  while (std::chrono::steady_clock::now() < deadline) {
    if (cache.stats().waiting_acquisitions >= expected)
      return true;
    std::this_thread::yield();
  }
  return cache.stats().waiting_acquisitions >= expected;
}

class LoadGate {
public:
  void wait_until_entered() {
    std::unique_lock lock(mutex_);
    ASSERT_TRUE(cv_.wait_for(lock, 2s, [&] { return entered_; }))
        << "loader did not enter";
  }
  void block() {
    std::unique_lock lock(mutex_);
    entered_ = true;
    cv_.notify_all();
    ASSERT_TRUE(cv_.wait_for(lock, 2s, [&] { return released_; }))
        << "test did not release loader";
  }
  void release() {
    std::lock_guard lock(mutex_);
    released_ = true;
    cv_.notify_all();
  }

private:
  std::mutex mutex_;
  std::condition_variable cv_;
  bool entered_ = false;
  bool released_ = false;
};

TEST(SnapshotCache, DigestCollisionStillComparesFullCompilationContext) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path)});
      });
  ctk::cache::CacheOptions options;
  options.profile_digest = [](std::string_view) { return "forced-collision"; };
  SnapshotCache cache(loader, options);

  auto first_context = context_for();
  auto second_context = first_context;
  second_context.target = "aarch64-unknown-linux-gnu";
  const auto first = cache.acquire("/src/main.cpp", first_context);
  const auto second = cache.acquire("/src/main.cpp", second_context);

  EXPECT_NE(first, second);
  EXPECT_EQ(loader->loads, 2);
}

TEST(SnapshotCache, InvalidatesReverseDependencyOutsideInvalidatedDirectory) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded(
            {file_input(path), file_input("/shared/include/api.hpp")});
      });
  SnapshotCache cache(loader);

  const auto original = cache.acquire("/workspace/app/main.cpp",
                                      context_for("/workspace/app/main.cpp"));
  cache.invalidate_path("/shared/include/api.hpp");
  const auto refreshed = cache.acquire("/workspace/app/main.cpp",
                                       context_for("/workspace/app/main.cpp"));

  EXPECT_NE(original, refreshed);
  EXPECT_EQ(loader->loads, 2);
}

TEST(SnapshotCache, TracksAbsentCandidatesAndDirectoryNamespaces) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path),
                       {"/include/new_header.hpp",
                        InputKind::Absent,
                        {},
                        "/include",
                        std::nullopt},
                       {"/include", InputKind::Directory, "names", "tree", 2}});
      });
  SnapshotCache cache(loader);

  const auto first = cache.acquire("/src/main.cpp", context_for());
  cache.invalidate_path("/include/new_header.hpp");
  const auto after_absent_candidate =
      cache.acquire("/src/main.cpp", context_for());
  cache.invalidate_directory("/include");
  const auto after_directory = cache.acquire("/src/main.cpp", context_for());

  EXPECT_NE(first, after_absent_candidate);
  EXPECT_NE(after_absent_candidate, after_directory);
  EXPECT_EQ(loader->loads, 3);
}

TEST(SnapshotCache, FilesInDirectoryUsesSeparatorBoundaryAndIncludesNamespace) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path)});
      });
  SnapshotCache cache(loader);
  (void)cache.acquire("/src/main.cpp", context_for());
  (void)cache.acquire("/src-old/other.cpp", context_for("/src-old/other.cpp"));
  (void)cache.acquire("/src/nested/other.cpp",
                      context_for("/src/nested/other.cpp"));

  const auto files = cache.files_in_directory("/src");
  std::set<std::string> paths;
  for (const auto &info : files)
    paths.insert(info.path);
  EXPECT_EQ(paths,
            (std::set<std::string>{"/src/main.cpp", "/src/nested/other.cpp"}));
}

TEST(SnapshotCache, SharesOneInFlightAcquisition) {
  auto gate = std::make_shared<LoadGate>();
  auto loader = std::make_shared<FunctionLoader>(
      [gate](const std::string &, const CompilationContext &) {
        gate->block();
        return loaded({file_input("/src/main.cpp")});
      });
  SnapshotCache cache(loader);
  auto context = context_for();
  auto leader = std::async(std::launch::async, [&] {
    return cache.acquire("/src/main.cpp", context);
  });
  gate->wait_until_entered();
  auto waiter = std::async(std::launch::async, [&] {
    return cache.acquire("/src/main.cpp", context);
  });
  ASSERT_TRUE(wait_for_waiting_acquisitions(cache, 1));
  gate->release();

  const auto first = leader.get();
  const auto second = waiter.get();
  EXPECT_EQ(first, second);
  EXPECT_EQ(loader->loads, 1);
}

TEST(SnapshotCache, RevalidatesSharedResultForWaiters) {
  auto validations = std::make_shared<std::atomic<int>>(0);
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path)});
      },
      [validations](const ctk::cache::SnapshotEntry &) {
        return ++*validations != 2;
      });
  SnapshotCache cache(loader);
  auto context = context_for();
  const auto first = cache.acquire("/src/main.cpp", context);
  const auto second = cache.acquire("/src/main.cpp", context);
  EXPECT_NE(first, second);
  EXPECT_EQ(loader->loads, 2);
  EXPECT_EQ(loader->validations, 3);
}

TEST(SnapshotCache, ConcurrentWaiterRevalidatesCompletedCandidate) {
  auto gate = std::make_shared<LoadGate>();
  auto validations = std::make_shared<std::atomic<int>>(0);
  auto loader = std::make_shared<FunctionLoader>(
      [gate](const std::string &path, const CompilationContext &) {
        gate->block();
        return loaded({file_input(path)});
      },
      [validations](const ctk::cache::SnapshotEntry &) {
        return ++*validations != 2;
      });
  SnapshotCache cache(loader);
  auto context = context_for();
  auto leader = std::async(std::launch::async, [&] {
    return cache.acquire("/src/main.cpp", context);
  });
  gate->wait_until_entered();
  auto waiter = std::async(std::launch::async, [&] {
    return cache.acquire("/src/main.cpp", context);
  });
  ASSERT_TRUE(wait_for_waiting_acquisitions(cache, 1));
  gate->release();

  const auto first = leader.get();
  const auto second = waiter.get();
  EXPECT_NE(first, second);
  EXPECT_EQ(loader->loads, 2);
  EXPECT_EQ(loader->validations, 3);
}

TEST(SnapshotCache, LoaderFailureReachesWaitersAndClearsFlight) {
  auto gate = std::make_shared<LoadGate>();
  auto loader = std::make_shared<FunctionLoader>(
      [gate](const std::string &,
             const CompilationContext &) -> LoadedSnapshot {
        gate->block();
        throw std::runtime_error("controlled loader failure");
      });
  SnapshotCache cache(loader);
  auto context = context_for();
  auto leader = std::async(std::launch::async, [&] {
    try {
      (void)cache.acquire("/src/main.cpp", context);
      return std::string{};
    } catch (const std::runtime_error &error) {
      return std::string(error.what());
    }
  });
  gate->wait_until_entered();
  auto waiter = std::async(std::launch::async, [&] {
    try {
      (void)cache.acquire("/src/main.cpp", context);
      return std::string{};
    } catch (const std::runtime_error &error) {
      return std::string(error.what());
    }
  });
  ASSERT_TRUE(wait_for_waiting_acquisitions(cache, 1));
  gate->release();

  EXPECT_EQ(leader.get(), "controlled loader failure");
  EXPECT_EQ(waiter.get(), "controlled loader failure");
  EXPECT_EQ(loader->loads, 1);
  EXPECT_EQ(cache.stats().pending_builds, 0);
}

TEST(SnapshotCache, InvalidationDuringLoadPreventsStalePublication) {
  auto gate = std::make_shared<LoadGate>();
  auto loader = std::make_shared<FunctionLoader>(
      [gate](const std::string &path, const CompilationContext &) {
        gate->block();
        return loaded({file_input(path)});
      });
  ctk::cache::CacheOptions options;
  options.max_acquisition_attempts = 2;
  SnapshotCache cache(loader, options);
  auto context = context_for();
  auto acquire = std::async(std::launch::async, [&] {
    return cache.acquire("/src/main.cpp", context);
  });
  gate->wait_until_entered();
  cache.invalidate_path("/src/main.cpp");
  gate->release();

  const auto result = acquire.get();
  EXPECT_EQ(loader->loads, 2);
  EXPECT_EQ(cache.stats().reusable_snapshots, 1);
  EXPECT_EQ(result->inputs.front().path, "/src/main.cpp");
}

TEST(SnapshotCache, ValidationRunsOutsideMetadataLock) {
  SnapshotCache *cache_ptr = nullptr;
  auto invalidated = std::make_shared<std::atomic<bool>>(false);
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path)});
      },
      [&, invalidated](const ctk::cache::SnapshotEntry &) {
        (void)cache_ptr->stats();
        if (!invalidated->exchange(true))
          cache_ptr->invalidate_path("/src/main.cpp");
        return true;
      });
  SnapshotCache cache(loader);
  cache_ptr = &cache;

  (void)cache.acquire("/src/main.cpp", context_for());
  const auto refreshed = cache.acquire("/src/main.cpp", context_for());
  EXPECT_NE(refreshed, nullptr);
  EXPECT_EQ(loader->loads, 2);
}

TEST(SnapshotCache, NativeOwnerIsDestroyedOutsideMetadataLock) {
  SnapshotCache *cache_ptr = nullptr;
  std::atomic<int> destructions{0};
  auto loader = std::make_shared<FunctionLoader>(
      [&](const std::string &, const CompilationContext &) {
        return loaded({file_input("/src/main.cpp")}, 64, [&] {
          ++destructions;
          (void)cache_ptr->stats();
        });
      });
  SnapshotCache cache(loader);
  cache_ptr = &cache;

  (void)cache.acquire("/src/main.cpp", context_for());
  cache.clear_reuse();
  EXPECT_EQ(destructions, 1);
  EXPECT_EQ(cache.stats().reusable_snapshots, 0);
}

TEST(SnapshotCache, LruEvictionDropsReuseReferenceButKeepsPinnedOwnerAlive) {
  std::weak_ptr<const ctk::cache::NativeSnapshotOwner> first_owner;
  auto loader = std::make_shared<FunctionLoader>(
      [&](const std::string &path, const CompilationContext &) {
        auto value = loaded({file_input(path)});
        if (path == "/src/first.cpp" && first_owner.expired())
          first_owner = value.owner;
        return value;
      });
  ctk::cache::CacheOptions options;
  options.max_snapshots = 1;
  SnapshotCache cache(loader, options);

  auto first = cache.acquire("/src/first.cpp", context_for("/src/first.cpp"));
  (void)cache.acquire("/src/second.cpp", context_for("/src/second.cpp"));
  EXPECT_FALSE(first_owner.expired());
  EXPECT_EQ(cache.stats().reusable_snapshots, 1);
  const auto rebuilt =
      cache.acquire("/src/first.cpp", context_for("/src/first.cpp"));
  EXPECT_NE(first, rebuilt);
  first.reset();
  EXPECT_TRUE(first_owner.expired());
}

TEST(SnapshotCache, EnforcesEstimatedByteAndPerProfileGenerationBudgets) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path)}, 8);
      });
  ctk::cache::CacheOptions options;
  options.max_estimated_bytes = 8;
  options.max_generations_per_profile = 1;
  SnapshotCache cache(loader, options);

  const auto first = cache.acquire("/src/main.cpp", context_for());
  cache.invalidate_path("/src/main.cpp");
  (void)cache.acquire("/src/main.cpp", context_for());
  EXPECT_EQ(cache.stats().estimated_reusable_bytes, 8);
  EXPECT_LE(cache.stats().reusable_snapshots, 1);
  EXPECT_EQ(loader->loads, 2);
  EXPECT_NE(first, nullptr);
}

TEST(SnapshotCache, CancelledWaiterLeavesSharedBuildAvailable) {
  auto gate = std::make_shared<LoadGate>();
  auto loader = std::make_shared<FunctionLoader>(
      [gate](const std::string &path, const CompilationContext &) {
        gate->block();
        return loaded({file_input(path)});
      });
  SnapshotCache cache(loader);
  auto context = context_for();
  auto leader = std::async(std::launch::async, [&] {
    return cache.acquire("/src/main.cpp", context);
  });
  gate->wait_until_entered();
  std::stop_source cancellation;
  auto waiter = std::async(std::launch::async, [&] {
    return cache.acquire("/src/main.cpp", context, cancellation.get_token());
  });
  ASSERT_TRUE(wait_for_waiting_acquisitions(cache, 1));
  cancellation.request_stop();
  EXPECT_THROW((void)waiter.get(), ctk::cache::AcquisitionCancelled);
  gate->release();
  EXPECT_NE(leader.get(), nullptr);
  EXPECT_EQ(loader->loads, 1);
}

TEST(SnapshotCache, CancellationOfLeaderDoesNotDiscardItsCompletedBuild) {
  auto gate = std::make_shared<LoadGate>();
  auto loader = std::make_shared<FunctionLoader>(
      [gate](const std::string &path, const CompilationContext &) {
        gate->block();
        return loaded({file_input(path)});
      });
  SnapshotCache cache(loader);
  auto context = context_for();
  std::stop_source cancellation;
  auto leader = std::async(std::launch::async, [&] {
    return cache.acquire("/src/main.cpp", context, cancellation.get_token());
  });
  gate->wait_until_entered();
  cancellation.request_stop();
  gate->release();

  EXPECT_THROW((void)leader.get(), ctk::cache::AcquisitionCancelled);
  const auto result = cache.acquire("/src/main.cpp", context);
  EXPECT_NE(result, nullptr);
  EXPECT_EQ(loader->loads, 1);
  EXPECT_EQ(cache.stats().reusable_snapshots, 1);
}

TEST(SnapshotCache, FilesAndInputsAreValueSnapshotsWithIndependentLifetime) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path), file_input("/include/api.hpp")});
      });
  std::vector<ctk::cache::FileInfo> file_snapshot;
  std::vector<InputObservation> input_snapshot;
  {
    auto cache = std::make_unique<SnapshotCache>(loader);
    const auto acquired = cache->acquire("/src/main.cpp", context_for());
    file_snapshot = cache->files();
    input_snapshot = acquired->inputs;
  }

  EXPECT_GE(std::ranges::distance(file_snapshot), 2);
  EXPECT_EQ(input_snapshot.size(), 2u);
  EXPECT_TRUE(std::ranges::any_of(input_snapshot, [](const auto &input) {
    return input.path == "/include/api.hpp";
  }));
  EXPECT_TRUE(std::ranges::any_of(file_snapshot, [](const auto &info) {
    return info.path == "/src/main.cpp";
  }));
}

TEST(SnapshotCache, PendingLimitAllowsJoiningFlightButRejectsDifferentBuild) {
  auto gate = std::make_shared<LoadGate>();
  auto loader = std::make_shared<FunctionLoader>(
      [gate](const std::string &path, const CompilationContext &) {
        if (path == "/src/first.cpp")
          gate->block();
        return loaded({file_input(path)});
      });
  ctk::cache::CacheOptions options;
  options.max_pending_builds = 1;
  SnapshotCache cache(loader, options);
  auto first_context = context_for("/src/first.cpp");
  auto leader = std::async(std::launch::async, [&] {
    return cache.acquire("/src/first.cpp", first_context);
  });
  gate->wait_until_entered();
  auto same_flight_waiter = std::async(std::launch::async, [&] {
    return cache.acquire("/src/first.cpp", first_context);
  });
  ASSERT_TRUE(wait_for_waiting_acquisitions(cache, 1));

  EXPECT_THROW(cache.acquire("/src/other.cpp", context_for("/src/other.cpp")),
               ctk::cache::ResourceExhausted);
  gate->release();
  EXPECT_EQ(leader.get(), same_flight_waiter.get());
  EXPECT_EQ(loader->loads, 1);
}

TEST(SnapshotCache,
     NonReusableAndZeroCapacityBuildsKeepMetadataButAreEphemeral) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path), file_input("/include/api.hpp")});
      });
  ctk::cache::CacheOptions options;
  options.max_snapshots = 0;
  SnapshotCache cache(loader, options);
  auto context = context_for();
  context.reusable = false;

  const auto first = cache.acquire("/src/main.cpp", context);
  const auto second = cache.acquire("/src/main.cpp", context);
  const auto metadata = cache.files();

  EXPECT_NE(first, second);
  EXPECT_EQ(cache.stats().reusable_snapshots, 0);
  EXPECT_EQ(loader->loads, 2);
  EXPECT_TRUE(std::ranges::any_of(
      metadata, [](const auto &file) { return file.path == "/src/main.cpp"; }));
  EXPECT_TRUE(std::ranges::any_of(metadata, [](const auto &file) {
    return file.path == "/include/api.hpp";
  }));
}

TEST(SnapshotCache, InvalidColdSnapshotsExhaustAttemptsWithoutPublishing) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path)});
      },
      [](const ctk::cache::SnapshotEntry &) { return false; });
  ctk::cache::CacheOptions options;
  options.max_acquisition_attempts = 3;
  SnapshotCache cache(loader, options);

  EXPECT_THROW(cache.acquire("/src/main.cpp", context_for()),
               std::runtime_error);
  EXPECT_EQ(loader->loads, 3);
  EXPECT_EQ(loader->validations, 3);
  EXPECT_EQ(cache.stats().reusable_snapshots, 0);
  EXPECT_EQ(cache.stats().pending_builds, 0);
}

TEST(SnapshotCache, UnknownPathInvalidationDuringLoadFencesPublication) {
  auto gate = std::make_shared<LoadGate>();
  auto loader = std::make_shared<FunctionLoader>(
      [gate](const std::string &path, const CompilationContext &) {
        gate->block();
        return loaded({file_input(path)});
      });
  SnapshotCache cache(loader);
  auto acquire = std::async(std::launch::async, [&] {
    return cache.acquire("/src/main.cpp", context_for());
  });
  gate->wait_until_entered();
  cache.invalidate_path("/newly-observed/header.hpp");
  gate->release();

  EXPECT_NE(acquire.get(), nullptr);
  EXPECT_EQ(loader->loads, 2);
  EXPECT_EQ(cache.stats().reusable_snapshots, 1);
}

TEST(SnapshotCache, InvalidationDuringWarmValidationRechecksBeforeReuse) {
  auto gate = std::make_shared<LoadGate>();
  auto validations = std::make_shared<std::atomic<int>>(0);
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path)});
      },
      [gate, validations](const ctk::cache::SnapshotEntry &) {
        if (++*validations == 2)
          gate->block();
        return true;
      });
  SnapshotCache cache(loader);
  const auto original = cache.acquire("/src/main.cpp", context_for());
  auto warm_acquire = std::async(std::launch::async, [&] {
    return cache.acquire("/src/main.cpp", context_for());
  });
  gate->wait_until_entered();
  cache.invalidate_path("/src/main.cpp");
  gate->release();

  const auto refreshed = warm_acquire.get();
  EXPECT_NE(original, refreshed);
  EXPECT_EQ(loader->loads, 2);
}

TEST(SnapshotCache, PathChangeInvalidatesParentNamespaceDependents) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path),
                       {"/src", InputKind::Directory, "names", "tree", 1}});
      });
  SnapshotCache cache(loader);
  const auto original = cache.acquire("/src/main.cpp", context_for());

  cache.notify_path_change("/src/new_header.hpp");
  const auto refreshed = cache.acquire("/src/main.cpp", context_for());
  EXPECT_NE(original, refreshed);
  EXPECT_EQ(loader->loads, 2);
}

TEST(SnapshotCache, CacheHitTouchesLruBeforeTheNextEviction) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path)});
      });
  ctk::cache::CacheOptions options;
  options.max_snapshots = 2;
  SnapshotCache cache(loader, options);

  (void)cache.acquire("/src/a.cpp", context_for("/src/a.cpp"));
  (void)cache.acquire("/src/b.cpp", context_for("/src/b.cpp"));
  (void)cache.acquire("/src/a.cpp", context_for("/src/a.cpp"));
  (void)cache.acquire("/src/c.cpp", context_for("/src/c.cpp"));
  (void)cache.acquire("/src/a.cpp", context_for("/src/a.cpp"));
  EXPECT_EQ(loader->loads, 3);
  (void)cache.acquire("/src/b.cpp", context_for("/src/b.cpp"));
  EXPECT_EQ(loader->loads, 4);
}

TEST(SnapshotCache, EvictionDestroysNativeOwnerOutsideMetadataLock) {
  SnapshotCache *cache_ptr = nullptr;
  std::atomic<int> first_owner_destructions{0};
  auto loader = std::make_shared<FunctionLoader>(
      [&](const std::string &path, const CompilationContext &) {
        auto on_destroy = [&, path] {
          if (path == "/src/a.cpp") {
            ++first_owner_destructions;
            (void)cache_ptr->stats();
          }
        };
        return loaded({file_input(path)}, 64, std::move(on_destroy));
      });
  ctk::cache::CacheOptions options;
  options.max_snapshots = 1;
  SnapshotCache cache(loader, options);
  cache_ptr = &cache;

  (void)cache.acquire("/src/a.cpp", context_for("/src/a.cpp"));
  EXPECT_EQ(first_owner_destructions, 0);
  (void)cache.acquire("/src/b.cpp", context_for("/src/b.cpp"));
  EXPECT_EQ(first_owner_destructions, 1);
  EXPECT_EQ(cache.stats().reusable_snapshots, 1);
}

TEST(SnapshotCache, MetadataEraseWaitsForProfilesAndReverseLinksButNotPins) {
  auto gate = std::make_shared<LoadGate>();
  auto loader = std::make_shared<FunctionLoader>(
      [gate](const std::string &path, const CompilationContext &) {
        gate->block();
        return loaded({file_input(path), file_input("/include/api.hpp")});
      });
  SnapshotCache cache(loader);
  auto acquired = std::async(std::launch::async, [&] {
    return cache.acquire("/src/main.cpp", context_for());
  });
  gate->wait_until_entered();
  EXPECT_FALSE(cache.erase_unused_path("/src/main.cpp"));
  gate->release();
  const auto pinned = acquired.get();

  EXPECT_FALSE(cache.erase_unused_path("/src/main.cpp"));
  EXPECT_FALSE(cache.erase_unused_path("/include/api.hpp"));
  cache.clear_reuse();
  EXPECT_TRUE(cache.erase_unused_path("/src/main.cpp"));
  EXPECT_TRUE(cache.erase_unused_path("/include/api.hpp"));
  EXPECT_EQ(pinned->inputs.size(), 2u);
  EXPECT_NE(pinned->owner, nullptr);
}

TEST(SnapshotCache, UnknownPathChangeInvalidatesKnownNamespaceAtPathCapacity) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path),
                       {"/include", InputKind::Directory, "names", "tree", 1}});
      });
  ctk::cache::CacheOptions options;
  options.max_paths = 2;
  SnapshotCache cache(loader, options);
  const auto original = cache.acquire("/src/main.cpp", context_for());
  ASSERT_EQ(cache.stats().paths, 2u);

  cache.notify_path_change("/include/new.hpp");
  const auto refreshed = cache.acquire("/src/main.cpp", context_for());
  EXPECT_NE(original, refreshed);
  EXPECT_EQ(loader->loads, 2);
  EXPECT_EQ(cache.stats().paths, 2u);
}

TEST(SnapshotCache,
     DirectoryInvalidationFindsDescendantsWhenPathCapacityIsFull) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path)});
      });
  ctk::cache::CacheOptions options;
  options.max_paths = 1;
  SnapshotCache cache(loader, options);
  const auto original = cache.acquire("/src/main.cpp", context_for());
  ASSERT_EQ(cache.stats().paths, 1u);

  cache.invalidate_directory("/src");
  const auto refreshed = cache.acquire("/src/main.cpp", context_for());
  EXPECT_NE(original, refreshed);
  EXPECT_EQ(loader->loads, 2);
  EXPECT_EQ(cache.stats().paths, 1u);
}

TEST(SnapshotCache,
     PerFileProfileAndPathLimitsRejectNewEntriesWithoutBreakingOldOnes) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path)});
      });
  ctk::cache::CacheOptions options;
  options.max_paths = 1;
  options.max_profiles_per_file = 1;
  SnapshotCache cache(loader, options);
  const auto original = cache.acquire("/src/main.cpp", context_for());

  auto other_profile = context_for();
  other_profile.target = "aarch64-unknown-linux-gnu";
  EXPECT_THROW(cache.acquire("/src/main.cpp", other_profile),
               ctk::cache::ResourceExhausted);
  EXPECT_THROW(cache.acquire("/src/other.cpp", context_for("/src/other.cpp")),
               ctk::cache::ResourceExhausted);
  EXPECT_EQ(cache.acquire("/src/main.cpp", context_for()), original);
  EXPECT_EQ(loader->loads, 1);
  EXPECT_EQ(cache.stats().paths, 1u);
}

TEST(SnapshotCache,
     UnrelatedInvalidationDuringWarmValidationKeepsReusableCandidate) {
  SnapshotCache *cache_ptr = nullptr;
  auto validations = std::make_shared<std::atomic<int>>(0);
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        return loaded({file_input(path)});
      },
      [&, validations](const ctk::cache::SnapshotEntry &) {
        const auto call = ++*validations;
        if (call == 2)
          cache_ptr->invalidate_path("/unrelated/header.hpp");
        return true;
      });
  SnapshotCache cache(loader);
  cache_ptr = &cache;
  const auto original = cache.acquire("/src/main.cpp", context_for());
  const auto warm = cache.acquire("/src/main.cpp", context_for());

  EXPECT_EQ(warm, original);
  EXPECT_EQ(loader->loads, 1);
  EXPECT_EQ(loader->validations, 2);
}

} // namespace

TEST(SnapshotCache, LoaderCanReturnFreshNonReusableSnapshotWithoutRetention) {
  auto loader = std::make_shared<FunctionLoader>(
      [](const std::string &path, const CompilationContext &) {
        auto result = loaded({file_input(path)});
        result.reusable = false;
        return result;
      });
  SnapshotCache cache(loader);
  auto context = context_for();
  const auto first = cache.acquire("/src/unsafe.cpp", context);
  const auto second = cache.acquire("/src/unsafe.cpp", context);
  EXPECT_FALSE(first->reusable);
  EXPECT_FALSE(second->reusable);
  EXPECT_NE(first, second);
  EXPECT_EQ(loader->loads, 2);
}
