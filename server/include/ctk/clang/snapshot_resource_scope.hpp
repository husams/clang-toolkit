#pragma once
#include "ctk/clang/tooling.hpp"

namespace ctk::clang_layer {
// Installed on the executor's native-operation thread. Every acquired snapshot
// is registered before match callbacks/serialization, even if execution fails.
class SnapshotResourceScope final {
public:
  using Claim = std::function<void(const FileInput &, ctk::cache::SnapshotPtr,
                                   std::function<void()>)>;
  SnapshotResourceScope(std::string scope_id, bool transient, Claim claim);
  ~SnapshotResourceScope();
  SnapshotResourceScope(const SnapshotResourceScope &) = delete;
  SnapshotResourceScope &operator=(const SnapshotResourceScope &) = delete;
  static SnapshotResourceScope *current() noexcept;
  const std::string &transient_owner() const noexcept;
  void acquired(const FileInput &file, ctk::cache::SnapshotPtr snapshot,
                std::function<void()> release_reuse) const;

private:
  std::string transient_owner_;
  Claim claim_;
  SnapshotResourceScope *previous_;
};
} // namespace ctk::clang_layer
