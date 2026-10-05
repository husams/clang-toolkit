#include "storage_internal.hpp"

#include <algorithm>
#include <stdexcept>

namespace ctk::storage {

void Store::Impl::flush_access_times_locked() {
  if (pending_access.empty()) return;
  detail::Transaction transaction(database);
  for (const auto &[id, accessed] : pending_access) {
    auto update = detail::Statement(database.handle(),
        "UPDATE snapshots SET last_accessed_at_ms=? WHERE snapshot_id=? AND state='READY'");
    update.bind(1, accessed);
    update.bind(2, id);
    update.execute();
  }
  transaction.commit();
  pending_access.clear();
  access_since_flush = 0;
}

void Store::Impl::collect_unreferenced_locked(std::size_t budget) {
  const auto deleting = metadata.snapshots_in_state("DELETING", budget);
  for (const auto id : deleting) {
    if (snapshot_leases.contains(id)) continue;
    {
      detail::Transaction transaction(database);
      metadata.delete_snapshot(id);
      metadata.prune_unused_identity_rows();
      transaction.commit();
    }
    snapshot_leases.erase(id);
  }

  for (const auto &[digest, size] : metadata.unreferenced_blobs(budget)) {
    (void)size;
    if (blob_leases.contains(digest)) continue;
    {
      detail::Transaction transaction(database);
      metadata.remove_blob_row(digest);
      transaction.commit();
    }
    blobs->remove(digest);
  }
}

void Store::Impl::release_lease(
    SnapshotId id, const std::vector<std::string> &digests) {
  std::lock_guard lock(mutex);
  if (auto lease = snapshot_leases.find(id); lease != snapshot_leases.end()) {
    if (--lease->second == 0) snapshot_leases.erase(lease);
  }
  for (const auto &digest : digests) {
    if (auto lease = blob_leases.find(digest); lease != blob_leases.end() &&
        --lease->second == 0)
      blob_leases.erase(lease);
  }
  collect_unreferenced_locked();
}

void Store::Impl::enforce_retention_locked() {
  const auto budget = std::max<std::size_t>(options.recovery_entry_budget * 4096, 4096);
  for (const auto id : metadata.retention_candidates(budget)) {
    if (blobs->physical_bytes(budget) <= options.max_physical_bytes) return;
    if (snapshot_leases.contains(id)) continue;
    {
      detail::Transaction transaction(database);
      metadata.set_state(id, SnapshotState::Deleting);
      transaction.commit();
    }
    collect_unreferenced_locked();
  }
}

SnapshotDescriptor Store::Impl::load_descriptor_locked(SnapshotId id) const {
  return metadata.load_snapshot(id);
}

void Store::recover() {
  std::unique_lock lock(impl_->mutex);
  impl_->publisher_condition.wait(lock, [this] {
    return impl_->active_publishers == 0;
  });
  const auto budget = impl_->options.recovery_entry_budget;
  impl_->blobs->clean_staging(budget);
  for (const auto id : impl_->metadata.snapshots_in_state("BUILDING", budget)) {
    detail::Transaction transaction(impl_->database);
    impl_->metadata.abandon_building(id);
    transaction.commit();
  }
  impl_->collect_unreferenced_locked(budget);

  auto ready = impl_->metadata.snapshots_in_state("READY", budget);
  for (const auto id : ready) {
    try {
      const auto snapshot = impl_->metadata.load_snapshot(id);
      detail::validate_stored_closure(snapshot);
      if (detail::sha256(snapshot.canonical_manifest) != snapshot.manifest_sha256)
        throw std::runtime_error("manifest digest mismatch");
      for (const auto &artifact : snapshot.artifacts) {
        const auto size = impl_->metadata.blob_size(artifact.blob_sha256);
        if (!size) throw std::runtime_error("artifact metadata is missing");
        impl_->blobs->read(artifact.blob_sha256, *size);
      }
    } catch (...) {
      detail::Transaction transaction(impl_->database);
      impl_->metadata.set_state(id, SnapshotState::Stale);
      transaction.commit();
    }
  }
  impl_->blobs->clean_orphans(
      [impl = impl_](std::string_view digest) {
        return impl->metadata.digest_referenced(digest);
      }, budget);
  impl_->enforce_retention_locked();
}

} // namespace ctk::storage
