#include "cache_state.hpp"

#include "ctk/cache/reverse_index.hpp"

#include <algorithm>
#include <utility>

namespace ctk::cache {
using detail::AcquisitionAttempt;
using detail::AcquisitionRequest;
using detail::FileEntry;
using detail::ProfileEntry;
using detail::SnapshotRecord;

SnapshotCache::Impl::Impl(std::shared_ptr<SnapshotLoader> adapter,
                          CacheOptions limits)
    : loader(std::move(adapter)), options(std::move(limits)) {
  if (!loader || !options.profile_digest ||
      options.max_acquisition_attempts == 0)
    throw std::invalid_argument(
        "cache requires loader, digest and acquisition attempts");
}

// The radix terminal remains the sole authoritative owner of each pathname.
std::shared_ptr<FileEntry>
SnapshotCache::Impl::ensure_file_locked(const std::string &path) {
  const auto found = files.find(path);
  if (found != files.end())
    return found->second;
  if (files.size() >= options.max_paths)
    throw ResourceExhausted();
  auto file = std::make_shared<FileEntry>(path);
  files.try_emplace(path, file);
  return file;
}

// Reclaim only idle metadata; active flights and retained owners keep their
// profiles indexed. This is a live-record cap, not a lifetime-context cap.
void SnapshotCache::Impl::prune_profiles_locked(FileEntry &file) {
  if (file.profiles.size() < options.max_profiles_per_file)
    return;
  std::erase_if(file.profiles, [](const auto &item) {
    return item.second->generations.empty() && !item.second->flight;
  });
}

// A digest hit must match the full identity. A collision returns no profile,
// selecting an ephemeral build without replacing the existing context.
std::shared_ptr<ProfileEntry>
SnapshotCache::Impl::find_profile_locked(const std::shared_ptr<FileEntry> &file,
                                         const AcquisitionRequest &request) {
  if (!request.context.reusable)
    return {};
  const auto hit = file->profiles.find(request.digest);
  if (hit != file->profiles.end())
    return hit->second->canonical_context == request.identity ? hit->second
                                                              : nullptr;
  prune_profiles_locked(*file);
  if (file->profiles.size() >= options.max_profiles_per_file)
    throw ResourceExhausted();
  auto profile = std::make_shared<ProfileEntry>(request.identity);
  file->profiles.emplace(request.digest, profile);
  return profile;
}

// Reserve one build slot only after joining an existing flight was ruled out.
// No throwing work remains after this flight becomes visible to other callers.
void SnapshotCache::Impl::start_flight_locked(AcquisitionAttempt &attempt) {
  if (pending_builds >= options.max_pending_builds)
    throw ResourceExhausted();
  attempt.flight = std::make_shared<detail::Flight>();
  if (attempt.profile)
    attempt.profile->flight = attempt.flight;
  ++pending_builds;
  attempt.generation = next_generation++;
}

bool SnapshotCache::Impl::same_file_locked(
    const AcquisitionRequest &request,
    const AcquisitionAttempt &attempt) const {
  const auto found = files.find(request.path);
  return found != files.end() && found->second == attempt.file;
}

// The global fence also covers dependencies first discovered during parsing.
bool SnapshotCache::Impl::can_publish_locked(
    const AcquisitionRequest &request,
    const AcquisitionAttempt &attempt) const {
  return attempt.epoch == invalidation_epoch &&
         same_file_locked(request, attempt);
}

// Copies and deduplication were prepared unlocked. Only the latest advisory
// hints are moved here; each snapshot keeps its own immutable observations.
void SnapshotCache::Impl::register_inputs_locked(
    detail::PreparedSnapshot &prepared) {
  for (auto &observation : prepared.observations) {
    auto file = ensure_file_locked(observation.path);
    file->observation_hint = std::move(observation);
    prepared.inputs.push_back(std::move(file));
  }
}

// Reserve reverse edges and retention storage before linking the generation.
// Any native owners evicted during commit stay in retired until after
// unlocking.
void SnapshotCache::Impl::retain_generation_locked(
    const std::shared_ptr<ProfileEntry> &profile,
    detail::PreparedSnapshot &prepared, std::vector<SnapshotPtr> &retired) {
  if (!profile || options.max_generations_per_profile == 0 ||
      options.max_snapshots == 0 ||
      prepared.snapshot->estimated_bytes > options.max_estimated_bytes)
    return;
  profile->generations.reserve(profile->generations.size() + 1);
  detail::prepare_reverse_links(prepared.record, prepared.inputs);
  retired.reserve(lru.size() + 1);
  // Last allocation before commit; the following attachments use reserved
  // space.
  lru.admit(prepared.record);
  detail::attach_reverse_links(prepared.record);
  profile->generations.push_back(prepared.record);
  enforce_limits_locked(profile, retired);
}

// Pin native ownership before removing discoverability. Passing the record by
// value also keeps it alive when its profile vector erases the originating
// slot.
void SnapshotCache::Impl::retire_locked(std::shared_ptr<SnapshotRecord> record,
                                        std::vector<SnapshotPtr> &retired) {
  if (!record->reusable)
    return;
  retired.push_back(record->snapshot);
  record->reusable = false;
  lru.remove(record);
  detail::detach_reverse_links(record);
  if (const auto profile = record->profile.lock())
    std::erase(profile->generations, record);
}

// A waiter may reject a completed owner after another caller already acquired
// it. Remove only reuse references to that owner; existing pins remain valid.
void SnapshotCache::Impl::retire_snapshot_locked(
    const std::shared_ptr<ProfileEntry> &profile, const SnapshotPtr &snapshot,
    std::vector<SnapshotPtr> &retired) {
  if (!profile)
    return;
  const auto generations = profile->generations;
  for (const auto &record : generations)
    if (record->snapshot == snapshot)
      retire_locked(record, retired);
}

// Direct profiles and weak reverse edges can both name one generation; retire
// is idempotent, so repeated paths never release an active native owner twice.
void SnapshotCache::Impl::invalidate_locked(
    const std::shared_ptr<FileEntry> &file, std::vector<SnapshotPtr> &retired) {
  const auto affected = detail::affected_snapshots(*file);
  retired.reserve(retired.size() + affected.size());
  ++file->invalidation_epoch;
  for (const auto &record : affected)
    retire_locked(record, retired);
}

// Limits apply to reusable ownership. Cursors keep their independent pins even
// after a generation loses its LRU token and profile retention reference.
void SnapshotCache::Impl::enforce_limits_locked(
    const std::shared_ptr<ProfileEntry> &profile,
    std::vector<SnapshotPtr> &retired) {
  while (profile->generations.size() > options.max_generations_per_profile)
    retire_locked(profile->generations.front(), retired);
  while (lru.size() > options.max_snapshots ||
         lru.estimated_bytes() > options.max_estimated_bytes) {
    const auto oldest = lru.oldest();
    if (!oldest)
      throw std::logic_error("expired reuse token");
    retire_locked(oldest, retired);
  }
}

FileInfo
SnapshotCache::Impl::info_locked(const std::shared_ptr<FileEntry> &file) const {
  const auto live_edges =
      std::ranges::count_if(file->dependent_snapshots,
                            [](const auto &weak) { return !weak.expired(); });
  return {file->path_key, file->observation_hint, file->invalidation_epoch,
          file->profiles.size(), static_cast<std::size_t>(live_edges)};
}

// Native validation can inspect lazy dependencies. Share the execution lane
// with cursor operations, but never hold the cache metadata mutex while
// waiting.
bool SnapshotCache::Impl::validate(const SnapshotEntry &snapshot) const {
  std::lock_guard lane(snapshot.execution_mutex());
  return loader->validate(snapshot);
}
} // namespace ctk::cache
