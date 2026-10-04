#pragma once

#include "ctk/cache/compilation_context.hpp"
#include "ctk/cache/snapshot.hpp"

#include <functional>
#include <limits>
#include <memory>
#include <stdexcept>
#include <stop_token>
#include <string_view>
#include <vector>

namespace ctk::cache {

struct CacheOptions {
  std::size_t max_snapshots = 64;
  std::size_t max_estimated_bytes = std::numeric_limits<std::size_t>::max();
  std::size_t max_generations_per_profile = 2;
  std::size_t max_pending_builds = 8;
  std::size_t max_paths = 65536;
  std::size_t max_profiles_per_file = 32;
  std::size_t max_inputs_per_snapshot = 16384;
  std::size_t max_acquisition_attempts = 8;
  std::function<std::string(std::string_view)> profile_digest =
      compilation_digest;
};

class AcquisitionCancelled : public std::runtime_error {
public:
  AcquisitionCancelled()
      : std::runtime_error("snapshot acquisition cancelled") {}
};
class ResourceExhausted : public std::runtime_error {
public:
  ResourceExhausted() : std::runtime_error("cache resource limit reached") {}
};

struct FileInfo {
  std::string path;
  std::optional<InputObservation> observation_hint;
  std::uint64_t invalidation_epoch;
  std::size_t profiles;
  std::size_t reverse_dependencies;
};
struct CacheStats {
  std::size_t paths;
  std::size_t reusable_snapshots;
  std::size_t estimated_reusable_bytes;
  std::size_t pending_builds;
  std::size_t waiting_acquisitions;
};

// Thread-safe coordination; loaders/validators and native destructors never run
// under metadata locking. Destruction requires all caller operations to finish.
class SnapshotCache final {
public:
  explicit SnapshotCache(std::shared_ptr<SnapshotLoader> loader,
                         CacheOptions options = {});
  ~SnapshotCache();
  SnapshotCache(const SnapshotCache &) = delete;
  SnapshotCache &operator=(const SnapshotCache &) = delete;

  SnapshotPtr acquire(std::string_view path, const CompilationContext &context,
                      std::stop_token cancellation = {});
  void invalidate_path(std::string_view path);
  void invalidate_directory(std::string_view directory);
  // Changes also invalidate the parent directory namespace (negative lookups).
  void notify_path_change(std::string_view path);
  void clear_reuse();
  bool erase_unused_path(std::string_view path);

  // Value snapshots are safe to iterate after mutation or cache destruction.
  // Tree iterators/entry pointers never escape the metadata critical section.
  std::vector<FileInfo> files() const;
  std::vector<FileInfo> files_in_directory(std::string_view directory) const;
  CacheStats stats() const;

private:
  class Impl;
  std::unique_ptr<Impl> impl_;
};

} // namespace ctk::cache
