#include "../src/net/file_digest_cache.hpp"
#include "../src/net/include_inventory_cache.hpp"
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
using ctk::net::index_detail::IncludeInventoryCache;
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

TEST(IncludeInventoryCache, CachesInventoriesAbovePreviousWatchBudget) {
  TemporaryDirectory temporary{"ctk-include-inventory-watch-budget"};
  const auto root = temporary.path() / "include";
  fs::create_directory(root);
  constexpr unsigned directory_count = 2100;
  for (unsigned i = 0; i < directory_count; ++i) {
    const auto name = std::to_string(i);
    ASSERT_TRUE(fs::create_directory(root / name));
  }
  if (!supports_reader_reuse(root))
    GTEST_SKIP() << "filesystem does not support index input reuse";

  // Confirm this OS/process can install the fixture's complete watch set.
  // This keeps a lower RLIMIT_NOFILE or kernel watch quota from making the
  // capacity regression fail on an otherwise valid fallback configuration.
  bool watch_set_supported = true;
  {
    ctk::platform::DirectoryWatch probe;
    watch_set_supported = probe.add(root.parent_path()) && probe.add(root);
    for (unsigned i = 0; watch_set_supported && i < directory_count; ++i)
      watch_set_supported = probe.add(root / std::to_string(i));
  }
  if (!watch_set_supported)
    GTEST_SKIP() << "platform cannot install the fixture's complete watch set";

  IncludeInventoryCache cache;
  std::size_t first_walk_entries = 0;
  const auto first = cache.digest(root, [&] {
    ++first_walk_entries;
    return true;
  });
  ASSERT_FALSE(first.empty());
  EXPECT_GE(first_walk_entries, directory_count);

  std::size_t second_walk_entries = 0;
  const auto second = cache.digest(root, [&] {
    ++second_walk_entries;
    return true;
  });
  EXPECT_EQ(second, first);
  EXPECT_EQ(second_walk_entries, 0u);

  const auto nested = root / "0" / "new";
  fs::create_directories(nested);
  write_file(nested / "header.hpp", "new header");
  std::size_t changed_walk_entries = 0;
  const auto changed = cache.digest(root, [&] {
    ++changed_walk_entries;
    return true;
  });
  EXPECT_NE(changed, second);
  EXPECT_GT(changed_walk_entries, 0u);
}

TEST(IndexInputWatch, DetectsContentWritesReplacementAndDeletion) {
  TemporaryDirectory temporary{"ctk-input-watch"};
  const auto file = temporary.path() / "input.cpp";
  write_file(file, "before");
  ctk::platform::DirectoryWatch watch;
  ASSERT_TRUE(watch.add_file(file));
  EXPECT_FALSE(watch.changed());
  const timespec access_only[2]{{1, 0}, {0, UTIME_OMIT}};
  ASSERT_EQ(utimensat(AT_FDCWD, file.c_str(), access_only, 0), 0);
  EXPECT_FALSE(watch.changed()) << "access metadata must not wake idle monitors";
  write_file(file, "after!");
  EXPECT_TRUE(watch.changed());
  watch.reset();
  ASSERT_TRUE(watch.add_file(file));
  const auto replacement = temporary.path() / "replacement";
  write_file(replacement, "replacement");
  fs::rename(replacement, file);
  EXPECT_TRUE(watch.changed());
  watch.reset();
  ASSERT_TRUE(watch.add_file(file));
  fs::remove(file);
  EXPECT_TRUE(watch.changed());
  watch.reset();
  EXPECT_FALSE(watch.add_file(file));
}

TEST(IncludeInventoryCache, IdleNotificationsIgnoreUnrelatedAncestorEntries) {
  TemporaryDirectory temporary{"ctk-inventory-notification"};
  const auto include = temporary.path() / "include";
  fs::create_directory(include);
  write_file(include / "one.hpp", "int one;");
  IncludeInventoryCache cache;
  const auto before = cache.digest(include);
  ASSERT_FALSE(before.empty());
  write_file(temporary.path() / "unrelated", "not an index input");
  EXPECT_FALSE(cache.inputs_changed());
  write_file(include / "two.hpp", "int two;");
  EXPECT_TRUE(cache.inputs_changed());
  const auto after = cache.digest(include);
  EXPECT_NE(after, before);
  // A safety sweep discards cached directory inventories even without events.
  cache.reset();
  EXPECT_EQ(cache.digest(include), after);
}

TEST(IndexInputWatch, SharesDescriptorsWithoutSharingQueuedEvents) {
#ifndef __APPLE__
  GTEST_SKIP() << "inotify watches do not retain per-path file descriptors";
#else
  TemporaryDirectory temporary{"ctk-shared-watch"};
  const auto file = temporary.path() / "input.cpp";
  write_file(file, "original");
  ctk::platform::DirectoryWatch first, second;
  const auto open_count = [] {
    rlimit limit{};
    EXPECT_EQ(getrlimit(RLIMIT_NOFILE, &limit), 0);
    unsigned count = 0;
    for (unsigned fd = 0; fd < std::min<rlim_t>(limit.rlim_cur, 8192); ++fd)
      count += fcntl(fd, F_GETFD) != -1;
    return count;
  };
  ASSERT_TRUE(first.add_file(file));
  const auto before = open_count();
  ASSERT_TRUE(second.add_file(file));
  EXPECT_EQ(open_count(), before);
  write_file(file, "modified");
  EXPECT_TRUE(first.changed());
  EXPECT_TRUE(second.changed());
  const auto replacement = temporary.path() / "replacement";
  write_file(replacement, "replacement");
  fs::rename(replacement, file);
  first.reset();
  ASSERT_TRUE(first.add_file(file));
  EXPECT_FALSE(first.changed());
  write_file(file, "new inode must be watched");
  EXPECT_TRUE(first.changed());
#endif
}

TEST(IndexInputWatch, ProcessWideBudgetPreservesTraversalAndForegroundDescriptors) {
#ifndef __APPLE__
  GTEST_SKIP() << "inotify watches do not retain per-path file descriptors";
#else
  TemporaryDirectory temporary{"ctk-watch-reserve"};
  for (unsigned i = 0; i != 400; ++i)
    write_file(temporary.path() / std::to_string(i), "input");
  const auto child = fork();
  ASSERT_GE(child, 0);
  if (child == 0) {
    rlimit limit{512, 512};
    if (setrlimit(RLIMIT_NOFILE, &limit) != 0)
      _exit(77);
    std::vector<std::unique_ptr<ctk::platform::DirectoryWatch>> watches;
    bool unavailable = false;
    for (unsigned group = 0; group != 4; ++group) {
      auto watch = std::make_unique<ctk::platform::DirectoryWatch>();
      for (unsigned i = group * 100; i != (group + 1) * 100; ++i)
        unavailable = !watch->add_file(temporary.path() / std::to_string(i)) || unavailable;
      watches.push_back(std::move(watch));
    }
    if (!unavailable)
      _exit(1);
    std::vector<std::unique_ptr<ctk::platform::IndexFileReader>> readers;
    for (unsigned i = 0; i != 128; ++i) {
      auto reader = std::make_unique<ctk::platform::IndexFileReader>(temporary.path() / "0");
      if (!reader->valid())
        _exit(5);
      if (reader->cacheable())
        readers.push_back(std::move(reader));
    }
    std::vector<int> foreground;
    for (unsigned i = 0; i != 128; ++i) {
      const int descriptor = open("/dev/null", O_RDONLY | O_CLOEXEC);
      if (descriptor < 0)
        _exit(2);
      foreground.push_back(descriptor);
    }
    try {
      unsigned entries = 0;
      for (const auto &entry : fs::directory_iterator(temporary.path())) {
        (void)entry;
        ++entries;
      }
      _exit(entries == 400 ? 0 : 3);
    } catch (...) {
      _exit(4);
    }
  }
  int status = 0;
  ASSERT_EQ(waitpid(child, &status, 0), child);
  if (WIFEXITED(status) && WEXITSTATUS(status) == 77)
    GTEST_SKIP() << "cannot set isolated child descriptor limit";
  ASSERT_TRUE(WIFEXITED(status));
  EXPECT_EQ(WEXITSTATUS(status), 0);
#endif
}
