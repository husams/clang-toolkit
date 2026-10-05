#pragma once

#include "ctk/storage/store.hpp"

#include <sqlite3.h>

#include <filesystem>
#include <functional>
#include <condition_variable>
#include <memory>
#include <mutex>
#include <string_view>
#include <unordered_map>
#include <unordered_set>

namespace ctk::storage::detail {

class Statement final {
public:
  Statement(sqlite3 *database, std::string_view sql);
  ~Statement();
  Statement(const Statement &) = delete;
  Statement &operator=(const Statement &) = delete;
  Statement(Statement &&other) noexcept;
  Statement &operator=(Statement &&other) noexcept;

  void bind(int index, std::int64_t value);
  void bind(int index, std::uint64_t value);
  void bind(int index, std::string_view value);
  void bind_blob(int index, std::string_view value);
  void bind_null(int index);
  bool step();
  void execute();
  std::int64_t integer(int column) const;
  std::uint64_t unsigned_integer(int column) const;
  std::string string(int column) const;
  Bytes blob(int column) const;
  bool is_null(int column) const;

private:
  sqlite3_stmt *statement_ = nullptr;
};

class Database final {
public:
  explicit Database(const std::filesystem::path &path);
  ~Database();
  Database(const Database &) = delete;
  Database &operator=(const Database &) = delete;
  sqlite3 *handle() const noexcept { return database_; }
  void exec(std::string_view sql) const;
  std::int64_t scalar_integer(std::string_view sql) const;
  void begin_immediate() const;
  void commit() const;
  void rollback() const noexcept;

private:
  void configure_connection();
  sqlite3 *database_ = nullptr;
};

class Transaction final {
public:
  explicit Transaction(const Database &database);
  ~Transaction();
  void commit();

private:
  const Database &database_;
  bool committed_ = false;
};

void migrate(Database &database);
std::string sha256(std::string_view bytes);
Bytes canonical_toolchain(const ToolchainIdentity &toolchain);
Bytes canonical_profile(const CompilationProfile &profile);
Bytes canonical_manifest(const SnapshotDraft &snapshot);
std::string validate_sha256(std::string_view digest);
void validate_path(std::string_view path);
void validate_snapshot_draft(const SnapshotDraft &snapshot,
                             std::uint64_t maximum_artifact_size);
void validate_stored_closure(const SnapshotDescriptor &snapshot);

class RootLock final {
public:
  explicit RootLock(const std::filesystem::path &root);
  ~RootLock();
  RootLock(const RootLock &) = delete;
  RootLock &operator=(const RootLock &) = delete;

private:
  int descriptor_ = -1;
};

class BlobStore final {
public:
  BlobStore(std::filesystem::path root, std::uint64_t max_artifact_bytes);
  std::string publish(std::string_view bytes, std::int64_t created_at_ms);
  Bytes read(std::string_view digest, std::uint64_t expected_size) const;
  void remove(std::string_view digest) const;
  std::uint64_t physical_bytes(std::size_t budget) const;
  std::size_t clean_staging(std::size_t budget) const;
  std::size_t clean_orphans(const std::function<bool(std::string_view)> &is_referenced,
                            std::size_t budget) const;
  std::filesystem::path blob_path(std::string_view digest) const;
  const std::filesystem::path &root() const noexcept { return root_; }

private:
  void ensure_layout() const;
  void sync_directory(const std::filesystem::path &path) const;
  std::filesystem::path root_;
  std::uint64_t max_artifact_bytes_;
};

class MetadataRepository final {
public:
  explicit MetadataRepository(Database &database) : database_(database) {}
  SnapshotId publish(const SnapshotDraft &snapshot,
                    const std::vector<std::string> &digests);
  std::vector<SnapshotDescriptor>
  ready_snapshots(const CompilationProfile &profile);
  SnapshotDescriptor load_snapshot(SnapshotId id) const;
  void set_state(SnapshotId id, SnapshotState state);
  std::vector<std::pair<std::string, std::uint64_t>> unreferenced_blobs(std::size_t limit) const;
  void remove_blob_row(std::string_view digest);
  std::optional<std::uint64_t> blob_size(std::string_view digest) const;
  void delete_snapshot(SnapshotId id);
  std::vector<SnapshotId> snapshots_in_state(std::string_view state,
                                             std::size_t limit) const;
  void abandon_building(SnapshotId id);
  void prune_unused_identity_rows();
  std::vector<std::string> blob_digests(SnapshotId id) const;
  std::vector<SnapshotId> retention_candidates(std::size_t limit) const;
  std::unordered_set<std::string> referenced_digests() const;
  bool digest_referenced(std::string_view digest) const;
  std::size_t count_snapshots(SnapshotState state) const;

private:
  std::int64_t resolve_profile(const CompilationProfile &profile);
  std::int64_t resolve_file_id(std::string_view path);
  std::int64_t resolve_toolchain_id(const ToolchainIdentity &toolchain);
  std::int64_t resolve_profile_id(std::int64_t file_id,
                                 std::int64_t toolchain_id,
                                 const CompilationProfile &profile);
  void ensure_arguments(std::int64_t profile_id,
                       const std::vector<std::string> &arguments);
  void insert_inputs(SnapshotId id, const SnapshotDraft &snapshot);
  void insert_artifacts(SnapshotId id, const SnapshotDraft &snapshot,
                        const std::vector<std::string> &digests);
  Database &database_;
};

} // namespace ctk::storage::detail

namespace ctk::storage {

struct SnapshotLease::Impl {
  SnapshotDescriptor snapshot;
  std::vector<std::string> digests;
  std::function<Bytes(std::size_t)> read;
  std::function<void()> release;
  ~Impl();
};

struct Store::Impl : std::enable_shared_from_this<Store::Impl> {
  explicit Impl(StoreOptions options);
  void release_lease(SnapshotId id, const std::vector<std::string> &digests);
  void reserve_publisher_blobs(const std::vector<std::string> &digests);
  void release_publisher_blobs(const std::vector<std::string> &digests);
  SnapshotId commit_publication(const SnapshotDraft &snapshot,
                                const std::vector<std::string> &digests);
  void complete_publication(const std::vector<std::string> &digests) noexcept;
  void cleanup_failed_publication(const std::vector<std::string> &digests);
  void collect_unreferenced_locked(std::size_t budget = 4096);
  void enforce_retention_locked();
  void flush_access_times_locked();
  SnapshotDescriptor load_descriptor_locked(SnapshotId id) const;

  StoreOptions options;
  detail::RootLock root_lock;
  detail::Database database;
  detail::MetadataRepository metadata;
  std::unique_ptr<detail::BlobStore> blobs;
  mutable std::mutex mutex;
  std::unordered_map<SnapshotId, std::size_t> snapshot_leases;
  std::unordered_map<std::string, std::size_t> blob_leases;
  std::condition_variable publisher_condition;
  std::size_t active_publishers = 0;
  std::unordered_map<SnapshotId, std::int64_t> pending_access;
  std::size_t access_since_flush = 0;
};

} // namespace ctk::storage
