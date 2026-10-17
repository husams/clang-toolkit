#include "ctk/application/operation_executor.hpp"
#include "ctk/cache/include_inventory.hpp"
#include "ctk/platform/index_worker.hpp"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <future>
#include <gtest/gtest.h>
#include <thread>

namespace ctk::platform {
namespace {
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
} // namespace
} // namespace ctk::platform
