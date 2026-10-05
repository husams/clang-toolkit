#include "storage_internal.hpp"

#include <stdexcept>

namespace ctk::storage::detail {
namespace {

constexpr std::string_view kCreateV1 = R"SQL(
CREATE TABLE files (
 file_id INTEGER PRIMARY KEY, path_key TEXT NOT NULL UNIQUE
);
CREATE TABLE toolchains (
 toolchain_id INTEGER PRIMARY KEY,
 compatibility_sha256 TEXT NOT NULL UNIQUE CHECK(length(compatibility_sha256)=64 AND compatibility_sha256 NOT GLOB '*[^0-9a-f]*'),
 canonical_context BLOB NOT NULL, clang_version TEXT NOT NULL, build_identity TEXT NOT NULL,
 target_triple TEXT NOT NULL, resource_directory TEXT NOT NULL
);
CREATE TABLE compilation_profiles (
 profile_id INTEGER PRIMARY KEY,
 file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE RESTRICT,
 toolchain_id INTEGER NOT NULL REFERENCES toolchains(toolchain_id) ON DELETE RESTRICT,
 profile_sha256 TEXT NOT NULL CHECK(length(profile_sha256)=64 AND profile_sha256 NOT GLOB '*[^0-9a-f]*'),
 canonical_context BLOB NOT NULL, input_spelling TEXT NOT NULL,
 working_directory TEXT NOT NULL, sysroot TEXT NOT NULL DEFAULT '',
 UNIQUE(file_id,toolchain_id,profile_sha256)
);
CREATE TABLE compilation_arguments (
 profile_id INTEGER NOT NULL REFERENCES compilation_profiles(profile_id) ON DELETE CASCADE,
 argument_index INTEGER NOT NULL CHECK(argument_index>=0), argument TEXT NOT NULL,
 PRIMARY KEY(profile_id,argument_index)
);
CREATE TABLE snapshots (
 snapshot_id INTEGER PRIMARY KEY,
 profile_id INTEGER NOT NULL REFERENCES compilation_profiles(profile_id) ON DELETE RESTRICT,
 manifest_sha256 TEXT NOT NULL CHECK(length(manifest_sha256)=64 AND manifest_sha256 NOT GLOB '*[^0-9a-f]*'),
 canonical_manifest BLOB NOT NULL,
 state TEXT NOT NULL DEFAULT 'BUILDING' CHECK(state IN ('BUILDING','READY','STALE','DELETING')),
 created_at_ms INTEGER NOT NULL CHECK(created_at_ms>=0),
 last_accessed_at_ms INTEGER NOT NULL CHECK(last_accessed_at_ms>=0)
);
CREATE TABLE snapshot_inputs (
 snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
 input_index INTEGER NOT NULL CHECK(input_index>=0),
 file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE RESTRICT,
 role TEXT NOT NULL CHECK(role IN ('MAIN_SOURCE','HEADER','RESPONSE','PCH_INPUT','MODULE_INPUT','VFS_OVERLAY','LOOKUP')),
 observation_kind TEXT NOT NULL CHECK(observation_kind IN ('CONTENT','ABSENT','DIRECTORY')),
 digest_sha256 TEXT CHECK(digest_sha256 IS NULL OR (length(digest_sha256)=64 AND digest_sha256 NOT GLOB '*[^0-9a-f]*')),
 size_bytes INTEGER CHECK(size_bytes IS NULL OR size_bytes>=0), mtime_ns INTEGER,
 validation_context BLOB NOT NULL,
 PRIMARY KEY(snapshot_id,input_index),
 CHECK((observation_kind='CONTENT' AND digest_sha256 IS NOT NULL AND size_bytes IS NOT NULL AND mtime_ns IS NOT NULL) OR
       (observation_kind='ABSENT' AND digest_sha256 IS NULL AND size_bytes IS NULL AND mtime_ns IS NULL) OR
       (observation_kind='DIRECTORY' AND digest_sha256 IS NOT NULL AND size_bytes IS NULL AND mtime_ns IS NOT NULL))
);
CREATE TABLE blobs (
 blob_sha256 TEXT PRIMARY KEY NOT NULL CHECK(length(blob_sha256)=64 AND blob_sha256 NOT GLOB '*[^0-9a-f]*'),
 relative_path TEXT NOT NULL UNIQUE, size_bytes INTEGER NOT NULL CHECK(size_bytes>=0),
 created_at_ms INTEGER NOT NULL CHECK(created_at_ms>=0)
);
CREATE TABLE snapshot_artifacts (
 snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
 artifact_index INTEGER NOT NULL CHECK(artifact_index>=0),
 artifact_kind TEXT NOT NULL CHECK(artifact_kind IN ('TRANSLATION_UNIT','PCH','MODULE')),
 blob_sha256 TEXT NOT NULL REFERENCES blobs(blob_sha256) ON DELETE RESTRICT,
 logical_path TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,artifact_index), UNIQUE(snapshot_id,logical_path)
);
CREATE TABLE artifact_dependencies (
 snapshot_id INTEGER NOT NULL, parent_index INTEGER NOT NULL, dependency_index INTEGER NOT NULL,
 PRIMARY KEY(snapshot_id,parent_index,dependency_index),
 FOREIGN KEY(snapshot_id,parent_index) REFERENCES snapshot_artifacts(snapshot_id,artifact_index) ON DELETE CASCADE,
 FOREIGN KEY(snapshot_id,dependency_index) REFERENCES snapshot_artifacts(snapshot_id,artifact_index) ON DELETE CASCADE,
 CHECK(parent_index<>dependency_index)
);
CREATE INDEX profiles_toolchain ON compilation_profiles(toolchain_id);
CREATE INDEX snapshots_lookup ON snapshots(profile_id,state,created_at_ms DESC,snapshot_id DESC);
CREATE INDEX snapshots_manifest ON snapshots(profile_id,manifest_sha256);
CREATE INDEX inputs_reverse ON snapshot_inputs(file_id,snapshot_id);
CREATE INDEX artifacts_blob ON snapshot_artifacts(blob_sha256);
CREATE INDEX artifact_dependencies_target ON artifact_dependencies(snapshot_id,dependency_index);
CREATE UNIQUE INDEX artifacts_one_tu ON snapshot_artifacts(snapshot_id) WHERE artifact_kind='TRANSLATION_UNIT';
CREATE UNIQUE INDEX inputs_one_main ON snapshot_inputs(snapshot_id) WHERE role='MAIN_SOURCE';
CREATE TRIGGER snapshots_insert_guard BEFORE INSERT ON snapshots WHEN NEW.state<>'BUILDING'
BEGIN SELECT RAISE(ABORT,'snapshot must enter BUILDING'); END;
CREATE TRIGGER snapshots_state_guard BEFORE UPDATE OF state ON snapshots
WHEN NOT (OLD.state=NEW.state OR (OLD.state='BUILDING' AND NEW.state IN ('READY','DELETING')) OR
 (OLD.state='READY' AND NEW.state IN ('STALE','DELETING')) OR (OLD.state='STALE' AND NEW.state='DELETING'))
BEGIN SELECT RAISE(ABORT,'invalid snapshot state transition'); END;
CREATE TRIGGER snapshots_ready_guard BEFORE UPDATE OF state ON snapshots
WHEN NEW.state='READY' AND OLD.state='BUILDING'
BEGIN
 SELECT CASE WHEN (SELECT count(*) FROM snapshot_artifacts WHERE snapshot_id=NEW.snapshot_id AND artifact_kind='TRANSLATION_UNIT')<>1
  THEN RAISE(ABORT,'one TU artifact required') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM snapshot_inputs i JOIN compilation_profiles p ON p.profile_id=NEW.profile_id
  WHERE i.snapshot_id=NEW.snapshot_id AND i.file_id=p.file_id AND i.role='MAIN_SOURCE' AND i.observation_kind='CONTENT')
  THEN RAISE(ABORT,'matching main source observation required') END;
END;
)SQL";

void verify_table_columns(Database &database, std::string_view table,
                          std::initializer_list<std::string_view> expected) {
  const auto sql = "PRAGMA table_info(" + std::string(table) + ")";
  Statement columns(database.handle(), sql);
  auto field = expected.begin();
  while (columns.step()) {
    if (field == expected.end() || columns.string(1) != *field)
      throw std::runtime_error("storage schema v1 column contract mismatch");
    ++field;
  }
  if (field != expected.end())
    throw std::runtime_error("storage schema v1 column contract mismatch");
}

std::vector<std::string> schema_definitions(sqlite3 *database) {
  Statement query(database,
      "SELECT type||':'||name||':'||sql FROM sqlite_master "
      "WHERE sql IS NOT NULL AND type IN ('table','index','trigger','view') "
      "ORDER BY type,name");
  std::vector<std::string> definitions;
  while (query.step()) definitions.push_back(query.string(0));
  return definitions;
}

void verify_schema_definitions(Database &database) {
  sqlite3 *expected = nullptr;
  if (sqlite3_open_v2(":memory:", &expected,
                      SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE, nullptr) != SQLITE_OK) {
    const std::string message = expected ? sqlite3_errmsg(expected) : "SQLite error";
    sqlite3_close_v2(expected);
    throw std::runtime_error("create expected storage schema: " + message);
  }
  try {
    char *error = nullptr;
    const auto status = sqlite3_exec(expected, kCreateV1.data(), nullptr, nullptr,
                                     &error);
    if (status != SQLITE_OK) {
      const std::string message = error ? error : sqlite3_errmsg(expected);
      sqlite3_free(error);
      throw std::runtime_error("build expected storage schema: " + message);
    }
    const auto expected_definitions = schema_definitions(expected);
    if (schema_definitions(database.handle()) != expected_definitions)
      throw std::runtime_error("storage schema v1 definition mismatch");
  } catch (...) {
    sqlite3_close_v2(expected);
    throw;
  }
  sqlite3_close_v2(expected);
}

void verify_schema_v1(Database &database) {
  if (database.scalar_integer(
          "SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") != 9 ||
      database.scalar_integer(
          "SELECT count(*) FROM sqlite_master WHERE type='index' AND sql IS NOT NULL") != 8 ||
      database.scalar_integer(
          "SELECT count(*) FROM sqlite_master WHERE type='trigger'") != 3)
    throw std::runtime_error("storage schema v1 object count mismatch");
  verify_table_columns(database, "files", {"file_id", "path_key"});
  verify_table_columns(database, "toolchains", {"toolchain_id", "compatibility_sha256", "canonical_context", "clang_version", "build_identity", "target_triple", "resource_directory"});
  verify_table_columns(database, "compilation_profiles", {"profile_id", "file_id", "toolchain_id", "profile_sha256", "canonical_context", "input_spelling", "working_directory", "sysroot"});
  verify_table_columns(database, "compilation_arguments", {"profile_id", "argument_index", "argument"});
  verify_table_columns(database, "snapshots", {"snapshot_id", "profile_id", "manifest_sha256", "canonical_manifest", "state", "created_at_ms", "last_accessed_at_ms"});
  verify_table_columns(database, "snapshot_inputs", {"snapshot_id", "input_index", "file_id", "role", "observation_kind", "digest_sha256", "size_bytes", "mtime_ns", "validation_context"});
  verify_table_columns(database, "blobs", {"blob_sha256", "relative_path", "size_bytes", "created_at_ms"});
  verify_table_columns(database, "snapshot_artifacts", {"snapshot_id", "artifact_index", "artifact_kind", "blob_sha256", "logical_path"});
  verify_table_columns(database, "artifact_dependencies", {"snapshot_id", "parent_index", "dependency_index"});
  verify_schema_definitions(database);
}

} // namespace

void migrate(Database &database) {
  const auto version = database.scalar_integer("PRAGMA user_version");
  if (version > 1)
    throw std::runtime_error("storage schema is newer than this server");
  if (version == 1) {
    verify_schema_v1(database);
    return;
  }
  if (database.scalar_integer(
          "SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") != 0)
    throw std::runtime_error("unversioned storage database is not empty");

  Transaction transaction(database);
  database.exec(kCreateV1);
  database.exec("PRAGMA user_version=1");
  transaction.commit();
  verify_schema_v1(database);
}

} // namespace ctk::storage::detail
