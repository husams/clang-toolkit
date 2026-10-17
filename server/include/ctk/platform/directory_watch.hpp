#pragma once

#include <cstdint>
#include <filesystem>
#include <memory>
#include <optional>

namespace ctk::platform {
// Owned by the background index thread. Any event/lost watch invalidates its
// derived directory inventories; unavailable/budget-exhausted watches fall back
// to fresh directory walks. File contents are always hashed separately.
class DirectoryWatch {
public:
  struct Identity {
    std::uint64_t device, inode;
    bool operator==(const Identity &) const = default;
  };
  DirectoryWatch();
  ~DirectoryWatch();
  DirectoryWatch(const DirectoryWatch &) = delete;
  DirectoryWatch &operator=(const DirectoryWatch &) = delete;
  bool add(const std::filesystem::path &directory);
  bool changed();
  void reset();
  static std::optional<Identity> identity(const std::filesystem::path &path);

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
} // namespace ctk::platform
