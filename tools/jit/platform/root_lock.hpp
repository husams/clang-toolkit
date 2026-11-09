#pragma once

#include <filesystem>

namespace ctk::jit {

class RootLock final {
public:
  explicit RootLock(const std::filesystem::path &root);
  ~RootLock();
  RootLock(const RootLock &) = delete;
  RootLock &operator=(const RootLock &) = delete;

private:
  int descriptor_ = -1;
};

} // namespace ctk::jit
