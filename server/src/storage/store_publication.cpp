#include "storage_internal.hpp"

#include <algorithm>
#include <chrono>
#include <set>

namespace ctk::storage {
namespace {

std::int64_t now_ms() {
  return std::chrono::duration_cast<std::chrono::milliseconds>(
             std::chrono::system_clock::now().time_since_epoch())
      .count();
}

std::vector<std::string> blob_digests(const SnapshotDraft &snapshot,
                                     std::vector<std::string> &unique) {
  std::vector<std::string> ordered;
  std::set<std::string> sorted;
  ordered.reserve(snapshot.artifacts.size());
  for (const auto &artifact : snapshot.artifacts) {
    ordered.push_back(detail::sha256(artifact.native_bytes));
    sorted.insert(ordered.back());
  }
  unique.assign(sorted.begin(), sorted.end());
  return ordered;
}

void stage_complete_blobs(detail::BlobStore &blobs,
                          const SnapshotDraft &snapshot) {
  for (const auto &artifact : snapshot.artifacts)
    blobs.publish(artifact.native_bytes, snapshot.created_at_ms);
}

} // namespace

void Store::Impl::reserve_publisher_blobs(
    const std::vector<std::string> &digests) {
  std::lock_guard lock(mutex);
  ++active_publishers;
  for (const auto &digest : digests) ++blob_leases[digest];
}

void Store::Impl::release_publisher_blobs(
    const std::vector<std::string> &digests) {
  for (const auto &digest : digests) {
    if (auto lease = blob_leases.find(digest); lease != blob_leases.end() &&
      --lease->second == 0)
      blob_leases.erase(lease);
  }
  if (active_publishers > 0) --active_publishers;
  publisher_condition.notify_all();
}

SnapshotId Store::Impl::commit_publication(
    const SnapshotDraft &snapshot, const std::vector<std::string> &digests) {
  std::lock_guard lock(mutex);
  enforce_retention_locked();
  const auto budget = std::max<std::size_t>(options.recovery_entry_budget * 4096,
                                            4096);
  if (blobs->physical_bytes(budget) > options.max_physical_bytes)
    throw std::runtime_error("storage quota remains exceeded after retention");
  const auto id = metadata.publish(snapshot, digests);
  return id;
}

void Store::Impl::complete_publication(
    const std::vector<std::string> &digests) noexcept {
  std::lock_guard lock(mutex);
  release_publisher_blobs(digests);
  try { collect_unreferenced_locked(); } catch (...) {}
}

void Store::Impl::cleanup_failed_publication(
    const std::vector<std::string> &digests) {
  std::lock_guard lock(mutex);
  release_publisher_blobs(digests);
  const auto referenced = metadata.referenced_digests();
  for (const auto &digest : digests) {
    if (!referenced.contains(digest) && !blob_leases.contains(digest)) {
      try { blobs->remove(digest); } catch (...) {}
    }
  }
  try { collect_unreferenced_locked(); } catch (...) {}
}

SnapshotId Store::publish(const SnapshotDraft &snapshot) {
  detail::validate_snapshot_draft(snapshot, impl_->options.max_artifact_bytes);
  SnapshotDraft complete = snapshot;
  if (complete.created_at_ms <= 0) complete.created_at_ms = now_ms();

  std::vector<std::string> unique;
  const auto digests = blob_digests(complete, unique);
  impl_->reserve_publisher_blobs(unique);
  try {
    stage_complete_blobs(*impl_->blobs, complete);
    const auto id = impl_->commit_publication(complete, digests);
    impl_->complete_publication(unique);
    return id;
  } catch (...) {
    impl_->cleanup_failed_publication(unique);
    throw;
  }
}

} // namespace ctk::storage
