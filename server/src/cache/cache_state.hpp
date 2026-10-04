#pragma once

#include "acquisition.hpp"
#include "ctk/cache/radix_tree.hpp"
#include "ctk/cache/reuse_policy.hpp"
#include "ctk/cache/snapshot_cache.hpp"

namespace ctk::cache {

// Implementation-only state shared by metadata operations and acquisition.
// Methods ending in _locked require mutex to be held by their caller. Methods
// without that suffix manage their own locking; loaders never run under mutex.
class SnapshotCache::Impl {
public:
  Impl(std::shared_ptr<SnapshotLoader> adapter, CacheOptions limits);

  SnapshotPtr acquire(const detail::AcquisitionRequest &request);
  detail::AcquisitionAttempt
  select_attempt(const detail::AcquisitionRequest &request);
  SnapshotPtr acquire_once(const detail::AcquisitionRequest &request);
  SnapshotPtr reuse_candidate(const detail::AcquisitionRequest &request,
                              const detail::AcquisitionAttempt &attempt);
  SnapshotPtr join_flight(const detail::AcquisitionRequest &request,
                          const detail::AcquisitionAttempt &attempt);
  SnapshotPtr build_generation(const detail::AcquisitionRequest &request,
                               const detail::AcquisitionAttempt &attempt);
  SnapshotPtr load_snapshot(const detail::AcquisitionRequest &request,
                            const detail::AcquisitionAttempt &attempt);
  SnapshotPtr publish_generation(const detail::AcquisitionRequest &request,
                                 const detail::AcquisitionAttempt &attempt,
                                 detail::PreparedSnapshot &prepared,
                                 std::vector<SnapshotPtr> &retired);
  void finish_flight(const detail::AcquisitionAttempt &attempt,
                     const detail::FlightResult &result);

  std::shared_ptr<detail::FileEntry>
  ensure_file_locked(const std::string &path);
  std::shared_ptr<detail::ProfileEntry>
  find_profile_locked(const std::shared_ptr<detail::FileEntry> &file,
                      const detail::AcquisitionRequest &request);
  void prune_profiles_locked(detail::FileEntry &file);
  void start_flight_locked(detail::AcquisitionAttempt &attempt);
  bool same_file_locked(const detail::AcquisitionRequest &request,
                        const detail::AcquisitionAttempt &attempt) const;
  bool can_publish_locked(const detail::AcquisitionRequest &request,
                          const detail::AcquisitionAttempt &attempt) const;
  void register_inputs_locked(detail::PreparedSnapshot &prepared);
  void
  retain_generation_locked(const std::shared_ptr<detail::ProfileEntry> &profile,
                           detail::PreparedSnapshot &prepared,
                           std::vector<SnapshotPtr> &retired);
  void retire_locked(std::shared_ptr<detail::SnapshotRecord> record,
                     std::vector<SnapshotPtr> &retired);
  void
  retire_snapshot_locked(const std::shared_ptr<detail::ProfileEntry> &profile,
                         const SnapshotPtr &snapshot,
                         std::vector<SnapshotPtr> &retired);
  void invalidate_locked(const std::shared_ptr<detail::FileEntry> &file,
                         std::vector<SnapshotPtr> &retired);
  void
  enforce_limits_locked(const std::shared_ptr<detail::ProfileEntry> &profile,
                        std::vector<SnapshotPtr> &retired);
  FileInfo info_locked(const std::shared_ptr<detail::FileEntry> &file) const;
  bool validate(const SnapshotEntry &snapshot) const;

  std::shared_ptr<SnapshotLoader> loader;
  const CacheOptions options;
  mutable std::mutex mutex;
  RadixTree<std::shared_ptr<detail::FileEntry>> files;
  detail::ReusePolicy lru;
  std::uint64_t invalidation_epoch = 0;
  std::uint64_t next_generation = 1;
  std::size_t pending_builds = 0;
  std::size_t waiting_acquisitions = 0;
};

} // namespace ctk::cache
