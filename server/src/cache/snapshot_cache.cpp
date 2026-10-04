#include "ctk/cache/snapshot_cache.hpp"

#include "cache_state.hpp"
#include "ctk/cache/path_policy.hpp"

#include <algorithm>
#include <utility>

namespace ctk::cache {

SnapshotCache::SnapshotCache(std::shared_ptr<SnapshotLoader> loader,
                             CacheOptions options)
    : impl_(std::make_unique<Impl>(std::move(loader), std::move(options))) {}
SnapshotCache::~SnapshotCache() = default;

// Prepare immutable identity before entering coordination. The acquisition
// engine owns selection, validation, flight waiting and publication separately.
SnapshotPtr SnapshotCache::acquire(std::string_view spelling,
                                   const CompilationContext &context,
                                   std::stop_token cancellation) {
  const auto path = path_key(spelling);
  const auto identity = context.canonical_bytes();
  const auto digest = impl_->options.profile_digest(identity);
  return impl_->acquire({path, identity, digest, context, cancellation});
}

void SnapshotCache::invalidate_path(std::string_view spelling) {
  const auto path = path_key(spelling);
  std::vector<SnapshotPtr> garbage;
  // Native retirement pins outlive this guard; destructors can call cache APIs.
  std::lock_guard lock(impl_->mutex);
  ++impl_->invalidation_epoch;
  const auto file = impl_->files.find(path);
  if (file != impl_->files.end())
    impl_->invalidate_locked(file->second, garbage);
}

void SnapshotCache::invalidate_directory(std::string_view spelling) {
  const auto exact = directory_key(spelling);
  const auto prefix = directory_prefix(spelling);
  std::vector<SnapshotPtr> garbage;
  std::lock_guard lock(impl_->mutex);
  ++impl_->invalidation_epoch;
  const auto directory = impl_->files.find(exact);
  // Include the directory namespace separately from its boundary-safe prefix.
  if (directory != impl_->files.end())
    impl_->invalidate_locked(directory->second, garbage);
  for (const auto &[key, file] : impl_->files.prefix(prefix)) {
    if (key != exact)
      impl_->invalidate_locked(file, garbage);
  }
}

void SnapshotCache::notify_path_change(std::string_view spelling) {
  const auto path = path_key(spelling);
  const auto separator = path.rfind('/');
  const auto parent = separator == 0 ? "/" : path.substr(0, separator);
  // Both events participate in the same metadata epoch/publication boundary.
  std::vector<SnapshotPtr> garbage;
  std::lock_guard lock(impl_->mutex);
  ++impl_->invalidation_epoch;
  const auto file = impl_->files.find(path);
  if (file != impl_->files.end())
    impl_->invalidate_locked(file->second, garbage);
  if (parent != path) {
    const auto directory = impl_->files.find(parent);
    if (directory != impl_->files.end())
      impl_->invalidate_locked(directory->second, garbage);
  }
}

void SnapshotCache::clear_reuse() {
  std::vector<SnapshotPtr> garbage;
  std::lock_guard lock(impl_->mutex);
  ++impl_->invalidation_epoch;
  garbage.reserve(impl_->lru.size());
  // Detach reuse and reverse edges; active operations retain their own owners.
  while (const auto oldest = impl_->lru.oldest())
    impl_->retire_locked(oldest, garbage);
}

bool SnapshotCache::erase_unused_path(std::string_view spelling) {
  const auto path = path_key(spelling);
  std::lock_guard lock(impl_->mutex);
  const auto found = impl_->files.find(path);
  if (found == impl_->files.end())
    return false;
  const auto file = found->second;
  // Metadata can go only after flights, retained profiles and reverse edges do.
  if (std::ranges::any_of(file->dependent_snapshots,
                          [](const auto &weak) { return !weak.expired(); }))
    return false;
  for (const auto &[digest, profile] : file->profiles) {
    (void)digest;
    if (profile->flight || !profile->generations.empty())
      return false;
  }
  ++impl_->invalidation_epoch;
  return impl_->files.erase(path) != 0;
}

std::vector<FileInfo> SnapshotCache::files() const {
  std::vector<FileInfo> result;
  std::lock_guard lock(impl_->mutex);
  result.reserve(impl_->files.size());
  for (const auto &[key, file] : impl_->files) {
    (void)key;
    result.push_back(impl_->info_locked(file));
  }
  return result;
}

std::vector<FileInfo>
SnapshotCache::files_in_directory(std::string_view spelling) const {
  const auto exact = directory_key(spelling);
  const auto prefix = directory_prefix(spelling);
  std::vector<FileInfo> result;
  std::lock_guard lock(impl_->mutex);
  const auto directory = impl_->files.find(exact);
  if (directory != impl_->files.end())
    result.push_back(impl_->info_locked(directory->second));
  for (const auto &[key, file] : impl_->files.prefix(prefix))
    if (key != exact)
      result.push_back(impl_->info_locked(file));
  return result;
}

CacheStats SnapshotCache::stats() const {
  std::lock_guard lock(impl_->mutex);
  return {impl_->files.size(), impl_->lru.size(), impl_->lru.estimated_bytes(),
          impl_->pending_builds, impl_->waiting_acquisitions};
}
} // namespace ctk::cache
