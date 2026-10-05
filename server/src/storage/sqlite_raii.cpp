#include "storage_internal.hpp"

#include <limits>
#include <stdexcept>
#include <utility>

namespace ctk::storage::detail {
namespace {

[[noreturn]] void fail(sqlite3 *database, std::string_view action) {
  throw std::runtime_error(std::string(action) + ": " +
                           (database ? sqlite3_errmsg(database) : "SQLite error"));
}

} // namespace

Statement::Statement(sqlite3 *database, std::string_view sql) {
  const auto status = sqlite3_prepare_v2(database, sql.data(),
                                         static_cast<int>(sql.size()),
                                         &statement_, nullptr);
  if (status != SQLITE_OK) {
    sqlite3_finalize(statement_);
    statement_ = nullptr;
    fail(database, "prepare statement");
  }
}

Statement::~Statement() { sqlite3_finalize(statement_); }

Statement::Statement(Statement &&other) noexcept
    : statement_(std::exchange(other.statement_, nullptr)) {}

Statement &Statement::operator=(Statement &&other) noexcept {
  if (this != &other) {
    sqlite3_finalize(statement_);
    statement_ = std::exchange(other.statement_, nullptr);
  }
  return *this;
}

void Statement::bind(int index, std::int64_t value) {
  if (sqlite3_bind_int64(statement_, index, value) != SQLITE_OK)
    fail(sqlite3_db_handle(statement_), "bind integer");
}

void Statement::bind(int index, std::uint64_t value) {
  if (value > static_cast<std::uint64_t>(std::numeric_limits<sqlite3_int64>::max()))
    throw std::overflow_error("SQLite integer is out of range");
  bind(index, static_cast<std::int64_t>(value));
}

void Statement::bind(int index, std::string_view value) {
  if (sqlite3_bind_text(statement_, index, value.data(),
                        static_cast<int>(value.size()), SQLITE_TRANSIENT) != SQLITE_OK)
    fail(sqlite3_db_handle(statement_), "bind text");
}

void Statement::bind_blob(int index, std::string_view value) {
  if (sqlite3_bind_blob64(statement_, index, value.data(), value.size(),
                          SQLITE_TRANSIENT) != SQLITE_OK)
    fail(sqlite3_db_handle(statement_), "bind blob");
}

void Statement::bind_null(int index) {
  if (sqlite3_bind_null(statement_, index) != SQLITE_OK)
    fail(sqlite3_db_handle(statement_), "bind null");
}

bool Statement::step() {
  const auto status = sqlite3_step(statement_);
  if (status == SQLITE_ROW)
    return true;
  if (status == SQLITE_DONE)
    return false;
  fail(sqlite3_db_handle(statement_), "execute statement");
}

void Statement::execute() {
  if (step())
    throw std::runtime_error("unexpected SQLite row");
}

std::int64_t Statement::integer(int column) const {
  return sqlite3_column_int64(statement_, column);
}

std::uint64_t Statement::unsigned_integer(int column) const {
  const auto value = integer(column);
  if (value < 0)
    throw std::runtime_error("negative SQLite value where unsigned expected");
  return static_cast<std::uint64_t>(value);
}

std::string Statement::string(int column) const {
  const auto *value = sqlite3_column_text(statement_, column);
  const auto size = sqlite3_column_bytes(statement_, column);
  return value ? std::string(reinterpret_cast<const char *>(value), size)
               : std::string{};
}

Bytes Statement::blob(int column) const {
  const auto *value = sqlite3_column_blob(statement_, column);
  const auto size = sqlite3_column_bytes(statement_, column);
  return value ? Bytes(reinterpret_cast<const char *>(value), size) : Bytes{};
}

bool Statement::is_null(int column) const {
  return sqlite3_column_type(statement_, column) == SQLITE_NULL;
}

Database::Database(const std::filesystem::path &path) {
  const auto native_path = path.string();
  const auto open_status = sqlite3_open_v2(
      native_path.c_str(), &database_,
      SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_FULLMUTEX,
      nullptr);
  if (open_status != SQLITE_OK) {
    const std::string message = database_ ? sqlite3_errmsg(database_)
                                          : "SQLite error";
    sqlite3_close_v2(database_);
    database_ = nullptr;
    throw std::runtime_error("open storage database: " + message);
  }
  try {
    configure_connection();
  } catch (...) {
    sqlite3_close_v2(database_);
    database_ = nullptr;
    throw;
  }
}

void Database::configure_connection() {
  if (!database_)
    fail(database_, "open storage database");
  sqlite3_extended_result_codes(database_, 1);
  // Inspect compatibility before changing persistent connection/database state.
  std::int64_t schema_version = 0;
  {
    Statement version(database_, "PRAGMA user_version");
    if (!version.step())
      throw std::runtime_error("cannot read storage schema version");
    schema_version = version.integer(0);
  }
  if (schema_version > 1)
    throw std::runtime_error("storage schema is newer than this server");
  if (schema_version == 0) {
    Statement tables(database_,
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'");
    if (!tables.step() || tables.integer(0) != 0)
      throw std::runtime_error("unversioned storage database is not empty");
  }
  sqlite3_busy_timeout(database_, 5000);
  exec("PRAGMA foreign_keys=ON");
  exec("PRAGMA journal_mode=WAL");
  exec("PRAGMA synchronous=FULL");
  if (scalar_integer("PRAGMA foreign_keys") != 1 ||
      scalar_integer("PRAGMA synchronous") != 2 ||
      scalar_integer("PRAGMA busy_timeout") != 5000)
    throw std::runtime_error("required SQLite connection settings unavailable");
  Statement mode(database_, "PRAGMA journal_mode");
  if (!mode.step() || mode.string(0) != "wal")
    throw std::runtime_error("SQLite WAL mode unavailable");
}

Database::~Database() { sqlite3_close_v2(database_); }

void Database::exec(std::string_view sql) const {
  char *message = nullptr;
  const auto status = sqlite3_exec(database_, std::string(sql).c_str(), nullptr,
                                   nullptr, &message);
  if (status != SQLITE_OK) {
    const std::string detail = message ? message : sqlite3_errmsg(database_);
    sqlite3_free(message);
    throw std::runtime_error("SQLite operation failed: " + detail);
  }
}

std::int64_t Database::scalar_integer(std::string_view sql) const {
  Statement statement(database_, sql);
  if (!statement.step())
    throw std::runtime_error("SQLite scalar query returned no value");
  return statement.integer(0);
}

void Database::begin_immediate() const { exec("BEGIN IMMEDIATE"); }
void Database::commit() const { exec("COMMIT"); }
void Database::rollback() const noexcept {
  sqlite3_exec(database_, "ROLLBACK", nullptr, nullptr, nullptr);
}

Transaction::Transaction(const Database &database) : database_(database) {
  database_.begin_immediate();
}

Transaction::~Transaction() {
  if (!committed_)
    database_.rollback();
}

void Transaction::commit() {
  database_.commit();
  committed_ = true;
}

} // namespace ctk::storage::detail
