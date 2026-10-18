#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>

namespace ctk::platform {

struct IndexFileIdentity {
  std::uint64_t device = 0;
  std::uint64_t inode = 0;
  std::uint64_t owner = 0;
  std::uint64_t group = 0;
  std::uint64_t size = 0;
  std::int64_t mtime_seconds = 0;
  std::int64_t mtime_nanoseconds = 0;
  std::int64_t ctime_seconds = 0;
  std::int64_t ctime_nanoseconds = 0;
  std::uint32_t mode = 0;
  friend bool operator==(const IndexFileIdentity &,
                         const IndexFileIdentity &) = default;
};

// Keeps a file descriptor open so index planning can re-read the same file
// without repeating open/close. Every digest still reads the current bytes.
class IndexFileReader {
public:
  explicit IndexFileReader(const std::filesystem::path &path);
  ~IndexFileReader();
  IndexFileReader(const IndexFileReader &) = delete;
  IndexFileReader &operator=(const IndexFileReader &) = delete;

  bool valid() const;
  bool cacheable() const;
  std::optional<IndexFileIdentity> identity() const;
  std::ptrdiff_t read_at(void *buffer, std::size_t size,
                         std::uint64_t offset) const;

  static std::optional<IndexFileIdentity>
  path_identity(const std::filesystem::path &path);
  static std::size_t descriptor_budget(std::size_t requested);

private:
  int descriptor_ = -1;
};

} // namespace ctk::platform
