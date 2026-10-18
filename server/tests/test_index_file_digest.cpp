#include "../src/net/file_digest_cache.hpp"
#include "../src/platform/index_filesystem.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include <gtest/gtest.h>

#include <cerrno>
#include <fcntl.h>
#include <filesystem>
#include <fstream>
#include <string>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

namespace fs = std::filesystem;
using ctk::net::index_detail::FileDigestCache;
using ctk::platform::TemporaryDirectory;

namespace {
bool supports_reader_reuse(const fs::path &path) {
  const int descriptor = open(path.c_str(), O_RDONLY | O_CLOEXEC);
  if (descriptor < 0)
    return false;
  const bool supported = ctk::platform::supports_index_input_reuse(descriptor);
  close(descriptor);
  return supported;
}

void write_file(const fs::path &path, const std::string &value) {
  std::ofstream output(path, std::ios::binary | std::ios::trunc);
  ASSERT_TRUE(output.good());
  output.write(value.data(), static_cast<std::streamsize>(value.size()));
  output.close();
  ASSERT_TRUE(output.good());
}
} // namespace

TEST(IndexFileDigestCache, ReusesOpenReaderButRehashesEveryCall) {
  TemporaryDirectory temporary{"ctk-file-digest"};
  const auto file = temporary.path() / "header.hpp";
  write_file(file, "first");
  FileDigestCache cache;

  const auto first = cache.digest(file.string());
  ASSERT_FALSE(first.empty());
  EXPECT_EQ(cache.digest(file.string()), first);
  EXPECT_EQ(cache.counters().hashes, 2u);
  if (supports_reader_reuse(file)) {
    EXPECT_EQ(cache.counters().hits, 1u);
    EXPECT_EQ(cache.size(), 1u);
  } else {
    EXPECT_EQ(cache.counters().hits, 0u);
    EXPECT_EQ(cache.counters().uncached, 2u);
    EXPECT_EQ(cache.size(), 0u);
  }
}

TEST(IndexFileDigestCache, ReusesOnlyOnSupportedLocalFilesystems) {
  TemporaryDirectory temporary{"ctk-file-digest"};
  const auto file = temporary.path() / "header.hpp";
  write_file(file, "contents");
  const int descriptor = open(file.c_str(), O_RDONLY | O_CLOEXEC);
  ASSERT_GE(descriptor, 0);
  const bool supported = ctk::platform::supports_index_input_reuse(descriptor);
  EXPECT_EQ(close(descriptor), 0);
#ifdef __APPLE__
  EXPECT_TRUE(supported);
#endif

  FileDigestCache cache;
  EXPECT_FALSE(cache.digest(file.string()).empty());
  if (!supported) {
    EXPECT_EQ(cache.size(), 0u);
    EXPECT_EQ(cache.counters().uncached, 1u);
  }
}

TEST(IndexFileDigestCache, DetectsSameSizeEditWithRestoredMtime) {
  TemporaryDirectory temporary{"ctk-file-digest"};
  const auto file = temporary.path() / "header.hpp";
  write_file(file, "first");
  FileDigestCache cache;
  const auto first = cache.digest(file.string());
  ASSERT_FALSE(first.empty());
  const auto time = fs::last_write_time(file);

  write_file(file, "other");
  fs::last_write_time(file, time);
  const auto second = cache.digest(file.string());
  EXPECT_NE(second, first);
  EXPECT_EQ(cache.counters().hashes, 2u);
}

TEST(IndexFileDigestCache, ReopensReaderAfterSameInodeMetadataChange) {
  TemporaryDirectory temporary{"ctk-file-digest"};
  const auto file = temporary.path() / "header.hpp";
  write_file(file, "contents");
  FileDigestCache cache;
  const auto first = cache.digest(file.string());
  ASSERT_FALSE(first.empty());

  struct stat before{};
  ASSERT_EQ(stat(file.c_str(), &before), 0);
  std::error_code error;
  fs::permissions(file, fs::perms::owner_exec, fs::perm_options::add, error);
  ASSERT_FALSE(error);
  struct stat after{};
  ASSERT_EQ(stat(file.c_str(), &after), 0);
  ASSERT_EQ(before.st_dev, after.st_dev);
  ASSERT_EQ(before.st_ino, after.st_ino);

  EXPECT_EQ(cache.digest(file.string()), first);
  if (supports_reader_reuse(file)) {
    EXPECT_EQ(cache.counters().invalidations, 1u);
    EXPECT_EQ(cache.counters().cached, 2u);
  } else {
    EXPECT_EQ(cache.size(), 0u);
    EXPECT_EQ(cache.counters().uncached, 2u);
  }
}

TEST(IndexFileDigestCache, ReadsMmapWritesOnAlreadyDirtySharedPage) {
  TemporaryDirectory temporary{"ctk-file-digest"};
  const auto file = temporary.path() / "mapped.hpp";
  write_file(file, "00");
  const int descriptor = open(file.c_str(), O_RDWR | O_CLOEXEC);
  ASSERT_GE(descriptor, 0);
  auto *mapping = static_cast<char *>(
      mmap(nullptr, 2, PROT_READ | PROT_WRITE, MAP_SHARED, descriptor, 0));
  ASSERT_NE(mapping, MAP_FAILED);
  mapping[0] = '1'; // Dirty the page before the reader is retained.

  FileDigestCache cache;
  const auto first = cache.digest(file.string());
  ASSERT_FALSE(first.empty());
  mapping[1] = '2'; // Same dirty page; no msync is issued.
  const auto second = cache.digest(file.string());

  EXPECT_NE(second, first);
  EXPECT_EQ(cache.counters().hashes, 2u);
  EXPECT_EQ(munmap(mapping, 2), 0);
  EXPECT_EQ(close(descriptor), 0);
}

TEST(IndexFileDigestCache, EditAndRestoreStillPerformsFreshHash) {
  TemporaryDirectory temporary{"ctk-file-digest"};
  const auto file = temporary.path() / "header.hpp";
  write_file(file, "first");
  FileDigestCache cache;
  const auto first = cache.digest(file.string());
  ASSERT_FALSE(first.empty());
  const auto time = fs::last_write_time(file);

  write_file(file, "other");
  fs::last_write_time(file, time);
  write_file(file, "first");
  fs::last_write_time(file, time);
  EXPECT_EQ(cache.digest(file.string()), first);
  EXPECT_EQ(cache.counters().hashes, 2u);
}

TEST(IndexFileDigestCache, DetectsAtomicReplacementAndDeleteRecreate) {
  TemporaryDirectory temporary{"ctk-file-digest"};
  const auto file = temporary.path() / "header.hpp";
  const auto replacement = temporary.path() / "replacement.hpp";
  write_file(file, "first");
  FileDigestCache cache;
  const auto first = cache.digest(file.string());
  ASSERT_FALSE(first.empty());

  write_file(replacement, "second");
  fs::rename(replacement, file);
  const auto second = cache.digest(file.string());
  EXPECT_NE(second, first);

  fs::remove(file);
  write_file(file, "third");
  const auto third = cache.digest(file.string());
  EXPECT_NE(third, second);
  EXPECT_EQ(cache.counters().hashes, 3u);
}

TEST(IndexFileDigestCache, DetectsSymlinkAndAncestorRetarget) {
  TemporaryDirectory temporary{"ctk-file-digest"};
  const auto first_target = temporary.path() / "first.hpp";
  const auto second_target = temporary.path() / "second.hpp";
  const auto link = temporary.path() / "header.hpp";
  write_file(first_target, "first");
  write_file(second_target, "second");
  fs::create_symlink(first_target, link);
  FileDigestCache cache;

  const auto first = cache.digest(link.string());
  ASSERT_FALSE(first.empty());
  fs::remove(link);
  fs::create_symlink(second_target, link);
  const auto second = cache.digest(link.string());
  EXPECT_NE(second, first);

  const auto old_dir = temporary.path() / "old";
  const auto new_dir = temporary.path() / "new";
  fs::create_directories(old_dir);
  fs::create_directories(new_dir);
  write_file(old_dir / "nested.hpp", "old");
  write_file(new_dir / "nested.hpp", "new");
  const auto parent_link = temporary.path() / "include";
  fs::create_directory_symlink(old_dir, parent_link);
  const auto nested = parent_link / "nested.hpp";
  const auto old_digest = cache.digest(nested.string());
  fs::remove(parent_link);
  fs::create_directory_symlink(new_dir, parent_link);
  const auto new_digest = cache.digest(nested.string());
  EXPECT_NE(new_digest, old_digest);
}

TEST(IndexFileDigestCache, BoundsReadersAndHashesUncachedFilesFresh) {
  TemporaryDirectory temporary{"ctk-file-digest"};
  const auto first = temporary.path() / "first.hpp";
  const auto second = temporary.path() / "second.hpp";
  write_file(first, "first");
  write_file(second, "second");
  FileDigestCache cache(1);

  ASSERT_FALSE(cache.digest(first.string()).empty());
  ASSERT_FALSE(cache.digest(second.string()).empty());
  ASSERT_FALSE(cache.digest(second.string()).empty());
  EXPECT_LE(cache.size(), 1u);
  EXPECT_EQ(cache.counters().hashes, 3u);
  if (cache.size() == 1)
    EXPECT_GE(cache.counters().uncached, 2u);
  else
    EXPECT_EQ(cache.counters().uncached, 3u);
}

TEST(IndexFileDigestCache, CancellationAfterReadingReturnsNoDigest) {
  TemporaryDirectory temporary{"ctk-file-digest"};
  const auto file = temporary.path() / "header.hpp";
  write_file(file, "contents");
  FileDigestCache cache;
  int checks = 0;
  EXPECT_TRUE(
      cache.digest(file.string(), [&checks] { return ++checks < 3; }).empty());
  EXPECT_EQ(cache.counters().hashes, 1u);
  EXPECT_FALSE(cache.digest(file.string()).empty());
  EXPECT_EQ(cache.counters().hashes, 2u);
}

TEST(IndexFileDigestCache, LowDescriptorLimitFallsBackInChildProcess) {
  TemporaryDirectory temporary{"ctk-file-digest"};
  const auto file = temporary.path() / "header.hpp";
  write_file(file, "contents");

  const auto child = fork();
  ASSERT_GE(child, 0);
  if (child == 0) {
    rlimit limit{};
    if (getrlimit(RLIMIT_NOFILE, &limit) != 0 || limit.rlim_max < 512)
      _exit(77);
    if (limit.rlim_max >= 4096) {
      limit.rlim_cur = 4096;
      if (setrlimit(RLIMIT_NOFILE, &limit) != 0 ||
          ctk::platform::IndexFileReader::descriptor_budget(2048) != 1536)
        _exit(4);
    }
    if (limit.rlim_max >= 8192) {
      limit.rlim_cur = 8192;
      if (setrlimit(RLIMIT_NOFILE, &limit) != 0 ||
          ctk::platform::IndexFileReader::descriptor_budget(2048) != 2048)
        _exit(5);
    }
    limit.rlim_cur = 512;
    if (setrlimit(RLIMIT_NOFILE, &limit) != 0 ||
        ctk::platform::IndexFileReader::descriptor_budget(2048) != 128 ||
        ctk::platform::IndexFileReader::descriptor_budget(64) != 64)
      _exit(1);

    limit.rlim_cur = 256;
    if (setrlimit(RLIMIT_NOFILE, &limit) != 0 ||
        ctk::platform::IndexFileReader::descriptor_budget(2048) != 0)
      _exit(2);

    FileDigestCache cache;
    const auto digest = cache.digest(file.string());
    const bool fallback_worked =
        !digest.empty() && cache.size() == 0 && cache.counters().uncached == 1;
    _exit(fallback_worked ? 0 : 3);
  }

  int status = 0;
  pid_t waited;
  do {
    waited = waitpid(child, &status, 0);
  } while (waited < 0 && errno == EINTR);
  ASSERT_EQ(waited, child);
  if (WIFEXITED(status) && WEXITSTATUS(status) == 77)
    GTEST_SKIP() << "cannot set the isolated child descriptor limit";
  ASSERT_TRUE(WIFEXITED(status));
  EXPECT_EQ(WEXITSTATUS(status), 0);
}
