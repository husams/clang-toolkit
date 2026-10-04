#pragma once

#include <cstddef>
#include <list>
#include <memory>

namespace ctk::cache::detail {
struct SnapshotRecord;

struct ReuseToken {
  std::weak_ptr<SnapshotRecord> record;
  std::size_t estimated_bytes;
};

// The policy knows only weak reuse records: no second pathname registry and no
// native ownership. The caller serializes bookkeeping under its metadata lock.
class ReusePolicy {
public:
  void admit(const std::shared_ptr<SnapshotRecord> &record);
  void touch(const std::shared_ptr<SnapshotRecord> &record) noexcept;
  void remove(const std::shared_ptr<SnapshotRecord> &record) noexcept;
  std::shared_ptr<SnapshotRecord> oldest() const noexcept;
  std::size_t size() const noexcept { return order_.size(); }
  std::size_t estimated_bytes() const noexcept { return estimated_bytes_; }

private:
  std::list<ReuseToken> order_;
  std::size_t estimated_bytes_ = 0;
};
} // namespace ctk::cache::detail
