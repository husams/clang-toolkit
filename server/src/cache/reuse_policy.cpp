#include "ctk/cache/reuse_policy.hpp"

#include "ctk/cache/cache_records.hpp"

#include <limits>
#include <stdexcept>

namespace ctk::cache::detail {
void ReusePolicy::admit(const std::shared_ptr<SnapshotRecord> &record) {
  const auto bytes = record->snapshot->estimated_bytes;
  if (bytes > std::numeric_limits<std::size_t>::max() - estimated_bytes_)
    throw std::overflow_error("snapshot accounting overflow");
  order_.push_front({record, bytes});
  estimated_bytes_ += bytes;
}

void ReusePolicy::touch(
    const std::shared_ptr<SnapshotRecord> &record) noexcept {
  for (auto it = order_.begin(); it != order_.end(); ++it) {
    if (it->record.lock() == record) {
      order_.splice(order_.begin(), order_, it);
      return;
    }
  }
}

void ReusePolicy::remove(
    const std::shared_ptr<SnapshotRecord> &record) noexcept {
  for (auto it = order_.begin(); it != order_.end();) {
    if (it->record.lock() == record) {
      estimated_bytes_ -= it->estimated_bytes;
      it = order_.erase(it);
    } else {
      ++it;
    }
  }
}

std::shared_ptr<SnapshotRecord> ReusePolicy::oldest() const noexcept {
  return order_.empty() ? nullptr : order_.back().record.lock();
}
} // namespace ctk::cache::detail
