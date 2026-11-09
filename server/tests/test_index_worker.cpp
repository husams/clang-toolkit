#include "../src/net/include_inventory_cache.hpp"
#include "ctk/application/operation_executor.hpp"
#include "ctk/cache/include_inventory.hpp"
#include "ctk/platform/index_worker.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include <cerrno>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <future>
#include <gtest/gtest.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <system_error>
#include <thread>
#include <unistd.h>
#include <vector>

namespace ctk::platform {
namespace {
namespace fs = std::filesystem;

TEST(IndexWorkerParallelism, ReservesForegroundCpusWithoutFixedWorkerCap) {
  constexpr std::uint64_t memory = 32ULL * 1024 * 1024 * 1024;
  EXPECT_EQ(index_worker_detail::parallelism_limit(10, memory), 8u);
  EXPECT_EQ(index_worker_detail::parallelism_limit(3, memory), 1u);
  EXPECT_EQ(index_worker_detail::parallelism_limit(2, memory), 1u);
}

TEST(IndexWorkerParallelism, ReducesConcurrencyForConstrainedMemory) {
  EXPECT_EQ(
      index_worker_detail::parallelism_limit(16, 8ULL * 1024 * 1024 * 1024),
      1u);
  EXPECT_EQ(
      index_worker_detail::parallelism_limit(16, 12ULL * 1024 * 1024 * 1024),
      3u);
}

TEST(IndexWorkerParallelism, UnknownResourcesFailClosedToOneWorker) {
  EXPECT_EQ(
      index_worker_detail::parallelism_limit(0, 32ULL * 1024 * 1024 * 1024),
      1u);
  EXPECT_EQ(index_worker_detail::parallelism_limit(10, 0), 1u);
}

TEST(IndexWorkerParallelism, ParsesCgroupMemoryLimits) {
  EXPECT_EQ(index_worker_detail::parse_memory_limit("2147483648"),
            2147483648ULL);
  const auto small_memory =
      index_worker_detail::parse_memory_limit("1073741824");
  ASSERT_TRUE(small_memory);
  EXPECT_EQ(index_worker_detail::parallelism_limit(10, *small_memory), 1u);
  EXPECT_FALSE(index_worker_detail::parse_memory_limit("max"));
  EXPECT_FALSE(index_worker_detail::parse_memory_limit("not-a-limit"));
}

TEST(IndexWorkerParallelism, ParsesFractionalCpuQuotaAndReservesTwoCpus) {
  const auto quota = index_worker_detail::parse_cpu_quota("550000 100000");
  ASSERT_TRUE(quota);
  EXPECT_EQ(*quota, 5u);
  EXPECT_EQ(index_worker_detail::parallelism_limit(*quota,
                                                   32ULL * 1024 * 1024 * 1024),
            3u);
  EXPECT_FALSE(index_worker_detail::parse_cpu_quota("max 100000"));
  EXPECT_FALSE(index_worker_detail::parse_cpu_quota("broken"));
}

TEST(IndexWorkerParallelism, PreservesFullCgroupV2CpuLimitLine) {
  const auto value =
      index_worker_detail::cgroup_limit_line("  400000 100000\n");
  EXPECT_EQ(value, "400000 100000");
  EXPECT_EQ(index_worker_detail::parse_cpu_quota(value), 4u);
  EXPECT_EQ(index_worker_detail::cgroup_limit_line("max 100000\n"),
            "max 100000");
}

TEST(IndexWorkerParallelism, MissingLimitsAreUnlimitedOnlyAtV2MountRoot) {
  EXPECT_TRUE(
      index_worker_detail::missing_cgroup_limit_is_unlimited(true, true));
  EXPECT_FALSE(
      index_worker_detail::missing_cgroup_limit_is_unlimited(true, false));
  EXPECT_FALSE(
      index_worker_detail::missing_cgroup_limit_is_unlimited(false, true));
}

TEST(IndexWorkerParallelism, ReadsMinimumOfAllV2AncestorLimits) {
  TemporaryDirectory temporary{"ctk-cgroup-v2-policy"};
  const auto mount = temporary.path() / "v2";
  fs::create_directories(mount / "child");
  std::ofstream(mount / "memory.max") << 12ULL * 1024 * 1024 * 1024;
  std::ofstream(mount / "child" / "memory.max") << 20ULL * 1024 * 1024 * 1024;
  std::ofstream(mount / "cpu.max") << "600000 100000\n";
  std::ofstream(mount / "child" / "cpu.max") << "400000 100000\n";
  const std::string membership = "0::/child\n";
  const std::string mounts =
      "29 23 0:25 / " + mount.string() + " rw - cgroup2 cgroup rw\n";
  EXPECT_EQ(index_worker_detail::cgroup_parallelism_limit(
                10, 32ULL * 1024 * 1024 * 1024, membership, mounts),
            2u);
}

TEST(IndexWorkerParallelism, HybridUnlimitedV2RootStillHonorsV1Memory) {
  TemporaryDirectory temporary{"ctk-cgroup-hybrid-policy"};
  const auto v2 = temporary.path() / "v2";
  const auto v1 = temporary.path() / "v1-memory";
  fs::create_directories(v2 / "child");
  fs::create_directories(v1 / "legacy");
  std::ofstream(v2 / "child" / "memory.max") << "max\n";
  std::ofstream(v2 / "child" / "cpu.max") << "max 100000\n";
  std::ofstream(v1 / "memory.limit_in_bytes") << 12ULL * 1024 * 1024 * 1024;
  std::ofstream(v1 / "legacy" / "memory.limit_in_bytes")
      << 20ULL * 1024 * 1024 * 1024;
  const std::string membership = "0::/child\n5:memory:/legacy\n";
  const std::string mounts = "29 23 0:25 / " + v2.string() +
                             " rw - cgroup2 cgroup rw\n" + "30 23 0:26 / " +
                             v1.string() + " rw - cgroup cgroup rw,memory\n";
  EXPECT_EQ(index_worker_detail::cgroup_parallelism_limit(
                10, 32ULL * 1024 * 1024 * 1024, membership, mounts),
            3u);
}

TEST(IndexWorkerParallelism, MissingCgroupLeafLimitFailsClosed) {
  TemporaryDirectory temporary{"ctk-cgroup-missing-leaf"};
  const auto mount = temporary.path() / "v2";
  fs::create_directories(mount / "child");
  std::ofstream(mount / "memory.max") << "max\n";
  std::ofstream(mount / "cpu.max") << "max 100000\n";
  std::ofstream(mount / "child" / "cpu.max") << "400000 100000\n";
  const std::string membership = "0::/child\n";
  const std::string mounts =
      "29 23 0:25 / " + mount.string() + " rw - cgroup2 cgroup rw\n";
  EXPECT_EQ(index_worker_detail::cgroup_parallelism_limit(
                10, 32ULL * 1024 * 1024 * 1024, membership, mounts),
            1u);
}

TEST(IndexWorkerParallelism, ReadsMinimumOfAllV1CpuAncestorQuotas) {
  TemporaryDirectory temporary{"ctk-cgroup-v1-cpu-policy"};
  const auto mount = temporary.path() / "v1-cpu";
  fs::create_directories(mount / "legacy");
  std::ofstream(mount / "cpu.cfs_quota_us") << 800000;
  std::ofstream(mount / "cpu.cfs_period_us") << 100000;
  std::ofstream(mount / "legacy" / "cpu.cfs_quota_us") << 500000;
  std::ofstream(mount / "legacy" / "cpu.cfs_period_us") << 100000;
  const auto memory = 32ULL * 1024 * 1024 * 1024;
  const auto v1_memory = temporary.path() / "v1-memory";
  fs::create_directories(v1_memory / "legacy");
  std::ofstream(v1_memory / "memory.limit_in_bytes") << memory;
  std::ofstream(v1_memory / "legacy" / "memory.limit_in_bytes") << memory;
  const std::string membership = "5:cpu,cpuacct:/legacy\n6:memory:/legacy\n";
  const std::string mounts = "29 23 0:25 / " + mount.string() +
                             " rw - cgroup cgroup rw,cpu,cpuacct\n" +
                             "30 23 0:26 / " + v1_memory.string() +
                             " rw - cgroup cgroup rw,memory\n";
  EXPECT_EQ(index_worker_detail::cgroup_parallelism_limit(10, memory,
                                                          membership, mounts),
            3u);
}

class IndexWorkerProcess : public ::testing::Test {
protected:
  std::filesystem::path root;
  void SetUp() override {
    root = std::filesystem::temp_directory_path() /
           ("ctk-index-worker-test-" +
            std::to_string(
                std::chrono::steady_clock::now().time_since_epoch().count()));
    std::filesystem::create_directory(root);
  }
  void TearDown() override { std::filesystem::remove_all(root); }
  std::filesystem::path script(const char *text) {
    const auto path = root / "worker";
    {
      std::ofstream output(path);
      output << "#!/bin/sh\n" << text;
    }
    std::filesystem::permissions(path, std::filesystem::perms::owner_all);
    return path;
  }
};

TEST_F(IndexWorkerProcess, PrioritySetupPreservesResourceLimitsAndLargeFiles) {
  const auto output = root / "large-result";
  const auto child = fork();
  ASSERT_GE(child, 0);
  if (child == 0) {
    const int resources[] = {RLIMIT_CPU, RLIMIT_FSIZE, RLIMIT_AS};
    rlimit before[3]{};
    for (int i = 0; i < 3; ++i)
      if (getrlimit(resources[i], &before[i]))
        _exit(1);
    try {
      lower_index_worker_priority();
    } catch (const std::system_error &error) {
      if (error.code().value() == EPERM || error.code().value() == EACCES)
        _exit(77);
      _exit(2);
    }
    for (int i = 0; i < 3; ++i) {
      rlimit after{};
      if (getrlimit(resources[i], &after) ||
          before[i].rlim_cur != after.rlim_cur ||
          before[i].rlim_max != after.rlim_max)
        _exit(3);
    }
    // A sparse file crosses the former cap without allocating 128 MiB.
    constexpr auto size = 128ULL * 1024 * 1024 + 1;
    if (before[1].rlim_cur == RLIM_INFINITY || before[1].rlim_cur >= size) {
      std::ofstream(output).close();
      std::error_code error;
      fs::resize_file(output, size, error);
      if (error)
        _exit(4);
    }
    _exit(0);
  }
  int status = 0;
  ASSERT_EQ(waitpid(child, &status, 0), child);
  ASSERT_TRUE(WIFEXITED(status));
  if (WEXITSTATUS(status) == 77)
    GTEST_SKIP() << "Process priority changes are denied by this environment";
  EXPECT_EQ(WEXITSTATUS(status), 0);
}

TEST_F(IndexWorkerProcess, PreservesWorkerStderrForStartupDiagnostics) {
  testing::internal::CaptureStderr();
  IndexWorker worker(script("echo 'worker startup diagnostic' >&2\nexit 7\n"),
                     root / "request", root / "result");
  std::optional<int> result;
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(5);
  while (!(result = worker.poll()) &&
         std::chrono::steady_clock::now() < deadline)
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  worker.stop();
  const auto diagnostic = testing::internal::GetCapturedStderr();
  ASSERT_TRUE(result);
  EXPECT_EQ(*result, 7);
  EXPECT_NE(diagnostic.find("worker startup diagnostic"), std::string::npos);
}

TEST_F(IndexWorkerProcess, ReturnsExitStatusAndReapsCompletedProcess) {
  IndexWorker worker(script("exit 7\n"), root / "request", root / "result");
  std::optional<int> result;
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(5);
  while (!(result = worker.poll()) &&
         std::chrono::steady_clock::now() < deadline)
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  ASSERT_TRUE(result);
  EXPECT_EQ(*result, 7);
  EXPECT_FALSE(worker.running());
}

TEST_F(IndexWorkerProcess, SuspendCachesAlreadyCompletedWorkersForOnePoll) {
  const auto pid_file = root / "worker.pid";
  IndexWorker worker(script("printf '%s' \"$$\" > \"$4\"\nexit 7\n"),
                     root / "request", pid_file);
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(5);
  int pid = -1;
  while (pid <= 0 && std::chrono::steady_clock::now() < deadline) {
    std::ifstream pid_input(pid_file);
    pid_input >> pid;
    if (pid <= 0)
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
  ASSERT_GT(pid, 0);

  siginfo_t information{};
  int wait_result = 0;
  do {
    wait_result = waitid(P_PID, static_cast<id_t>(pid), &information,
                         WEXITED | WNOHANG | WNOWAIT);
    ASSERT_EQ(wait_result, 0);
    if (!information.si_pid)
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
  } while (!information.si_pid && std::chrono::steady_clock::now() < deadline);
  ASSERT_EQ(information.si_pid, pid);

  worker.suspend();
  worker.resume();
  EXPECT_FALSE(worker.running());
  const auto status = worker.poll();
  ASSERT_TRUE(status);
  EXPECT_EQ(*status, 7);
  EXPECT_FALSE(worker.poll());
}

TEST_F(IndexWorkerProcess, RapidSuspendResumePreservesImmediateExitStatus) {
  for (int attempt = 0; attempt < 32; ++attempt) {
    IndexWorker worker(script("exit 7\n"), root / "request", root / "result");
    worker.suspend();
    worker.resume();

    std::optional<int> status;
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(2);
    while (!(status = worker.poll()) &&
           std::chrono::steady_clock::now() < deadline)
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    ASSERT_TRUE(status) << "attempt " << attempt;
    EXPECT_EQ(*status, 7) << "attempt " << attempt;
    EXPECT_FALSE(worker.running());
  }
}

TEST_F(IndexWorkerProcess, StopKillsAndReapsIsolatedExtraction) {
  IndexWorker worker(script("exec sleep 60\n"), root / "request",
                     root / "result");
  EXPECT_TRUE(worker.running());
  worker.stop();
  EXPECT_FALSE(worker.running());
  EXPECT_FALSE(worker.poll());
  worker.stop();
}

TEST_F(IndexWorkerProcess, MissingExecutableFailsWithoutLeavingRunningWorker) {
  IndexWorker worker;
  EXPECT_THROW(
      worker.start(root / "missing", root / "request", root / "result"),
      std::system_error);
  EXPECT_FALSE(worker.running());
}

TEST_F(IndexWorkerProcess, SuspendedProcessResumesItsExistingExtraction) {
  IndexWorker worker(script("while [ ! -f \"$2\" ]; do sleep 0.01; done\n"
                            "printf completed > \"$4\"\n"),
                     root / "request", root / "result");
  worker.suspend();
  std::this_thread::sleep_for(std::chrono::milliseconds(100));
  std::ofstream(root / "request") << "ready";
  std::this_thread::sleep_for(std::chrono::milliseconds(100));
  EXPECT_FALSE(fs::exists(root / "result"));
  EXPECT_FALSE(worker.poll());
  worker.resume();
  std::optional<int> result;
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(5);
  while (!(result = worker.poll()) &&
         std::chrono::steady_clock::now() < deadline)
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  ASSERT_TRUE(result);
  EXPECT_EQ(*result, 0);
  EXPECT_TRUE(fs::exists(root / "result"));
  worker.suspend();
  worker.resume();
}

TEST_F(IndexWorkerProcess, StopReapsSuspendedProcessGroup) {
  IndexWorker worker(script("sleep 60 &\nwait\n"), root / "request",
                     root / "result");
  worker.suspend();
  worker.stop();
  EXPECT_FALSE(worker.running());
  EXPECT_FALSE(worker.poll());
}

TEST_F(IndexWorkerProcess,
       IncludeInventoryMatchesCanonicalWalkAcrossSymlinkAliases) {
  namespace fs = std::filesystem;
  fs::create_directories(root / "real" / "nested");
  std::ofstream(root / "real" / "nested" / "header.hpp") << "int header;";
  fs::create_directory_symlink(root / "real", root / "alias");
  fs::create_directory_symlink(root, root / "real" / "nested" / "cycle");
  fs::create_directory_symlink(root / "real" / "nested", root / "other");
  std::vector<std::string> names;
  std::set<fs::path> visited{fs::weakly_canonical(root)};
  for (fs::recursive_directory_iterator
           it(root, fs::directory_options::follow_directory_symlink),
       end;
       it != end; ++it) {
    names.push_back(it->path().lexically_relative(root).generic_string());
    if (it->is_symlink())
      names.push_back(std::string("\0symlink\0", 9) + names.back() + '\0' +
                      fs::read_symlink(it->path()).generic_string());
    if (it->is_directory() &&
        !visited.insert(fs::weakly_canonical(it->path())).second)
      it.disable_recursion_pending();
  }
  std::sort(names.begin(), names.end());
  std::string expected;
  for (const auto &name : names)
    expected += std::to_string(name.size()) + ':' + name;
  EXPECT_EQ(cache::include_inventory(root), expected);
}

TEST_F(IndexWorkerProcess,
       IncludeInventoryDetectsNewHeadersAndStopsSymlinkCycles) {
  const auto before = cache::include_inventory(root);
  {
    std::ofstream output(root / "new.hpp");
    output << "int header;";
  }
  const auto after = cache::include_inventory(root);
  EXPECT_NE(before, after);
  {
    std::ofstream output(root / "new.hpp");
    output << "int changed;";
  }
  EXPECT_EQ(after, cache::include_inventory(root));
  std::filesystem::create_directory_symlink(root, root / "cycle");
  EXPECT_FALSE(cache::include_inventory(root).empty());
}

TEST(IndexForegroundAdmission, CountsRunningWorkWhileThePendingQueueIsEmpty) {
  auto executor = application::make_operation_executor(1, 2);
  std::promise<void> started, release, finished;
  auto released = release.get_future().share();
  ASSERT_TRUE(executor->enqueue([&] {
    started.set_value();
    released.wait();
    finished.set_value();
  }));
  const auto state = started.get_future().wait_for(std::chrono::seconds(5));
  EXPECT_EQ(state, std::future_status::ready);
  EXPECT_EQ(executor->pending_count(), 0);
  EXPECT_EQ(executor->active_count(), 1);
  release.set_value();
  EXPECT_EQ(finished.get_future().wait_for(std::chrono::seconds(5)),
            std::future_status::ready);
}

TEST_F(IndexWorkerProcess, DirectoryInventoryReuseDetectsPreservedTimeEdits) {
  fs::create_directories(root / "nested");
  std::ofstream(root / "nested" / "first.hpp") << "int first;";
  net::index_detail::IncludeInventoryCache inventories;
  unsigned scans = 0;
  const auto allowed = [&] {
    ++scans;
    return true;
  };
  const auto before = inventories.digest(root, allowed);
  ASSERT_FALSE(before.empty());
  scans = 0;
  EXPECT_EQ(inventories.digest(root, allowed), before);
  if (scans)
    GTEST_SKIP()
        << "Directory notifications unavailable; full-scan fallback used";
  const auto time = fs::last_write_time(root / "nested");
  std::ofstream(root / "nested" / "new.hpp") << "int newHeader;";
  fs::last_write_time(root / "nested", time);
  EXPECT_NE(inventories.digest(root, allowed), before);
  EXPECT_GT(scans, 0u);
  fs::remove(root / "nested" / "new.hpp");
  fs::last_write_time(root / "nested", time);
  EXPECT_EQ(inventories.digest(root), before);
}

TEST_F(IndexWorkerProcess,
       DirectoryInventoryTracksAliasedDirectoriesAndRetargets) {
  fs::create_directories(root / "one");
  fs::create_directories(root / "two");
  std::ofstream(root / "one" / "value.hpp") << "int one;";
  std::ofstream(root / "two" / "value.hpp") << "int two;";
  fs::create_directory_symlink(root / "one", root / "alias");
  net::index_detail::IncludeInventoryCache inventories;
  const auto before = inventories.digest(root);
  fs::remove(root / "alias");
  fs::create_directory_symlink(root / "two", root / "alias");
  EXPECT_NE(inventories.digest(root), before);
  const auto alias = inventories.digest(root / "alias");
  std::ofstream(root / "two" / "added.hpp") << "int added;";
  EXPECT_NE(inventories.digest(root / "alias"), alias);
  fs::create_symlink(root / "one" / "value.hpp", root / "header.hpp");
  const auto linked = inventories.digest(root);
  fs::remove(root / "header.hpp");
  fs::create_symlink(root / "two" / "value.hpp", root / "header.hpp");
  EXPECT_NE(inventories.digest(root), linked);
}

TEST_F(IndexWorkerProcess,
       DirectoryInventoryDoesNotCacheMissingOrReplacedRoots) {
  net::index_detail::IncludeInventoryCache inventories;
  const auto missing = inventories.digest(root / "include");
  fs::create_directory(root / "include");
  std::ofstream(root / "include" / "value.hpp") << "int value;";
  const auto existing = inventories.digest(root / "include");
  EXPECT_NE(existing, missing);
  fs::rename(root / "include", root / "old");
  fs::create_directory(root / "include");
  EXPECT_NE(inventories.digest(root / "include"), existing);
}

TEST_F(IndexWorkerProcess, DirectoryInventoryRefreshInvalidatesOnNewShadow) {
  const auto include = root / "include";
  fs::create_directories(include);
  std::ofstream(include / "base.hpp") << "int base;";
  net::index_detail::IncludeInventoryCache inventories;
  const auto before = inventories.digest(include);
  ASSERT_FALSE(before.empty());
  const auto generation = inventories.generation();

  std::ofstream(include / "shadow.hpp") << "int shadow;";
  bool refreshed = false;
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(2);
  while (!refreshed && std::chrono::steady_clock::now() < deadline) {
    refreshed = inventories.refresh();
    if (!refreshed)
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  if (!refreshed)
    GTEST_SKIP() << "Directory notifications unavailable for this filesystem";

  EXPECT_GT(inventories.generation(), generation);
  const auto after = inventories.digest(include);
  EXPECT_NE(after, before);
  EXPECT_EQ(after,
            net::index_detail::digest_text(cache::include_inventory(include)));
}

TEST_F(IndexWorkerProcess,
       DirectoryInventoryCapacityUsesUncachedFallbackWithoutInvalidation) {
  std::vector<fs::path> roots;
  for (unsigned i = 0; i < 129; ++i) {
    const auto path = root / ("include-" + std::to_string(i));
    fs::create_directories(path);
    std::ofstream(path / "value.hpp") << "int value;";
    roots.push_back(path);
  }

  net::index_detail::IncludeInventoryCache inventories;
  const auto generation = inventories.generation();
  for (const auto &path : roots)
    EXPECT_EQ(inventories.digest(path),
              net::index_detail::digest_text(cache::include_inventory(path)));
  EXPECT_EQ(inventories.generation(), generation);

  unsigned cached_scans = 0;
  inventories.digest(roots.front(), [&] {
    ++cached_scans;
    return true;
  });
  if (cached_scans != 0)
    GTEST_SKIP() << "Directory notifications unavailable; "
                    "cache uses full scans";

  unsigned overflow_scans = 0;
  inventories.digest(roots.back(), [&] {
    ++overflow_scans;
    return true;
  });
  EXPECT_GT(overflow_scans, 0u);
  EXPECT_EQ(inventories.generation(), generation);
  EXPECT_FALSE(inventories.refresh());
  EXPECT_EQ(inventories.generation(), generation);
}

TEST_F(IndexWorkerProcess,
       DirectoryInventoryRetriesChangesDuringItsInitialWalk) {
  std::ofstream(root / "first.hpp") << "int first;";
  net::index_detail::IncludeInventoryCache inventories;
  bool edited = false;
  const auto digest = inventories.digest(root, [&] {
    if (!edited) {
      edited = true;
      std::ofstream(root / "second.hpp") << "int second;";
    }
    return true;
  });
  EXPECT_TRUE(edited);
  EXPECT_EQ(digest,
            net::index_detail::digest_text(cache::include_inventory(root)));
}

TEST_F(IndexWorkerProcess, DirectoryInventoryTracksExternalSymlinkChains) {
  TemporaryDirectory outside{"ctk-inventory-outside"};
  fs::create_directories(outside.path() / "one" / "nested");
  fs::create_directories(outside.path() / "two" / "nested");
  std::ofstream(outside.path() / "one" / "nested" / "one.hpp") << "int one;";
  std::ofstream(outside.path() / "two" / "nested" / "two.hpp") << "int two;";
  fs::create_directory_symlink(outside.path() / "one", outside.path() / "link");
  fs::create_directory_symlink(outside.path() / "link" / "nested",
                               root / "alias");
  net::index_detail::IncludeInventoryCache inventories;
  const auto before = inventories.digest(root);
  const auto stamp = fs::last_write_time(outside.path());
  fs::remove(outside.path() / "link");
  fs::create_directory_symlink(outside.path() / "two", outside.path() / "link");
  fs::last_write_time(outside.path(), stamp);
  const auto after = inventories.digest(root);
  EXPECT_NE(after, before);
  EXPECT_EQ(after,
            net::index_detail::digest_text(cache::include_inventory(root)));
  fs::remove(outside.path() / "link");
  fs::create_directory_symlink(outside.path() / "one", outside.path() / "link");
  const auto restored = inventories.digest(root);
  fs::rename(outside.path() / "one", outside.path() / "old");
  fs::rename(outside.path() / "two", outside.path() / "one");
  EXPECT_NE(inventories.digest(root), restored);
}
} // namespace
} // namespace ctk::platform
