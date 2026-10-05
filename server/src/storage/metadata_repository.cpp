#include "storage_internal.hpp"

#include <algorithm>
#include <map>
#include <stdexcept>

namespace ctk::storage::detail {
namespace {

std::string_view role_name(InputRole role) {
  switch (role) {
  case InputRole::MainSource: return "MAIN_SOURCE";
  case InputRole::Header: return "HEADER";
  case InputRole::Response: return "RESPONSE";
  case InputRole::PchInput: return "PCH_INPUT";
  case InputRole::ModuleInput: return "MODULE_INPUT";
  case InputRole::VfsOverlay: return "VFS_OVERLAY";
  case InputRole::Lookup: return "LOOKUP";
  }
  throw std::invalid_argument("unknown input role");
}

InputRole parse_role(std::string_view role) {
  if (role == "MAIN_SOURCE") return InputRole::MainSource;
  if (role == "HEADER") return InputRole::Header;
  if (role == "RESPONSE") return InputRole::Response;
  if (role == "PCH_INPUT") return InputRole::PchInput;
  if (role == "MODULE_INPUT") return InputRole::ModuleInput;
  if (role == "VFS_OVERLAY") return InputRole::VfsOverlay;
  if (role == "LOOKUP") return InputRole::Lookup;
  throw std::runtime_error("unknown stored input role");
}

std::string_view observation_name(ObservationKind kind) {
  switch (kind) {
  case ObservationKind::Content: return "CONTENT";
  case ObservationKind::Absent: return "ABSENT";
  case ObservationKind::Directory: return "DIRECTORY";
  }
  throw std::invalid_argument("unknown observation kind");
}

ObservationKind parse_observation(std::string_view kind) {
  if (kind == "CONTENT") return ObservationKind::Content;
  if (kind == "ABSENT") return ObservationKind::Absent;
  if (kind == "DIRECTORY") return ObservationKind::Directory;
  throw std::runtime_error("unknown stored observation kind");
}

std::string_view artifact_name(ArtifactKind kind) {
  switch (kind) {
  case ArtifactKind::TranslationUnit: return "TRANSLATION_UNIT";
  case ArtifactKind::Pch: return "PCH";
  case ArtifactKind::Module: return "MODULE";
  }
  throw std::invalid_argument("unknown artifact kind");
}

ArtifactKind parse_artifact(std::string_view kind) {
  if (kind == "TRANSLATION_UNIT") return ArtifactKind::TranslationUnit;
  if (kind == "PCH") return ArtifactKind::Pch;
  if (kind == "MODULE") return ArtifactKind::Module;
  throw std::runtime_error("unknown stored artifact kind");
}

SnapshotState parse_state(std::string_view state) {
  if (state == "READY") return SnapshotState::Ready;
  if (state == "STALE") return SnapshotState::Stale;
  if (state == "DELETING") return SnapshotState::Deleting;
  throw std::runtime_error("unexpected stored snapshot state");
}

void bind_optional(Statement &statement, int index,
                   const std::optional<std::string> &value) {
  if (value) statement.bind(index, *value); else statement.bind_null(index);
}

void bind_optional(Statement &statement, int index,
                   const std::optional<std::uint64_t> &value) {
  if (value) statement.bind(index, *value); else statement.bind_null(index);
}

void bind_optional(Statement &statement, int index,
                   const std::optional<std::int64_t> &value) {
  if (value) statement.bind(index, *value); else statement.bind_null(index);
}

std::string require_envelope(const Bytes &bytes, std::string_view prefix) {
  if (!bytes.starts_with(prefix))
    throw std::invalid_argument("unsupported or unversioned canonical bytes");
  return bytes;
}

} // namespace

std::int64_t MetadataRepository::resolve_profile(
    const CompilationProfile &profile) {
  validate_path(profile.main_path);
  const auto file_id = resolve_file_id(profile.main_path);
  const auto toolchain_id = resolve_toolchain_id(profile.toolchain);
  const auto profile_id = resolve_profile_id(file_id, toolchain_id, profile);
  ensure_arguments(profile_id, profile.arguments);
  return profile_id;
}

std::int64_t MetadataRepository::resolve_file_id(std::string_view path) {
  auto file = Statement(database_.handle(),
      "INSERT INTO files(path_key) VALUES(?) ON CONFLICT(path_key) DO NOTHING");
  file.bind(1, path);
  file.execute();
  auto file_query = Statement(database_.handle(),
      "SELECT file_id FROM files WHERE path_key=?");
  file_query.bind(1, path);
  if (!file_query.step()) throw std::runtime_error("file identity disappeared");
  return file_query.integer(0);
}

std::int64_t MetadataRepository::resolve_toolchain_id(
    const ToolchainIdentity &identity) {
  const auto canonical = require_envelope(canonical_toolchain(identity),
                                            "ctk-toolchain-v1:");
  const auto digest = sha256(canonical);
  auto insert_toolchain = Statement(database_.handle(),
      "INSERT INTO toolchains(compatibility_sha256,canonical_context,clang_version,build_identity,target_triple,resource_directory) "
      "VALUES(?,?,?,?,?,?) ON CONFLICT(compatibility_sha256) DO NOTHING");
  insert_toolchain.bind(1, digest);
  insert_toolchain.bind_blob(2, canonical);
  insert_toolchain.bind(3, identity.clang_version);
  insert_toolchain.bind(4, identity.build_identity);
  insert_toolchain.bind(5, identity.target_triple);
  insert_toolchain.bind(6, identity.resource_directory);
  insert_toolchain.execute();
  auto toolchain = Statement(database_.handle(),
      "SELECT toolchain_id,canonical_context,clang_version,build_identity,target_triple,resource_directory "
      "FROM toolchains WHERE compatibility_sha256=?");
  toolchain.bind(1, digest);
  if (!toolchain.step()) throw std::runtime_error("toolchain identity disappeared");
  if (toolchain.blob(1) != canonical ||
      toolchain.string(2) != identity.clang_version ||
      toolchain.string(3) != identity.build_identity ||
      toolchain.string(4) != identity.target_triple ||
      toolchain.string(5) != identity.resource_directory)
    throw std::runtime_error("toolchain SHA-256 collision or inconsistent metadata");
  return toolchain.integer(0);
}

std::int64_t MetadataRepository::resolve_profile_id(
    std::int64_t file_id, std::int64_t toolchain_id,
    const CompilationProfile &profile) {
  const auto canonical = require_envelope(canonical_profile(profile),
                                            "ctk-profile-v1:");
  const auto digest = sha256(canonical);
  auto insert_profile = Statement(database_.handle(),
      "INSERT INTO compilation_profiles(file_id,toolchain_id,profile_sha256,canonical_context,input_spelling,working_directory,sysroot) "
      "VALUES(?,?,?,?,?,?,?) ON CONFLICT(file_id,toolchain_id,profile_sha256) DO NOTHING");
  insert_profile.bind(1, file_id);
  insert_profile.bind(2, toolchain_id);
  insert_profile.bind(3, digest);
  insert_profile.bind_blob(4, canonical);
  insert_profile.bind(5, profile.input_spelling);
  insert_profile.bind(6, profile.working_directory);
  insert_profile.bind(7, profile.sysroot);
  insert_profile.execute();
  auto profile_query = Statement(database_.handle(),
      "SELECT profile_id,canonical_context,input_spelling,working_directory,sysroot "
      "FROM compilation_profiles WHERE file_id=? AND toolchain_id=? AND profile_sha256=?");
  profile_query.bind(1, file_id);
  profile_query.bind(2, toolchain_id);
  profile_query.bind(3, digest);
  if (!profile_query.step()) throw std::runtime_error("profile identity disappeared");
  const auto profile_id = profile_query.integer(0);
  if (profile_query.blob(1) != canonical ||
      profile_query.string(2) != profile.input_spelling ||
      profile_query.string(3) != profile.working_directory ||
      profile_query.string(4) != profile.sysroot)
    throw std::runtime_error("profile SHA-256 collision or inconsistent metadata");
  return profile_id;
}

void MetadataRepository::ensure_arguments(
    std::int64_t profile_id, const std::vector<std::string> &arguments) {
  auto existing_args = Statement(database_.handle(),
      "SELECT argument_index,argument FROM compilation_arguments WHERE profile_id=? ORDER BY argument_index");
  existing_args.bind(1, profile_id);
  std::size_t index = 0;
  while (existing_args.step()) {
    if (index >= arguments.size() ||
        existing_args.unsigned_integer(0) != index ||
        existing_args.string(1) != arguments[index])
      throw std::runtime_error("ordered arguments disagree with canonical profile");
    ++index;
  }
  if (index != arguments.size()) {
    if (index != 0)
      throw std::runtime_error("stored profile arguments are incomplete");
    for (std::size_t argument_index = 0;
         argument_index < arguments.size(); ++argument_index) {
      auto argument = Statement(database_.handle(),
          "INSERT INTO compilation_arguments(profile_id,argument_index,argument) VALUES(?,?,?)");
      argument.bind(1, profile_id);
      argument.bind(2, static_cast<std::uint64_t>(argument_index));
      argument.bind(3, arguments[argument_index]);
      argument.execute();
    }
  }
}

void MetadataRepository::insert_inputs(SnapshotId id,
                                       const SnapshotDraft &snapshot) {
  for (std::size_t index = 0; index < snapshot.inputs.size(); ++index) {
    const auto &input = snapshot.inputs[index];
    auto file = Statement(database_.handle(),
        "INSERT INTO files(path_key) VALUES(?) ON CONFLICT(path_key) DO NOTHING");
    file.bind(1, input.path);
    file.execute();
    auto path = Statement(database_.handle(), "SELECT file_id FROM files WHERE path_key=?");
    path.bind(1, input.path);
    if (!path.step()) throw std::runtime_error("input path identity disappeared");
    auto observation = Statement(database_.handle(),
        "INSERT INTO snapshot_inputs(snapshot_id,input_index,file_id,role,observation_kind,digest_sha256,size_bytes,mtime_ns,validation_context) "
        "VALUES(?,?,?,?,?,?,?,?,?)");
    observation.bind(1, id);
    observation.bind(2, static_cast<std::uint64_t>(index));
    observation.bind(3, path.integer(0));
    observation.bind(4, role_name(input.role));
    observation.bind(5, observation_name(input.kind));
    bind_optional(observation, 6, input.digest_sha256);
    bind_optional(observation, 7, input.size_bytes);
    bind_optional(observation, 8, input.mtime_ns);
    observation.bind_blob(9, input.validation_context);
    observation.execute();
  }
}

void MetadataRepository::insert_artifacts(
    SnapshotId id, const SnapshotDraft &snapshot,
    const std::vector<std::string> &digests) {
  for (std::size_t index = 0; index < snapshot.artifacts.size(); ++index) {
    const auto &artifact = snapshot.artifacts[index];
    auto blob = Statement(database_.handle(),
        "INSERT INTO blobs(blob_sha256,relative_path,size_bytes,created_at_ms) VALUES(?,?,?,?) "
        "ON CONFLICT(blob_sha256) DO NOTHING");
    const auto relative = "blobs/" + digests[index].substr(0, 2) + "/" +
                          digests[index].substr(2, 2) + "/" + digests[index] + ".ast";
    blob.bind(1, digests[index]);
    blob.bind(2, relative);
    blob.bind(3, static_cast<std::uint64_t>(snapshot.artifacts[index].native_bytes.size()));
    blob.bind(4, snapshot.created_at_ms);
    blob.execute();
    auto verify_blob = Statement(database_.handle(),
        "SELECT relative_path,size_bytes FROM blobs WHERE blob_sha256=?");
    verify_blob.bind(1, digests[index]);
    if (!verify_blob.step() || verify_blob.string(0) != relative ||
        verify_blob.unsigned_integer(1) != snapshot.artifacts[index].native_bytes.size())
      throw std::runtime_error("blob metadata disagrees with content-addressed bytes");
    auto artifact_row = Statement(database_.handle(),
        "INSERT INTO snapshot_artifacts(snapshot_id,artifact_index,artifact_kind,blob_sha256,logical_path) VALUES(?,?,?,?,?)");
    artifact_row.bind(1, id);
    artifact_row.bind(2, static_cast<std::uint64_t>(index));
    artifact_row.bind(3, artifact_name(artifact.kind));
    artifact_row.bind(4, digests[index]);
    artifact_row.bind(5, artifact.logical_path);
    artifact_row.execute();
  }
  for (const auto &edge : snapshot.dependencies) {
    auto dependency = Statement(database_.handle(),
        "INSERT INTO artifact_dependencies(snapshot_id,parent_index,dependency_index) VALUES(?,?,?)");
    dependency.bind(1, id);
    dependency.bind(2, static_cast<std::uint64_t>(edge.parent_index));
    dependency.bind(3, static_cast<std::uint64_t>(edge.dependency_index));
    dependency.execute();
  }
}

SnapshotId MetadataRepository::publish(const SnapshotDraft &snapshot,
                                        const std::vector<std::string> &digests) {
  const auto manifest = canonical_manifest(snapshot);
  Transaction transaction(database_);
  const auto profile_id = resolve_profile(snapshot.profile);
  auto insert = Statement(database_.handle(),
      "INSERT INTO snapshots(profile_id,manifest_sha256,canonical_manifest,state,created_at_ms,last_accessed_at_ms) "
      "VALUES(?,?,?,'BUILDING',?,?)");
  insert.bind(1, profile_id);
  insert.bind(2, sha256(manifest));
  insert.bind_blob(3, manifest);
  insert.bind(4, snapshot.created_at_ms);
  insert.bind(5, snapshot.created_at_ms);
  insert.execute();
  const auto id = sqlite3_last_insert_rowid(database_.handle());
  insert_inputs(id, snapshot);
  insert_artifacts(id, snapshot, digests);
  auto ready = Statement(database_.handle(),
      "UPDATE snapshots SET state='READY' WHERE snapshot_id=? AND state='BUILDING'");
  ready.bind(1, static_cast<std::int64_t>(id));
  ready.execute();
  transaction.commit();
  return id;
}

SnapshotDescriptor MetadataRepository::load_snapshot(SnapshotId id) const {
  SnapshotDescriptor snapshot;
  auto row = Statement(database_.handle(),
      "SELECT manifest_sha256,canonical_manifest,state,created_at_ms,last_accessed_at_ms FROM snapshots WHERE snapshot_id=?");
  row.bind(1, id);
  if (!row.step()) throw std::runtime_error("snapshot no longer exists");
  snapshot.id = id;
  snapshot.manifest_sha256 = row.string(0);
  snapshot.canonical_manifest = row.blob(1);
  snapshot.state = parse_state(row.string(2));
  snapshot.created_at_ms = row.integer(3);
  snapshot.last_accessed_at_ms = row.integer(4);

  auto inputs = Statement(database_.handle(),
      "SELECT f.path_key,i.role,i.observation_kind,i.digest_sha256,i.size_bytes,i.mtime_ns,i.validation_context "
      "FROM snapshot_inputs i JOIN files f ON f.file_id=i.file_id WHERE i.snapshot_id=? ORDER BY i.input_index");
  inputs.bind(1, id);
  while (inputs.step()) {
    StoredInput input;
    input.path = inputs.string(0);
    input.role = parse_role(inputs.string(1));
    input.kind = parse_observation(inputs.string(2));
    if (!inputs.is_null(3)) input.digest_sha256 = inputs.string(3);
    if (!inputs.is_null(4)) input.size_bytes = inputs.unsigned_integer(4);
    if (!inputs.is_null(5)) input.mtime_ns = inputs.integer(5);
    input.validation_context = inputs.blob(6);
    snapshot.inputs.push_back(std::move(input));
  }

  auto artifacts = Statement(database_.handle(),
      "SELECT a.artifact_kind,a.blob_sha256,a.logical_path FROM snapshot_artifacts a "
      "WHERE a.snapshot_id=? ORDER BY a.artifact_index");
  artifacts.bind(1, id);
  while (artifacts.step())
    snapshot.artifacts.push_back({parse_artifact(artifacts.string(0)),
                                  artifacts.string(1), artifacts.string(2)});
  auto dependencies = Statement(database_.handle(),
      "SELECT parent_index,dependency_index FROM artifact_dependencies WHERE snapshot_id=? "
      "ORDER BY parent_index,dependency_index");
  dependencies.bind(1, id);
  while (dependencies.step())
    snapshot.dependencies.push_back({
        static_cast<std::uint32_t>(dependencies.unsigned_integer(0)),
        static_cast<std::uint32_t>(dependencies.unsigned_integer(1))});
  return snapshot;
}

std::vector<SnapshotDescriptor> MetadataRepository::ready_snapshots(
    const CompilationProfile &profile) {
  validate_path(profile.main_path);
  const auto toolchain_canonical = canonical_toolchain(profile.toolchain);
  const auto profile_canonical = canonical_profile(profile);
  const auto toolchain_digest = sha256(toolchain_canonical);
  const auto profile_digest = sha256(profile_canonical);
  auto identity = Statement(database_.handle(),
      "SELECT p.profile_id,p.canonical_context,p.input_spelling,p.working_directory,p.sysroot,"
      "t.canonical_context,t.clang_version,t.build_identity,t.target_triple,t.resource_directory "
      "FROM compilation_profiles p JOIN files f ON f.file_id=p.file_id "
      "JOIN toolchains t ON t.toolchain_id=p.toolchain_id WHERE f.path_key=? "
      "AND t.compatibility_sha256=? AND p.profile_sha256=?");
  identity.bind(1, profile.main_path);
  identity.bind(2, toolchain_digest);
  identity.bind(3, profile_digest);
  if (!identity.step() || identity.blob(1) != profile_canonical ||
      identity.string(2) != profile.input_spelling ||
      identity.string(3) != profile.working_directory ||
      identity.string(4) != profile.sysroot ||
      identity.blob(5) != toolchain_canonical ||
      identity.string(6) != profile.toolchain.clang_version ||
      identity.string(7) != profile.toolchain.build_identity ||
      identity.string(8) != profile.toolchain.target_triple ||
      identity.string(9) != profile.toolchain.resource_directory)
    return {};
  const auto profile_id = identity.integer(0);

  auto arguments = Statement(database_.handle(),
      "SELECT argument_index,argument FROM compilation_arguments WHERE profile_id=? ORDER BY argument_index");
  arguments.bind(1, profile_id);
  std::size_t argument_index = 0;
  while (arguments.step()) {
    if (argument_index >= profile.arguments.size() ||
        arguments.unsigned_integer(0) != argument_index ||
        arguments.string(1) != profile.arguments[argument_index])
      return {};
    ++argument_index;
  }
  if (argument_index != profile.arguments.size()) return {};

  auto query = Statement(database_.handle(),
      "SELECT snapshot_id FROM snapshots WHERE profile_id=? AND state='READY' "
      "ORDER BY created_at_ms DESC,snapshot_id DESC");
  query.bind(1, profile_id);
  std::vector<SnapshotDescriptor> result;
  while (query.step()) result.push_back(load_snapshot(query.integer(0)));
  return result;
}

void MetadataRepository::set_state(SnapshotId id, SnapshotState state) {
  const auto name = state == SnapshotState::Stale ? "STALE" : "DELETING";
  auto update = Statement(database_.handle(),
      "UPDATE snapshots SET state=? WHERE snapshot_id=? AND state IN ('READY','STALE')");
  update.bind(1, name);
  update.bind(2, id);
  update.execute();
}

std::vector<std::pair<std::string, std::uint64_t>>
MetadataRepository::unreferenced_blobs(std::size_t limit) const {
  auto query = Statement(database_.handle(),
      "SELECT b.blob_sha256,b.size_bytes FROM blobs b WHERE NOT EXISTS "
      "(SELECT 1 FROM snapshot_artifacts a WHERE a.blob_sha256=b.blob_sha256) LIMIT ?");
  query.bind(1, static_cast<std::uint64_t>(limit));
  std::vector<std::pair<std::string, std::uint64_t>> result;
  while (query.step()) result.emplace_back(query.string(0), query.unsigned_integer(1));
  return result;
}

void MetadataRepository::remove_blob_row(std::string_view digest) {
  auto remove = Statement(database_.handle(), "DELETE FROM blobs WHERE blob_sha256=?");
  remove.bind(1, digest);
  remove.execute();
}

std::optional<std::uint64_t>
MetadataRepository::blob_size(std::string_view digest) const {
  auto query = Statement(database_.handle(),
      "SELECT size_bytes FROM blobs WHERE blob_sha256=?");
  query.bind(1, digest);
  if (!query.step()) return std::nullopt;
  return query.unsigned_integer(0);
}

void MetadataRepository::delete_snapshot(SnapshotId id) {
  auto remove = Statement(database_.handle(),
      "DELETE FROM snapshots WHERE snapshot_id=? AND state='DELETING'");
  remove.bind(1, id);
  remove.execute();
}

std::vector<SnapshotId>
MetadataRepository::snapshots_in_state(std::string_view state,
                                       std::size_t limit) const {
  if (state != "BUILDING" && state != "DELETING" && state != "READY" &&
      state != "STALE")
    throw std::invalid_argument("invalid snapshot state query");
  auto query = Statement(database_.handle(),
      "SELECT snapshot_id FROM snapshots WHERE state=? ORDER BY snapshot_id LIMIT ?");
  query.bind(1, state);
  query.bind(2, static_cast<std::uint64_t>(limit));
  std::vector<SnapshotId> result;
  while (query.step()) result.push_back(query.integer(0));
  return result;
}

void MetadataRepository::abandon_building(SnapshotId id) {
  auto update = Statement(database_.handle(),
      "UPDATE snapshots SET state='DELETING' WHERE snapshot_id=? AND state='BUILDING'");
  update.bind(1, id);
  update.execute();
}

void MetadataRepository::prune_unused_identity_rows() {
  database_.exec("DELETE FROM compilation_profiles WHERE NOT EXISTS(SELECT 1 FROM snapshots s WHERE s.profile_id=compilation_profiles.profile_id)");
  database_.exec("DELETE FROM toolchains WHERE NOT EXISTS(SELECT 1 FROM compilation_profiles p WHERE p.toolchain_id=toolchains.toolchain_id)");
  database_.exec("DELETE FROM files WHERE NOT EXISTS(SELECT 1 FROM compilation_profiles p WHERE p.file_id=files.file_id) AND NOT EXISTS(SELECT 1 FROM snapshot_inputs i WHERE i.file_id=files.file_id)");
}

std::vector<std::string> MetadataRepository::blob_digests(SnapshotId id) const {
  auto query = Statement(database_.handle(),
      "SELECT blob_sha256 FROM snapshot_artifacts WHERE snapshot_id=?");
  query.bind(1, id);
  std::vector<std::string> result;
  while (query.step()) result.push_back(query.string(0));
  std::ranges::sort(result);
  result.erase(std::unique(result.begin(), result.end()), result.end());
  return result;
}

std::vector<SnapshotId> MetadataRepository::retention_candidates(std::size_t limit) const {
  auto query = Statement(database_.handle(),
      "SELECT snapshot_id FROM snapshots WHERE state IN ('STALE','READY') "
      "ORDER BY CASE state WHEN 'STALE' THEN 0 ELSE 1 END,last_accessed_at_ms ASC,snapshot_id ASC LIMIT ?");
  query.bind(1, static_cast<std::uint64_t>(limit));
  std::vector<SnapshotId> result;
  while (query.step()) result.push_back(query.integer(0));
  return result;
}

std::unordered_set<std::string> MetadataRepository::referenced_digests() const {
  auto query = Statement(database_.handle(), "SELECT blob_sha256 FROM snapshot_artifacts");
  std::unordered_set<std::string> result;
  while (query.step()) result.insert(query.string(0));
  return result;
}

bool MetadataRepository::digest_referenced(std::string_view digest) const {
  auto query = Statement(database_.handle(),
      "SELECT 1 FROM snapshot_artifacts WHERE blob_sha256=? LIMIT 1");
  query.bind(1, digest);
  return query.step();
}

std::size_t MetadataRepository::count_snapshots(SnapshotState state) const {
  const auto name = state == SnapshotState::Ready ? "READY" : "STALE";
  auto query = Statement(database_.handle(), "SELECT count(*) FROM snapshots WHERE state=?");
  query.bind(1, name);
  if (!query.step()) return 0;
  return static_cast<std::size_t>(query.unsigned_integer(0));
}

} // namespace ctk::storage::detail
