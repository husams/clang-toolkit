#include "storage_internal.hpp"

#include <algorithm>
#include <chrono>
#include <stdexcept>

namespace ctk::storage {
namespace {

std::int64_t now_ms() {
  return std::chrono::duration_cast<std::chrono::milliseconds>(
             std::chrono::system_clock::now().time_since_epoch())
      .count();
}

} // namespace

Store::Impl::Impl(StoreOptions value)
    : options(std::move(value)), root_lock(options.root),
      database(options.root / "index.sqlite3"), metadata(database) {
  detail::migrate(database);
  blobs = std::make_unique<detail::BlobStore>(options.root,
                                               options.max_artifact_bytes);
}

SnapshotLease::Impl::~Impl() {
  if (release) release();
}

SnapshotLease::SnapshotLease(std::shared_ptr<Impl> impl)
    : impl_(std::move(impl)) {}
SnapshotLease::~SnapshotLease() = default;

const SnapshotDescriptor &SnapshotLease::descriptor() const noexcept {
  return impl_->snapshot;
}

Bytes SnapshotLease::read_artifact(std::size_t artifact_index) const {
  if (artifact_index >= impl_->snapshot.artifacts.size())
    throw std::out_of_range("artifact index is outside the leased snapshot");
  return impl_->read(artifact_index);
}

Store::Store(std::shared_ptr<Impl> impl)
    : impl_(std::move(impl)) {}
Store::~Store() {
  try {
    std::lock_guard lock(impl_->mutex);
    impl_->flush_access_times_locked();
  } catch (...) {
    // Access-time hints are advisory; shutdown must not fail on a cache write.
  }
}

std::unique_ptr<Store> Store::open(StoreOptions options) {
  if (options.root.empty() || !options.root.is_absolute())
    throw std::invalid_argument("storage root must be an absolute path");
  if (options.max_artifact_bytes == 0 || options.recovery_entry_budget == 0 ||
      options.access_write_coalesce == 0)
    throw std::invalid_argument("storage limits must be positive");
  auto impl = std::make_shared<Impl>(std::move(options));
  auto store = std::unique_ptr<Store>(new Store(std::move(impl)));
  store->recover();
  return store;
}

std::vector<SnapshotLeasePtr>
Store::acquire_ready(const CompilationProfile &profile) {
  if (!profile.reusable) return {};
  std::lock_guard lock(impl_->mutex);
  const auto snapshots = impl_->metadata.ready_snapshots(profile);
  std::vector<SnapshotLeasePtr> leases;
  leases.reserve(snapshots.size());
  const auto accessed = now_ms();
  for (const auto &snapshot : snapshots) {
    auto lease_impl = std::make_shared<SnapshotLease::Impl>();
    lease_impl->snapshot = snapshot;
    for (const auto &artifact : snapshot.artifacts) {
      if (std::ranges::find(lease_impl->digests, artifact.blob_sha256) ==
          lease_impl->digests.end())
        lease_impl->digests.push_back(artifact.blob_sha256);
    }
    ++impl_->snapshot_leases[snapshot.id];
    for (const auto &digest : lease_impl->digests)
      ++impl_->blob_leases[digest];
    const auto shared_impl = impl_->shared_from_this();
    const auto id = snapshot.id;
    const auto digests = lease_impl->digests;
    lease_impl->read = [shared_impl, snapshot, digests](std::size_t index) {
      const auto &artifact = snapshot.artifacts[index];
      std::optional<std::uint64_t> size;
      {
        std::lock_guard guard(shared_impl->mutex);
        size = shared_impl->metadata.blob_size(artifact.blob_sha256);
      }
      if (!size) throw std::runtime_error("leased artifact metadata disappeared");
      return shared_impl->blobs->read(artifact.blob_sha256, *size);
    };
    lease_impl->release = [shared_impl, id, digests] {
      shared_impl->release_lease(id, digests);
    };
    impl_->pending_access[snapshot.id] = accessed;
    ++impl_->access_since_flush;
    leases.push_back(SnapshotLeasePtr(new SnapshotLease(std::move(lease_impl))));
  }
  if (impl_->access_since_flush >= impl_->options.access_write_coalesce)
    impl_->flush_access_times_locked();
  return leases;
}

void Store::mark_stale(SnapshotId id) {
  std::lock_guard lock(impl_->mutex);
  detail::Transaction transaction(impl_->database);
  impl_->metadata.set_state(id, SnapshotState::Stale);
  transaction.commit();
}

void Store::retire(SnapshotId id) {
  std::lock_guard lock(impl_->mutex);
  {
    detail::Transaction transaction(impl_->database);
    impl_->metadata.set_state(id, SnapshotState::Deleting);
    transaction.commit();
  }
  impl_->collect_unreferenced_locked();
}

void Store::enforce_retention() {
  std::lock_guard lock(impl_->mutex);
  impl_->enforce_retention_locked();
}

StoreStats Store::stats() const {
  std::lock_guard lock(impl_->mutex);
  return {impl_->blobs->physical_bytes(
              std::max<std::size_t>(impl_->options.recovery_entry_budget * 4096, 4096)),
          impl_->metadata.count_snapshots(SnapshotState::Ready),
          impl_->metadata.count_snapshots(SnapshotState::Stale),
          impl_->snapshot_leases.size()};
}

} // namespace ctk::storage
