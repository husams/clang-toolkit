#include "ctk/net/index_service.hpp"
#include "ctk/platform/index_worker.hpp"
#include "include_inventory_cache.hpp"
#include "project_index_store.hpp"

#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <fstream>
#include <map>
#include <mutex>
#include <set>
#include <thread>

namespace ctk::net {
namespace {
using namespace ctk::index::v1;
using namespace index_detail;

class Interrupted : public std::exception {};
struct Job {
  std::string root, commands;
  unsigned interval = 2;
  std::uint64_t epoch = 0;
};
std::string escaped_prefix(const std::string &value) {
  std::string pattern;
  for (char c : value) {
    if (c == '%' || c == '_' || c == '\\')
      pattern += '\\';
    pattern += c;
  }
  return pattern + '%';
}
std::uint64_t count_units(Database &db) {
  Statement row(db, "SELECT count(*) FROM translation_unit WHERE indexed_at>0");
  row.step();
  return row.number(0);
}
} // namespace

// This controller owns no native ASTs and never runs work on the foreground
// pool.
class BackgroundSymbolIndexer {
public:
  BackgroundSymbolIndexer(fs::path root, std::function<bool()> foreground_busy,
                          fs::path executable)
      : storage_(std::move(root) / "symbol-index"),
        executable_(executable.empty() ? platform::current_executable_sibling(
                                             "ctk-index-worker")
                                       : std::move(executable)),
        foreground_busy_(std::move(foreground_busy)),
        thread_([this] { loop(); }) {}
  ~BackgroundSymbolIndexer() {
    {
      std::lock_guard lock(mutex_);
      stopping_ = true;
    }
    changed_.notify_all();
    thread_.join();
  }
  fs::path database_path(const std::string &root) const {
    return storage_ / digest_text(root) / "symbols.sqlite3";
  }
  ProjectIndexStatus start(const StartProjectIndexRequest &request) {
    const auto key = root_key(request.project_root());
    std::lock_guard lock(mutex_);
    if (!job_.root.empty() && !cancelled_) {
      if (job_.root != key)
        throw std::logic_error(
            "cancel the active project index before starting another project");
      return status_;
    }
    job_.root = key;
    job_.commands = request.compile_commands();
    job_.interval = std::clamp(
        request.poll_interval_seconds() ? request.poll_interval_seconds() : 2u,
        1u, 3600u);
    ++job_.epoch;
    cancelled_ = false;
    paused_ = false;
    status_.Clear();
    status_.set_project_root(key);
    status_.set_state(INDEX_STATE_QUEUED);
    changed_.notify_all();
    return status_;
  }
  ProjectIndexStatus status(const std::string &root) {
    const auto key = root_key(root);
    std::lock_guard lock(mutex_);
    if (job_.root.empty() || key != job_.root) {
      ProjectIndexStatus idle;
      idle.set_project_root(key);
      idle.set_state(INDEX_STATE_IDLE);
      return idle;
    }
    return status_;
  }
  ProjectIndexStatus control(const std::string &root, int action) {
    const auto key = root_key(root);
    std::lock_guard lock(mutex_);
    require_project(key);
    if (action == 2) {
      cancelled_ = true;
      paused_ = false;
      status_.set_state(INDEX_STATE_CANCELLED);
      status_.clear_paused_reason();
    } else if (cancelled_) {
      throw std::logic_error("cancelled index must be started before resuming");
    } else if (action == 0) {
      paused_ = true;
      status_.set_state(INDEX_STATE_PAUSED);
      status_.set_paused_reason(
          "paused by client; uncommitted extraction will be retried");
    } else {
      paused_ = false;
      status_.set_state(INDEX_STATE_QUEUED);
      status_.clear_paused_reason();
    }
    changed_.notify_all();
    return status_;
  }
  FindSymbolsResponse find(grpc::ServerContext &context,
                           const std::string &root, const std::string &query,
                           std::uint32_t requested_limit, bool prefix,
                           bool by_usr) {
    const auto key = root_key(root);
    if (query.empty())
      throw std::invalid_argument("symbol query cannot be empty");
    if (query.size() > 4096)
      throw std::invalid_argument("symbol query exceeds 4096 bytes");
    Database db(database_path(key), false);
    // Cold index pages may require disk I/O while the background writer is
    // active. Keep a bounded budget without rejecting otherwise cheap queries
    // at the former 250ms cutoff; client deadlines/cancellation still win.
    const auto deadline =
        std::min(context.deadline(),
                 std::chrono::system_clock::now() + std::chrono::seconds(1));
    struct QueryBudget {
      grpc::ServerContext &context;
      std::chrono::system_clock::time_point deadline;
    } budget{context, deadline};
    sqlite3_progress_handler(
        db.handle, 1000,
        [](void *raw) {
          auto &value = *static_cast<QueryBudget *>(raw);
          return value.context.IsCancelled() ||
                         std::chrono::system_clock::now() >= value.deadline
                     ? 1
                     : 0;
        },
        &budget);
    db.exec("BEGIN");
    FindSymbolsResponse response;
    response.set_revision(revision(db));
    response.set_translation_units_indexed(count_units(db));
    {
      Statement total(db, "SELECT value FROM metadata WHERE key='total'");
      if (total.step())
        response.set_translation_units_total(std::stoull(total.text(0)));
    }
    {
      Statement stale(
          db, "SELECT count(*) FROM translation_unit WHERE status!='ready'");
      stale.step();
      response.set_stale(stale.number(0) != 0 ||
                         response.translation_units_indexed() <
                             response.translation_units_total());
    }
    {
      std::lock_guard lock(mutex_);
      if (key != job_.root || status_.state() != INDEX_STATE_COMPLETE)
        response.set_stale(true);
    }
    // Sort narrow candidates before loading symbol payloads and TU metadata.
    // Joining first reads the large TU overflow records once per match, even
    // when nearly all those matches will be discarded by LIMIT.
    const std::string projection =
        "SELECT tu_id,usr,file_path,byte_offset,is_definition,qualified_name "
        "FROM symbol";
    const std::string columns = projection + " WHERE ";
    // Prefix matching and ordering share NOCASE, allowing the qualified-name
    // index to stop early. Bound each OR arm before merging and deduplicating.
    const std::string order =
        prefix ? "qualified_name COLLATE NOCASE,file_path,byte_offset,tu_id"
               : "qualified_name,file_path,byte_offset,tu_id";
    std::string sql;
    if (prefix) {
      sql = "WITH name_matches AS MATERIALIZED (" + columns +
            "name LIKE ?1 ESCAPE '\\' ORDER BY " + order +
            " LIMIT ?3), qualified_matches AS MATERIALIZED (" + columns +
            "qualified_name LIKE ?2 ESCAPE '\\' ORDER BY " + order +
            " LIMIT ?3), selected AS MATERIALIZED ("
            "SELECT * FROM name_matches UNION SELECT * FROM qualified_matches "
            "ORDER BY " +
            order + " LIMIT ?3), ";
    } else if (!by_usr) {
      // Unary + keeps BINARY equality as a residual filter: otherwise SQLite
      // can choose that equality for access and scan instead of the NOCASE
      // index.
      sql = "WITH selected AS MATERIALIZED (" + projection +
            " INDEXED BY symbol_name_prefix WHERE name=?1 COLLATE NOCASE "
            "AND +name=?1 COLLATE BINARY UNION " +
            projection +
            " INDEXED BY symbol_qualified_prefix WHERE qualified_name=?2 "
            "COLLATE NOCASE AND +qualified_name=?2 COLLATE BINARY ORDER BY " +
            order + " LIMIT ?3), ";
    } else {
      sql = "WITH selected AS MATERIALIZED (" + columns + "usr=?1 ORDER BY " +
            order + " LIMIT ?2), ";
    }
    // A shared header owner can expand into many TUs. Include every owner tied
    // at the physical boundary before limiting logical results by real TU ID.
    sql +=
        "boundary AS MATERIALIZED (SELECT qualified_name,file_path,byte_offset "
        "FROM selected ORDER BY qualified_name" +
        std::string(prefix ? " COLLATE NOCASE" : "") +
        " DESC,file_path DESC,byte_offset DESC LIMIT 1), "
        "candidates AS MATERIALIZED (SELECT * FROM selected UNION " +
        projection +
        " INDEXED BY symbol_qualified_prefix WHERE qualified_name="
        "(SELECT qualified_name FROM boundary) COLLATE NOCASE " +
        (prefix ? std::string()
                : "AND +qualified_name=(SELECT qualified_name FROM boundary) "
                  "COLLATE BINARY ") +
        "AND file_path=(SELECT file_path FROM boundary) AND byte_offset="
        "(SELECT byte_offset FROM boundary) AND " +
        (by_usr ? "usr=?1"
         : prefix
             ? "(name LIKE ?1 ESCAPE '\\' OR qualified_name LIKE ?2 ESCAPE "
               "'\\')"
             : "(name=?1 COLLATE BINARY OR qualified_name=?2 COLLATE BINARY)") +
        "), ";
    // Older stores remain readable before their background schema upgrade.
    // Once available, force the covering index: SQLite otherwise sometimes
    // prefers the TU primary key without accounting for manifest overflow I/O.
    Statement lookup_index(db, "SELECT 1 FROM sqlite_master WHERE type='index' "
                               "AND name='translation_unit_lookup'");
    const std::string metadata_source =
        lookup_index.step()
            ? "translation_unit INDEXED BY translation_unit_lookup"
            : "translation_unit";
    Statement header_index(db, "SELECT 1 FROM sqlite_master WHERE type='index' "
                               "AND name='translation_unit_header_members'");
    if (header_index.step()) {
      sql +=
          "owners AS MATERIALIZED (SELECT id,dependencies_json FROM "
          "translation_unit INDEXED BY translation_unit_header_members "
          "WHERE indexed_at=0 AND id IN (SELECT tu_id FROM candidates)), "
          "expanded AS MATERIALIZED (SELECT c.tu_id AS owner_id,"
          "COALESCE(m.value,c.tu_id) AS tu_id,c.usr,c.file_path,c.byte_offset,"
          "c.is_definition,c.qualified_name FROM candidates c LEFT JOIN "
          "owners o ON o.id=c.tu_id LEFT JOIN json_each(o.dependencies_json) m "
          "ORDER BY c.qualified_name" +
          std::string(prefix ? " COLLATE NOCASE" : "") +
          ",c.file_path,c.byte_offset,COALESCE(m.value,c.tu_id) LIMIT " +
          (by_usr ? "?2), " : "?3), ");
    } else {
      sql += "expanded AS MATERIALIZED (SELECT *,tu_id AS owner_id FROM "
             "candidates), ";
    }
    sql +=
        "units AS MATERIALIZED (SELECT id,main_file,arguments,status FROM " +
        metadata_source +
        " WHERE id IN (SELECT tu_id FROM expanded)) "
        "SELECT "
        "s.usr,s.name,s.qualified_name,s.kind,s.file_path,s.line,s.column_no,s."
        "signature,t.main_file,t.arguments,s.byte_offset,s.is_definition,t."
        "status FROM expanded c JOIN symbol s ON s.tu_id=c.owner_id AND "
        "s.usr=c.usr AND s.file_path=c.file_path AND "
        "s.byte_offset=c.byte_offset "
        "AND s.is_definition=c.is_definition "
        "JOIN units t ON t.id=c.tu_id ORDER BY s.qualified_name" +
        std::string(prefix ? " COLLATE NOCASE" : "") +
        ",s.file_path,s.byte_offset,t.id";
    Statement symbols(db, sql.c_str());
    const auto pattern = prefix ? escaped_prefix(query) : query;
    symbols.bind(1, pattern);
    if (!by_usr)
      symbols.bind(2, pattern);
    const auto limit =
        std::clamp(requested_limit ? requested_limit : 100u, 1u, 1000u);
    symbols.bind(by_usr ? 2 : 3, static_cast<std::uint64_t>(limit + 1));
    while (symbols.step()) {
      if (response.symbols_size() == static_cast<int>(limit)) {
        response.set_truncated(true);
        break;
      }
      auto *symbol = response.add_symbols();
      symbol->set_usr(symbols.text(0));
      symbol->set_name(symbols.text(1));
      symbol->set_qualified_name(symbols.text(2));
      symbol->set_kind(symbols.text(3));
      symbol->set_file_path(symbols.text(4));
      symbol->set_line(symbols.number(5));
      symbol->set_column(symbols.number(6));
      symbol->set_signature(symbols.text(7));
      symbol->set_translation_unit(symbols.text(8));
      symbol->set_compile_context(symbols.text(9));
      symbol->set_byte_offset(symbols.number(10));
      symbol->set_is_definition(symbols.number(11));
      symbol->set_stale(response.stale() || symbols.text(12) != "ready");
      symbol->set_index_revision(response.revision());
    }
    return response;
  }

private:
  void require_project(const std::string &key) const {
    if (job_.root.empty() || key != job_.root)
      throw std::logic_error("project has not been started on this server");
  }
  bool current(const Job &job) {
    std::lock_guard lock(mutex_);
    return !stopping_ && !cancelled_ && job.epoch == job_.epoch;
  }
  bool admitted(const Job &job) {
    std::lock_guard lock(mutex_);
    return !stopping_ && !cancelled_ && !paused_ && job.epoch == job_.epoch;
  }
  void await_admission(const Job &job) {
    for (;;) {
      {
        std::unique_lock lock(mutex_);
        if (stopping_ || cancelled_ || job.epoch != job_.epoch)
          throw Interrupted();
        if (paused_) {
          changed_.wait_for(lock, std::chrono::milliseconds(100));
          continue;
        }
      }
      if (!foreground_busy_ || !foreground_busy_())
        return;
      std::unique_lock lock(mutex_);
      changed_.wait_for(lock, std::chrono::milliseconds(50));
    }
  }
  IndexWorkerResponse execute(const Job &job, IndexWorkerRequest request,
                              const fs::path &directory) {
    await_admission(job);
    const auto request_path = directory / "worker.request";
    const auto result_path = directory / "worker.result";
    struct Cleanup {
      fs::path request, result;
      ~Cleanup() {
        std::error_code error;
        fs::remove(request, error);
        fs::remove(result, error);
      }
    } cleanup{request_path, result_path};
    {
      std::ofstream output(request_path, std::ios::binary | std::ios::trunc);
      if (!request.SerializeToOstream(&output))
        throw std::runtime_error("cannot stage index request");
    }
    platform::IndexWorker worker(executable_, request_path, result_path);
    auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(120);
    for (;;) {
      if (!admitted(job))
        throw Interrupted();
      if (foreground_busy_ && foreground_busy_()) {
        // Retain the AST and current reconciliation position while giving
        // foreground requests the CPU and disk. The process group includes
        // wrapper children; cancellation still kills and reaps it immediately.
        const auto yielded_at = std::chrono::steady_clock::now();
        worker.suspend();
        await_admission(job);
        worker.resume();
        deadline += std::chrono::steady_clock::now() - yielded_at;
        continue;
      }
      if (auto bytes = worker.resident_bytes();
          bytes && *bytes > 1536ULL * 1024 * 1024)
        throw std::runtime_error("index worker exceeded 1.5 GiB memory budget");
      const auto exit = worker.poll();
      if (exit) {
        IndexWorkerResponse response;
        std::ifstream input(result_path, std::ios::binary);
        if (!input || !response.ParseFromIstream(&input))
          throw std::runtime_error(
              "index worker failed without a valid result (exit " +
              std::to_string(*exit) + ")");
        if (*exit || !response.success())
          throw std::runtime_error(response.error().empty()
                                       ? "index extraction failed"
                                       : response.error());
        return response;
      }
      if (std::chrono::steady_clock::now() >= deadline)
        throw std::runtime_error("index worker exceeded 120 second deadline");
      std::unique_lock lock(mutex_);
      changed_.wait_for(lock, std::chrono::milliseconds(25));
    }
  }
  bool manifest_current(const Job &job,
                        const std::map<std::string, std::string> &manifest,
                        std::map<std::string, std::string> &cache) {
    if (manifest.empty())
      return false;
    for (const auto &[path, hash] : manifest) {
      await_admission(job);
      auto found = cache.find(path);
      if (path.starts_with("@include-tree:")) {
        found = cache
                    .insert_or_assign(
                        path, inventories_.digest(path.substr(14),
                                                  [&] {
                                                    await_admission(job);
                                                    return true;
                                                  }))
                    .first;
      } else if (found == cache.end()) {
        try {
          found = cache
                      .emplace(path, digest_file(path,
                                                 [&] {
                                                   await_admission(job);
                                                   return true;
                                                 }))
                      .first;
        } catch (...) {
          if (!admitted(job) || (foreground_busy_ && foreground_busy_()))
            throw Interrupted();
          throw;
        }
      }
      if (found->second != hash)
        return false;
    }
    return true;
  }
  void progress(const Job &job,
                const std::function<void(ProjectIndexStatus &)> &update) {
    std::lock_guard lock(mutex_);
    if (job.epoch != job_.epoch || cancelled_ || stopping_)
      throw Interrupted();
    update(status_);
    if (paused_)
      status_.set_state(INDEX_STATE_PAUSED);
  }
  void bump(Database &db) {
    metadata(db, "revision", std::to_string(revision(db) + 1));
    metadata(db, "updated_at", std::to_string(timestamp()));
  }
  void commit(const Job &job, Transaction &transaction) {
    // Only commit needs this gate. Parsing, hashing and inserts never hold the
    // status mutex. A pause acknowledgement precedes any subsequent commit.
    for (;;) {
      await_admission(job);
      std::lock_guard lock(mutex_);
      if (stopping_ || cancelled_ || paused_ || job.epoch != job_.epoch)
        throw Interrupted();
      if (foreground_busy_ && foreground_busy_())
        continue;
      transaction.commit();
      return;
    }
  }
  void upgrade_symbols(const Job &job, Database &db) {
    bool legacy = false;
    {
      Statement schema(db, "SELECT sql FROM sqlite_master WHERE name='symbol'");
      legacy = schema.step() &&
               schema.text(0).find("WITHOUT ROWID") != std::string::npos;
    }
    if (!legacy)
      return;
    await_admission(job);
    const auto saved_count = count_units(db), saved_revision = revision(db);
    std::uint64_t total = saved_count;
    {
      Statement row(db, "SELECT value FROM metadata WHERE key='total'");
      if (row.step())
        total = std::stoull(row.text(0));
    }
    progress(job, [&](auto &s) {
      s.set_state(INDEX_STATE_INDEXING);
      s.set_translation_units_indexed(saved_count);
      s.set_translation_units_total(total);
      s.set_translation_units_pending(total);
      s.set_revision(saved_revision);
    });
    // Retire the legacy pass's accumulated WAL before copying its rows. Large
    // frame histories otherwise make even the migration's reads expensive.
    checkpoint(job, db);
    // Destroy the progress handler before transaction rollback on every error.
    Transaction transaction(db);
    struct Budget {
      BackgroundSymbolIndexer &owner;
      const Job &job;
      bool interrupted = false;
    } budget{*this, job};
    sqlite3_progress_handler(
        db.handle, 1000,
        [](void *raw) {
          auto &b = *static_cast<Budget *>(raw);
          b.interrupted =
              !b.owner.admitted(b.job) ||
              (b.owner.foreground_busy_ && b.owner.foreground_busy_());
          return b.interrupted ? 1 : 0;
        },
        &budget);
    struct Reset {
      sqlite3 *handle;
      ~Reset() { sqlite3_progress_handler(handle, 0, nullptr, nullptr); }
    } reset{db.handle};
    try {
      db.exec("ALTER TABLE symbol RENAME TO symbol_legacy;");
      db.exec(symbol_schema);
      db.exec("INSERT INTO symbol SELECT * FROM symbol_legacy;");
      db.exec("DROP TABLE symbol_legacy;");
      db.exec(symbol_indexes);
      metadata(db, "schema_version", "2");
      sqlite3_progress_handler(db.handle, 0, nullptr, nullptr);
      commit(job, transaction);
    } catch (...) {
      if (budget.interrupted)
        throw Interrupted();
      throw;
    }
  }
  void checkpoint(const Job &job, Database &db) {
    await_admission(job);
    // Never wait on readers or checkpoint under the status/control mutex.
    // Bound the WAL after each contribution, rather than after the entire
    // project: long first passes otherwise accumulate gigabytes of frames.
    sqlite3_wal_checkpoint_v2(db.handle, nullptr, SQLITE_CHECKPOINT_PASSIVE,
                              nullptr, nullptr);
  }
  void release_group(Database &db, const std::string &owner,
                     const std::string &id) {
    Statement release(
        db, "UPDATE translation_unit SET dependencies_json=(SELECT "
            "json_group_array(value) FROM json_each(dependencies_json) WHERE "
            "value!=?1) WHERE id=?2");
    release.bind(1, id);
    release.bind(2, owner);
    release.step();
  }
  IndexWorkerResponse stored_response(const Job &job, Database &db,
                                      const std::string &id,
                                      const std::string &manifest) {
    IndexWorkerResponse response;
    response.set_success(true);
    for (const auto &[path, hash] : dependencies(manifest)) {
      auto *dependency = response.add_dependencies();
      dependency->set_path(path);
      dependency->set_sha256(hash);
    }
    Statement rows(
        db, "SELECT usr,name,qualified_name,kind,file_path,byte_offset,"
            "is_definition,line,column_no,signature FROM symbol WHERE tu_id=?");
    rows.bind(1, id);
    while (rows.step()) {
      await_admission(job);
      auto *symbol = response.add_symbols();
      symbol->set_usr(rows.text(0));
      symbol->set_name(rows.text(1));
      symbol->set_qualified_name(rows.text(2));
      symbol->set_kind(rows.text(3));
      symbol->set_file_path(rows.text(4));
      symbol->set_byte_offset(rows.number(5));
      symbol->set_is_definition(rows.number(6));
      symbol->set_line(rows.number(7));
      symbol->set_column(rows.number(8));
      symbol->set_signature(rows.text(9));
    }
    return response;
  }
  void replace(const Job &job, Database &db,
               const IndexWorkerTranslationUnit &unit, const std::string &id,
               const std::string &command_hash,
               const IndexWorkerResponse &response,
               const std::string &commands_digest,
               fs::file_time_type worker_time) {
    std::map<std::string, std::vector<const Symbol *>> files, owners;
    std::map<std::string, std::string> header_files;
    for (const auto &symbol : response.symbols())
      files[symbol.file_path()].push_back(&symbol);
    google::protobuf::Struct manifest;
    for (const auto &dependency : response.dependencies())
      (*manifest.mutable_fields())[dependency.path()].set_string_value(
          dependency.sha256());
    (*manifest.mutable_fields())["@symbol-layout"].set_string_value(
        "shared-v1");
    for (const auto &[file, symbols] : files) {
      if (file == unit.source()) {
        owners[id] = symbols;
        continue;
      }
      std::vector<std::string> records;
      for (const auto *symbol : symbols)
        records.push_back(symbol->SerializeAsString());
      std::sort(records.begin(), records.end());
      records.erase(std::unique(records.begin(), records.end()), records.end());
      std::string content;
      for (const auto &record : records)
        content += std::to_string(record.size()) + ':' + record;
      const auto owner = "header:" + digest_text(file + '\n' + content);
      owners[owner] = symbols;
      header_files[owner] = file;
      (*manifest.mutable_fields())["@symbol-group:" + owner].set_string_value(
          owner);
    }
    const auto encoded = json(manifest);
    std::map<std::string, std::string> fresh;
    if (!manifest_current(job, dependencies(encoded), fresh))
      throw Interrupted();
    await_admission(job);
    Transaction transaction(db);
    std::set<std::string> previous_groups;
    {
      Statement previous(
          db, "SELECT dependencies_json FROM translation_unit WHERE id=?");
      previous.bind(1, id);
      if (previous.step())
        previous_groups = symbol_groups(previous.text(0));
    }
    Statement row(
        db,
        "INSERT INTO "
        "translation_unit(id,main_file,working_directory,arguments,command_"
        "hash,input_fingerprint,dependencies_json,indexed_at,status,last_error)"
        " VALUES(?,?,?,?,?,?,?,?, 'ready','') ON CONFLICT(id) DO UPDATE SET "
        "working_directory=excluded.working_directory,arguments=excluded."
        "arguments,command_hash=excluded.command_hash,input_fingerprint="
        "excluded.input_fingerprint,dependencies_json=excluded.dependencies_"
        "json,indexed_at=excluded.indexed_at,status='ready',last_error=''");
    row.bind(1, id);
    row.bind(2, unit.source());
    row.bind(3, unit.working_directory());
    row.bind(4, unit.compile_context());
    row.bind(5, command_hash);
    row.bind(6, digest_text(command_hash + encoded));
    row.bind(7, encoded);
    row.bind(8, timestamp());
    row.step();
    std::set<std::string> new_owners;
    for (const auto &[owner, file] : header_files) {
      await_admission(job);
      Statement create(
          db,
          "INSERT INTO translation_unit "
          "VALUES(?,?,'','',?,?,'[]',0,'ready','') ON CONFLICT(id) DO NOTHING");
      create.bind(1, owner);
      create.bind(2, file);
      create.bind(3, owner);
      create.bind(4, owner);
      create.step();
      if (sqlite3_changes(db.handle))
        new_owners.insert(owner);
      Statement member(db, "UPDATE translation_unit SET "
                           "dependencies_json=json_insert(dependencies_json,'$["
                           "#]',?1) WHERE id=?2 AND NOT EXISTS (SELECT 1 FROM "
                           "json_each(dependencies_json) WHERE value=?1)");
      member.bind(1, id);
      member.bind(2, owner);
      member.step();
      previous_groups.erase(owner);
    }
    for (const auto &owner : previous_groups)
      release_group(db, owner, id);
    db.exec("DELETE FROM translation_unit WHERE indexed_at=0 AND "
            "dependencies_json='[]'");
    // Track this response's keys in connection-local temporary storage. Keep
    // unchanged header rows in place instead of deleting/reinserting them.
    db.exec("CREATE TEMP TABLE IF NOT EXISTS index_symbol_seen(usr TEXT NOT "
            "NULL,file_path TEXT NOT NULL,byte_offset INTEGER NOT NULL,"
            "is_definition INTEGER NOT NULL,PRIMARY KEY(usr,file_path,"
            "byte_offset,is_definition)) WITHOUT ROWID;"
            "DELETE FROM temp.index_symbol_seen;");
    Statement seen(db, "INSERT OR IGNORE INTO temp.index_symbol_seen "
                       "VALUES(?,?,?,?)");
    Statement symbol(
        db,
        "INSERT INTO "
        "symbol(tu_id,usr,name,qualified_name,kind,file_path,byte_offset,is_"
        "definition,line,column_no,signature) VALUES(?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(tu_id,usr,file_path,byte_offset,is_definition) DO UPDATE "
        "SET name=excluded.name,qualified_name=excluded.qualified_name,"
        "kind=excluded.kind,line=excluded.line,column_no=excluded.column_no,"
        "signature=excluded.signature WHERE name!=excluded.name OR "
        "qualified_name!=excluded.qualified_name OR kind!=excluded.kind OR "
        "line!=excluded.line OR column_no!=excluded.column_no OR "
        "signature!=excluded.signature");
    for (const auto &[owner, symbols] : owners) {
      if (owner != id && !new_owners.contains(owner))
        continue;
      for (const auto *entry : symbols) {
        const auto &value = *entry;
        // WAL readers do not need our writer lock. Yield to foreground work
        // without discarding all already-staged rows and re-extracting the TU.
        await_admission(job);
        symbol.bind(1, owner);
        symbol.bind(2, value.usr());
        symbol.bind(3, value.name());
        symbol.bind(4, value.qualified_name());
        symbol.bind(5, value.kind());
        symbol.bind(6, value.file_path());
        symbol.bind(7, value.byte_offset());
        symbol.bind(8, static_cast<std::uint64_t>(value.is_definition()));
        symbol.bind(9, static_cast<std::uint64_t>(value.line()));
        symbol.bind(10, static_cast<std::uint64_t>(value.column()));
        symbol.bind(11, value.signature());
        symbol.step();
        symbol.reset();
        if (owner == id) {
          seen.bind(1, value.usr());
          seen.bind(2, value.file_path());
          seen.bind(3, value.byte_offset());
          seen.bind(4, static_cast<std::uint64_t>(value.is_definition()));
          seen.step();
          seen.reset();
        }
      }
    }
    await_admission(job);
    Statement remove(db, "DELETE FROM symbol WHERE tu_id=? AND NOT EXISTS "
                         "(SELECT 1 FROM temp.index_symbol_seen s WHERE "
                         "s.usr=symbol.usr AND s.file_path=symbol.file_path "
                         "AND s.byte_offset=symbol.byte_offset AND "
                         "s.is_definition=symbol.is_definition)");
    remove.bind(1, id);
    remove.step();
    // Files or build commands may have changed while publication yielded.
    // Publish only if the extracted inputs still match the current inputs.
    fresh.clear();
    if (!manifest_current(job, dependencies(encoded), fresh) ||
        commands_digest !=
            digest_file(
                (fs::path(job.commands) / "compile_commands.json").string()) ||
        worker_time != fs::last_write_time(executable_))
      throw Interrupted();
    progress(job, [](auto &s) { s.set_state(INDEX_STATE_INDEXING); });
    bump(db);
    commit(job, transaction);
  }
  void mark_failed(const Job &job, Database &db, const std::string &id,
                   const std::string &source,
                   const std::set<std::string> &active,
                   const std::string &error) {
    await_admission(job);
    Transaction transaction(db);
    Statement row(
        db,
        "UPDATE translation_unit SET status='failed',last_error=? WHERE id=?");
    row.bind(1, error);
    row.bind(2, id);
    row.step();
    // A changed compile command has a new ID. Keep any last-good contribution
    // for this source, but expose it as stale while the new context fails.
    Statement previous(
        db,
        "SELECT id FROM translation_unit WHERE main_file=? AND indexed_at>0");
    previous.bind(1, source);
    Statement stale(db,
                    "UPDATE translation_unit SET status='failed',last_error=? "
                    "WHERE id=?");
    while (previous.step()) {
      const auto old_id = previous.text(0);
      if (active.contains(old_id))
        continue;
      stale.bind(1, error);
      stale.bind(2, old_id);
      stale.step();
      stale.reset();
    }
    commit(job, transaction);
  }
  void reconcile(const Job &job, Database &db, const fs::path &directory) {
    IndexWorkerRequest listing;
    listing.set_list_translation_units(true);
    listing.set_compile_commands_directory(job.commands);
    const auto commands_digest = digest_file(
        (fs::path(job.commands) / "compile_commands.json").string());
    const auto worker_time = fs::last_write_time(executable_);
    auto listing_result = execute(job, listing, directory);
    if (worker_time != fs::last_write_time(executable_) ||
        commands_digest.empty() ||
        commands_digest !=
            digest_file(
                (fs::path(job.commands) / "compile_commands.json").string()))
      throw Interrupted();
    const auto total = listing_result.translation_units_size();
    metadata(db, "total", std::to_string(total));
    std::set<std::string> active;
    std::uint64_t completed = 0, skipped = 0, failed = 0;
    std::set<std::string> failed_sources;
    std::map<std::string, std::string> digest_cache;
    // The worker context includes its extraction-source fingerprint, Clang
    // version, compiler, arguments and environment. Executable bytes also
    // contain unrelated build metadata and must not invalidate every TU.
    auto saved_revision = revision(db), saved_count = count_units(db);
    progress(job, [&](auto &s) {
      s.set_state(INDEX_STATE_INDEXING);
      s.set_translation_units_total(total);
      s.set_translation_units_completed(0);
      s.set_translation_units_skipped(0);
      s.set_translation_units_failed(0);
      s.set_translation_units_pending(total);
      s.set_revision(saved_revision);
      s.set_translation_units_indexed(saved_count);
      s.clear_error();
    });
    for (const auto &unit : listing_result.translation_units()) {
      const auto command_hash = digest_text(unit.compile_context());
      active.insert(digest_text(unit.source() + '\n' + command_hash));
    }
    for (const auto &unit : listing_result.translation_units()) {
      await_admission(job);
      const auto command_hash = digest_text(unit.compile_context());
      const auto id = digest_text(unit.source() + '\n' + command_hash);
      progress(job,
               [&](auto &s) { s.set_current_translation_unit(unit.source()); });
      bool unchanged = false;
      std::string previous_manifest;
      {
        Statement prior(
            db, "SELECT dependencies_json FROM translation_unit WHERE id=?");
        prior.bind(1, id);
        if (prior.step()) {
          previous_manifest = prior.text(0);
          unchanged = manifest_current(job, dependencies(previous_manifest),
                                       digest_cache);
        }
      }
      const bool migrate =
          unchanged &&
          previous_manifest.find("\"@symbol-layout\"") == std::string::npos;
      if (unchanged && !migrate) {
        Transaction transaction(db);
        Statement ready(
            db, "UPDATE translation_unit SET status='ready',last_error='' "
                "WHERE id=? AND status!='ready'");
        ready.bind(1, id);
        ready.step();
        commit(job, transaction);
        ++skipped;
        ++completed;
      } else {
        try {
          IndexWorkerResponse response;
          if (migrate && symbol_groups(previous_manifest).empty())
            response = stored_response(job, db, id, previous_manifest);
          else {
            IndexWorkerRequest request;
            request.set_source(unit.source());
            request.set_header_cache_directory(
                (directory / "header-definitions").string());
            request.set_compile_commands_directory(job.commands);
            request.set_working_directory(unit.working_directory());
            *request.mutable_compile_arguments() = unit.compile_arguments();
            response = execute(job, std::move(request), directory);
          }
          if (commands_digest !=
              digest_file(
                  (fs::path(job.commands) / "compile_commands.json").string()))
            throw Interrupted();
          replace(job, db, unit, id, command_hash, response, commands_digest,
                  worker_time);
          ++completed;
        } catch (const Interrupted &) {
          throw;
        } catch (const std::exception &error) {
          mark_failed(job, db, id, unit.source(), active, error.what());
          failed_sources.insert(unit.source());
          ++failed;
          progress(job, [&](auto &s) { s.set_error(error.what()); });
        }
      }
      saved_revision = revision(db);
      saved_count = count_units(db);
      progress(job, [&](auto &s) {
        s.set_translation_units_completed(completed);
        s.set_translation_units_skipped(skipped);
        s.set_translation_units_failed(failed);
        s.set_translation_units_pending(total - completed - failed);
        s.set_revision(saved_revision);
        s.set_translation_units_indexed(saved_count);
      });
      if (!unchanged || migrate)
        checkpoint(job, db);
    }
    await_admission(job);
    std::vector<std::string> obsolete;
    std::vector<std::string> retained;
    {
      Statement rows(
          db, "SELECT id,main_file FROM translation_unit WHERE indexed_at>0");
      while (rows.step()) {
        if (!active.contains(rows.text(0)) &&
            !failed_sources.contains(rows.text(1)))
          obsolete.push_back(rows.text(0));
        else
          retained.push_back(rows.text(0));
      }
    }
    if (!obsolete.empty()) {
      const bool compact =
          obsolete.size() >= 32 && obsolete.size() > retained.size() / 4;
      Transaction transaction(db);
      struct Budget {
        BackgroundSymbolIndexer &owner;
        const Job &job;
        bool interrupted = false;
      } budget{*this, job};
      sqlite3_progress_handler(
          db.handle, 1000,
          [](void *raw) {
            auto &b = *static_cast<Budget *>(raw);
            try {
              b.owner.await_admission(b.job);
              return 0;
            } catch (...) {
              b.interrupted = true;
              return 1;
            }
          },
          &budget);
      struct Reset {
        sqlite3 *handle;
        ~Reset() { sqlite3_progress_handler(handle, 0, nullptr, nullptr); }
      } reset{db.handle};
      try {
        for (const auto &id : obsolete) {
          Statement previous(
              db, "SELECT dependencies_json FROM translation_unit WHERE id=?");
          previous.bind(1, id);
          if (previous.step())
            for (const auto &owner : symbol_groups(previous.text(0)))
              release_group(db, owner, id);
        }
        {
          Statement groups(db, "SELECT id FROM translation_unit WHERE "
                               "indexed_at=0 AND dependencies_json!='[]'");
          while (groups.step())
            retained.push_back(groups.text(0));
        }
        // A policy upgrade can retire millions of repeated system symbols.
        // Copy retained contributions and rebuild their much smaller indexes,
        // rather than updating every secondary index for every discarded row.
        // WAL readers see the previous three-table schema until this commits.
        if (compact) {
          db.exec("ALTER TABLE symbol RENAME TO symbol_retired;");
          db.exec(symbol_schema);
          {
            Statement copy(db, "INSERT INTO symbol SELECT * FROM "
                               "symbol_retired WHERE tu_id=?");
            for (const auto &id : retained) {
              await_admission(job);
              copy.bind(1, id);
              copy.step();
              copy.reset();
            }
          }
          db.exec("DROP TABLE symbol_retired;");
          db.exec(symbol_indexes);
        }
        Statement remove(db, "DELETE FROM translation_unit WHERE id=?");
        for (const auto &id : obsolete) {
          await_admission(job);
          remove.bind(1, id);
          remove.step();
          remove.reset();
        }
        db.exec("DELETE FROM translation_unit WHERE indexed_at=0 AND "
                "dependencies_json='[]'");
        bump(db);
        sqlite3_progress_handler(db.handle, 0, nullptr, nullptr);
        commit(job, transaction);
      } catch (...) {
        if (budget.interrupted)
          throw Interrupted();
        throw;
      }
    }
    saved_revision = revision(db);
    saved_count = count_units(db);
    progress(job, [&](auto &s) {
      s.set_state(failed ? INDEX_STATE_FAILED : INDEX_STATE_COMPLETE);
      s.clear_current_translation_unit();
      s.set_last_reconciled_unix_seconds(timestamp());
      s.set_revision(saved_revision);
      s.set_translation_units_indexed(saved_count);
    });
    // PASSIVE never waits for a reader. Checkpoint I/O remains background work.
    checkpoint(job, db);
  }
  void loop() {
    platform::lower_index_thread_priority();
    std::uint64_t processed_epoch = 0;
    for (;;) {
      Job job;
      {
        std::unique_lock lock(mutex_);
        changed_.wait(lock, [&] {
          return stopping_ || (!cancelled_ && !job_.root.empty() &&
                               job_.epoch != processed_epoch);
        });
        if (stopping_)
          return;
        job = job_;
        processed_epoch = job.epoch;
      }
      try {
        if (!fs::is_directory(job.root))
          throw std::invalid_argument("project_root must name a directory");
        if (job.commands.empty())
          job.commands = job.root;
        else if (fs::path(job.commands).is_relative())
          job.commands =
              (fs::path(job.root) / job.commands).lexically_normal().string();
        if (fs::is_regular_file(job.commands))
          job.commands = fs::path(job.commands).parent_path().string();
        const auto directory = database_path(job.root).parent_path();
        fs::create_directories(directory);
        fs::permissions(directory, fs::perms::owner_all,
                        fs::perm_options::replace);
        Database db(database_path(job.root), true);
        metadata(db, "project_root", job.root);
        while (current(job)) {
          try {
            upgrade_symbols(job, db);
            metadata(db, "schema_version", "2");
            reconcile(job, db, directory);
          } catch (const Interrupted &) {
            if (!current(job))
              break;
            await_admission(job);
            continue;
          } catch (const std::exception &error) {
            progress(job, [&](auto &s) {
              s.set_state(INDEX_STATE_FAILED);
              s.set_error(error.what());
            });
          }
          std::unique_lock lock(mutex_);
          changed_.wait_for(lock, std::chrono::seconds(job.interval), [&] {
            return stopping_ || cancelled_ || paused_ ||
                   job.epoch != job_.epoch;
          });
          if (paused_) {
            lock.unlock();
            await_admission(job);
          }
        }
      } catch (const Interrupted &) {
        // A new start, cancellation, or shutdown superseded this job.
      } catch (const std::exception &error) {
        std::lock_guard lock(mutex_);
        if (job.epoch == job_.epoch) {
          status_.set_state(INDEX_STATE_FAILED);
          status_.set_error(error.what());
          cancelled_ = true;
        }
      }
    }
  }
  fs::path storage_, executable_;
  std::function<bool()> foreground_busy_;
  IncludeInventoryCache inventories_;
  std::mutex mutex_;
  std::condition_variable changed_;
  Job job_;
  ProjectIndexStatus status_;
  bool stopping_ = false, cancelled_ = true, paused_ = false;
  std::thread thread_;
};

namespace {
template <class Function> grpc::Status rpc(Function &&function) {
#ifndef CTK_WITH_CLANG
  return {grpc::StatusCode::UNIMPLEMENTED,
          "Clang support is disabled in this server build"};
#else
  try {
    function();
    return grpc::Status::OK;
  } catch (const std::invalid_argument &e) {
    return {grpc::StatusCode::INVALID_ARGUMENT, e.what()};
  } catch (const std::logic_error &e) {
    return {grpc::StatusCode::FAILED_PRECONDITION, e.what()};
  } catch (const std::exception &e) {
    return {grpc::StatusCode::UNAVAILABLE, e.what()};
  }
#endif
}
} // namespace
IndexServiceAdapter::IndexServiceAdapter(fs::path root,
                                         std::function<bool()> foreground_busy,
                                         fs::path executable)
    : indexer_(std::make_shared<BackgroundSymbolIndexer>(
          std::move(root), std::move(foreground_busy), std::move(executable))) {
}
IndexServiceAdapter::~IndexServiceAdapter() = default;
grpc::Status
IndexServiceAdapter::StartProjectIndex(grpc::ServerContext *,
                                       const StartProjectIndexRequest *request,
                                       ProjectIndexStatus *out) {
  return rpc([&] { *out = indexer_->start(*request); });
}
grpc::Status
IndexServiceAdapter::GetProjectIndexStatus(grpc::ServerContext *,
                                           const ProjectIndexRequest *request,
                                           ProjectIndexStatus *out) {
  return rpc([&] { *out = indexer_->status(request->project_root()); });
}
grpc::Status
IndexServiceAdapter::PauseProjectIndex(grpc::ServerContext *,
                                       const ProjectIndexRequest *request,
                                       ProjectIndexStatus *out) {
  return rpc([&] { *out = indexer_->control(request->project_root(), 0); });
}
grpc::Status
IndexServiceAdapter::ResumeProjectIndex(grpc::ServerContext *,
                                        const ProjectIndexRequest *request,
                                        ProjectIndexStatus *out) {
  return rpc([&] { *out = indexer_->control(request->project_root(), 1); });
}
grpc::Status
IndexServiceAdapter::CancelProjectIndex(grpc::ServerContext *,
                                        const ProjectIndexRequest *request,
                                        ProjectIndexStatus *out) {
  return rpc([&] { *out = indexer_->control(request->project_root(), 2); });
}
grpc::Status IndexServiceAdapter::FindSymbols(grpc::ServerContext *context,
                                              const FindSymbolsRequest *request,
                                              FindSymbolsResponse *out) {
  return rpc([&] {
    *out = indexer_->find(
        *context, request->project_root(), request->query(), request->limit(),
        request->match_mode() == FindSymbolsRequest::MATCH_MODE_PREFIX, false);
  });
}
grpc::Status
IndexServiceAdapter::LookupSymbol(grpc::ServerContext *context,
                                  const LookupSymbolRequest *request,
                                  FindSymbolsResponse *out) {
  return rpc([&] {
    *out = indexer_->find(*context, request->project_root(), request->usr(),
                          1000, false, true);
  });
}
} // namespace ctk::net
