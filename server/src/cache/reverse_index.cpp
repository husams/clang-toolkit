#include "ctk/cache/reverse_index.hpp"

#include <algorithm>

namespace ctk::cache::detail {
void prepare_reverse_links(
    const std::shared_ptr<SnapshotRecord> &record,
    const std::vector<std::shared_ptr<FileEntry>> &inputs) {
  record->dependencies.reserve(inputs.size());
  for (const auto &input : inputs) {
    // Acquisition deduplicates paths before taking metadata locking.
    std::erase_if(input->dependent_snapshots,
                  [](const auto &weak) { return weak.expired(); });
    input->dependent_snapshots.reserve(input->dependent_snapshots.size() + 1);
    record->dependencies.push_back(input);
  }
}

void attach_reverse_links(
    const std::shared_ptr<SnapshotRecord> &record) noexcept {
  for (const auto &weak : record->dependencies)
    if (const auto file = weak.lock())
      file->dependent_snapshots.push_back(record);
}

void detach_reverse_links(
    const std::shared_ptr<SnapshotRecord> &record) noexcept {
  for (const auto &weak : record->dependencies) {
    if (const auto file = weak.lock()) {
      std::erase_if(file->dependent_snapshots, [&](const auto &edge) {
        const auto dependent = edge.lock();
        return !dependent || dependent == record;
      });
    }
  }
}

std::vector<std::shared_ptr<SnapshotRecord>>
affected_snapshots(const FileEntry &file) {
  std::vector<std::shared_ptr<SnapshotRecord>> result;
  for (const auto &[digest, profile] : file.profiles) {
    (void)digest;
    result.insert(result.end(), profile->generations.begin(),
                  profile->generations.end());
  }
  for (const auto &weak : file.dependent_snapshots)
    if (auto record = weak.lock())
      result.push_back(std::move(record));
  return result;
}
} // namespace ctk::cache::detail
