#pragma once

#include <filesystem>
#include <string_view>

namespace ctk::platform {

// Owns an atomically created, owner-only temporary directory.
class TemporaryDirectory final {
public:
  explicit TemporaryDirectory(std::string_view prefix = "ctk");
  ~TemporaryDirectory();
  TemporaryDirectory(const TemporaryDirectory &) = delete;
  TemporaryDirectory &operator=(const TemporaryDirectory &) = delete;

  const std::filesystem::path &path() const noexcept { return path_; }

private:
  std::filesystem::path path_;
};

} // namespace ctk::platform
