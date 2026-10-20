#pragma once

#include "ctk/cache/include_inventory.hpp"

#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <functional>
#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <map>
#include <memory>
#include <openssl/evp.h>
#include <set>
#include <sqlite3.h>
#include <stdexcept>
#include <string>

namespace ctk::net::index_detail {
namespace fs = std::filesystem;

inline std::string root_key(const std::string &path) {
  if (path.empty() || !fs::path(path).is_absolute())
    throw std::invalid_argument("project_root must be an absolute path");
  // No filesystem access on the status/control path.
  auto normalized = fs::path(path).lexically_normal();
  if (normalized != normalized.root_path() && normalized.filename().empty())
    normalized = normalized.parent_path();
  return normalized.string();
}
inline std::string hex(const unsigned char *data, unsigned length) {
  static constexpr char digits[] = "0123456789abcdef";
  std::string result;
  result.reserve(length * 2);
  for (unsigned i = 0; i < length; ++i) {
    result += digits[data[i] >> 4];
    result += digits[data[i] & 15];
  }
  return result;
}
inline std::string digest_text(const std::string &value) {
  unsigned char bytes[EVP_MAX_MD_SIZE];
  unsigned count = 0;
  if (!EVP_Digest(value.data(), value.size(), bytes, &count, EVP_sha256(),
                  nullptr))
    throw std::runtime_error("cannot hash index input");
  return hex(bytes, count);
}
inline std::string digest_file(const std::string &path,
                               const std::function<bool()> &allowed = {}) {
  if (path.starts_with("@include-tree:"))
    return digest_text(cache::include_inventory(path.substr(14), allowed));
  std::ifstream input(path, std::ios::binary);
  if (!input)
    return {};
  std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)> ctx(EVP_MD_CTX_new(),
                                                              EVP_MD_CTX_free);
  if (!ctx || !EVP_DigestInit_ex(ctx.get(), EVP_sha256(), nullptr))
    throw std::runtime_error("cannot hash index dependency");
  std::array<char, 65536> buffer;
  while (input) {
    if (allowed && !allowed())
      return {};
    input.read(buffer.data(), buffer.size());
    if (input.gcount() &&
        !EVP_DigestUpdate(ctx.get(), buffer.data(), input.gcount()))
      throw std::runtime_error("cannot hash index dependency");
  }
  if (!input.eof())
    return {};
  unsigned char bytes[EVP_MAX_MD_SIZE];
  unsigned count = 0;
  if (!EVP_DigestFinal_ex(ctx.get(), bytes, &count))
    throw std::runtime_error("cannot finalize dependency digest");
  return hex(bytes, count);
}
inline std::string json(const google::protobuf::Struct &value) {
  std::string result;
  if (!google::protobuf::util::MessageToJsonString(value, &result).ok())
    throw std::runtime_error("cannot encode index dependency manifest");
  return result;
}
inline std::map<std::string, std::string>
dependencies(const std::string &json_text) {
  google::protobuf::Struct value;
  if (!google::protobuf::util::JsonStringToMessage(json_text, &value).ok())
    throw std::runtime_error("invalid stored index dependency manifest");
  std::map<std::string, std::string> result;
  for (const auto &[path, hash] : value.fields()) {
    if (hash.kind_case() != google::protobuf::Value::kStringValue ||
        hash.string_value().empty())
      throw std::runtime_error("invalid stored index dependency digest");
    if (path == "@symbol-layout" || path.starts_with("@symbol-group:"))
      continue;
    result.emplace(path, hash.string_value());
  }
  return result;
}
inline std::set<std::string> symbol_groups(const std::string &encoded) {
  google::protobuf::Struct value;
  if (!google::protobuf::util::JsonStringToMessage(encoded, &value).ok())
    throw std::runtime_error("invalid stored index dependency manifest");
  std::set<std::string> groups;
  for (const auto &[key, field] : value.fields())
    if (key.starts_with("@symbol-group:"))
      groups.insert(field.string_value());
  return groups;
}

inline constexpr auto symbol_schema =
    "CREATE TABLE IF NOT EXISTS symbol(tu_id TEXT NOT NULL REFERENCES "
    "translation_unit(id) ON DELETE CASCADE,usr TEXT NOT NULL,name "
    "TEXT NOT NULL,qualified_name TEXT NOT NULL,kind TEXT NOT "
    "NULL,file_path TEXT NOT NULL,byte_offset INTEGER NOT "
    "NULL,is_definition INTEGER NOT NULL,line INTEGER NOT "
    "NULL,column_no INTEGER NOT NULL,signature TEXT NOT NULL,PRIMARY "
    "KEY(tu_id,usr,file_path,byte_offset,is_definition));";
inline constexpr auto symbol_indexes =
    "CREATE INDEX IF NOT EXISTS symbol_usr ON symbol(usr);"
    "CREATE INDEX IF NOT EXISTS symbol_name_prefix ON symbol(name "
    "COLLATE NOCASE); CREATE INDEX IF NOT EXISTS "
    "symbol_qualified_prefix ON symbol(qualified_name COLLATE NOCASE);"
    // Blank alias browsing must not scan unrelated symbols and their payloads.
    // Keep this covering index partial so ordinary symbols add no write cost.
    "CREATE INDEX IF NOT EXISTS symbol_alias_browse ON "
    "symbol(usr,file_path,byte_offset,is_definition,qualified_name,tu_id,kind) "
    "WHERE kind IN ('TypeAlias','Typedef');"
    // Exact lookups use the NOCASE search plus an explicit BINARY filter.
    // Maintaining both collations as separate indexes doubles name-index I/O.
    "DROP INDEX IF EXISTS symbol_name; DROP INDEX IF EXISTS symbol_qualified;";

class Database {
public:
  sqlite3 *handle = nullptr;
  Database(const fs::path &path, bool writer) {
    const int flags = (writer ? SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE
                              : SQLITE_OPEN_READONLY) |
                      SQLITE_OPEN_NOMUTEX;
    const int result =
        sqlite3_open_v2(path.string().c_str(), &handle, flags, nullptr);
    if (result != SQLITE_OK) {
      const std::string error =
          handle ? sqlite3_errmsg(handle) : "cannot open symbol index";
      if (handle)
        sqlite3_close_v2(handle);
      handle = nullptr;
      throw std::runtime_error(error);
    }
    sqlite3_busy_timeout(handle, 0);
    if (writer) {
      try {
        exec("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA "
             "foreign_keys=ON; PRAGMA wal_autocheckpoint=0; "
             "PRAGMA cache_size=-32768; PRAGMA journal_size_limit=67108864;");
        exec("CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value "
             "TEXT NOT NULL) WITHOUT ROWID;");
        exec("CREATE TABLE IF NOT EXISTS translation_unit(id TEXT PRIMARY "
             "KEY,main_file TEXT NOT NULL,working_directory TEXT NOT "
             "NULL,arguments TEXT NOT NULL,command_hash TEXT NOT "
             "NULL,input_fingerprint TEXT NOT NULL,dependencies_json TEXT NOT "
             "NULL,indexed_at INTEGER NOT NULL,status TEXT NOT NULL,last_error "
             "TEXT NOT NULL) WITHOUT ROWID;");
        // Coverage/status reads must not traverse each TU's large dependency
        // manifest, which precedes these fields in the row's overflow payload.
        exec("CREATE INDEX IF NOT EXISTS translation_unit_coverage ON "
             "translation_unit(status,indexed_at);");
        // Symbol responses need these fields without visiting the TU record's
        // potentially multi-megabyte dependency manifest overflow pages.
        exec("CREATE INDEX IF NOT EXISTS translation_unit_lookup ON "
             "translation_unit(id,main_file,arguments,status);");
        // Header contribution owners have indexed_at=0 and a JSON array of
        // referring TU IDs. Actual TUs retain positive publication timestamps.
        exec("CREATE INDEX IF NOT EXISTS translation_unit_header_members ON "
             "translation_unit(id,dependencies_json) WHERE indexed_at=0;");
        // Secondary indexes store a compact rowid instead of repeating the
        // long (TU, USR, file, offset, definition) primary key in every entry.
        exec(symbol_schema);
        exec(symbol_indexes);
      } catch (...) {
        sqlite3_close_v2(handle);
        handle = nullptr;
        throw;
      }
    }
  }
  ~Database() {
    if (handle)
      sqlite3_close_v2(handle);
  }
  Database(const Database &) = delete;
  Database &operator=(const Database &) = delete;
  void exec(const char *query) {
    char *error = nullptr;
    if (sqlite3_exec(handle, query, nullptr, nullptr, &error) != SQLITE_OK) {
      std::string message = error ? error : sqlite3_errmsg(handle);
      sqlite3_free(error);
      throw std::runtime_error(message);
    }
  }
};
class Statement {
public:
  sqlite3_stmt *handle = nullptr;
  explicit Statement(Database &db, const char *query) : db_(db) {
    if (sqlite3_prepare_v2(db.handle, query, -1, &handle, nullptr) != SQLITE_OK)
      throw std::runtime_error(sqlite3_errmsg(db.handle));
  }
  ~Statement() { sqlite3_finalize(handle); }
  void bind(int position, const std::string &value) {
    if (sqlite3_bind_text(handle, position, value.data(), value.size(),
                          SQLITE_TRANSIENT) != SQLITE_OK)
      throw std::runtime_error(sqlite3_errmsg(db_.handle));
  }
  void bind(int position, std::uint64_t value) {
    if (sqlite3_bind_int64(handle, position,
                           static_cast<sqlite3_int64>(value)) != SQLITE_OK)
      throw std::runtime_error(sqlite3_errmsg(db_.handle));
  }
  bool step() {
    const auto result = sqlite3_step(handle);
    if (result != SQLITE_ROW && result != SQLITE_DONE)
      throw std::runtime_error(sqlite3_errmsg(db_.handle));
    return result == SQLITE_ROW;
  }
  void reset() {
    if (sqlite3_reset(handle) != SQLITE_OK ||
        sqlite3_clear_bindings(handle) != SQLITE_OK)
      throw std::runtime_error(sqlite3_errmsg(db_.handle));
  }
  std::string text(int column) const {
    const auto *data = sqlite3_column_text(handle, column);
    return data ? reinterpret_cast<const char *>(data) : "";
  }
  std::uint64_t number(int column) const {
    return sqlite3_column_int64(handle, column);
  }

private:
  Database &db_;
};
class Transaction {
public:
  explicit Transaction(Database &db) : db_(db) { db_.exec("BEGIN IMMEDIATE"); }
  ~Transaction() {
    if (!committed_)
      sqlite3_exec(db_.handle, "ROLLBACK", nullptr, nullptr, nullptr);
  }
  void commit() {
    db_.exec("COMMIT");
    committed_ = true;
  }

private:
  Database &db_;
  bool committed_ = false;
};
inline std::uint64_t revision(Database &db) {
  Statement value(db, "SELECT value FROM metadata WHERE key='revision'");
  return value.step() ? std::stoull(value.text(0)) : 0;
}
inline void metadata(Database &db, const std::string &key,
                     const std::string &value) {
  Statement row(db, "INSERT INTO metadata(key,value) VALUES(?,?) ON "
                    "CONFLICT(key) DO UPDATE SET value=excluded.value");
  row.bind(1, key);
  row.bind(2, value);
  row.step();
}
inline std::uint64_t timestamp() {
  return std::chrono::duration_cast<std::chrono::seconds>(
             std::chrono::system_clock::now().time_since_epoch())
      .count();
}
} // namespace ctk::net::index_detail
