#include "ctk/net/index_service.hpp"
#include "../platform/index_input_watch.hpp"
#include "ctk/platform/index_worker.hpp"
#include "file_digest_cache.hpp"
#include "include_inventory_cache.hpp"
#include "project_index_store.hpp"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <fstream>
#include <future>
#include <limits>
#include <map>
#include <mutex>
#include <optional>
#include <semaphore>
#include <set>
#include <thread>
#include <unordered_map>
#include <utility>

#include <google/protobuf/util/json_util.h>

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
// WAL cleanup after a monitor stops can briefly hold an exclusive lock. Keep
// foreground reads retryable within their existing deadline/cancellation
// budget.
class ReadBudget {
public:
  explicit ReadBudget(
      grpc::ServerContext &context,
      std::chrono::seconds operation_budget = std::chrono::seconds(1))
      : context_(context), deadline_(std::min(context.deadline(),
                                              std::chrono::system_clock::now() +
                                                  operation_budget)) {}
  bool interrupted() const {
    return context_.IsCancelled() ||
           std::chrono::system_clock::now() >= deadline_;
  }
  void wait_for_locks(Database &db) {
    sqlite3_busy_handler(
        db.handle,
        [](void *raw, int) {
          auto &budget = *static_cast<ReadBudget *>(raw);
          if (budget.interrupted())
            return 0;
          std::this_thread::sleep_for(std::chrono::milliseconds(1));
          return budget.interrupted() ? 0 : 1;
        },
        this);
  }
  void limit_query(Database &db) {
    wait_for_locks(db);
    sqlite3_progress_handler(
        db.handle, 1000,
        [](void *raw) {
          return static_cast<ReadBudget *>(raw)->interrupted() ? 1 : 0;
        },
        this);
  }

private:
  grpc::ServerContext &context_;
  std::chrono::system_clock::time_point deadline_;
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
void load_last_pass(Database &db, ProjectIndexStatus &status) {
  Statement row(db,
                "SELECT value FROM metadata WHERE key='last_completed_pass'");
  IndexPassSummary summary;
  if (row.step() &&
      google::protobuf::util::JsonStringToMessage(row.text(0), &summary).ok()) {
    *status.mutable_last_completed_pass() = summary;
    status.set_last_reconciled_unix_seconds(summary.finished_unix_seconds());
  }
}

struct SourcePathFilter {
  explicit SourcePathFilter(const fs::path &root)
      : lexical_root_(root.lexically_normal()) {
    std::error_code error;
    root_ = fs::weakly_canonical(root, error);
    if (error)
      root_.clear();
  }

  bool contains(const std::string &raw_path) {
    if (const auto found = cache_.find(raw_path); found != cache_.end())
      return found->second;
    const auto result = compute(raw_path);
    cache_.emplace(raw_path, result);
    return result;
  }

private:
  bool compute(const std::string &raw_path) const {
    if (root_.empty() || raw_path.empty())
      return false;
    const auto raw = fs::path(raw_path).lexically_normal();
    auto relative = raw.lexically_relative(lexical_root_);
    if (relative.empty() || relative.is_absolute() ||
        *relative.begin() == "..") {
      // A logical/physical alias such as /var vs /private/var needs the
      // filesystem fallback below before deciding containment.
      relative.clear();
    } else if (excluded(relative)) {
      return false;
    }
    const auto parent = raw.parent_path();
    const auto parent_key = parent.string();
    auto parent_result = directory_cache_.find(parent_key);
    if (parent_result == directory_cache_.end()) {
      std::error_code parent_error;
      auto canonical_parent = fs::weakly_canonical(parent, parent_error);
      parent_result = directory_cache_
                          .emplace(parent_key,
                                   parent_error
                                       ? std::optional<fs::path>{}
                                       : std::optional<fs::path>{
                                             std::move(canonical_parent)})
                          .first;
    }
    if (!parent_result->second)
      return false;
    const auto &canonical_parent = *parent_result->second;
    auto canonical = canonical_parent / raw.filename();
    std::error_code status_error;
    const auto final_status = fs::symlink_status(raw, status_error);
    const bool missing =
        status_error == std::errc::no_such_file_or_directory ||
        final_status.type() == fs::file_type::not_found;
    if (status_error && !missing)
      return false;
    if (!missing && fs::is_symlink(final_status)) {
      std::error_code canonical_error;
      canonical = fs::weakly_canonical(raw, canonical_error);
      if (canonical_error)
        return false;
    }
    relative = canonical.lexically_relative(root_);
    if (relative.empty() || relative.is_absolute())
      return false;
    return !excluded(relative);
  }

  static bool excluded(const fs::path &relative) {
    for (const auto &part : relative) {
      const auto component = part.string();
      if (component == ".." || component == ".git" ||
          component == "node_modules" || component == ".venv" ||
          component == ".cache" || component == "dist" ||
          component == "build" || component == "vendor" ||
          component == "third_party" || component == "_deps" ||
          component.starts_with("build-") ||
          component.starts_with("cmake-build-"))
        return true;
    }
    return false;
  }

  fs::path lexical_root_;
  fs::path root_;
  std::unordered_map<std::string, bool> cache_;
  mutable std::unordered_map<std::string, std::optional<fs::path>>
      directory_cache_;
};

void source_path_sqlite(sqlite3_context *context, int argc,
                        sqlite3_value **argv) noexcept {
  if (argc != 1 || sqlite3_value_type(argv[0]) == SQLITE_NULL) {
    sqlite3_result_int(context, 0);
    return;
  }
  auto *filter = static_cast<SourcePathFilter *>(sqlite3_user_data(context));
  const auto *value = sqlite3_value_text(argv[0]);
  if (!filter || !value) {
    sqlite3_result_int(context, 0);
    return;
  }
  try {
    sqlite3_result_int(
        context, filter->contains(reinterpret_cast<const char *>(value)) ? 1
                                                                         : 0);
  } catch (const std::bad_alloc &) {
    sqlite3_result_error_nomem(context);
  } catch (...) {
    sqlite3_result_error(context, "cannot classify indexed source path", -1);
  }
}

void register_source_path_filter(Database &db, SourcePathFilter &filter) {
  const auto status = sqlite3_create_function_v2(
      db.handle, "ctk_source_path", 1, SQLITE_UTF8, &filter,
      source_path_sqlite, nullptr, nullptr, nullptr);
  if (status != SQLITE_OK)
    throw std::runtime_error(sqlite3_errmsg(db.handle));
}
} // namespace

// This controller owns no native ASTs and never runs work on the foreground
// pool.
class ProjectSymbolMonitor {
public:
  ProjectSymbolMonitor(fs::path root, std::function<bool()> foreground_busy,
                       fs::path executable, std::size_t max_workers,
                       std::counting_semaphore<4> &worker_slots)
      : storage_(std::move(root) / "symbol-index"),
        executable_(executable.empty() ? platform::current_executable_sibling(
                                             "ctk-index-worker")
                                       : std::move(executable)),
        foreground_busy_(std::move(foreground_busy)),
        max_workers_(std::clamp<std::size_t>(
            max_workers ? max_workers
                        : platform::index_worker_parallelism_limit(),
            1, 4)),
        worker_slots_(worker_slots) {}
  void stop() {
    {
      std::lock_guard lock(mutex_);
      stopping_ = true;
    }
    changed_.notify_all();
  }
  ~ProjectSymbolMonitor() {
    stop();
    if (thread_.joinable())
      thread_.join();
  }
  fs::path database_path(const std::string &root) const {
    return storage_ / digest_text(root) / "symbols.sqlite3";
  }
  ListProjectIndexesResponse list(grpc::ServerContext &context) {
    ReadBudget budget(context);
    std::map<std::string, ProjectIndexStatus> projects;
    // Only index metadata is read; never hold the controller mutex during I/O.
    // A database may still be being initialized by the background worker.
    if (fs::exists(storage_)) {
      for (const auto &entry : fs::directory_iterator(storage_)) {
        if (context.IsCancelled())
          throw std::runtime_error("project index listing cancelled");
        const auto path = entry.path() / "symbols.sqlite3";
        if (!entry.is_directory() || !fs::is_regular_file(path))
          continue;
        Database db(path, false);
        budget.wait_for_locks(db);
        db.exec("BEGIN");
        Statement schema(db, "SELECT count(*) FROM sqlite_master WHERE "
                             "type='table' AND name IN "
                             "('metadata','translation_unit')");
        schema.step();
        if (schema.number(0) != 2)
          continue;
        Statement root(db, "SELECT value FROM metadata WHERE key='project_root'");
        if (!root.step() || root.text(0).empty())
          continue;
        const auto key = root_key(root.text(0));
        if (path != database_path(key))
          continue;
        ProjectIndexStatus saved;
        saved.set_project_root(key);
        saved.set_state(INDEX_STATE_IDLE);
        saved.set_revision(revision(db));
        saved.set_translation_units_indexed(count_units(db));
        load_last_pass(db, saved);
        Statement total(db, "SELECT value FROM metadata WHERE key='total'");
        if (total.step())
          saved.set_translation_units_total(std::stoull(total.text(0)));
        Statement failed(db, "SELECT count(*) FROM translation_unit "
                             "WHERE indexed_at>0 AND status='failed'");
        failed.step();
        saved.set_translation_units_failed(failed.number(0));
        if (saved.translation_units_total() > saved.translation_units_indexed())
          saved.set_translation_units_pending(saved.translation_units_total() -
                                              saved.translation_units_indexed());
        projects.emplace(key, std::move(saved));
      }
    }
    {
      std::lock_guard lock(mutex_);
      // Include queued work before its database exists, without duplicating
      // the saved row; live progress takes precedence over persisted coverage.
      if (!job_.root.empty())
        projects[job_.root] = status_;
    }
    ListProjectIndexesResponse response;
    for (auto &[key, status] : projects)
      *response.add_projects() = std::move(status);
    response.set_total_count(response.projects_size());
    return response;
  }
  ProjectIndexStatus start(const StartProjectIndexRequest &request) {
    const auto key = root_key(request.project_root());
    std::lock_guard lock(mutex_);
    if (!thread_.joinable())
      thread_ = std::thread([this] { loop(); });
    if (!job_.root.empty() && !cancelled_)
      return status_;
    job_.root = key;
    job_.commands = request.compile_commands();
    job_.interval = std::clamp(
        request.poll_interval_seconds() ? request.poll_interval_seconds() : 2u,
        1u, 3600u);
    ++job_.epoch;
    ++generation_;
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
    {
      std::lock_guard lock(mutex_);
      if (!job_.root.empty() && key == job_.root)
        return status_;
    }
    grpc::ServerContext context;
    const auto saved_projects = list(context);
    for (const auto &saved : saved_projects.projects()) {
      if (saved.project_root() == key)
        return saved;
    }
    ProjectIndexStatus idle;
    idle.set_project_root(key);
    idle.set_state(INDEX_STATE_IDLE);
    return idle;
  }
  ProjectIndexStatus control(const std::string &root, int action) {
    const auto key = root_key(root);
    std::lock_guard lock(mutex_);
    require_project(key);
    if (action == 2) {
      cancelled_ = true;
      paused_ = false;
      ++generation_;
      status_.set_state(INDEX_STATE_CANCELLED);
      status_.clear_paused_reason();
    } else if (cancelled_) {
      throw std::logic_error("cancelled index must be started before resuming");
    } else if (action == 0) {
      paused_ = true;
      ++generation_;
      status_.set_state(INDEX_STATE_PAUSED);
      status_.set_paused_reason(
          "paused by client; uncommitted extraction will be retried");
    } else {
      paused_ = false;
      ++generation_;
      status_.set_state(INDEX_STATE_QUEUED);
      status_.clear_paused_reason();
    }
    changed_.notify_all();
    return status_;
  }
  FindSymbolsResponse
  find(grpc::ServerContext &context, const std::string &root,
       const std::string &query, std::uint32_t requested_limit, bool prefix,
       bool by_usr,
       FindSymbolsRequest::Kind kind = FindSymbolsRequest::KIND_ANY,
       bool unique_symbols = false, bool source_only = false,
       std::uint64_t offset = 0, std::uint64_t expected_revision = 0) {
    std::string kind_filter;
    switch (kind) {
    case FindSymbolsRequest::KIND_ANY:
      break;
    case FindSymbolsRequest::KIND_FUNCTION:
      kind_filter = "kind IN ('Function','CXXMethod','CXXConstructor',"
                    "'CXXDestructor','CXXConversion','CXXDeductionGuide') AND ";
      break;
    case FindSymbolsRequest::KIND_CLASS:
      kind_filter =
          "kind IN ('Record','CXXRecord','ClassTemplateSpecialization',"
          "'ClassTemplatePartialSpecialization') AND ";
      break;
    case FindSymbolsRequest::KIND_VARIABLE:
      kind_filter =
          "kind IN ('Var','VarTemplateSpecialization',"
          "'VarTemplatePartialSpecialization','Field','Binding') AND ";
      break;
    case FindSymbolsRequest::KIND_ALIAS:
      kind_filter = "kind IN ('TypeAlias','Typedef') AND ";
      break;
    default:
      throw std::invalid_argument("invalid symbol kind filter");
    }
    const auto key = root_key(root);
    if (query.empty() &&
        !(prefix && kind == FindSymbolsRequest::KIND_ALIAS && !by_usr))
      throw std::invalid_argument("symbol query cannot be empty");
    if (query.size() > 4096)
      throw std::invalid_argument("symbol query exceeds 4096 bytes");
    const auto path = database_path(key);
    FindSymbolsResponse response;
    std::error_code path_error;
    if (!fs::exists(path, path_error) || path_error) {
      response.set_stale(true);
      return response;
    }
    // Source classification may consult filesystem metadata for distinct
    // indexed paths. Parent-path caching bounds that work, with a longer
    // finite budget than ordinary index reads under storage contention.
    // Client deadlines and cancellation still take precedence.
    const auto operation_budget =
        source_only || query.empty() ? std::chrono::seconds(5)
                                    : std::chrono::seconds(1);
    ReadBudget budget(context, operation_budget);
    std::optional<SourcePathFilter> source_paths;
    Database db(path, false);
    if (source_only) {
      source_paths.emplace(key);
      register_source_path_filter(db, *source_paths);
    }
    budget.limit_query(db);
    db.exec("BEGIN");
    {
      Statement schema(db, "SELECT count(*) FROM sqlite_master WHERE "
                           "(type='table' AND name IN "
                           "('metadata','translation_unit','symbol')) OR "
                           "(type='index' AND name IN "
                           "('symbol_name_prefix','symbol_qualified_prefix'))");
      schema.step();
      if (schema.number(0) != 5) {
        db.exec("ROLLBACK");
        response.set_stale(true);
        return response;
      }
    }
    response.set_revision(revision(db));
    if (expected_revision && expected_revision != response.revision())
      throw std::logic_error(
          "symbol index revision changed; restart pagination");
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
        std::string(unique_symbols ? "SELECT MIN(tu_id) AS tu_id,"
                                   : "SELECT tu_id,") +
        "usr,file_path,byte_offset,is_definition,qualified_name FROM symbol";
    const std::string group =
        unique_symbols
            ? " GROUP BY "
              "usr,file_path,byte_offset,is_definition,qualified_name "
            : " ";
    std::string source_filter;
    if (source_only)
      source_filter = "ctk_source_path(file_path)=1 AND ";
    const std::string filtered_columns =
        projection + " WHERE " + kind_filter + source_filter;
    const std::string name_columns =
        unique_symbols ? projection + " INDEXED BY symbol_name_prefix WHERE " +
                             kind_filter + source_filter
                       : filtered_columns;
    const std::string qualified_columns =
        unique_symbols
            ? projection + " INDEXED BY symbol_qualified_prefix WHERE " +
                  kind_filter + source_filter
            : filtered_columns;
    const std::string order =
        std::string(
            prefix ? "qualified_name COLLATE NOCASE,file_path,byte_offset,tu_id"
                   : "qualified_name,file_path,byte_offset,tu_id") +
        ",usr,is_definition,qualified_name COLLATE BINARY";
    const bool browse_aliases =
        query.empty() && prefix && kind == FindSymbolsRequest::KIND_ALIAS &&
        !by_usr;
    std::string sql;
    if (browse_aliases) {
      sql = "WITH selected AS MATERIALIZED (" + projection +
            " NOT INDEXED WHERE " + kind_filter + source_filter + "1" + group +
            "ORDER BY " + order + " LIMIT ?3), ";
    } else if (prefix) {
      sql = "WITH name_matches AS MATERIALIZED (" + name_columns +
            "name LIKE ?1 ESCAPE '\\'" + group + "ORDER BY " + order +
            " LIMIT ?3), qualified_matches AS MATERIALIZED (" +
            qualified_columns + "qualified_name LIKE ?2 ESCAPE '\\'" + group +
            "ORDER BY " + order +
            " LIMIT ?3), selected AS MATERIALIZED ("
            "SELECT * FROM name_matches UNION SELECT * FROM qualified_matches "
            "ORDER BY " +
            order + " LIMIT ?3), ";
    } else if (!by_usr) {
      // Keep the BINARY test residual so the existing NOCASE index can seek.
      sql = "WITH selected AS MATERIALIZED (" + projection +
            " INDEXED BY symbol_name_prefix WHERE " + kind_filter +
            source_filter +
            "name=?1 COLLATE NOCASE AND +name=?1 COLLATE BINARY" + group +
            "UNION " + projection +
            " INDEXED BY symbol_qualified_prefix WHERE " + kind_filter +
            source_filter +
            "qualified_name=?2 COLLATE NOCASE AND +qualified_name=?2 COLLATE "
            "BINARY" +
            group + "ORDER BY " + order + " LIMIT ?3), ";
    } else {
      sql = "WITH selected AS MATERIALIZED (" + filtered_columns + "usr=?1" +
            group + "ORDER BY " + order + " LIMIT ?2), ";
    }
    if (unique_symbols) {
      // Group physical definitions before LIMIT, so repeated TU contributions
      // cannot hide later unique results or make truncation misleading.
      sql += "candidates AS MATERIALIZED (SELECT * FROM selected), ";
    } else {
      sql +=
          "boundary AS MATERIALIZED (SELECT "
          "qualified_name,file_path,byte_offset "
          "FROM selected ORDER BY qualified_name" +
          std::string(prefix ? " COLLATE NOCASE" : "") +
          " DESC,file_path DESC,byte_offset DESC LIMIT 1), "
          "candidates AS MATERIALIZED (SELECT * FROM selected UNION " +
          projection + " INDEXED BY symbol_qualified_prefix WHERE " +
          kind_filter + source_filter +
          "qualified_name="
          "(SELECT qualified_name FROM boundary) COLLATE NOCASE " +
          (prefix ? std::string()
                  : "AND +qualified_name=(SELECT qualified_name FROM boundary) "
                    "COLLATE BINARY ") +
          "AND file_path=(SELECT file_path FROM boundary) AND byte_offset="
          "(SELECT byte_offset FROM boundary) AND " +
          kind_filter +
          (browse_aliases
               ? "1"
           : by_usr
               ? "usr=?1"
           : prefix
               ? "(name LIKE ?1 ESCAPE '\\' OR qualified_name LIKE ?2 "
                 "ESCAPE '\\')"
               : "(name=?1 COLLATE BINARY OR qualified_name=?2 COLLATE "
                 "BINARY)") +
          "), ";
    }
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
      if (unique_symbols) {
        sql +=
            "owners AS MATERIALIZED (SELECT id,dependencies_json FROM "
            "translation_unit INDEXED BY translation_unit_header_members "
            "WHERE indexed_at=0 AND id IN (SELECT tu_id FROM candidates)), "
            "expanded AS MATERIALIZED (SELECT c.tu_id AS owner_id,"
            "COALESCE((SELECT MIN(value) FROM "
            "json_each(o.dependencies_json)),c.tu_id) AS tu_id,"
            "c.usr,c.file_path,c.byte_offset,c.is_definition,c.qualified_name "
            "FROM candidates c LEFT JOIN owners o ON o.id=c.tu_id), ";
      } else {
        sql += "owners AS MATERIALIZED (SELECT id,dependencies_json FROM "
               "translation_unit INDEXED BY translation_unit_header_members "
               "WHERE indexed_at=0 AND id IN (SELECT tu_id FROM candidates)), "
               "expanded AS MATERIALIZED (SELECT c.tu_id AS owner_id,"
               "COALESCE(m.value,c.tu_id) AS "
               "tu_id,c.usr,c.file_path,c.byte_offset,"
               "c.is_definition,c.qualified_name FROM candidates c LEFT JOIN "
               "owners o ON o.id=c.tu_id LEFT JOIN "
               "json_each(o.dependencies_json) m "
               "ORDER BY c.qualified_name" +
               std::string(prefix ? " COLLATE NOCASE" : "") +
               ",c.file_path,c.byte_offset,COALESCE(m.value,c.tu_id) LIMIT " +
               (by_usr ? "?2), " : "?3), ");
      }
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
        ",s.file_path,s.byte_offset,t.id,s.usr,s.is_definition,s.qualified_"
        "name COLLATE BINARY";
    Statement symbols(db, sql.c_str());
    const auto pattern = prefix ? escaped_prefix(query) : query;
    if (!browse_aliases) {
      symbols.bind(1, pattern);
      if (!by_usr)
        symbols.bind(2, pattern);
    }
    const auto limit =
        std::clamp(requested_limit ? requested_limit : 100u, 1u, 1000u);
    if (offset >
        static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()) -
            limit - 1)
      throw std::invalid_argument("symbol offset exceeds supported range");
    const auto candidate_limit = offset + limit + 1;
    symbols.bind(by_usr ? 2 : 3, candidate_limit);
    std::uint64_t skipped = 0;
    while (symbols.step()) {
      if (skipped < offset) {
        ++skipped;
        continue;
      }
      if (response.symbols_size() == static_cast<int>(limit)) {
        response.set_truncated(true);
        response.set_next_offset(offset + limit);
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
    if (response.truncated())
      response.set_next_offset(offset + response.symbols_size());
    return response;
  }

private:
  class PendingExtraction {
  public:
    PendingExtraction(ProjectSymbolMonitor &owner, Job job,
                      IndexWorkerRequest request, fs::path directory,
                      std::uint64_t generation)
        : owner_(owner), job_(std::move(job)), generation_(generation),
          result_(promise_.get_future()),
          thread_([this, request = std::move(request),
                   directory = std::move(directory)]() mutable {
            platform::lower_index_thread_priority();
            try {
              promise_.set_value(
                  owner_.execute(job_, std::move(request), directory, [this] {
                    return stopped_.load(std::memory_order_acquire) ||
                           !owner_.admitted(job_, generation_);
                  }));
            } catch (...) {
              promise_.set_exception(std::current_exception());
            }
          }) {}
    PendingExtraction(const PendingExtraction &) = delete;
    PendingExtraction &operator=(const PendingExtraction &) = delete;
    ~PendingExtraction() { stop_and_join(); }

    IndexWorkerResponse get() {
      try {
        auto response = result_.get();
        stop_and_join();
        return response;
      } catch (...) {
        stop_and_join();
        throw;
      }
    }
    void request_stop() { stopped_.store(true, std::memory_order_release); }
    void join() {
      if (thread_.joinable())
        thread_.join();
    }

  private:
    void stop_and_join() {
      request_stop();
      join();
    }

    ProjectSymbolMonitor &owner_;
    Job job_;
    std::uint64_t generation_;
    std::promise<IndexWorkerResponse> promise_;
    std::future<IndexWorkerResponse> result_;
    std::atomic<bool> stopped_{false};
    std::thread thread_;
  };

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
  bool admitted(const Job &job, std::uint64_t generation) {
    std::lock_guard lock(mutex_);
    return !stopping_ && !cancelled_ && !paused_ && job.epoch == job_.epoch &&
           generation == generation_;
  }
  bool foreground_busy() {
    if (!foreground_busy_)
      return false;
    std::lock_guard lock(foreground_mutex_);
    return foreground_busy_();
  }
  std::uint64_t generation() {
    std::lock_guard lock(mutex_);
    return generation_;
  }
  bool await_admission(const Job &job, const std::function<bool()> &stop = {}) {
    bool waited = false;
    for (;;) {
      if (stop && stop())
        throw Interrupted();
      {
        std::unique_lock lock(mutex_);
        if (stopping_ || cancelled_ || job.epoch != job_.epoch)
          throw Interrupted();
        if (paused_) {
          waited = true;
          changed_.wait_for(lock, std::chrono::milliseconds(100));
          continue;
        }
      }
      if (!foreground_busy())
        return waited;
      waited = true;
      std::unique_lock lock(mutex_);
      changed_.wait_for(lock, std::chrono::milliseconds(50));
    }
  }
  void end_extraction(const Job &job) {
    std::lock_guard lock(mutex_);
    if (job.epoch != job_.epoch)
      return;
    const auto active = status_.translation_units_indexing();
    status_.set_translation_units_indexing(active ? active - 1 : 0);
    if (status_.state() == INDEX_STATE_INDEXING && active <= 1)
      status_.set_state(INDEX_STATE_CHECKING);
  }
  IndexWorkerResponse execute(const Job &job, IndexWorkerRequest request,
                              const fs::path &directory,
                              const std::function<bool()> &stop = {}) {
    await_admission(job, stop);
    // All project monitors share the server's extraction budget. Polling the
    // permit keeps cancellation and shutdown responsive while another project
    // occupies the workers.
    while (!worker_slots_.try_acquire_for(std::chrono::milliseconds(25)))
      await_admission(job, stop);
    struct ReleaseSlot {
      std::counting_semaphore<4> &slots;
      ~ReleaseSlot() { slots.release(); }
    } release_slot{worker_slots_};
    if ((stop && stop()) || !admitted(job))
      throw Interrupted();
    // Count actual worker permits, not scheduled futures waiting for a slot.
    // Destruction runs after the worker is stopped and reaped on every exit.
    struct ExtractionStatus {
      ProjectSymbolMonitor &owner;
      const Job &job;
      bool active = false;
      ~ExtractionStatus() {
        if (active)
          owner.end_extraction(job);
      }
    } extraction_status{*this, job};
    if (!request.list_translation_units()) {
      progress(job, [](auto &s) {
        s.set_translation_units_indexing(s.translation_units_indexing() + 1);
        s.set_state(INDEX_STATE_INDEXING);
      });
      extraction_status.active = true;
    }
    fs::create_directories(directory);
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
      if ((stop && stop()) || !admitted(job))
        throw Interrupted();
      if (foreground_busy()) {
        // Retain the AST and current reconciliation position while giving
        // foreground requests the CPU and disk. The process group includes
        // wrapper children; cancellation still kills and reaps it immediately.
        const auto yielded_at = std::chrono::steady_clock::now();
        worker.suspend();
        await_admission(job, stop);
        worker.resume();
        deadline += std::chrono::steady_clock::now() - yielded_at;
        continue;
      }
      if (auto bytes = worker.resident_bytes();
          bytes && *bytes > 1536ULL * 1024 * 1024)
        throw std::runtime_error("index worker exceeded 1.5 GiB memory budget");
      const auto exit = worker.poll();
      if (exit) {
        if ((stop && stop()) || !admitted(job))
          throw Interrupted();
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
        if ((stop && stop()) || !admitted(job))
          throw Interrupted();
        return response;
      }
      if (std::chrono::steady_clock::now() >= deadline)
        throw std::runtime_error("index worker exceeded 120 second deadline");
      std::unique_lock lock(mutex_);
      changed_.wait_for(lock, std::chrono::milliseconds(25));
    }
  }
  bool manifest_current(const Job &job,
                        const std::map<std::string, std::string> &manifest) {
    if (manifest.empty())
      return false;
    for (;;) {
      inventories_.refresh();
      const auto inventory_generation = inventories_.generation();
      bool waited = false;
      bool matches = true;
      for (const auto &[path, hash] : manifest) {
        waited = await_admission(job) || waited;
        std::string current;
        const auto allowed = [&] {
          waited = await_admission(job) || waited;
          return true;
        };
        if (path.starts_with("@include-tree:")) {
          current = inventories_.digest(path.substr(14), allowed);
        } else {
          try {
            current = files_.digest(path, allowed);
          } catch (...) {
            if (!admitted(job) || foreground_busy())
              throw Interrupted();
            throw;
          }
        }
        if (current != hash) {
          matches = false;
          break;
        }
      }
      // Include names can change while later file contents are being read.
      // Content hashes are always fresh, including for memory-mapped writes.
      const bool trees_changed =
          inventories_.refresh() ||
          inventory_generation != inventories_.generation();
      if (!waited && !trees_changed)
        return matches;
      // A wait or directory event requires another complete validation pass.
    }
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
  void commit(const Job &job, Transaction &transaction,
              const std::function<void()> &validate = {},
              std::uint64_t expected_generation = 0) {
    // Only commit needs this gate. Parsing, hashing and inserts never hold the
    // status mutex. Revalidate after any foreground or pause wait, and again
    // whenever new foreground work wins admission before the commit lock.
    for (;;) {
      await_admission(job);
      if (validate)
        validate();
      std::lock_guard lock(mutex_);
      if (stopping_ || cancelled_ || paused_ || job.epoch != job_.epoch)
        throw Interrupted();
      if (expected_generation && expected_generation != generation_)
        throw Interrupted();
      if (foreground_busy())
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
      s.set_state(INDEX_STATE_CHECKING);
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
      ProjectSymbolMonitor &owner;
      const Job &job;
      bool interrupted = false;
    } budget{*this, job};
    sqlite3_progress_handler(
        db.handle, 1000,
        [](void *raw) {
          auto &b = *static_cast<Budget *>(raw);
          b.interrupted = !b.owner.admitted(b.job) || b.owner.foreground_busy();
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
  void stage_replace(const Job &job, Database &db,
                     const IndexWorkerTranslationUnit &unit,
                     const std::string &id, const std::string &command_hash,
                     const IndexWorkerResponse &response) {
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
    bump(db);
  }
  void replace(const Job &job, Database &db,
               const IndexWorkerTranslationUnit &unit, const std::string &id,
               const std::string &command_hash,
               const IndexWorkerResponse &response,
               const std::string &commands_digest,
               fs::file_time_type worker_time,
               std::uint64_t expected_generation) {
    google::protobuf::Struct manifest;
    for (const auto &dependency : response.dependencies())
      (*manifest.mutable_fields())[dependency.path()].set_string_value(
          dependency.sha256());
    const auto input_manifest = dependencies(json(manifest));
    await_admission(job);
    Transaction transaction(db);
    stage_replace(job, db, unit, id, command_hash, response);
    // Input validation belongs after commit admission: a foreground burst or
    // pause may otherwise change an input while the staged writer waits.
    commit(
        job, transaction,
        [&] {
          for (;;) {
            if (!manifest_current(job, input_manifest))
              throw Interrupted();
            bool waited = await_admission(job);
            const auto current_commands = digest_file(
                (fs::path(job.commands) / "compile_commands.json").string(),
                [&] {
                  waited = await_admission(job) || waited;
                  return true;
                });
            if (waited)
              continue;
            if (commands_digest != current_commands ||
                worker_time != fs::last_write_time(executable_))
              throw Interrupted();
            return;
          }
        },
        expected_generation);
  }
  void mark_failed(const Job &job, Database &db, const std::string &id,
                   const std::string &source,
                   const std::set<std::string> &active,
                   const std::string &error,
                   std::uint64_t expected_generation = 0) {
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
    commit(job, transaction, {}, expected_generation);
  }
  void reconcile(const Job &job, Database &db, const fs::path &directory,
                 const std::function<void(const std::string &)> &watch_input) {
    ProjectIndexStatus saved_status;
    load_last_pass(db, saved_status);
    progress(job, [](auto &s) {
      s.set_state(INDEX_STATE_CHECKING);
      s.set_translation_units_indexing(0);
      s.set_translation_units_completed(0);
      s.set_translation_units_skipped(0);
      s.set_translation_units_failed(0);
      s.set_translation_units_pending(s.translation_units_total());
      s.clear_current_translation_unit();
    });
    progress(job, [&](auto &s) {
      if (saved_status.has_last_completed_pass()) {
        *s.mutable_last_completed_pass() = saved_status.last_completed_pass();
        s.set_last_reconciled_unix_seconds(
            saved_status.last_reconciled_unix_seconds());
      }
    });
    IndexWorkerRequest listing;
    listing.set_list_translation_units(true);
    listing.set_compile_commands_directory(job.commands);
    const auto commands_digest = digest_file(
        (fs::path(job.commands) / "compile_commands.json").string());
    const auto worker_time = fs::last_write_time(executable_);
    auto listing_result = execute(job, listing, directory / "listing");
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
    // The worker context includes its extraction-source fingerprint, Clang
    // version, compiler, arguments and environment. Executable bytes also
    // contain unrelated build metadata and must not invalidate every TU.
    auto saved_revision = revision(db), saved_count = count_units(db);
    progress(job, [&](auto &s) {
      s.set_state(INDEX_STATE_CHECKING);
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
      // Failed first-time extractions have no saved manifest yet.
      watch_input(unit.source());
      const auto command_hash = digest_text(unit.compile_context());
      active.insert(digest_text(unit.source() + '\n' + command_hash));
    }
    struct UnitPlan {
      const IndexWorkerTranslationUnit *unit;
      std::string command_hash, id, previous_manifest;
      std::map<std::string, std::string> manifest;
      bool unchanged = false, migrate = false, manifest_validated = false;
    };
    const auto plan_unit = [&](const IndexWorkerTranslationUnit &unit) {
      await_admission(job);
      UnitPlan plan{&unit};
      plan.command_hash = digest_text(unit.compile_context());
      plan.id = digest_text(unit.source() + '\n' + plan.command_hash);
      Statement prior(
          db, "SELECT dependencies_json FROM translation_unit WHERE id=?");
      prior.bind(1, plan.id);
      if (prior.step()) {
        plan.previous_manifest = prior.text(0);
        plan.manifest = dependencies(plan.previous_manifest);
      }
      return plan;
    };
    const auto validate_plans = [&](const std::vector<UnitPlan *> &plans,
                                    std::uint64_t expected_generation) {
      std::map<std::string, std::string> expected;
      std::map<std::string, std::set<std::string>> hashes_by_path;
      std::vector<UnitPlan *> fallback;
      for (auto *plan : plans) {
        plan->unchanged = false;
        plan->manifest_validated = true;
        if (plan->manifest.empty())
          continue;
        for (const auto &[path, hash] : plan->manifest)
          hashes_by_path[path].insert(hash);
      }
      for (const auto &[path, hashes] : hashes_by_path) {
        if (hashes.size() != 1)
          continue;
        expected.emplace(path, *hashes.begin());
      }
      for (auto *plan : plans) {
        if (plan->manifest.empty())
          continue;
        const bool conflicts = std::any_of(
            plan->manifest.begin(), plan->manifest.end(), [&](const auto &dep) {
              return hashes_by_path[dep.first].size() > 1;
            });
        if (conflicts)
          fallback.push_back(plan);
      }
      std::set<std::string> mismatches;
      if (!expected.empty()) {
        for (;;) {
          if (!admitted(job, expected_generation))
            throw Interrupted();
          inventories_.refresh();
          const auto inventory_generation = inventories_.generation();
          bool waited = false;
          mismatches.clear();
          for (const auto &[path, hash] : expected) {
            waited = await_admission(job) || waited;
            if (!admitted(job, expected_generation))
              throw Interrupted();
            const auto allowed = [&] {
              waited = await_admission(job) || waited;
              if (!admitted(job, expected_generation))
                throw Interrupted();
              return true;
            };
            std::string current;
            if (path.starts_with("@include-tree:")) {
              current = inventories_.digest(path.substr(14), allowed);
            } else {
              try {
                current = files_.digest(path, allowed);
              } catch (...) {
                if (!admitted(job, expected_generation) || foreground_busy())
                  throw Interrupted();
                throw;
              }
            }
            if (current != hash)
              mismatches.insert(path);
          }
          const bool trees_changed =
              inventories_.refresh() ||
              inventory_generation != inventories_.generation();
          if (waited || trees_changed)
            continue;
          break;
        }
        for (auto *plan : plans) {
          if (plan->manifest.empty() ||
              std::find(fallback.begin(), fallback.end(), plan) !=
                  fallback.end())
            continue;
          plan->unchanged = std::none_of(
              plan->manifest.begin(), plan->manifest.end(),
              [&](const auto &dep) { return mismatches.contains(dep.first); });
        }
      }
      for (auto *plan : fallback)
        plan->unchanged = manifest_current(job, plan->manifest);
      for (auto *plan : plans)
        plan->migrate = plan->unchanged &&
                        plan->previous_manifest.find("\"@symbol-layout\"") ==
                            std::string::npos;
    };
    const auto needs_worker = [](const UnitPlan &plan) {
      return !(plan.unchanged && !plan.migrate) &&
             !(plan.migrate && symbol_groups(plan.previous_manifest).empty());
    };
    const auto make_request = [&](const IndexWorkerTranslationUnit &unit) {
      IndexWorkerRequest request;
      request.set_source(unit.source());
      request.set_header_cache_directory(
          (directory / "header-definitions").string());
      request.set_compile_commands_directory(job.commands);
      request.set_working_directory(unit.working_directory());
      *request.mutable_compile_arguments() = unit.compile_arguments();
      const std::vector<std::string> arguments(unit.compile_arguments().begin(),
                                               unit.compile_arguments().end());
      for (const auto &root : cache::include_roots(
               unit.source(), unit.working_directory(), arguments)) {
        auto *inventory = request.add_precomputed_include_inventories();
        inventory->set_path(root);
        inventory->set_sha256(inventories_.digest(root, [&] {
          await_admission(job);
          return true;
        }));
      }
      return request;
    };
    const auto &units = listing_result.translation_units();
    struct ScheduledUnit {
      UnitPlan plan;
      std::exception_ptr planning_error;
      std::unique_ptr<PendingExtraction> extraction;
      std::optional<IndexWorkerResponse> response;
      std::exception_ptr extraction_error;
      std::uint64_t generation = 0;
      bool extraction_slot = false;
    };
    struct SchedulerWindow {
      std::deque<ScheduledUnit> items;
      ~SchedulerWindow() {
        for (auto &item : items)
          if (item.extraction)
            item.extraction->request_stop();
        for (auto &item : items)
          if (item.extraction)
            item.extraction->join();
      }
    } scheduled;
    struct StaleSkip {};
    std::size_t active_extractions = 0;
    int next_unit = 0;
    const auto enqueue_next = [&] {
      await_admission(job);
      const auto &candidate = units.Get(next_unit++);
      try {
        auto plan = plan_unit(candidate);
        ScheduledUnit item{std::move(plan)};
        item.generation = generation();
        scheduled.items.push_back(std::move(item));
      } catch (const Interrupted &) {
        throw;
      } catch (...) {
        ScheduledUnit item{UnitPlan{&candidate}};
        item.plan.command_hash = digest_text(candidate.compile_context());
        item.plan.id =
            digest_text(candidate.source() + '\n' + item.plan.command_hash);
        item.planning_error = std::current_exception();
        item.generation = generation();
        scheduled.items.push_back(std::move(item));
      }
    };
    const auto launch_extraction = [&](ScheduledUnit &item) {
      if (!item.planning_error && needs_worker(item.plan) && !item.extraction &&
          active_extractions < max_workers_) {
        try {
          const auto &unit = *item.plan.unit;
          item.extraction = std::make_unique<PendingExtraction>(
              *this, job, make_request(unit),
              directory / "units" / item.plan.id /
                  std::to_string(item.generation),
              item.generation);
          item.extraction_slot = true;
          ++active_extractions;
        } catch (const Interrupted &) {
          throw;
        } catch (...) {
          item.planning_error = std::current_exception();
        }
      }
    };
    const auto launch_available = [&] {
      for (auto &candidate : scheduled.items) {
        if (active_extractions >= max_workers_)
          break;
        launch_extraction(candidate);
      }
    };
    const auto ensure_response = [&](ScheduledUnit &item) {
      if (item.response)
        return;
      if (item.extraction_error)
        std::rethrow_exception(item.extraction_error);
      try {
        if (item.planning_error)
          std::rethrow_exception(item.planning_error);
        const auto &unit = *item.plan.unit;
        if (item.plan.migrate &&
            symbol_groups(item.plan.previous_manifest).empty()) {
          item.response = stored_response(job, db, item.plan.id,
                                          item.plan.previous_manifest);
        } else if (item.extraction) {
          item.response = item.extraction->get();
          if (item.extraction_slot) {
            item.extraction_slot = false;
            --active_extractions;
          }
          launch_available();
        } else {
          if (needs_worker(item.plan)) {
            while (active_extractions >= max_workers_) {
              auto other =
                  std::find_if(scheduled.items.begin(), scheduled.items.end(),
                               [&](auto &candidate) {
                                 return &candidate != &item &&
                                        candidate.extraction &&
                                        candidate.extraction_slot;
                               });
              if (other == scheduled.items.end())
                break;
              try {
                other->response = other->extraction->get();
              } catch (const Interrupted &) {
                throw;
              } catch (...) {
                other->extraction_error = std::current_exception();
              }
              other->extraction_slot = false;
              --active_extractions;
            }
            launch_extraction(item);
            if (item.extraction) {
              item.response = item.extraction->get();
              item.extraction_slot = false;
              --active_extractions;
              launch_available();
            } else {
              item.response = execute(job, make_request(unit),
                                      directory / "units" / item.plan.id /
                                          std::to_string(item.generation));
            }
          } else {
            item.response = execute(job, make_request(unit),
                                    directory / "units" / item.plan.id /
                                        std::to_string(item.generation));
          }
        }
      } catch (const Interrupted &) {
        if (item.extraction_slot) {
          item.extraction_slot = false;
          --active_extractions;
        }
        throw;
      } catch (...) {
        if (item.extraction_slot) {
          item.extraction_slot = false;
          --active_extractions;
        }
        item.extraction_error = std::current_exception();
        throw;
      }
    };
    const auto publish_batch = [&](const std::vector<ScheduledUnit *> &batch) {
      if (batch.size() < 2)
        return false;
      std::map<std::string, std::string> manifest;
      for (const auto *item : batch) {
        for (const auto &dependency : item->response->dependencies()) {
          const auto [found, inserted] =
              manifest.emplace(dependency.path(), dependency.sha256());
          if (!inserted && found->second != dependency.sha256())
            return false;
        }
      }
      const auto expected_generation = batch.front()->generation;
      if (!admitted(job, expected_generation) ||
          commands_digest != digest_file(
                                 (fs::path(job.commands) /
                                  "compile_commands.json")
                                     .string()))
        throw Interrupted();
      await_admission(job);
      Transaction transaction(db);
      try {
        for (const auto *item : batch) {
          progress(job, [&](auto &s) {
            s.set_current_translation_unit(item->plan.unit->source());
          });
          stage_replace(job, db, *item->plan.unit, item->plan.id,
                        item->plan.command_hash, *item->response);
        }
        const auto validate_commands = [&] {
          for (;;) {
            if (!manifest_current(job, manifest))
              throw Interrupted();
            bool waited = await_admission(job);
            const auto current_commands = digest_file(
                (fs::path(job.commands) / "compile_commands.json").string(),
                [&] {
                  waited = await_admission(job) || waited;
                  return true;
                });
            if (waited)
              continue;
            if (commands_digest != current_commands ||
                worker_time != fs::last_write_time(executable_))
              throw Interrupted();
            return;
          }
        };
        commit(job, transaction, validate_commands, expected_generation);
      } catch (const Interrupted &) {
        throw;
      } catch (const std::exception &) {
        // The transaction rolls back. The caller falls back to the existing
        // single-TU publication path, preserving its failure isolation.
        return false;
      }
      return true;
    };
    for (int unit_index = 0; unit_index < units.size(); ++unit_index) {
      // Plan on the controller, and keep the database and digest caches out of
      // worker threads. Fill a bounded ordered window before publishing rows.
      while (next_unit < units.size() && scheduled.items.size() < 16) {
        enqueue_next();
      }
      {
        std::vector<UnitPlan *> plans;
        for (auto &candidate : scheduled.items)
          if (!candidate.planning_error && !candidate.plan.manifest_validated &&
              !candidate.plan.manifest.empty())
            plans.push_back(&candidate.plan);
        if (!plans.empty())
          validate_plans(plans, scheduled.items.front().generation);
        launch_available();
      }
      if (scheduled.items.empty())
        throw Interrupted();
      auto &item = scheduled.items.front();
      if (!admitted(job, item.generation))
        throw Interrupted();
      const auto &unit = *item.plan.unit;
      if (!item.plan.unchanged && !item.planning_error) {
        std::vector<ScheduledUnit *> batch;
        constexpr std::size_t max_batch_units = 16;
        for (std::size_t i = 0; i < max_batch_units; ++i) {
          while (i >= scheduled.items.size() && next_unit < units.size()) {
            enqueue_next();
            auto &added = scheduled.items.back();
            if (!added.planning_error && !added.plan.manifest.empty()) {
              const std::vector<UnitPlan *> one{&added.plan};
              validate_plans(one, added.generation);
            }
            launch_available();
          }
          if (i >= scheduled.items.size())
            break;
          auto &candidate = scheduled.items[i];
          if (candidate.plan.unchanged || candidate.planning_error ||
              candidate.generation != item.generation)
            break;
          try {
            ensure_response(candidate);
          } catch (const Interrupted &) {
            throw;
          } catch (...) {
            break;
          }
          batch.push_back(&candidate);
          // ensure_response joined this unit's worker; launch_available keeps
          // the bounded extraction slots occupied from the planned window.
        }
        if (batch.size() > 1 && publish_batch(batch)) {
          completed += batch.size();
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
          checkpoint(job, db);
          const auto published = batch.size();
          for (std::size_t i = 0; i < published; ++i)
            scheduled.items.pop_front();
          unit_index += static_cast<int>(published) - 1;
          continue;
        }
      }
      if (item.plan.unchanged && !item.plan.migrate) {
        std::vector<ScheduledUnit *> skips;
        constexpr std::size_t max_batch_units = 16;
        for (std::size_t i = 0; i < max_batch_units; ++i) {
          while (i >= scheduled.items.size() && next_unit < units.size()) {
            enqueue_next();
            auto &added = scheduled.items.back();
            if (!added.planning_error && !added.plan.manifest.empty()) {
              const std::vector<UnitPlan *> one{&added.plan};
              validate_plans(one, added.generation);
            }
            launch_available();
          }
          if (i >= scheduled.items.size())
            break;
          auto &candidate = scheduled.items[i];
          if (!candidate.plan.unchanged || candidate.plan.migrate ||
              candidate.planning_error ||
              candidate.generation != item.generation)
            break;
          skips.push_back(&candidate);
        }
        std::vector<UnitPlan *> skip_plans;
        for (auto *skip : skips)
          skip_plans.push_back(&skip->plan);
        try {
          Transaction transaction(db);
          for (auto *skip : skips) {
            Statement ready(
                db, "UPDATE translation_unit SET status='ready',last_error='' "
                    "WHERE id=? AND status!='ready'");
            ready.bind(1, skip->plan.id);
            ready.step();
          }
          const auto validate_skips = [&] {
            for (;;) {
              validate_plans(skip_plans, item.generation);
              if (std::any_of(
                      skip_plans.begin(), skip_plans.end(),
                      [](const auto *plan) { return !plan->unchanged; }))
                throw StaleSkip{};
              bool waited = await_admission(job);
              const auto current_commands = digest_file(
                  (fs::path(job.commands) / "compile_commands.json").string(),
                  [&] {
                    waited = await_admission(job) || waited;
                    return true;
                  });
              if (waited)
                continue;
              if (!admitted(job, item.generation) ||
                  commands_digest != current_commands ||
                  worker_time != fs::last_write_time(executable_))
                throw Interrupted();
              return;
            }
          };
          commit(job, transaction, validate_skips, item.generation);
          skipped += skips.size();
          completed += skips.size();
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
          checkpoint(job, db);
          const auto published = skips.size();
          for (std::size_t i = 0; i < published; ++i)
            scheduled.items.pop_front();
          unit_index += static_cast<int>(published) - 1;
          continue;
        } catch (const StaleSkip &) {
          // A stale later TU may follow an unchanged head. Retry the head so
          // the next skip window ends at the stale entry and commits this
          // freshly validated prefix. A stale head falls through to extraction.
          if (item.plan.unchanged) {
            --unit_index;
            continue;
          }
        }
      }
      auto &plan = item.plan;
      if (plan.unchanged) {
        // Revalidate each preplanned skip immediately before consumption.
        // The controller owns the row, so reuse its decoded manifest only.
        plan.unchanged = manifest_current(job, plan.manifest);
        if (!plan.unchanged)
          plan.migrate = false;
      }
      const auto &id = plan.id;
      progress(job,
               [&](auto &s) { s.set_current_translation_unit(unit.source()); });
      try {
        if (item.planning_error) {
          auto error = std::exchange(item.planning_error, {});
          std::rethrow_exception(error);
        }
        if (item.extraction_error)
          std::rethrow_exception(item.extraction_error);
        ensure_response(item);
        IndexWorkerResponse response = std::move(*item.response);
        if (commands_digest !=
            digest_file(
                (fs::path(job.commands) / "compile_commands.json").string()))
          throw Interrupted();
        if (!admitted(job, item.generation))
          throw Interrupted();
        replace(job, db, unit, id, plan.command_hash, response, commands_digest,
                worker_time, item.generation);
        ++completed;
      } catch (const Interrupted &) {
        throw;
      } catch (const std::exception &error) {
        if (!admitted(job, item.generation))
          throw Interrupted();
        mark_failed(job, db, id, unit.source(), active, error.what(),
                    item.generation);
        failed_sources.insert(unit.source());
        ++failed;
        progress(job, [&](auto &s) { s.set_error(error.what()); });
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
      if (!plan.unchanged || plan.migrate)
        checkpoint(job, db);
      scheduled.items.pop_front();
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
        ProjectSymbolMonitor &owner;
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
    IndexPassSummary summary;
    summary.set_total(total);
    summary.set_reused(skipped);
    summary.set_newly_indexed(completed - skipped);
    summary.set_failed(failed);
    summary.set_finished_unix_seconds(timestamp());
    std::string summary_json;
    if (!google::protobuf::util::MessageToJsonString(summary, &summary_json)
             .ok())
      throw std::runtime_error("cannot encode completed index pass");
    {
      Transaction transaction(db);
      metadata(db, "last_completed_pass", summary_json);
      commit(job, transaction);
    }
    progress(job, [&](auto &s) {
      s.set_translation_units_indexing(0);
      s.set_state(failed ? INDEX_STATE_FAILED : INDEX_STATE_COMPLETE);
      s.clear_current_translation_unit();
      *s.mutable_last_completed_pass() = summary;
      s.set_last_reconciled_unix_seconds(summary.finished_unix_seconds());
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
        // Arm before reconciling, so edits during extraction remain queued.
        platform::IndexInputWatch inputs;
        std::set<std::string> watched;
        auto arm_input = [&](const std::string &path) {
          if (!watched.insert(path).second)
            return false;
          inputs.add_file(path);
          return true;
        };
        auto arm_inputs = [&] {
          arm_input((fs::path(job.commands) / "compile_commands.json").string());
          arm_input(executable_.string());
          std::set<std::string> paths;
          Statement rows(db, "SELECT main_file,dependencies_json FROM "
                             "translation_unit WHERE indexed_at>0");
          while (rows.step()) {
            // Register sources and dependencies by path; idle notifications
            // do not retain a descriptor for every input file.
            arm_input(rows.text(0));
            try {
              for (const auto &[path, digest] : dependencies(rows.text(1)))
                if (!path.starts_with("@include-tree:"))
                  paths.insert(path);
            } catch (const std::runtime_error &) {
              // Reconciliation handles corrupt manifests per TU, preserving
              // valid publications from the rest of the project.
            }
          }
          bool added = false;
          for (const auto &path : paths) {
            added = arm_input(path) || added;
          }
          return added;
        };
        arm_inputs();
        inputs.arm();
        while (current(job)) {
          try {
            upgrade_symbols(job, db);
            metadata(db, "schema_version", "2");
            reconcile(job, db, directory, arm_input);
          } catch (const Interrupted &) {
            if (!current(job))
              break;
            await_admission(job);
            continue;
          } catch (const std::exception &error) {
            progress(job, [&](auto &s) {
              s.set_state(INDEX_STATE_FAILED);
              s.set_translation_units_indexing(0);
              s.set_error(error.what());
            });
          }
          // Newly discovered inputs need one guarded validation pass after
          // arming. Afterwards idle projects do no per-file work until an
          // event or the bounded safety sweep (also covers lost watches).
          const bool new_inputs = arm_inputs();
          inputs.arm();
          // Watch budgets bound resource use, not the reconciliation interval.
          // Missing/lost notifications are covered by the same five-minute
          // sweep.
          const auto deadline = std::chrono::steady_clock::now() +
                                std::chrono::seconds(new_inputs ? 2 : 300);
          while (current(job)) {
            std::unique_lock lock(mutex_);
            changed_.wait_for(
                lock, std::chrono::seconds(std::min(job.interval, 2u)), [&] {
                  return stopping_ || cancelled_ || paused_ ||
                         job.epoch != job_.epoch;
                });
            const bool resumed = paused_;
            lock.unlock();
            if (resumed)
              await_admission(job);
            if (resumed || inputs.changed() || inventories_.inputs_changed() ||
                std::chrono::steady_clock::now() >= deadline) {
              // Reopen watches after rename/delete/revoke/overflow. Retaining
              // the old descriptors would miss later edits to replacements.
              inventories_.reset();
              inputs.reset();
              watched.clear();
              arm_inputs();
              inputs.arm();
              break;
            }
          }
        }
      } catch (const Interrupted &) {
        // A new start, cancellation, or shutdown superseded this job.
      } catch (const std::exception &error) {
        std::lock_guard lock(mutex_);
        if (job.epoch == job_.epoch) {
          status_.set_state(INDEX_STATE_FAILED);
          status_.set_translation_units_indexing(0);
          status_.set_error(error.what());
          cancelled_ = true;
        }
      }
    }
  }
  fs::path storage_, executable_;
  std::function<bool()> foreground_busy_;
  std::size_t max_workers_;
  std::counting_semaphore<4> &worker_slots_;
  std::mutex foreground_mutex_;
  IncludeInventoryCache inventories_;
  FileDigestCache files_;
  std::mutex mutex_;
  std::condition_variable changed_;
  Job job_;
  ProjectIndexStatus status_;
  bool stopping_ = false, cancelled_ = true, paused_ = false;
  std::uint64_t generation_ = 0;
  std::thread thread_;
};

// Own each project's reconciliation state independently, while sharing the
// process budget and foreground gate across all monitors. The reader never
// starts a thread; it serves persisted indexes not started in this process.
class BackgroundSymbolIndexer {
public:
  BackgroundSymbolIndexer(fs::path root, std::function<bool()> foreground_busy,
                          fs::path executable, std::size_t max_workers)
      : storage_(std::move(root)), executable_(std::move(executable)),
        foreground_busy_(std::move(foreground_busy)),
        max_workers_(std::clamp<std::size_t>(
            max_workers ? max_workers
                        : platform::index_worker_parallelism_limit(),
            1, 4)),
        worker_slots_(max_workers_),
        reader_(storage_, foreground_gate(), executable_, max_workers_,
                worker_slots_) {}
  ~BackgroundSymbolIndexer() {
    // Signal every monitor before joining any of them, including monitors
    // waiting for another project's extraction slot.
    for (auto &[root, monitor] : monitors_)
      monitor->stop();
    monitors_.clear();
  }
  ListProjectIndexesResponse list(grpc::ServerContext &context) {
    auto saved = reader_.list(context);
    std::map<std::string, ProjectIndexStatus> projects;
    for (const auto &status : saved.projects())
      projects[status.project_root()] = status;
    std::map<std::string, std::shared_ptr<ProjectSymbolMonitor>> monitors;
    {
      std::lock_guard lock(mutex_);
      monitors = monitors_;
    }
    // Do not hold the registry mutex during filesystem reads or while taking
    // individual monitor locks. Include queued monitors before their DB exists.
    for (const auto &[root, monitor] : monitors) {
      if (context.IsCancelled())
        throw std::runtime_error("project index listing cancelled");
      projects[root] = monitor->status(root);
    }
    ListProjectIndexesResponse response;
    for (const auto &[root, status] : projects)
      *response.add_projects() = status;
    response.set_total_count(response.projects_size());
    return response;
  }
  ProjectIndexStatus start(const StartProjectIndexRequest &request) {
    const auto key = root_key(request.project_root());
    std::lock_guard lock(mutex_);
    auto &monitor = monitors_[key];
    if (!monitor)
      monitor = std::make_shared<ProjectSymbolMonitor>(
          storage_, foreground_gate(), executable_, max_workers_,
          worker_slots_);
    return monitor->start(request);
  }
  ProjectIndexStatus status(const std::string &root) {
    if (auto monitor = project(root))
      return monitor->status(root);
    return reader_.status(root);
  }
  ProjectIndexStatus control(const std::string &root, int action) {
    auto monitor = project(root);
    if (!monitor)
      throw std::logic_error("project has not been started on this server");
    return monitor->control(root, action);
  }
  FindSymbolsResponse
  find(grpc::ServerContext &context, const std::string &root,
       const std::string &query, std::uint32_t limit, bool prefix, bool by_usr,
       FindSymbolsRequest::Kind kind = FindSymbolsRequest::KIND_ANY,
       bool unique_symbols = false, bool source_only = false,
       std::uint64_t offset = 0, std::uint64_t expected_revision = 0) {
    auto monitor = project(root);
    return (monitor ? *monitor : reader_)
        .find(context, root, query, limit, prefix, by_usr, kind,
              unique_symbols, source_only, offset, expected_revision);
  }

private:
  std::function<bool()> foreground_gate() {
    return [this] {
      std::lock_guard lock(foreground_mutex_);
      return foreground_busy_ && foreground_busy_();
    };
  }
  std::shared_ptr<ProjectSymbolMonitor> project(const std::string &root) {
    const auto key = root_key(root);
    std::lock_guard lock(mutex_);
    const auto found = monitors_.find(key);
    return found == monitors_.end() ? nullptr : found->second;
  }
  fs::path storage_, executable_;
  std::function<bool()> foreground_busy_;
  std::mutex foreground_mutex_;
  std::size_t max_workers_;
  std::counting_semaphore<4> worker_slots_;
  ProjectSymbolMonitor reader_;
  std::mutex mutex_;
  std::map<std::string, std::shared_ptr<ProjectSymbolMonitor>> monitors_;
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
                                         fs::path executable,
                                         std::size_t max_workers)
    : indexer_(std::make_shared<BackgroundSymbolIndexer>(
          std::move(root), std::move(foreground_busy), std::move(executable),
          max_workers)) {}
IndexServiceAdapter::~IndexServiceAdapter() = default;
grpc::Status
IndexServiceAdapter::ListProjectIndexes(grpc::ServerContext *context,
                                        const ListProjectIndexesRequest *,
                                        ListProjectIndexesResponse *out) {
  // Inventory reads do not require the native extraction backend. In
  // particular, ServerStatus must remain available in builds without Clang.
  try {
    *out = indexer_->list(*context);
    return grpc::Status::OK;
  } catch (const std::exception &error) {
    return {grpc::StatusCode::UNAVAILABLE, error.what()};
  }
}
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
        request->match_mode() == FindSymbolsRequest::MATCH_MODE_PREFIX, false,
        request->kind(), request->unique_symbols(), request->source_only(),
        request->offset(), request->expected_revision());
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
