#include "../src/net/include_inventory_cache.hpp"
#include "ctk/application/operation_executor.hpp"
#include "ctk/cache/include_inventory.hpp"
#include "ctk/platform/index_worker.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <future>
#include <gtest/gtest.h>
#include <sys/wait.h>
#include <thread>

namespace ctk::platform {
namespace {
namespace fs = std::filesystem;
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
