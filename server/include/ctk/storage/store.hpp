#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace ctk::storage {

using Bytes = std::string;
using SnapshotId = std::int64_t;

enum class InputRole {
  MainSource,
  Header,
  Response,
  PchInput,
  ModuleInput,
  VfsOverlay,
  Lookup
};
enum class ObservationKind { Content, Absent, Directory };
enum class ArtifactKind { TranslationUnit, Pch, Module };
enum class SnapshotState { Ready, Stale, Deleting };

struct ToolchainIdentity {
  std::string clang_version;
  std::string build_identity;
  std::string target_triple;
  std::string resource_directory;
  std::string resource_content_identity;
};

struct CompilationProfile {
  std::uint32_t schema_version = 1;
  std::string main_path;
  ToolchainIdentity toolchain;
  std::string input_spelling;
  std::string working_directory;
  std::string sysroot;
  std::vector<std::string> arguments;
  std::vector<std::pair<std::string, std::string>> environment;
  std::vector<std::string> vfs_overlays;
  bool reusable = true;
};

struct InputObservation {
  std::string path;
  InputRole role = InputRole::Header;
  ObservationKind kind = ObservationKind::Content;
  std::optional<std::string> digest_sha256;
  std::optional<std::uint64_t> size_bytes;
  std::optional<std::int64_t> mtime_ns;
  Bytes validation_context;
};

struct ArtifactInput {
  ArtifactKind kind = ArtifactKind::TranslationUnit;
  std::string logical_path;
  Bytes native_bytes;
};

struct ArtifactDependency {
  std::uint32_t parent_index = 0;
  std::uint32_t dependency_index = 0;
};

struct SnapshotDraft {
  CompilationProfile profile;
  std::vector<InputObservation> inputs;
  std::vector<ArtifactInput> artifacts;
  std::vector<ArtifactDependency> dependencies;
  std::int64_t created_at_ms = 0;
};

struct StoredInput {
  std::string path;
  InputRole role = InputRole::Header;
  ObservationKind kind = ObservationKind::Content;
  std::optional<std::string> digest_sha256;
  std::optional<std::uint64_t> size_bytes;
  std::optional<std::int64_t> mtime_ns;
  Bytes validation_context;
};

struct StoredArtifact {
  ArtifactKind kind = ArtifactKind::TranslationUnit;
  std::string blob_sha256;
  std::string logical_path;
};

struct SnapshotDescriptor {
  SnapshotId id = 0;
  std::string manifest_sha256;
  Bytes canonical_manifest;
  SnapshotState state = SnapshotState::Ready;
  std::int64_t created_at_ms = 0;
  std::int64_t last_accessed_at_ms = 0;
  std::vector<StoredInput> inputs;
  std::vector<StoredArtifact> artifacts;
  std::vector<ArtifactDependency> dependencies;
};

struct StoreOptions {
  std::filesystem::path root;
  std::uint64_t max_physical_bytes = 10ULL * 1024 * 1024 * 1024;
  std::uint64_t max_artifact_bytes = 2ULL * 1024 * 1024 * 1024;
  std::size_t recovery_entry_budget = 256;
  std::size_t access_write_coalesce = 64;
};

struct StoreStats {
  std::uint64_t physical_bytes = 0;
  std::size_t ready_snapshots = 0;
  std::size_t stale_snapshots = 0;
  std::size_t leased_snapshots = 0;
};

class Store;

// A lease prevents retirement from collecting any blob in the snapshot closure.
class SnapshotLease final {
public:
  ~SnapshotLease();
  SnapshotLease(const SnapshotLease &) = delete;
  SnapshotLease &operator=(const SnapshotLease &) = delete;

  const SnapshotDescriptor &descriptor() const noexcept;
  Bytes read_artifact(std::size_t artifact_index) const;

private:
  struct Impl;
  explicit SnapshotLease(std::shared_ptr<Impl> impl);
  std::shared_ptr<Impl> impl_;
  friend class Store;
};

using SnapshotLeasePtr = std::shared_ptr<SnapshotLease>;

// Typed native-artifact persistence. SQLite and filesystem details are private.
class Store final {
public:
  static std::unique_ptr<Store> open(StoreOptions options);
  ~Store();
  Store(const Store &) = delete;
  Store &operator=(const Store &) = delete;

  SnapshotId publish(const SnapshotDraft &snapshot);
  std::vector<SnapshotLeasePtr>
  acquire_ready(const CompilationProfile &profile);
  void mark_stale(SnapshotId id);
  void retire(SnapshotId id);
  void enforce_retention();
  void recover();
  StoreStats stats() const;

private:
  struct Impl;
  explicit Store(std::shared_ptr<Impl> impl);
  std::shared_ptr<Impl> impl_;
  friend class SnapshotLease;
};

} // namespace ctk::storage
