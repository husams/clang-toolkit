#include "../src/platform/index_filesystem.hpp"
#include "../src/platform/index_input_watch.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include <gtest/gtest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <thread>

namespace fs = std::filesystem;
using ctk::platform::IndexInputWatch;
using ctk::platform::TemporaryDirectory;

namespace {
void write_file(const fs::path &path, const std::string &contents) {
  std::ofstream output(path, std::ios::binary | std::ios::trunc);
  ASSERT_TRUE(output.good());
  output.write(contents.data(), static_cast<std::streamsize>(contents.size()));
  output.close();
  ASSERT_TRUE(output.good());
}

void atomic_write(const fs::path &path, const std::string &contents) {
  auto replacement = path;
  replacement += ".replacement";
  write_file(replacement, contents);
  fs::rename(replacement, path);
}

class DescriptorReservations {
public:
  ~DescriptorReservations() {
    while (count_ != 0) {
      ctk::platform::release_index_descriptor();
      --count_;
    }
  }
  bool exhaust() {
    while (ctk::platform::reserve_index_descriptor())
      ++count_;
    return count_ != 0;
  }

private:
  std::size_t count_ = 0;
};

void settle_watch(IndexInputWatch &watch) {
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(3);
  auto quiet_since = std::chrono::steady_clock::now();
  while (std::chrono::steady_clock::now() < deadline &&
         std::chrono::steady_clock::now() - quiet_since <
             std::chrono::milliseconds(500)) {
    if (watch.changed())
      quiet_since = std::chrono::steady_clock::now();
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
}

bool wait_for_change(IndexInputWatch &watch, std::chrono::milliseconds timeout =
                                                 std::chrono::seconds(2)) {
  const auto deadline = std::chrono::steady_clock::now() + timeout;
  do {
    if (watch.changed())
      return true;
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  } while (std::chrono::steady_clock::now() < deadline);
  return watch.changed();
}
} // namespace

TEST(IndexInputWatch, TracksThousandsOfFilesWithSharedNotificationResources) {
  TemporaryDirectory temporary{"ctk-index-input-watch"};
  constexpr unsigned file_count = 5000;
  for (unsigned i = 0; i != file_count; ++i)
    write_file(temporary.path() / ("input" + std::to_string(i) + ".h"),
               "struct Input" + std::to_string(i) + " {};\n");

  IndexInputWatch watch;
  for (unsigned i = 0; i != file_count; ++i)
    ASSERT_TRUE(watch.add_file(temporary.path() /
                               ("input" + std::to_string(i) + ".h")));
  ASSERT_TRUE(watch.arm());
  settle_watch(watch);
  EXPECT_FALSE(watch.changed());

  const auto last =
      temporary.path() / ("input" + std::to_string(file_count - 1) + ".h");
  write_file(last, "struct LastInputChanged {};\n");
  EXPECT_TRUE(wait_for_change(watch))
      << "the last registration must remain observable past the former cap";
}

TEST(IndexInputWatch, RepeatedAtomicSavesAndDeleteRecreateRemainObservable) {
  TemporaryDirectory temporary{"ctk-index-input-watch"};
  const auto file = temporary.path() / "source.cpp";
  write_file(file, "int first;\n");

  IndexInputWatch watch;
  ASSERT_TRUE(watch.add_file(file));
  ASSERT_TRUE(watch.arm());
  settle_watch(watch);
  EXPECT_FALSE(watch.changed());
  for (int save = 0; save != 3; ++save) {
    atomic_write(file, "int saved" + std::to_string(save) + ";\n");
    ASSERT_TRUE(wait_for_change(watch)) << "atomic save " << save;
  }

  fs::remove(file);
  ASSERT_TRUE(wait_for_change(watch)) << "deletion";
  write_file(file, "int recreated;\n");
  EXPECT_TRUE(wait_for_change(watch)) << "recreation";
}

TEST(IndexInputWatch, WatchersForDifferentProjectsRemainIndependent) {
  TemporaryDirectory temporary{"ctk-index-input-watch"};
  const auto first_project = temporary.path() / "first";
  const auto second_project = temporary.path() / "second";
  fs::create_directories(first_project);
  fs::create_directories(second_project);
  const auto first_file = first_project / "main.cpp";
  const auto second_file = second_project / "main.cpp";
  write_file(first_file, "int first;\n");
  write_file(second_file, "int second;\n");

  IndexInputWatch first;
  IndexInputWatch second;
  ASSERT_TRUE(first.add_file(first_file));
  ASSERT_TRUE(second.add_file(second_file));
  ASSERT_TRUE(first.arm());
  ASSERT_TRUE(second.arm());
  settle_watch(first);
  settle_watch(second);
  EXPECT_FALSE(first.changed());
  EXPECT_FALSE(second.changed());

  write_file(first_file, "int first_changed;\n");
  ASSERT_TRUE(wait_for_change(first));
  EXPECT_FALSE(second.changed());

  write_file(second_file, "int second_changed;\n");
  ASSERT_TRUE(wait_for_change(second));
  EXPECT_FALSE(first.changed());
}

TEST(IndexInputWatch, DirectoryWatchSeesNewHeadersButIgnoresSiblingActivity) {
  TemporaryDirectory temporary{"ctk-index-input-watch"};
  const auto project = temporary.path() / "project";
  const auto headers = project / "include";
  fs::create_directories(headers);
  write_file(headers / "existing.hpp", "struct Existing {};\n");
  const auto sibling = project / "unrelated.txt";
  write_file(sibling, "unchanged\n");

  IndexInputWatch watch;
  ASSERT_TRUE(watch.add_directory(headers));
  ASSERT_TRUE(watch.arm());
  settle_watch(watch);
  EXPECT_FALSE(watch.changed());

  std::ifstream existing(headers / "existing.hpp");
  std::string contents;
  std::getline(existing, contents);
  std::ifstream unrelated(sibling);
  std::getline(unrelated, contents);
  write_file(sibling, "unrelated edit\n");
  EXPECT_FALSE(wait_for_change(watch, std::chrono::milliseconds(100)))
      << "reads and edits outside the watched directory must stay quiet";

  write_file(headers / "new.hpp", "struct NewlyDiscovered {};\n");
  EXPECT_TRUE(wait_for_change(watch))
      << "new direct children must invalidate the directory inventory";
}

TEST(IndexInputWatch,
     NotificationsWorkWithSharedIndexDescriptorQuotaExhausted) {
  TemporaryDirectory temporary{"ctk-index-input-watch"};
  const auto file = temporary.path() / "source.cpp";
  write_file(file, "int before;\n");

  DescriptorReservations reservations;
  ASSERT_TRUE(reservations.exhaust());
  const bool reservation_became_available =
      ctk::platform::reserve_index_descriptor();
  EXPECT_FALSE(reservation_became_available);
  if (reservation_became_available)
    ctk::platform::release_index_descriptor();

  IndexInputWatch watch;
  ASSERT_TRUE(watch.add_file(file));
  ASSERT_TRUE(watch.arm());
  settle_watch(watch);
  EXPECT_FALSE(watch.changed());
  write_file(file, "int after;\n");
  EXPECT_TRUE(wait_for_change(watch));
}

TEST(IndexInputWatch,
     LateRegistrationRetainsChangesAcrossUnrelatedStreamWatermark) {
  TemporaryDirectory temporary{"ctk-index-input-watch"};
  const auto old_root = temporary.path() / "old-root";
  const auto new_root = temporary.path() / "new-root";
  fs::create_directories(old_root);
  fs::create_directories(new_root);
  const auto old_input = old_root / "existing.hpp";
  const auto new_input = new_root / "late.hpp";
  write_file(old_input, "struct Existing {};\n");
  write_file(new_input, "struct BeforeRegistration {};\n");

  IndexInputWatch watch;
  ASSERT_TRUE(watch.add_file(old_input));
  ASSERT_TRUE(watch.arm());
  settle_watch(watch);
  EXPECT_FALSE(watch.changed());

  ASSERT_TRUE(watch.add_file(new_input));
  write_file(new_input, "struct ChangedBeforeNextArm {};\n");
  // Advance the current stream past the late file's event without changing a
  // registered input. The next arm must replay from the registration floor.
  write_file(old_root / "unregistered-sibling.txt", "noise\n");
  std::this_thread::sleep_for(std::chrono::milliseconds(300));
  ASSERT_TRUE(watch.arm());
  EXPECT_TRUE(wait_for_change(watch, std::chrono::seconds(5)))
      << "late registration changes must survive unrelated stream events";
}

TEST(IndexInputWatch, RetargetedParentSymlinkCanBeRearmedAndFollowed) {
  TemporaryDirectory temporary{"ctk-index-input-watch"};
  const auto target_a = temporary.path() / "target-a";
  const auto target_b = temporary.path() / "target-b";
  fs::create_directories(target_a);
  fs::create_directories(target_b);
  write_file(target_a / "input.hpp", "struct VersionA {};\n");
  write_file(target_b / "input.hpp", "struct VersionB {};\n");
  const auto alias = temporary.path() / "alias";
  fs::create_directory_symlink(target_a, alias);
  const auto input = alias / "input.hpp";

  IndexInputWatch watch;
  ASSERT_TRUE(watch.add_file(input));
  ASSERT_TRUE(watch.arm());
  settle_watch(watch);
  EXPECT_FALSE(watch.changed());

  const auto replacement = temporary.path() / "alias.replacement";
  fs::create_directory_symlink(target_b, replacement);
  fs::rename(replacement, alias);
  ASSERT_TRUE(wait_for_change(watch, std::chrono::seconds(5)))
      << "replacing a parent symlink must invalidate the watched input";

  watch.reset();
  ASSERT_TRUE(watch.add_file(input));
  ASSERT_TRUE(watch.arm());
  settle_watch(watch);
  EXPECT_FALSE(watch.changed());
  write_file(target_b / "input.hpp", "struct VersionBChanged {};\n");
  EXPECT_TRUE(wait_for_change(watch, std::chrono::seconds(5)))
      << "the rearmed alias must follow its new target";
}
