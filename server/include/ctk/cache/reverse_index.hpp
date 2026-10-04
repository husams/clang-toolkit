#pragma once

#include "ctk/cache/cache_records.hpp"

namespace ctk::cache::detail {

// Reserve every edge before publication: committing reverse links then cannot
// allocate. The caller supplies unique paths. No path hash is needed;
// dependencies are handles found in the radix.
void prepare_reverse_links(
    const std::shared_ptr<SnapshotRecord> &record,
    const std::vector<std::shared_ptr<FileEntry>> &inputs);
void attach_reverse_links(
    const std::shared_ptr<SnapshotRecord> &record) noexcept;
void detach_reverse_links(
    const std::shared_ptr<SnapshotRecord> &record) noexcept;
std::vector<std::shared_ptr<SnapshotRecord>>
affected_snapshots(const FileEntry &file);

} // namespace ctk::cache::detail
