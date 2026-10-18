#include "ctk/platform/index_file_reader.hpp"
#include "index_filesystem.hpp"

#include <algorithm>
#include <cerrno>
#include <fcntl.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <unistd.h>

namespace ctk::platform {
namespace {
std::optional<IndexFileIdentity> from_stat(const struct stat &value) {
  if (!S_ISREG(value.st_mode))
    return std::nullopt;
#ifdef __APPLE__
  const auto mtime_seconds = value.st_mtimespec.tv_sec;
  const auto mtime_nanoseconds = value.st_mtimespec.tv_nsec;
  const auto ctime_seconds = value.st_ctimespec.tv_sec;
  const auto ctime_nanoseconds = value.st_ctimespec.tv_nsec;
#else
  const auto mtime_seconds = value.st_mtim.tv_sec;
  const auto mtime_nanoseconds = value.st_mtim.tv_nsec;
  const auto ctime_seconds = value.st_ctim.tv_sec;
  const auto ctime_nanoseconds = value.st_ctim.tv_nsec;
#endif
  return IndexFileIdentity{static_cast<std::uint64_t>(value.st_dev),
                           static_cast<std::uint64_t>(value.st_ino),
                           static_cast<std::uint64_t>(value.st_uid),
                           static_cast<std::uint64_t>(value.st_gid),
                           static_cast<std::uint64_t>(value.st_size),
                           static_cast<std::int64_t>(mtime_seconds),
                           static_cast<std::int64_t>(mtime_nanoseconds),
                           static_cast<std::int64_t>(ctime_seconds),
                           static_cast<std::int64_t>(ctime_nanoseconds),
                           static_cast<std::uint32_t>(value.st_mode)};
}
} // namespace

IndexFileReader::IndexFileReader(const std::filesystem::path &path)
    : descriptor_(open(path.c_str(), O_RDONLY | O_CLOEXEC)) {}

IndexFileReader::~IndexFileReader() {
  if (descriptor_ >= 0)
    close(descriptor_);
}

bool IndexFileReader::valid() const { return descriptor_ >= 0; }
bool IndexFileReader::cacheable() const {
  return descriptor_ >= 0 && supports_index_input_reuse(descriptor_);
}

std::optional<IndexFileIdentity> IndexFileReader::identity() const {
  struct stat value{};
  if (descriptor_ < 0 || fstat(descriptor_, &value) != 0)
    return std::nullopt;
  return from_stat(value);
}

std::ptrdiff_t IndexFileReader::read_at(void *buffer, std::size_t size,
                                        std::uint64_t offset) const {
  if (descriptor_ < 0)
    return -1;
  ssize_t result;
  do {
    result = pread(descriptor_, buffer, size, static_cast<off_t>(offset));
  } while (result < 0 && errno == EINTR);
  return static_cast<std::ptrdiff_t>(result);
}

std::optional<IndexFileIdentity>
IndexFileReader::path_identity(const std::filesystem::path &path) {
  struct stat value{};
  if (stat(path.c_str(), &value) != 0)
    return std::nullopt;
  return from_stat(value);
}

std::size_t IndexFileReader::descriptor_budget(std::size_t requested) {
  rlimit limit{};
  if (getrlimit(RLIMIT_NOFILE, &limit) != 0 || limit.rlim_cur <= 256)
    return 0;
  const auto available = static_cast<std::size_t>((limit.rlim_cur - 256) / 2);
  return std::min(requested, available);
}

} // namespace ctk::platform
