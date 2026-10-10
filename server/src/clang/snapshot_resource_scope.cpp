#include "ctk/clang/snapshot_resource_scope.hpp"
#include <utility>
namespace ctk::clang_layer {
namespace {
thread_local SnapshotResourceScope *active_scope = nullptr;
}
SnapshotResourceScope::SnapshotResourceScope(std::string scope_id,
                                             bool transient, Claim claim)
    : transient_owner_(transient ? std::move(scope_id) : std::string{}),
      claim_(std::move(claim)), previous_(active_scope) {
  active_scope = this;
}
SnapshotResourceScope::~SnapshotResourceScope() { active_scope = previous_; }
SnapshotResourceScope *SnapshotResourceScope::current() noexcept {
  return active_scope;
}
const std::string &SnapshotResourceScope::transient_owner() const noexcept {
  return transient_owner_;
}
void SnapshotResourceScope::acquired(
    const FileInput &file, ctk::cache::SnapshotPtr snapshot,
    std::function<void()> release_reuse) const {
  try {
    claim_(file, std::move(snapshot), release_reuse);
  } catch (...) {
    if (release_reuse)
      release_reuse();
    throw;
  }
}
} // namespace ctk::clang_layer
