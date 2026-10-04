#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

namespace ctk::cache {

struct CompilationContext;

enum class InputKind { File, Absent, Directory };

// Digests describe the buffers actually consumed, or relevant directory names.
// Absence/directory validation_context tells the adapter how to repeat lookup.
struct InputObservation {
  std::string path;
  InputKind kind = InputKind::File;
  std::string content_digest;
  std::string validation_context;
  std::optional<std::uint64_t> stat_hint;
};

// Implemented by the native adapter; no LLVM types cross this boundary.
class NativeSnapshotOwner {
public:
  virtual ~NativeSnapshotOwner() = default;
};

struct LoadedSnapshot {
  std::shared_ptr<const NativeSnapshotOwner> owner;
  std::vector<InputObservation> inputs;
  std::size_t estimated_bytes = 0;
};

class SnapshotEntry final {
public:
  SnapshotEntry(std::uint64_t generation, std::string profile_identity,
                LoadedSnapshot loaded);

  const std::uint64_t generation;
  const std::string profile_identity;
  const std::string canonical_manifest;
  const std::vector<InputObservation> inputs;
  const std::shared_ptr<const NativeSnapshotOwner> owner;
  const std::size_t estimated_bytes;

  // Hold this lane for every native operation; never acquire it under the
  // cache metadata lock. Immutable ownership does not make Clang thread-safe.
  std::mutex &execution_mutex() const noexcept { return execution_mutex_; }

private:
  mutable std::mutex execution_mutex_;
};

using SnapshotPtr = std::shared_ptr<const SnapshotEntry>;

class SnapshotLoader {
public:
  virtual ~SnapshotLoader() = default;
  // Capture a stable native owner and complete consumed-input/lookup manifest.
  // This callback deliberately receives no individual waiter's cancellation.
  virtual LoadedSnapshot load(const std::string &path,
                              const CompilationContext &context) = 0;
  // Repeat content/absence/directory checks, including lazy native
  // dependencies. Stat hints alone must never establish freshness. The cache
  // holds the snapshot's execution lane; the adapter must not lock it again.
  // Validation of different snapshots may run concurrently.
  virtual bool validate(const SnapshotEntry &snapshot) = 0;
};

} // namespace ctk::cache
