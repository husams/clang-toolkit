#pragma once

#include "ctk/cache/snapshot.hpp"

#include <condition_variable>
#include <exception>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace ctk::cache::detail {

struct SnapshotRecord;

struct Flight {
  std::mutex mutex;
  std::condition_variable_any ready;
  bool done = false;
  SnapshotPtr snapshot;
  std::uint64_t publication_epoch = 0;
  std::exception_ptr error;
};

struct ProfileEntry {
  explicit ProfileEntry(std::string bytes)
      : canonical_context(std::move(bytes)) {}
  const std::string canonical_context;
  std::vector<std::shared_ptr<SnapshotRecord>> generations;
  std::shared_ptr<Flight> flight;
};

// Only the radix terminal owns this authoritative path record. All fields below
// (except immutable identity) require the cache's one metadata mutex.
struct FileEntry {
  explicit FileEntry(std::string key) : path_key(std::move(key)) {}
  const std::string path_key;
  std::optional<InputObservation> observation_hint;
  std::uint64_t invalidation_epoch = 0;
  std::unordered_map<std::string, std::shared_ptr<ProfileEntry>> profiles;
  std::vector<std::weak_ptr<SnapshotRecord>> dependent_snapshots;
};

struct SnapshotRecord {
  SnapshotPtr snapshot;
  std::weak_ptr<ProfileEntry> profile;
  std::vector<std::weak_ptr<FileEntry>> dependencies;
  bool reusable = true;
};

} // namespace ctk::cache::detail
