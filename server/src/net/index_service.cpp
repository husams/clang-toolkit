#include "ctk/net/index_service.hpp"
#include "ctk/platform/index_worker.hpp"
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
    const auto deadline =
        std::min(context.deadline(), std::chrono::system_clock::now() +
                                         std::chrono::milliseconds(250));
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
    std::string sql =
        "SELECT "
        "s.usr,s.name,s.qualified_name,s.kind,s.file_path,s.line,s.column_no,s."
        "signature,t.main_file,t.arguments,s.byte_offset,s.is_definition,t."
        "status FROM symbol s JOIN translation_unit t ON t.id=s.tu_id WHERE ";
    if (by_usr)
      sql += "s.usr=?";
    else if (prefix)
      sql +=
          "(s.name LIKE ? ESCAPE '\\' OR s.qualified_name LIKE ? ESCAPE '\\')";
    else
      sql += "(s.name=? OR s.qualified_name=?)";
    sql +=
        " ORDER BY s.qualified_name,s.file_path,s.byte_offset,s.tu_id LIMIT ?";
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
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(120);
    for (;;) {
      if (!admitted(job))
        throw Interrupted();
      if (foreground_busy_ && foreground_busy_())
        throw Interrupted();
      if (auto bytes = worker.resident_bytes();
          bytes && *bytes > 1024ULL * 1024 * 1024)
        throw std::runtime_error("index worker exceeded 1 GiB memory budget");
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
      if (found == cache.end()) {
        try {
          found = cache
                      .emplace(path, digest_file(path,
                                                 [&] {
                                                   return admitted(job) &&
                                                          (!foreground_busy_ ||
                                                           !foreground_busy_());
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
    std::lock_guard lock(mutex_);
    if (stopping_ || cancelled_ || paused_ || job.epoch != job_.epoch)
      throw Interrupted();
    if (foreground_busy_ && foreground_busy_())
      throw Interrupted();
    transaction.commit();
  }
  void replace(const Job &job, Database &db,
               const IndexWorkerTranslationUnit &unit, const std::string &id,
               const std::string &command_hash,
               const IndexWorkerResponse &response) {
    google::protobuf::Struct manifest;
    for (const auto &dependency : response.dependencies())
      (*manifest.mutable_fields())[dependency.path()].set_string_value(
          dependency.sha256());
    const auto encoded = json(manifest);
    std::map<std::string, std::string> fresh;
    if (!manifest_current(job, dependencies(encoded), fresh))
      throw Interrupted();
    await_admission(job);
    Transaction transaction(db);
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
    Statement remove(db, "DELETE FROM symbol WHERE tu_id=?");
    remove.bind(1, id);
    remove.step();
    Statement symbol(
        db,
        "INSERT OR IGNORE INTO "
        "symbol(tu_id,usr,name,qualified_name,kind,file_path,byte_offset,is_"
        "definition,line,column_no,signature) VALUES(?,?,?,?,?,?,?,?,?,?,?)");
    for (const auto &value : response.symbols()) {
      if (!admitted(job) || (foreground_busy_ && foreground_busy_()))
        throw Interrupted();
      symbol.bind(1, id);
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
    }
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
    Statement previous(db, "SELECT id FROM translation_unit WHERE main_file=?");
    previous.bind(1, source);
    Statement stale(db, "UPDATE translation_unit SET status='failed',last_error=? "
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
    auto listing_result = execute(job, listing, directory);
    if (commands_digest.empty() ||
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
    // Version/toolchain identity is part of each command key. Replacing the
    // extractor invalidates its saved contributions without a fourth table.
    const auto executable_time = fs::last_write_time(executable_);
    if (extractor_stamp_.empty() || executable_time != extractor_time_) {
      extractor_stamp_ =
          digest_file(executable_.string(), [&] { return admitted(job); });
      if (extractor_stamp_.empty())
        throw Interrupted();
      extractor_time_ = executable_time;
    }
    const auto &extractor_stamp = extractor_stamp_;
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
      const auto command_hash =
          digest_text(unit.compile_context() + extractor_stamp);
      active.insert(digest_text(unit.source() + '\n' + command_hash));
    }
    for (const auto &unit : listing_result.translation_units()) {
      await_admission(job);
      const auto command_hash =
          digest_text(unit.compile_context() + extractor_stamp);
      const auto id = digest_text(unit.source() + '\n' + command_hash);
      progress(job,
               [&](auto &s) { s.set_current_translation_unit(unit.source()); });
      bool unchanged = false;
      {
        Statement prior(
            db, "SELECT dependencies_json FROM translation_unit WHERE id=?");
        prior.bind(1, id);
        if (prior.step())
          unchanged =
              manifest_current(job, dependencies(prior.text(0)), digest_cache);
      }
      if (unchanged) {
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
          IndexWorkerRequest request;
          request.set_source(unit.source());
          request.set_compile_commands_directory(job.commands);
          request.set_working_directory(unit.working_directory());
          *request.mutable_compile_arguments() = unit.compile_arguments();
          auto response = execute(job, std::move(request), directory);
          if (commands_digest !=
              digest_file(
                  (fs::path(job.commands) / "compile_commands.json").string()))
            throw Interrupted();
          replace(job, db, unit, id, command_hash, response);
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
    }
    await_admission(job);
    std::vector<std::string> obsolete;
    {
      Statement rows(db, "SELECT id,main_file FROM translation_unit");
      while (rows.step())
        if (!active.contains(rows.text(0)) &&
            !failed_sources.contains(rows.text(1)))
          obsolete.push_back(rows.text(0));
    }
    if (!obsolete.empty()) {
      Transaction transaction(db);
      Statement remove(db, "DELETE FROM translation_unit WHERE id=?");
      for (const auto &id : obsolete) {
        remove.bind(1, id);
        remove.step();
        remove.reset();
      }
      bump(db);
      commit(job, transaction);
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
    await_admission(job);
    sqlite3_wal_checkpoint_v2(db.handle, nullptr, SQLITE_CHECKPOINT_PASSIVE,
                              nullptr, nullptr);
  }
  void loop() {
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
        metadata(db, "schema_version", "1");
        metadata(db, "project_root", job.root);
        while (current(job)) {
          try {
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
  std::string extractor_stamp_;
  fs::file_time_type extractor_time_{};
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
