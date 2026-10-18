#include "../src/net/project_index_store.hpp"
#include "ctk/net/index_service.hpp"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <filesystem>
#include <fstream>
#include <gtest/gtest.h>
#include <iterator>
#include <mutex>
#include <set>
#include <signal.h>
#include <sqlite3.h>
#include <string_view>
#include <thread>
#include <utility>
#include <vector>

struct sqlite3_api_routines;

namespace ctk::net {
namespace fs = std::filesystem;
namespace {
using namespace ctk::index::v1;
struct RevisionTrace {
  fs::path database;
  std::atomic<bool> revision_one{false};
};
RevisionTrace *active_revision_trace = nullptr;
struct PipelineTrace {
  fs::path database, counter, release_file;
  fs::path edit_file;
  std::string edit_contents;
  std::uintmax_t required_workers = 0;
  std::atomic<bool> publication_started{false};
  std::atomic<bool> publication_gate_entered{false};
  std::atomic<bool> overlapped{false};
};
PipelineTrace *active_pipeline_trace = nullptr;

int trace_revision_one(unsigned event, void *context, void *statement, void *) {
  if (event != SQLITE_TRACE_PROFILE)
    return 0;
  auto &trace = *static_cast<RevisionTrace *>(context);
  auto *database = sqlite3_db_handle(static_cast<sqlite3_stmt *>(statement));
  const char *filename = sqlite3_db_filename(database, "main");
  if (!filename)
    return 0;
  std::error_code path_error;
  const bool same_database =
      fs::equivalent(filename, trace.database, path_error);
  if (path_error || !same_database)
    return 0;
  char *expanded = sqlite3_expanded_sql(static_cast<sqlite3_stmt *>(statement));
  const std::string_view sql(expanded ? expanded : "");
  if (sql.find("INSERT INTO metadata") != std::string_view::npos &&
      sql.find("'revision'") != std::string_view::npos &&
      sql.find("'1'") != std::string_view::npos)
    trace.revision_one.store(true, std::memory_order_release);
  sqlite3_free(expanded);
  return 0;
}

int install_revision_trace(sqlite3 *database, char **,
                           const sqlite3_api_routines *) {
  if (active_revision_trace)
    sqlite3_trace_v2(database, SQLITE_TRACE_PROFILE, trace_revision_one,
                     active_revision_trace);
  if (active_pipeline_trace) {
    sqlite3_trace_v2(
        database, SQLITE_TRACE_STMT,
        [](unsigned event, void *raw, void *statement, void *) {
          if (event != SQLITE_TRACE_STMT)
            return 0;
          auto &trace = *static_cast<PipelineTrace *>(raw);
          auto *database =
              sqlite3_db_handle(static_cast<sqlite3_stmt *>(statement));
          const char *filename = sqlite3_db_filename(database, "main");
          if (!filename)
            return 0;
          std::error_code path_error;
          if (!fs::equivalent(filename, trace.database, path_error) ||
              path_error)
            return 0;
          const char *sql = sqlite3_sql(static_cast<sqlite3_stmt *>(statement));
          if (sql && std::string_view(sql).find("INSERT INTO symbol") !=
                         std::string_view::npos)
            trace.publication_started.store(true, std::memory_order_release);
          return 0;
        },
        active_pipeline_trace);
    sqlite3_create_function(
        database, "block_index_publication", 0, SQLITE_UTF8,
        active_pipeline_trace,
        [](sqlite3_context *context, int, sqlite3_value **) {
          auto &trace =
              *static_cast<PipelineTrace *>(sqlite3_user_data(context));
          if (trace.publication_gate_entered.exchange(
                  true, std::memory_order_acq_rel)) {
            sqlite3_result_int(context, 0);
            return;
          }
          const auto deadline =
              std::chrono::steady_clock::now() + std::chrono::seconds(5);
          while (std::chrono::steady_clock::now() < deadline) {
            std::error_code error;
            if (fs::file_size(trace.counter, error) >= trace.required_workers) {
              trace.overlapped.store(true, std::memory_order_release);
              break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
          }
          if (trace.overlapped.load(std::memory_order_acquire) &&
              !trace.release_file.empty()) {
            const auto release_deadline =
                std::chrono::steady_clock::now() + std::chrono::seconds(10);
            while (!fs::exists(trace.release_file) &&
                   std::chrono::steady_clock::now() < release_deadline)
              std::this_thread::sleep_for(std::chrono::milliseconds(5));
          }
          if (!trace.edit_file.empty())
            std::ofstream(trace.edit_file) << trace.edit_contents;
          sqlite3_result_int(context, 0);
        },
        nullptr, nullptr);
  }
  return SQLITE_OK;
}

class RevisionTraceRegistration {
public:
  explicit RevisionTraceRegistration(RevisionTrace &trace) {
    active_revision_trace = &trace;
    registered_ = sqlite3_auto_extension(reinterpret_cast<void (*)(void)>(
                      install_revision_trace)) == SQLITE_OK;
  }
  ~RevisionTraceRegistration() {
    if (registered_)
      sqlite3_cancel_auto_extension(
          reinterpret_cast<void (*)(void)>(install_revision_trace));
    active_revision_trace = nullptr;
  }
  bool registered() const { return registered_; }

private:
  bool registered_ = false;
};

class PipelineTraceRegistration {
public:
  explicit PipelineTraceRegistration(PipelineTrace &trace) {
    active_pipeline_trace = &trace;
    registered_ = sqlite3_auto_extension(reinterpret_cast<void (*)(void)>(
                      install_revision_trace)) == SQLITE_OK;
  }
  ~PipelineTraceRegistration() {
    if (registered_)
      sqlite3_cancel_auto_extension(
          reinterpret_cast<void (*)(void)>(install_revision_trace));
    active_pipeline_trace = nullptr;
  }
  bool registered() const { return registered_; }

private:
  bool registered_ = false;
};

class ReleaseFileGuard {
public:
  explicit ReleaseFileGuard(fs::path path) : path_(std::move(path)) {}
  ~ReleaseFileGuard() { std::ofstream(path_) << "continue\n"; }

private:
  fs::path path_;
};

class ProjectIndexServiceTest : public ::testing::Test {
protected:
  fs::path root =
      fs::temp_directory_path() /
      ("ctk-project-index-" +
       std::to_string(
           std::chrono::steady_clock::now().time_since_epoch().count()));
  fs::path project = root / "project";
  fs::path storage = root / "storage";
  void SetUp() override {
    fs::create_directories(project);
    write("shared.h", "#if FLAVOR == 1\n#define ALPHA_FEATURE "
                      "1\n#else\n#define BETA_FEATURE 1\n#endif\n");
    write("one.cpp",
          "#include \"shared.h\"\n#ifdef ALPHA_FEATURE\nint alphaOnly(){return "
          "1;}\n#else\nint betaOnly(){return 2;}\n#endif\n");
    write("two.cpp",
          "#include \"shared.h\"\n#ifdef ALPHA_FEATURE\nint alphaOnly(){return "
          "3;}\n#else\nint betaOnly(){return 4;}\n#endif\n");
    write_commands();
  }
  void TearDown() override {
    std::error_code ec;
    fs::remove_all(root, ec);
  }
  void write(const char *name, const std::string &body) {
    std::ofstream(project / name) << body;
  }
  std::string quote(const std::string &v) {
    std::string out = "\"";
    for (char c : v) {
      if (c == '\\' || c == '\"')
        out += '\\';
      if (c == '\n')
        out += "\\n";
      else
        out += c;
    }
    return out + "\"";
  }
  void write_commands() {
    std::ofstream out(project / "compile_commands.json");
    out << "[";
    const auto compiler = quote(CTK_TEST_CLANG_TOOL_PATH);
    const auto directory = quote(project.string());
    const auto source_one = quote((project / "one.cpp").string());
    const auto source_two = quote((project / "two.cpp").string());
    out << "{\"directory\":" << directory << ",\"file\":" << source_one
        << ",\"arguments\":[" << compiler
        << ",\"-std=c++20\",\"-I.\",\"-DFLAVOR=1\",\"-c\"," << source_one
        << "]},";
    out << "{\"directory\":" << directory << ",\"file\":" << source_one
        << ",\"arguments\":[" << compiler
        << ",\"-std=c++20\",\"-I.\",\"-DFLAVOR=2\",\"-c\"," << source_one
        << "]},";
    out << "{\"directory\":" << directory << ",\"file\":" << source_two
        << ",\"arguments\":[" << compiler
        << ",\"-std=c++20\",\"-I.\",\"-DFLAVOR=1\",\"-c\"," << source_two
        << "]}]";
  }
  void write_single_variant_commands() {
    std::ofstream out(project / "compile_commands.json");
    const auto compiler = quote(CTK_TEST_CLANG_TOOL_PATH);
    const auto directory = quote(project.string());
    const auto source_one = quote((project / "one.cpp").string());
    const auto source_two = quote((project / "two.cpp").string());
    out << "["
        << "{\"directory\":" << directory << ",\"file\":" << source_one
        << ",\"arguments\":[" << compiler
        << ",\"-std=c++20\",\"-I.\",\"-DFLAVOR=1\",\"-c\"," << source_one
        << "]},"
        << "{\"directory\":" << directory << ",\"file\":" << source_two
        << ",\"arguments\":[" << compiler
        << ",\"-std=c++20\",\"-I.\",\"-DFLAVOR=1\",\"-c\"," << source_two
        << "]}]";
  }
  fs::path worker_wrapper(const fs::path &counter,
                          const std::string &before_exec = {}) {
    const auto shell_word = [](const std::string &value) {
      std::string out = "'";
      for (char c : value)
        out += c == '\'' ? "'\"'\"'" : std::string(1, c);
      return out + "'";
    };
    const auto path = root / "index-worker-wrapper";
    std::ofstream(path) << "#!/bin/sh\nprintf . >> "
                        << shell_word(counter.string()) << '\n'
                        << before_exec << "exec "
                        << shell_word(CTK_TEST_INDEX_WORKER) << " \"$@\"\n";
    fs::permissions(path, fs::perms::owner_all);
    return path;
  }
  fs::path worker_wrapper_with_release_barrier(const fs::path &counter,
                                               const fs::path &started,
                                               const fs::path &release) {
    const auto shell_word = [](const std::string &value) {
      std::string out = "'";
      for (char c : value)
        out += c == '\'' ? "'\"'\"'" : std::string(1, c);
      return out + "'";
    };
    const auto path = root / "index-worker-barrier-wrapper";
    const auto count_file = shell_word(counter.string());
    std::ofstream(path) << "#!/bin/sh\nprintf . >> " << count_file << '\n'
                        << "starts=$(wc -c < " << count_file << ")\n"
                        << "if [ \"$starts\" -gt 1 ]; then\n"
                        << "  touch " << shell_word(started.string()) << "/$$\n"
                        << "  while [ ! -e " << shell_word(release.string())
                        << " ]; do sleep 0.01; done\nfi\n"
                        << "exec " << shell_word(CTK_TEST_INDEX_WORKER)
                        << " \"$@\"\n";
    fs::permissions(path, fs::perms::owner_all);
    fs::create_directories(started);
    return path;
  }
  fs::path worker_wrapper_with_lock(const fs::path &counter,
                                    const fs::path &lock,
                                    const fs::path &overlap,
                                    const fs::path &pids = {},
                                    const std::string &before_exec = {}) {
    const auto shell_word = [](const std::string &value) {
      std::string out = "'";
      for (char c : value)
        out += c == '\'' ? "'\"'\"'" : std::string(1, c);
      return out + "'";
    };
    const auto path = root / "index-worker-lock-wrapper";
    std::ofstream(path)
        << "#!/bin/sh\n"
        << (pids.empty() ? ""
                         : "echo $$ >> " + shell_word(pids.string()) + "\n")
        << "printf . >> " << shell_word(counter.string()) << '\n'
        << "if ! mkdir " << shell_word(lock.string()) << " 2>/dev/null; then\n"
        << "  touch " << shell_word(overlap.string()) << "\nfi\n"
        << before_exec << shell_word(CTK_TEST_INDEX_WORKER)
        << " \"$@\"\nstatus=$?\n"
        << "rmdir " << shell_word(lock.string()) << " 2>/dev/null\n"
        << "exit $status\n";
    fs::permissions(path, fs::perms::owner_all);
    return path;
  }
  void replace_argument(const std::string &original,
                        const std::string &replacement) {
    const auto path = project / "compile_commands.json";
    std::ifstream input(path);
    std::string contents(std::istreambuf_iterator<char>{input}, {});
    const auto position = contents.find(original);
    ASSERT_NE(position, std::string::npos);
    contents.replace(position, original.size(), replacement);
    std::ofstream(path) << contents;
  }
  void write_shadow_commands(const std::string &option, const fs::path &first,
                             const fs::path &second) {
    std::ofstream out(project / "compile_commands.json");
    const auto compiler = quote(CTK_TEST_CLANG_TOOL_PATH);
    const auto directory = quote(project.string());
    const auto source_one = quote((project / "one.cpp").string());
    const auto source_two = quote((project / "two.cpp").string());
    const auto include_first = quote(option + first.string());
    const auto include_second = quote(option + second.string());
    out << "[";
    for (int flavor = 1; flavor <= 2; ++flavor) {
      out << "{\"directory\":" << directory << ",\"file\":" << source_one
          << ",\"arguments\":[" << compiler << ",\"-std=c++20\","
          << include_first << "," << include_second << ",\"-DFLAVOR=" << flavor
          << "\",\"-c\"," << source_one << "]},";
    }
    out << "{\"directory\":" << directory << ",\"file\":" << source_two
        << ",\"arguments\":[" << compiler
        << ",\"-std=c++20\",\"-I.\",\"-DFLAVOR=1\",\"-c\"," << source_two
        << "]}]";
  }
  fs::path database_file() {
    for (const auto &entry : fs::recursive_directory_iterator(storage))
      if (entry.path().filename() == "symbols.sqlite3")
        return entry.path();
    return {};
  }
  ProjectIndexStatus start_and_wait(IndexServiceAdapter &service) {
    StartProjectIndexRequest request;
    request.set_project_root(project.string());
    request.set_poll_interval_seconds(1);
    ProjectIndexStatus started;
    grpc::ServerContext context;
    EXPECT_TRUE(service.StartProjectIndex(&context, &request, &started).ok());
    ProjectIndexRequest status_request;
    status_request.set_project_root(project.string());
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(60);
    ProjectIndexStatus status;
    do {
      grpc::ServerContext status_context;
      EXPECT_TRUE(
          service
              .GetProjectIndexStatus(&status_context, &status_request, &status)
              .ok());
      if (status.state() == INDEX_STATE_COMPLETE ||
          status.state() == INDEX_STATE_FAILED)
        break;
      std::this_thread::sleep_for(std::chrono::milliseconds(25));
    } while (std::chrono::steady_clock::now() < deadline);
    EXPECT_EQ(status.state(), INDEX_STATE_COMPLETE) << status.error();
    return status;
  }
  FindSymbolsResponse find(IndexServiceAdapter &service,
                           const std::string &name, bool prefix) {
    FindSymbolsRequest request;
    request.set_project_root(project.string());
    request.set_query(name);
    request.set_limit(100);
    request.set_match_mode(prefix ? FindSymbolsRequest::MATCH_MODE_PREFIX
                                  : FindSymbolsRequest::MATCH_MODE_EXACT);
    FindSymbolsResponse result;
    grpc::ServerContext context;
    EXPECT_TRUE(service.FindSymbols(&context, &request, &result).ok());
    return result;
  }
};

TEST_F(ProjectIndexServiceTest,
       ExcludesSystemHeadersAndPreservesProjectHeaderVariants) {
  write("system.hpp", "#pragma GCC system_header\n"
                      "namespace vendor { struct SystemOnly {}; }\n");
  write("shared.h", "struct Shared {\n#if FLAVOR == 1\nint value;\n"
                    "#else\nlong value;\n#endif\n};\n");
  const std::string includes = "#include <vector>\n#include <string>\n"
                               "#include \"system.hpp\"\n"
                               "#include \"shared.h\"\n";
  write("one.cpp",
        includes + "struct Own { std::vector<std::string> values; };\n");
  write("two.cpp", includes + "int entry(){return 1;}\n");
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  const auto status = start_and_wait(service);
  EXPECT_EQ(status.translation_units_failed(), 0);
  EXPECT_EQ(find(service, "Shared", false).symbols_size(), 3);
  EXPECT_EQ(find(service, "Own", false).symbols_size(), 2);
  EXPECT_EQ(find(service, "std::", true).symbols_size(), 0);
  EXPECT_EQ(find(service, "SystemOnly", false).symbols_size(), 0);
  EXPECT_EQ(find(service, "vendor", false).symbols_size(), 0);
  const auto members = find(service, "Shared::value", false);
  ASSERT_EQ(members.symbols_size(), 3);
  // Macro variants remain separate even though their source location is shared.
  std::set<std::string> contexts;
  for (const auto &symbol : members.symbols())
    contexts.insert(symbol.compile_context());
  EXPECT_EQ(contexts.size(), 2);
}

TEST_F(ProjectIndexServiceTest,
       LookupBeforeIndexSchemaExistsReturnsEmptyStaleResult) {
  const auto key = ctk::net::index_detail::root_key(project.string());
  const auto database = storage / "symbol-index" /
                        ctk::net::index_detail::digest_text(key) /
                        "symbols.sqlite3";
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  const auto missing = find(service, "alphaOnly", false);
  EXPECT_TRUE(missing.stale());
  EXPECT_EQ(missing.symbols_size(), 0);

  fs::create_directories(database.parent_path());
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database.c_str(), &db), SQLITE_OK);
  ASSERT_EQ(sqlite3_exec(db,
                         "CREATE TABLE temporary(value); "
                         "DROP TABLE temporary;",
                         nullptr, nullptr, nullptr),
            SQLITE_OK);
  sqlite3_close(db);
  const auto before = find(service, "alphaOnly", false);
  EXPECT_TRUE(before.stale());
  EXPECT_EQ(before.symbols_size(), 0);
  const auto indexed = start_and_wait(service);
  EXPECT_EQ(indexed.translation_units_failed(), 0);
  EXPECT_EQ(find(service, "alphaOnly", false).symbols_size(), 2);
}

TEST_F(ProjectIndexServiceTest,
       ReadyUnitsPublishAtomicallyAfterSharedDependencyValidation) {
  ProjectIndexStatus first;
  {
    IndexServiceAdapter initial(storage, {}, CTK_TEST_INDEX_WORKER);
    first = start_and_wait(initial);
  }
  ASSERT_EQ(first.translation_units_total(), 3);

  const auto database = database_file();
  ASSERT_FALSE(database.empty());
  const auto counter = root / "batch-worker-counter";
  std::ofstream(counter);
  const auto release_file = root / "release-batch-publication";
  PipelineTrace trace;
  trace.database = database;
  trace.counter = counter;
  trace.release_file = release_file;
  trace.required_workers = 0;
  PipelineTraceRegistration registration(trace);
  ASSERT_TRUE(registration.registered());

  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database.c_str(), &db), SQLITE_OK);
  const auto trigger =
      "CREATE TRIGGER block_last_batch_unit BEFORE INSERT ON symbol WHEN "
      "NEW.file_path='" +
      (project / "two.cpp").string() +
      "' BEGIN SELECT block_index_publication(); END;";
  char *error = nullptr;
  const auto trigger_status =
      sqlite3_exec(db, trigger.c_str(), nullptr, nullptr, &error);
  const std::string trigger_error = error ? error : "";
  sqlite3_free(error);
  sqlite3_close(db);
  ASSERT_EQ(trigger_status, SQLITE_OK) << trigger_error;

  write("one.cpp", "#include \"shared.h\"\nint batchOne(){return 11;}\n");
  write("two.cpp", "#include \"shared.h\"\nint batchTwo(){return 22;}\n");
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER, 4);
  ReleaseFileGuard release_on_exit(release_file);
  StartProjectIndexRequest start;
  start.set_project_root(project.string());
  ProjectIndexStatus status;
  grpc::ServerContext start_context;
  ASSERT_TRUE(service.StartProjectIndex(&start_context, &start, &status).ok());

  const auto gate_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(30);
  while (!trace.publication_gate_entered.load(std::memory_order_acquire) &&
         std::chrono::steady_clock::now() < gate_deadline)
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  ASSERT_TRUE(trace.publication_gate_entered.load(std::memory_order_acquire));
  EXPECT_EQ(find(service, "batchOne", false).symbols_size(), 0);
  EXPECT_EQ(find(service, "alphaOnly", false).symbols_size(), 2);
  std::ofstream(release_file) << "continue\n";

  ProjectIndexRequest status_request;
  status_request.set_project_root(project.string());
  const auto completion_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(60);
  do {
    grpc::ServerContext context;
    ASSERT_TRUE(service.GetProjectIndexStatus(&context, &status_request, &status)
                    .ok());
    if (status.state() == INDEX_STATE_COMPLETE ||
        status.state() == INDEX_STATE_FAILED)
      break;
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  } while (std::chrono::steady_clock::now() < completion_deadline);
  ASSERT_EQ(status.state(), INDEX_STATE_COMPLETE) << status.error();
  EXPECT_EQ(status.translation_units_failed(), 0);
  EXPECT_EQ(find(service, "batchOne", false).symbols_size(), 2);
  EXPECT_EQ(find(service, "batchTwo", false).symbols_size(), 1);
  EXPECT_EQ(find(service, "alphaOnly", false).symbols_size(), 0);
  EXPECT_EQ(status.revision(), first.revision() + 3);
  ASSERT_EQ(sqlite3_open(database.c_str(), &db), SQLITE_OK);
  sqlite3_stmt *tables = nullptr;
  ASSERT_EQ(sqlite3_prepare_v2(
                db,
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND "
                "name NOT LIKE 'sqlite_%'",
                -1, &tables, nullptr),
            SQLITE_OK);
  ASSERT_EQ(sqlite3_step(tables), SQLITE_ROW);
  EXPECT_EQ(sqlite3_column_int(tables, 0), 3);
  sqlite3_finalize(tables);
  sqlite3_close(db);
}

TEST_F(ProjectIndexServiceTest,
       StartsNextChangedUnitDuringCurrentSymbolPublication) {
  const auto counter = root / "worker-starts";
  const auto lock = root / "worker-lock";
  const auto overlap = root / "worker-overlap";
  const auto wrapper = worker_wrapper_with_lock(counter, lock, overlap);
  fs::path database;
  {
    IndexServiceAdapter initial(storage, {}, wrapper);
    start_and_wait(initial);
    database = database_file();
  }
  ASSERT_FALSE(database.empty());
  std::error_code ec;
  const auto previous_starts = fs::file_size(counter, ec);
  ASSERT_FALSE(ec);
  PipelineTrace trace;
  trace.database = database;
  trace.counter = counter;
  trace.required_workers = previous_starts + 3;
  PipelineTraceRegistration registration(trace);
  ASSERT_TRUE(registration.registered());
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database.c_str(), &db), SQLITE_OK);
  char *error = nullptr;
  const auto trigger_status = sqlite3_exec(
      db,
      "CREATE TRIGGER block_symbol_publication BEFORE INSERT ON symbol BEGIN "
      "SELECT block_index_publication(); END;",
      nullptr, nullptr, &error);
  const std::string trigger_error = error ? error : "";
  sqlite3_free(error);
  sqlite3_close(db);
  ASSERT_EQ(trigger_status, SQLITE_OK) << trigger_error;

  write("shared.h", "#if FLAVOR == 1\n#define ALPHA_FEATURE 1\n"
                    "#else\n#define BETA_FEATURE 1\n#endif\n"
                    "struct ChangedHeader { int value; };\n");
  IndexServiceAdapter service(storage, {}, wrapper);
  const auto status = start_and_wait(service);
  EXPECT_EQ(status.translation_units_failed(), 0);
  EXPECT_TRUE(trace.publication_started.load(std::memory_order_acquire));
  EXPECT_TRUE(trace.overlapped.load(std::memory_order_acquire));
  EXPECT_TRUE(fs::exists(overlap));
}

TEST_F(ProjectIndexServiceTest,
       RevalidatesUnchangedLookaheadAfterCurrentPublication) {
  write_single_variant_commands();
  {
    IndexServiceAdapter initial(storage, {}, CTK_TEST_INDEX_WORKER);
    start_and_wait(initial);
  }
  const auto database = database_file();
  PipelineTrace trace;
  trace.database = database;
  trace.counter = root / "worker-starts";
  trace.edit_file = project / "two.cpp";
  trace.edit_contents =
      "#include \"shared.h\"\nint editedDuringPublication(){return 2;}\n";
  PipelineTraceRegistration registration(trace);
  ASSERT_TRUE(registration.registered());
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database.c_str(), &db), SQLITE_OK);
  char *error = nullptr;
  const auto trigger_status = sqlite3_exec(
      db,
      "CREATE TRIGGER edit_next_input BEFORE INSERT ON symbol BEGIN "
      "SELECT block_index_publication(); END;",
      nullptr, nullptr, &error);
  const std::string trigger_error = error ? error : "";
  sqlite3_free(error);
  sqlite3_close(db);
  ASSERT_EQ(trigger_status, SQLITE_OK) << trigger_error;

  write("one.cpp", "#include \"shared.h\"\n"
                   "int changedCurrentUnit(){return 1;}\n");
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  const auto status = start_and_wait(service);
  EXPECT_EQ(status.translation_units_failed(), 0);
  EXPECT_TRUE(trace.publication_started.load(std::memory_order_acquire));
  EXPECT_EQ(find(service, "editedDuringPublication", false).symbols_size(), 1);
  EXPECT_EQ(find(service, "alphaOnly", false).symbols_size(), 0);
}

TEST_F(ProjectIndexServiceTest,
       LookaheadManifestErrorDoesNotDiscardCurrentExtraction) {
  write_single_variant_commands();
  {
    IndexServiceAdapter initial(storage, {}, CTK_TEST_INDEX_WORKER);
    start_and_wait(initial);
  }
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  sqlite3_stmt *corrupt = nullptr;
  ASSERT_EQ(sqlite3_prepare_v2(
                db,
                "UPDATE translation_unit SET dependencies_json='not-json' "
                "WHERE main_file LIKE ? AND indexed_at>0",
                -1, &corrupt, nullptr),
            SQLITE_OK);
  ASSERT_EQ(sqlite3_bind_text(corrupt, 1, "%two.cpp", -1, SQLITE_STATIC),
            SQLITE_OK);
  ASSERT_EQ(sqlite3_step(corrupt), SQLITE_DONE);
  ASSERT_EQ(sqlite3_changes(db), 1) << sqlite3_errmsg(db);
  sqlite3_finalize(corrupt);
  sqlite3_close(db);

  write("one.cpp", "#include \"shared.h\"\n"
                   "int currentSurvivesLookaheadError(){return 1;}\n");
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  StartProjectIndexRequest start;
  start.set_project_root(project.string());
  start.set_poll_interval_seconds(1);
  ProjectIndexStatus status;
  grpc::ServerContext start_context;
  ASSERT_TRUE(service.StartProjectIndex(&start_context, &start, &status).ok());
  ProjectIndexRequest request;
  request.set_project_root(project.string());
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(60);
  do {
    grpc::ServerContext status_context;
    ASSERT_TRUE(
        service.GetProjectIndexStatus(&status_context, &request, &status).ok());
    if (status.state() == INDEX_STATE_FAILED ||
        status.state() == INDEX_STATE_COMPLETE)
      break;
    std::this_thread::sleep_for(std::chrono::milliseconds(25));
  } while (std::chrono::steady_clock::now() < deadline);
  EXPECT_EQ(status.state(), INDEX_STATE_FAILED)
      << status.error() << " failed=" << status.translation_units_failed()
      << " completed=" << status.translation_units_completed();
  EXPECT_EQ(
      find(service, "currentSurvivesLookaheadError", false).symbols_size(), 1);
}

TEST_F(ProjectIndexServiceTest,
       PauseStopsPendingWorkerWhileForegroundLookupRemainsResponsive) {
  const auto counter = root / "worker-starts";
  const auto lock = root / "worker-lock";
  const auto overlap = root / "worker-overlap";
  const auto pids = root / "worker-pids";
  fs::path database;
  {
    IndexServiceAdapter initial(storage, {}, worker_wrapper(counter));
    start_and_wait(initial);
    database = database_file();
  }
  ASSERT_FALSE(database.empty());
  std::error_code ec;
  const auto previous_starts = fs::file_size(counter, ec);
  ASSERT_FALSE(ec);
  const auto release_file = root / "release-publication";
  PipelineTrace trace;
  trace.database = database;
  trace.counter = counter;
  trace.release_file = release_file;
  trace.required_workers = previous_starts + 3;
  PipelineTraceRegistration registration(trace);
  ASSERT_TRUE(registration.registered());
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database.c_str(), &db), SQLITE_OK);
  char *error = nullptr;
  const auto trigger_status = sqlite3_exec(
      db,
      "CREATE TRIGGER block_symbol_publication BEFORE INSERT ON symbol BEGIN "
      "SELECT block_index_publication(); END;",
      nullptr, nullptr, &error);
  const std::string trigger_error = error ? error : "";
  sqlite3_free(error);
  sqlite3_close(db);
  ASSERT_EQ(trigger_status, SQLITE_OK) << trigger_error;
  write("shared.h", "#if FLAVOR == 1\n#define ALPHA_FEATURE 1\n"
                    "#else\n#define BETA_FEATURE 1\n#endif\n"
                    "struct ChangedHeader { int value; };\n");

  std::atomic<bool> foreground_busy{false};
  const auto wrapper =
      worker_wrapper_with_lock(counter, lock, overlap, pids, "sleep 4\n");
  IndexServiceAdapter service(
      storage, [&] { return foreground_busy.load(); }, wrapper, 2);
  ReleaseFileGuard release_on_exit(release_file);
  StartProjectIndexRequest start;
  start.set_project_root(project.string());
  start.set_poll_interval_seconds(1);
  ProjectIndexStatus status;
  grpc::ServerContext start_context;
  ASSERT_TRUE(service.StartProjectIndex(&start_context, &start, &status).ok());

  const auto overlap_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(30);
  while (!trace.overlapped.load(std::memory_order_acquire) &&
         std::chrono::steady_clock::now() < overlap_deadline)
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  ASSERT_TRUE(trace.publication_started.load(std::memory_order_acquire));
  ASSERT_TRUE(trace.overlapped.load(std::memory_order_acquire));

  foreground_busy.store(true);
  FindSymbolsRequest lookup;
  lookup.set_project_root(project.string());
  lookup.set_query("alphaOnly");
  lookup.set_limit(10);
  FindSymbolsResponse found;
  grpc::ServerContext lookup_context;
  const auto lookup_started = std::chrono::steady_clock::now();
  ASSERT_TRUE(service.FindSymbols(&lookup_context, &lookup, &found).ok());
  EXPECT_LT(std::chrono::steady_clock::now() - lookup_started,
            std::chrono::seconds(1));
  EXPECT_GT(found.symbols_size(), 0);

  ProjectIndexRequest control;
  control.set_project_root(project.string());
  grpc::ServerContext pause_context;
  ASSERT_TRUE(
      service.PauseProjectIndex(&pause_context, &control, &status).ok());
  ASSERT_EQ(status.state(), INDEX_STATE_PAUSED);
  std::ifstream pid_input(pids);
  std::vector<long> worker_pids;
  long value = 0;
  while (pid_input >> value)
    worker_pids.push_back(value);
  ASSERT_GE(worker_pids.size(), 3u);
  for (const auto pid : worker_pids)
    ASSERT_GT(pid, 0);
  const auto reap_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(2);
  const auto any_worker_alive = [&] {
    return std::any_of(worker_pids.begin(), worker_pids.end(), [](long pid) {
      return ::kill(static_cast<pid_t>(pid), 0) == 0;
    });
  };
  while (any_worker_alive() && std::chrono::steady_clock::now() < reap_deadline)
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  EXPECT_FALSE(any_worker_alive());

  std::ofstream(release_file) << "continue\n";
  foreground_busy.store(false);
  grpc::ServerContext resume_context;
  ASSERT_TRUE(
      service.ResumeProjectIndex(&resume_context, &control, &status).ok());
  const auto completion_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(60);
  do {
    grpc::ServerContext status_context;
    ASSERT_TRUE(
        service.GetProjectIndexStatus(&status_context, &control, &status).ok());
    if (status.state() == INDEX_STATE_COMPLETE ||
        status.state() == INDEX_STATE_FAILED)
      break;
    std::this_thread::sleep_for(std::chrono::milliseconds(25));
  } while (std::chrono::steady_clock::now() < completion_deadline);
  EXPECT_EQ(status.state(), INDEX_STATE_COMPLETE) << status.error();
}

TEST_F(ProjectIndexServiceTest,
       SharedHeaderPayloadIsStoredOnceWithEveryTuProvenance) {
  std::string header;
  for (int i = 0; i < 200; ++i)
    header += "inline int SharedSymbol" + std::to_string(i) + "(){return 1;}\n";
  write("shared.h", header);
  std::ofstream commands(project / "compile_commands.json");
  commands << '[';
  for (int i = 0; i < 20; ++i) {
    const auto name = "source" + std::to_string(i) + ".cpp";
    write(name.c_str(), "#include \"shared.h\"\nint entry" + std::to_string(i) +
                            "(){return 1;}\n");
    if (i)
      commands << ',';
    const auto source = quote((project / name).string());
    commands << "{\"directory\":" << quote(project.string())
             << ",\"file\":" << source << ",\"arguments\":["
             << quote(CTK_TEST_CLANG_TOOL_PATH) << ",\"-std=c++20\",\"-c\","
             << source << "]}";
  }
  commands << ']';
  commands.close();
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  const auto status = start_and_wait(service);
  EXPECT_EQ(status.translation_units_indexed(), 20);
  const auto found = find(service, "SharedSymbol199", false);
  ASSERT_EQ(found.symbols_size(), 20);
  std::set<std::string> tus;
  for (const auto &symbol : found.symbols())
    tus.insert(symbol.translation_unit());
  EXPECT_EQ(tus.size(), 20);
  const auto prefix = find(service, "SharedSymbol", true);
  EXPECT_EQ(prefix.symbols_size(), 100);
  EXPECT_TRUE(prefix.truncated());
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  sqlite3_stmt *count = nullptr;
  ASSERT_EQ(sqlite3_prepare_v2(
                db,
                "SELECT count(*) FROM symbol WHERE name LIKE 'SharedSymbol%'",
                -1, &count, nullptr),
            SQLITE_OK);
  ASSERT_EQ(sqlite3_step(count), SQLITE_ROW);
  EXPECT_EQ(sqlite3_column_int(count, 0), 200);
  sqlite3_finalize(count);
  sqlite3_close(db);
}

TEST_F(ProjectIndexServiceTest,
       SharedVariantLimitUsesRealTuOrderRatherThanHeaderOwnerOrder) {
  {
    IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
    start_and_wait(service);
  }
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  for (int i = 0; i < 3; ++i) {
    const auto member = std::string("member-") + char('a' + i);
    const auto owner = std::string("header:") + char('c' - i);
    const auto source = std::string("/") + char('a' + i) + ".cpp";
    const std::string sql =
        "INSERT INTO translation_unit VALUES('" + member + "','" + source +
        "','','','hash','hash','{}',1,'ready','');"
        "INSERT INTO translation_unit VALUES('" +
        owner + "','/header.hpp','','','hash','hash','[\"" + member +
        "\"]',0,'ready','');"
        "INSERT INTO symbol VALUES('" +
        owner +
        "','shared-usr','VariantHeader','VariantHeader','Function',"
        "'/header.hpp',7,0,1,8,'signature" +
        std::to_string(i) + "');";
    ASSERT_EQ(sqlite3_exec(db, sql.c_str(), nullptr, nullptr, nullptr),
              SQLITE_OK);
  }
  sqlite3_close(db);
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  FindSymbolsRequest request;
  request.set_project_root(project.string());
  request.set_query("VariantHeader");
  request.set_limit(1);
  FindSymbolsResponse result;
  grpc::ServerContext context;
  ASSERT_TRUE(service.FindSymbols(&context, &request, &result).ok());
  ASSERT_EQ(result.symbols_size(), 1);
  EXPECT_EQ(result.symbols(0).translation_unit(), "/a.cpp");
  EXPECT_TRUE(result.truncated());
}

TEST_F(ProjectIndexServiceTest,
       UnchangedFlatContributionsMigrateWithoutReextracting) {
  write("shared.h", "struct Shared {};\n");
  const auto counter = root / "worker-launches";
  const auto wrapper = worker_wrapper(counter);
  {
    IndexServiceAdapter service(storage, {}, wrapper);
    start_and_wait(service);
  }
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  // Reconstruct the previous per-TU layout without changing its input hashes.
  ASSERT_EQ(
      sqlite3_exec(db,
                   "PRAGMA foreign_keys=ON;BEGIN;"
                   "INSERT INTO symbol SELECT "
                   "m.value,s.usr,s.name,s.qualified_name,s.kind,"
                   "s.file_path,s.byte_offset,s.is_definition,s.line,s.column_"
                   "no,s.signature "
                   "FROM symbol s JOIN translation_unit g ON g.id=s.tu_id "
                   "JOIN json_each(g.dependencies_json) m WHERE g.indexed_at=0;"
                   "DELETE FROM translation_unit WHERE indexed_at=0;"
                   "UPDATE translation_unit SET dependencies_json=(SELECT "
                   "json_group_object(key,value) "
                   "FROM json_each(dependencies_json) WHERE key NOT LIKE "
                   "'@symbol-%');COMMIT;",
                   nullptr, nullptr, nullptr),
      SQLITE_OK);
  sqlite3_close(db);
  IndexServiceAdapter service(storage, {}, wrapper);
  const auto status = start_and_wait(service);
  EXPECT_EQ(status.translation_units_indexed(), 3);
  EXPECT_EQ(find(service, "Shared", false).symbols_size(), 3);
  std::ifstream launches(counter);
  // Initial discovery + three extractions, then discovery only for migration.
  EXPECT_EQ(std::string(std::istreambuf_iterator<char>(launches), {}).size(),
            5);
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  sqlite3_stmt *count = nullptr;
  ASSERT_EQ(
      sqlite3_prepare_v2(db, "SELECT count(*) FROM symbol WHERE name='Shared'",
                         -1, &count, nullptr),
      SQLITE_OK);
  ASSERT_EQ(sqlite3_step(count), SQLITE_ROW);
  EXPECT_EQ(sqlite3_column_int(count, 0), 1);
  sqlite3_finalize(count);
  sqlite3_close(db);
}

TEST_F(ProjectIndexServiceTest,
       SourceRefreshDoesNotRewriteUnchangedHeaderRows) {
  write("shared.h", "struct Shared { int value; };\n");
  write("one.cpp", "#include \"shared.h\"\nint oldEntry(){return 1;}\n");
  {
    IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
    start_and_wait(service);
  }
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  // Fail if a source-only edit physically rewrites an unchanged header row.
  for (const char *event : {"INSERT", "UPDATE", "DELETE"}) {
    const std::string query = "CREATE TRIGGER unchanged_header_" +
                              std::string(event) + " AFTER " + event +
                              " ON symbol WHEN " +
                              (std::string(event) == "DELETE" ? "old" : "new") +
                              ".name='Shared' BEGIN SELECT "
                              "RAISE(ABORT,'unchanged header rewritten'); "
                              "END;";
    ASSERT_EQ(sqlite3_exec(db, query.c_str(), nullptr, nullptr, nullptr),
              SQLITE_OK);
  }
  sqlite3_close(db);
  write("one.cpp", "#include \"shared.h\"\nint newEntry(){return 2;}\n");
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  const auto status = start_and_wait(service);
  EXPECT_EQ(status.translation_units_failed(), 0);
  EXPECT_EQ(status.translation_units_skipped(), 1);
  EXPECT_EQ(find(service, "Shared", false).symbols_size(), 3);
  EXPECT_EQ(find(service, "oldEntry", false).symbols_size(), 0);
  EXPECT_EQ(find(service, "newEntry", false).symbols_size(), 2);
}

TEST_F(ProjectIndexServiceTest,
       LargeRetirementCopiesOnlyRetainedContributionsAtomically) {
  write("shared.h", "struct Shared {};\n");
  {
    IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
    start_and_wait(service);
  }
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  for (int i = 0; i < 33; ++i) {
    const auto id = "obsolete-" + std::to_string(i);
    const std::string row =
        "INSERT INTO translation_unit SELECT '" + id +
        "',main_file,working_directory,arguments,command_hash,"
        "input_fingerprint,dependencies_json,indexed_at,status,last_error "
        "FROM translation_unit WHERE indexed_at>0 AND id NOT LIKE 'obsolete-%' "
        "LIMIT 1;"
        "INSERT INTO symbol SELECT '" +
        id +
        "',usr,'RetiredOnly','RetiredOnly',kind,file_path,byte_offset,"
        "is_definition,line,column_no,signature FROM symbol WHERE tu_id="
        "(SELECT id FROM translation_unit WHERE indexed_at>0 AND id NOT LIKE "
        "'obsolete-%' "
        "LIMIT 1);";
    ASSERT_EQ(sqlite3_exec(db, row.c_str(), nullptr, nullptr, nullptr),
              SQLITE_OK);
  }
  sqlite3_close(db);
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  const auto status = start_and_wait(service);
  EXPECT_EQ(status.translation_units_failed(), 0);
  EXPECT_EQ(status.translation_units_skipped(), 3);
  EXPECT_EQ(status.translation_units_indexed(), 3);
  EXPECT_EQ(find(service, "RetiredOnly", false).symbols_size(), 0);
  EXPECT_EQ(find(service, "Shared", false).symbols_size(), 3);
  EXPECT_EQ(find(service, "betaOnly", false).symbols_size(), 3);
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  sqlite3_stmt *schema = nullptr;
  ASSERT_EQ(sqlite3_prepare_v2(db,
                               "SELECT count(*) FROM sqlite_master WHERE "
                               "type='table' AND name NOT LIKE 'sqlite_%'",
                               -1, &schema, nullptr),
            SQLITE_OK);
  ASSERT_EQ(sqlite3_step(schema), SQLITE_ROW);
  EXPECT_EQ(sqlite3_column_int(schema, 0), 3);
  sqlite3_finalize(schema);
  sqlite3_close(db);
}

TEST_F(ProjectIndexServiceTest,
       WorkerRebuildMetadataDoesNotInvalidateUnchangedTus) {
  const auto counter = root / "worker-launches";
  const auto wrapper = worker_wrapper(counter);
  ProjectIndexStatus initial;
  {
    IndexServiceAdapter service(storage, {}, wrapper);
    initial = start_and_wait(service);
  }
  // Same extractor behavior, different executable bytes (e.g. relink/build
  // UUID).
  std::ofstream(wrapper, std::ios::app) << "# unrelated rebuild metadata\n";
  {
    IndexServiceAdapter service(storage, {}, wrapper);
    const auto restarted = start_and_wait(service);
    EXPECT_EQ(restarted.revision(), initial.revision());
    EXPECT_EQ(restarted.translation_units_skipped(), 3);
    EXPECT_EQ(restarted.translation_units_indexed(), 3);
    EXPECT_EQ(find(service, "alphaOnly", false).symbols_size(), 2);
  }
  std::ifstream launches(counter);
  EXPECT_EQ(std::string(std::istreambuf_iterator<char>(launches), {}).size(),
            5);
}

TEST_F(ProjectIndexServiceTest,
       ForegroundBurstResumesExtractionWithoutRediscovery) {
  const auto counter = root / "worker-launches";
  const auto wrapper = worker_wrapper(counter, "sleep 0.3\n");
  bool yielded = false;
  std::chrono::steady_clock::time_point busy_until{};
  IndexServiceAdapter service(
      storage,
      [&] {
        if (!yielded && fs::exists(counter) && fs::file_size(counter) >= 2) {
          yielded = true;
          busy_until =
              std::chrono::steady_clock::now() + std::chrono::milliseconds(200);
        }
        return std::chrono::steady_clock::now() < busy_until;
      },
      wrapper, 1);
  const auto status = start_and_wait(service);
  EXPECT_TRUE(yielded);
  EXPECT_EQ(status.translation_units_failed(), 0);
  EXPECT_EQ(find(service, "alphaOnly", false).symbols_size(), 2);
  std::ifstream launches(counter);
  EXPECT_EQ(std::string(std::istreambuf_iterator<char>(launches), {}).size(),
            4);
}

TEST_F(ProjectIndexServiceTest, ExtractsTranslationUnitsInParallelWithinCap) {
  const auto counter = root / "worker-starts";
  const auto started = root / "worker-started";
  const auto release = root / "worker-release";
  const auto wrapper =
      worker_wrapper_with_release_barrier(counter, started, release);
  IndexServiceAdapter service(storage, {}, wrapper, 2);
  ReleaseFileGuard release_on_exit(release);
  StartProjectIndexRequest start;
  start.set_project_root(project.string());
  ProjectIndexStatus status;
  grpc::ServerContext start_context;
  ASSERT_TRUE(service.StartProjectIndex(&start_context, &start, &status).ok());

  const auto barrier_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(10);
  while (std::distance(fs::directory_iterator(started),
                       fs::directory_iterator{}) < 2 &&
         std::chrono::steady_clock::now() < barrier_deadline)
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  ASSERT_EQ(
      std::distance(fs::directory_iterator(started), fs::directory_iterator{}),
      2);
  ASSERT_EQ(fs::file_size(counter), 3u); // Listing plus the two held workers.
  std::this_thread::sleep_for(std::chrono::milliseconds(100));
  EXPECT_EQ(fs::file_size(counter),
            3u); // The third extraction is still queued.
  std::ofstream(release) << "continue\n";

  ProjectIndexRequest project_request;
  project_request.set_project_root(project.string());
  const auto completion_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(30);
  do {
    grpc::ServerContext status_context;
    ASSERT_TRUE(
        service
            .GetProjectIndexStatus(&status_context, &project_request, &status)
            .ok());
    if (status.state() == INDEX_STATE_COMPLETE ||
        status.state() == INDEX_STATE_FAILED)
      break;
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
  } while (std::chrono::steady_clock::now() < completion_deadline);
  ASSERT_EQ(status.state(), INDEX_STATE_COMPLETE) << status.error();
  EXPECT_EQ(fs::file_size(counter), 4u);
  EXPECT_EQ(status.translation_units_total(), 3u);
  EXPECT_EQ(status.translation_units_completed(), 3u);
  EXPECT_EQ(status.state(), INDEX_STATE_COMPLETE);
}

TEST_F(ProjectIndexServiceTest, CancelReapsEveryParallelExtractionWorker) {
  const auto pids = root / "worker-pids";
  const auto counter = root / "worker-starts";
  const auto lock = root / "worker-lock";
  const auto overlap = root / "worker-overlap";
  const auto wrapper =
      worker_wrapper_with_lock(counter, lock, overlap, pids, "sleep 4\n");
  IndexServiceAdapter service(storage, {}, wrapper, 3);
  StartProjectIndexRequest start;
  start.set_project_root(project.string());
  ProjectIndexStatus status;
  grpc::ServerContext start_context;
  ASSERT_TRUE(service.StartProjectIndex(&start_context, &start, &status).ok());

  const auto launch_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(10);
  while ((!fs::exists(overlap) || !fs::exists(counter) ||
          fs::file_size(counter) < 4) &&
         std::chrono::steady_clock::now() < launch_deadline)
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  ASSERT_TRUE(fs::exists(overlap));
  const auto read_pids = [&] {
    std::ifstream pid_input(pids);
    std::vector<long> worker_pids;
    long pid = 0;
    while (pid_input >> pid)
      worker_pids.push_back(pid);
    return worker_pids;
  };
  ASSERT_EQ(fs::file_size(counter), 4u); // Listing plus all three workers.
  auto worker_pids = read_pids();
  ASSERT_EQ(worker_pids.size(), 4u);

  ProjectIndexRequest control;
  control.set_project_root(project.string());
  grpc::ServerContext cancel_context;
  ASSERT_TRUE(
      service.CancelProjectIndex(&cancel_context, &control, &status).ok());
  EXPECT_EQ(status.state(), INDEX_STATE_CANCELLED);
  worker_pids = read_pids();
  ASSERT_EQ(worker_pids.size(), 4u);
  const auto reap_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(2);
  const auto any_worker_alive = [&] {
    return std::any_of(worker_pids.begin(), worker_pids.end(), [](long value) {
      return ::kill(static_cast<pid_t>(value), 0) == 0;
    });
  };
  while (any_worker_alive() && std::chrono::steady_clock::now() < reap_deadline)
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  EXPECT_FALSE(any_worker_alive());
  EXPECT_EQ(fs::file_size(counter), 4u);
}

TEST_F(ProjectIndexServiceTest,
       RapidPauseResumeDiscardsResultsFromPriorGeneration) {
  const auto counter = root / "worker-starts";
  const auto wrapper = worker_wrapper(counter, "sleep 0.3\n");
  IndexServiceAdapter service(storage, {}, wrapper, 2);
  StartProjectIndexRequest start;
  start.set_project_root(project.string());
  ProjectIndexStatus status;
  grpc::ServerContext start_context;
  ASSERT_TRUE(service.StartProjectIndex(&start_context, &start, &status).ok());

  const auto launch_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(10);
  while ((!fs::exists(counter) || fs::file_size(counter) < 2) &&
         std::chrono::steady_clock::now() < launch_deadline)
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  ASSERT_TRUE(fs::exists(counter));
  ASSERT_GE(fs::file_size(counter), 2u);

  ProjectIndexRequest control;
  control.set_project_root(project.string());
  grpc::ServerContext pause_context;
  ASSERT_TRUE(
      service.PauseProjectIndex(&pause_context, &control, &status).ok());
  write("one.cpp", "int newestOnly(){return 7;}\n");
  grpc::ServerContext resume_context;
  ASSERT_TRUE(
      service.ResumeProjectIndex(&resume_context, &control, &status).ok());

  const auto completion_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(30);
  do {
    grpc::ServerContext status_context;
    ASSERT_TRUE(
        service.GetProjectIndexStatus(&status_context, &control, &status).ok());
    if (status.state() == INDEX_STATE_COMPLETE ||
        status.state() == INDEX_STATE_FAILED)
      break;
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
  } while (std::chrono::steady_clock::now() < completion_deadline);
  ASSERT_EQ(status.state(), INDEX_STATE_COMPLETE) << status.error();
  EXPECT_GT(find(service, "newestOnly", false).symbols_size(), 0);
}

TEST_F(ProjectIndexServiceTest,
       ForegroundBurstYieldsStagedPublicationWithoutReextracting) {
  std::string source = "#include \"shared.h\"\n";
  for (int i = 0; i != 3000; ++i)
    source += "int burst" + std::to_string(i) + "(){return 1;}\n";
  write("one.cpp", source);
  const auto counter = root / "worker-launches";
  const auto wrapper = worker_wrapper(counter);
  std::atomic<unsigned> calls{0};
  std::chrono::steady_clock::time_point busy_until{};
  IndexServiceAdapter service(
      storage,
      [&] {
        if (++calls == 1000)
          busy_until =
              std::chrono::steady_clock::now() + std::chrono::milliseconds(200);
        return std::chrono::steady_clock::now() < busy_until;
      },
      wrapper);
  start_and_wait(service);
  EXPECT_GE(calls.load(), 1000u);
  EXPECT_EQ(find(service, "burst2999", false).symbols_size(), 2);
  std::ifstream launches(counter);
  // One discovery and three successful extractions, despite the burst.
  EXPECT_EQ(std::string(std::istreambuf_iterator<char>(launches), {}).size(),
            4);
}

TEST_F(ProjectIndexServiceTest,
       InputEditWhilePublicationYieldsIsReextractedBeforeCommit) {
  std::string source = "#include \"shared.h\"\n";
  for (int i = 0; i != 3000; ++i)
    source += "int burst" + std::to_string(i) + "(){return 1;}\n";
  write("one.cpp", source);
  std::atomic<unsigned> calls{0};
  std::chrono::steady_clock::time_point busy_until{};
  IndexServiceAdapter service(
      storage,
      [&] {
        if (++calls == 1000) {
          write("shared.h", "struct AddedDuringForeground {};\n");
          busy_until =
              std::chrono::steady_clock::now() + std::chrono::milliseconds(200);
        }
        return std::chrono::steady_clock::now() < busy_until;
      },
      CTK_TEST_INDEX_WORKER);
  start_and_wait(service);
  EXPECT_GE(calls.load(), 1000u);
  EXPECT_EQ(find(service, "AddedDuringForeground", false).symbols_size(), 3);
}

TEST_F(ProjectIndexServiceTest,
       HeaderEditDuringFinalCommitAdmissionIsRevalidated) {
  RevisionTrace trace;
  trace.database =
      storage / "symbol-index" /
      index_detail::digest_text(index_detail::root_key(project.string())) /
      "symbols.sqlite3";
  RevisionTraceRegistration registration(trace);
  ASSERT_TRUE(registration.registered());

  std::atomic<bool> edited{false};
  std::chrono::steady_clock::time_point busy_until{};
  IndexServiceAdapter service(
      storage,
      [&] {
        if (trace.revision_one.load(std::memory_order_acquire) &&
            !edited.exchange(true)) {
          write("shared.h", "struct AddedDuringCommit {} prime;\n");
          busy_until =
              std::chrono::steady_clock::now() + std::chrono::milliseconds(300);
        }
        return std::chrono::steady_clock::now() < busy_until;
      },
      CTK_TEST_INDEX_WORKER);
  const auto status = start_and_wait(service);
  EXPECT_TRUE(trace.revision_one.load(std::memory_order_acquire));
  EXPECT_TRUE(edited.load());
  EXPECT_EQ(status.translation_units_failed(), 0);
  EXPECT_EQ(find(service, "AddedDuringCommit", false).symbols_size(), 3);
}

TEST_F(ProjectIndexServiceTest,
       HeaderEditDuringInnerValidationWaitRestartsManifestPass) {
  write("a.h", "struct ExistingBeforeValidation {};\n");
  write("one.cpp", "#include \"a.h\"\n#include \"shared.h\"\n"
                   "#ifdef ALPHA_FEATURE\nint alphaOnly(){return 1;}\n"
                   "#else\nint betaOnly(){return 2;}\n#endif\n");

  RevisionTrace trace;
  trace.database =
      storage / "symbol-index" /
      index_detail::digest_text(index_detail::root_key(project.string())) /
      "symbols.sqlite3";
  RevisionTraceRegistration registration(trace);
  ASSERT_TRUE(registration.registered());

  std::atomic<unsigned> checks_after_revision{0};
  std::atomic<bool> edited{false};
  std::chrono::steady_clock::time_point busy_until{};
  IndexServiceAdapter service(
      storage,
      [&] {
        // The sorted manifest begins with /a.h then /one.cpp. After commit
        // admission (1), /a.h admission and its single-chunk hash callback
        // (2-3), call 4 is admission for /one.cpp, so /a.h was already
        // validated when this wait edits it.
        if (trace.revision_one.load(std::memory_order_acquire) &&
            checks_after_revision.fetch_add(1) + 1 == 4 &&
            !edited.exchange(true)) {
          write("a.h", "struct ExistingBeforeValidation {};\n"
                       "struct AddedDuringValidation {};\n");
          busy_until =
              std::chrono::steady_clock::now() + std::chrono::milliseconds(300);
        }
        return std::chrono::steady_clock::now() < busy_until;
      },
      CTK_TEST_INDEX_WORKER);
  const auto status = start_and_wait(service);
  EXPECT_TRUE(trace.revision_one.load(std::memory_order_acquire));
  EXPECT_TRUE(edited.load());
  EXPECT_GE(checks_after_revision.load(), 4u);
  EXPECT_EQ(status.translation_units_failed(), 0);
  EXPECT_EQ(find(service, "AddedDuringValidation", false).symbols_size(), 2);
}

TEST_F(ProjectIndexServiceTest,
       PopulatedLookupsBoundMetadataReadsBeforeJoining) {
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  start_and_wait(service);
  ProjectIndexRequest project_request;
  project_request.set_project_root(project.string());
  ProjectIndexStatus paused;
  grpc::ServerContext pause_context;
  ASSERT_TRUE(
      service.PauseProjectIndex(&pause_context, &project_request, &paused)
          .ok());
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  // Large manifests sit before status in each TU's overflow record. A lookup
  // must not read them for thousands of candidates discarded by its limit.
  ASSERT_EQ(sqlite3_exec(
                db,
                "UPDATE translation_unit SET "
                "dependencies_json=printf('%.*c',2097152,'x');"
                "WITH RECURSIVE n(v) AS (VALUES(0) UNION ALL SELECT v+1 FROM n "
                "WHERE v<999) "
                "INSERT INTO symbol SELECT t.id,'c:@LookupProbe','LookupProbe',"
                "'ns::LookupProbe','function',t.main_file,n.v,1,1,1,'int()' "
                "FROM translation_unit t CROSS JOIN n;",
                nullptr, nullptr, nullptr),
            SQLITE_OK);
  sqlite3_close(db);
  for (const auto &[query, prefix] :
       {std::pair{"LookupProbe", false}, std::pair{"ns::LookupProbe", false},
        std::pair{"lookuppro", true}, std::pair{"ns::lookuppro", true}}) {
    FindSymbolsRequest request;
    request.set_project_root(project.string());
    request.set_query(query);
    request.set_match_mode(prefix ? FindSymbolsRequest::MATCH_MODE_PREFIX
                                  : FindSymbolsRequest::MATCH_MODE_EXACT);
    request.set_limit(2);
    FindSymbolsResponse result;
    grpc::ServerContext context;
    ASSERT_TRUE(service.FindSymbols(&context, &request, &result).ok());
    ASSERT_EQ(result.symbols_size(), 2);
    EXPECT_TRUE(result.truncated());
    EXPECT_TRUE(result.stale());
    EXPECT_EQ(result.symbols(0).byte_offset(), 0);
    EXPECT_EQ(result.symbols(1).byte_offset(), 0);
    EXPECT_NE(result.symbols(0).compile_context(),
              result.symbols(1).compile_context());
  }
  LookupSymbolRequest request;
  request.set_project_root(project.string());
  request.set_usr("c:@LookupProbe");
  FindSymbolsResponse result;
  grpc::ServerContext context;
  ASSERT_TRUE(service.LookupSymbol(&context, &request, &result).ok());
  EXPECT_EQ(result.symbols_size(), 1000);
  EXPECT_TRUE(result.truncated());
  // Index sharing must not turn exact searches into case-insensitive searches.
  EXPECT_EQ(find(service, "lookupprobe", false).symbols_size(), 0);
  EXPECT_EQ(find(service, "NS::LOOKUPPROBE", false).symbols_size(), 0);
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  ASSERT_EQ(sqlite3_exec(db,
                         "INSERT INTO symbol SELECT id,'c:@literal',"
                         "'Lookup%_Probe','Lookup%_Probe','function',main_file,"
                         "2000,1,1,1,'int()' FROM translation_unit;",
                         nullptr, nullptr, nullptr),
            SQLITE_OK);
  sqlite3_close(db);
  // Both search arms match these rows: deduplicate contributions while keeping
  // distinct TU variants, and preserve literal LIKE wildcard escaping.
  const auto literal = find(service, "Lookup%_", true);
  EXPECT_EQ(literal.symbols_size(), 3);
  EXPECT_FALSE(literal.truncated());
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  ASSERT_EQ(sqlite3_exec(db, "DROP INDEX translation_unit_lookup", nullptr,
                         nullptr, nullptr),
            SQLITE_OK);
  sqlite3_close(db);
  // A reader must also work on a pre-upgrade store before indexing starts.
  EXPECT_EQ(find(service, "Lookup%_", true).symbols_size(), 3);
}

TEST_F(ProjectIndexServiceTest,
       ThreeTableIndexMatchesPrefixesTracksMacroHeaderAndReusesRestart) {
  const fs::path worker = CTK_TEST_INDEX_WORKER;
  ProjectIndexStatus first;
  {
    IndexServiceAdapter service(storage, {}, worker);
    first = start_and_wait(service);
    EXPECT_EQ(first.translation_units_total(), 3);
    EXPECT_GE(first.revision(), 3u);
    EXPECT_GE(find(service, "alphaOnly", false).symbols_size(), 2);
    EXPECT_GE(find(service, "alpha", true).symbols_size(), 2);
  }
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  sqlite3_stmt *tables = nullptr;
  ASSERT_EQ(sqlite3_prepare_v2(db,
                               "SELECT count(*) FROM sqlite_master WHERE "
                               "type='table' AND name NOT LIKE 'sqlite_%'",
                               -1, &tables, nullptr),
            SQLITE_OK);
  ASSERT_EQ(sqlite3_step(tables), SQLITE_ROW);
  EXPECT_EQ(sqlite3_column_int(tables, 0), 3);
  sqlite3_finalize(tables);
  ASSERT_EQ(sqlite3_prepare_v2(db,
                               "SELECT count(*) FROM sqlite_master WHERE "
                               "type='index' AND tbl_name='symbol' "
                               "AND name NOT LIKE 'sqlite_%'",
                               -1, &tables, nullptr),
            SQLITE_OK);
  ASSERT_EQ(sqlite3_step(tables), SQLITE_ROW);
  EXPECT_EQ(sqlite3_column_int(tables, 0), 3);
  sqlite3_finalize(tables);
  sqlite3_stmt *exact_plan = nullptr;
  ASSERT_EQ(
      sqlite3_prepare_v2(db,
                         "EXPLAIN QUERY PLAN SELECT name FROM symbol "
                         "INDEXED BY symbol_name_prefix WHERE "
                         "name='alphaOnly' COLLATE NOCASE AND "
                         "+name='alphaOnly' COLLATE BINARY UNION SELECT name "
                         "FROM symbol INDEXED BY symbol_qualified_prefix WHERE "
                         "qualified_name='alphaOnly' COLLATE NOCASE AND "
                         "+qualified_name='alphaOnly' COLLATE BINARY",
                         -1, &exact_plan, nullptr),
      SQLITE_OK);
  bool name_seek = false, qualified_seek = false;
  while (sqlite3_step(exact_plan) == SQLITE_ROW) {
    const auto *detail =
        reinterpret_cast<const char *>(sqlite3_column_text(exact_plan, 3));
    const std::string plan = detail ? detail : "";
    name_seek |= plan.find("symbol_name_prefix") != std::string::npos;
    qualified_seek |= plan.find("symbol_qualified_prefix") != std::string::npos;
    EXPECT_EQ(plan.find("SCAN symbol"), std::string::npos);
  }
  EXPECT_TRUE(name_seek);
  EXPECT_TRUE(qualified_seek);
  sqlite3_finalize(exact_plan);
  // These hot-path counts must remain independent of manifest payload size.
  for (const char *query :
       {"EXPLAIN QUERY PLAN SELECT count(*) FROM "
        "translation_unit WHERE indexed_at>0",
        "EXPLAIN QUERY PLAN SELECT count(*) FROM "
        "translation_unit WHERE status!='ready'",
        "EXPLAIN QUERY PLAN SELECT main_file,arguments,status "
        "FROM translation_unit INDEXED BY "
        "translation_unit_lookup WHERE id='test'"}) {
    sqlite3_stmt *plan = nullptr;
    ASSERT_EQ(sqlite3_prepare_v2(db, query, -1, &plan, nullptr), SQLITE_OK);
    bool covering = false;
    while (sqlite3_step(plan) == SQLITE_ROW) {
      const auto *detail =
          reinterpret_cast<const char *>(sqlite3_column_text(plan, 3));
      covering |= detail && std::string(detail).find("COVERING INDEX") !=
                                std::string::npos;
    }
    EXPECT_TRUE(covering) << query;
    sqlite3_finalize(plan);
  }
  sqlite3_close(db);

  write("shared.h", "#if FLAVOR == 1\n#define BETA_FEATURE 1\n#else\n#define "
                    "ALPHA_FEATURE 1\n#endif\n");
  {
    IndexServiceAdapter service(storage, {}, worker);
    StartProjectIndexRequest start;
    start.set_project_root(project.string());
    start.set_poll_interval_seconds(1);
    ProjectIndexStatus started;
    grpc::ServerContext start_context;
    ASSERT_TRUE(
        service.StartProjectIndex(&start_context, &start, &started).ok());
    ProjectIndexRequest status_request;
    status_request.set_project_root(project.string());
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(60);
    ProjectIndexStatus status;
    do {
      grpc::ServerContext context;
      ASSERT_TRUE(
          service.GetProjectIndexStatus(&context, &status_request, &status)
              .ok());
      if (status.state() == INDEX_STATE_FAILED)
        FAIL() << status.error();
      if (status.revision() >= first.revision() + 3)
        break;
      std::this_thread::sleep_for(std::chrono::milliseconds(50));
    } while (std::chrono::steady_clock::now() < deadline);
    EXPECT_GE(status.revision(), first.revision() + 3);
    EXPECT_GE(find(service, "betaOnly", false).symbols_size(), 2);
  }

  {
    IndexServiceAdapter restarted(storage, {}, worker);
    auto again = start_and_wait(restarted);
    EXPECT_EQ(again.revision(), first.revision() + 3);
    EXPECT_EQ(again.translation_units_skipped(), 3u);
  }
}

TEST_F(ProjectIndexServiceTest,
       FailedCommandChangeKeepsLastGoodSymbolsUntilReplacementSucceeds) {
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  const auto initial = start_and_wait(service);
  ASSERT_EQ(find(service, "alphaOnly", false).symbols_size(), 2);

  write("shared.h",
        "#if FLAVOR == 3\n#error invalid context\n#elif FLAVOR == 1\n"
        "#define ALPHA_FEATURE 1\n#else\n#define BETA_FEATURE 1\n#endif\n");
  replace_argument("-DFLAVOR=1", "-DFLAVOR=3");
  ProjectIndexRequest request;
  request.set_project_root(project.string());
  ProjectIndexStatus status;
  const auto failure_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(60);
  do {
    grpc::ServerContext context;
    ASSERT_TRUE(
        service.GetProjectIndexStatus(&context, &request, &status).ok());
    if (status.state() == INDEX_STATE_FAILED)
      break;
    std::this_thread::sleep_for(std::chrono::milliseconds(25));
  } while (std::chrono::steady_clock::now() < failure_deadline);
  ASSERT_EQ(status.state(), INDEX_STATE_FAILED);
  const auto stale = find(service, "alphaOnly", false);
  EXPECT_EQ(stale.symbols_size(), 2);
  EXPECT_TRUE(stale.stale());
  for (const auto &symbol : stale.symbols())
    EXPECT_TRUE(symbol.stale());

  write("shared.h", "#if FLAVOR == 1\n#define ALPHA_FEATURE 1\n#else\n"
                    "#define BETA_FEATURE 1\n#endif\n");
  const auto recovery_deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(60);
  do {
    grpc::ServerContext context;
    ASSERT_TRUE(
        service.GetProjectIndexStatus(&context, &request, &status).ok());
    if (status.state() == INDEX_STATE_COMPLETE &&
        status.revision() > initial.revision())
      break;
    std::this_thread::sleep_for(std::chrono::milliseconds(25));
  } while (std::chrono::steady_clock::now() < recovery_deadline);
  ASSERT_EQ(status.state(), INDEX_STATE_COMPLETE) << status.error();
  EXPECT_GT(status.revision(), initial.revision());
  EXPECT_EQ(status.translation_units_indexed(), 3);
  EXPECT_EQ(find(service, "alphaOnly", false).symbols_size(), 1);
}

TEST_F(ProjectIndexServiceTest,
       InvalidDriverFlagCannotReplaceCommittedSymbolsWithEmptyResult) {
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  start_and_wait(service);
  replace_argument("-DFLAVOR=1", "-fno-such-index-flag");
  ProjectIndexRequest request;
  request.set_project_root(project.string());
  ProjectIndexStatus status;
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(60);
  do {
    grpc::ServerContext context;
    ASSERT_TRUE(
        service.GetProjectIndexStatus(&context, &request, &status).ok());
    if (status.state() == INDEX_STATE_FAILED)
      break;
    std::this_thread::sleep_for(std::chrono::milliseconds(25));
  } while (std::chrono::steady_clock::now() < deadline);
  ASSERT_EQ(status.state(), INDEX_STATE_FAILED);
  EXPECT_EQ(find(service, "alphaOnly", false).symbols_size(), 2);
  EXPECT_TRUE(find(service, "alphaOnly", false).stale());
}

TEST_F(ProjectIndexServiceTest,
       LegacySymbolLayoutMigratesWithoutLosingSymbolsOrBlockingReaders) {
  ProjectIndexStatus initial;
  {
    IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
    initial = start_and_wait(service);
  }
  sqlite3 *db = nullptr;
  ASSERT_EQ(sqlite3_open(database_file().string().c_str(), &db), SQLITE_OK);
  sqlite3_stmt *schema = nullptr;
  ASSERT_EQ(sqlite3_prepare_v2(
                db, "SELECT sql FROM sqlite_master WHERE name='symbol'", -1,
                &schema, nullptr),
            SQLITE_OK);
  ASSERT_EQ(sqlite3_step(schema), SQLITE_ROW);
  std::string legacy(
      reinterpret_cast<const char *>(sqlite3_column_text(schema, 0)));
  sqlite3_finalize(schema);
  legacy += " WITHOUT ROWID;";
  const auto downgrade =
      "BEGIN; ALTER TABLE symbol RENAME TO saved_symbol;" + legacy +
      "INSERT INTO symbol SELECT tu_id,usr,name,qualified_name,kind,"
      "file_path,byte_offset,is_definition,line,column_no,signature "
      "FROM saved_symbol; DROP TABLE saved_symbol; COMMIT;";
  ASSERT_EQ(sqlite3_exec(db, downgrade.c_str(), nullptr, nullptr, nullptr),
            SQLITE_OK)
      << sqlite3_errmsg(db);
  // Keep a WAL reader on the old schema while the background migration runs.
  ASSERT_EQ(sqlite3_exec(db, "BEGIN; SELECT count(*) FROM symbol;", nullptr,
                         nullptr, nullptr),
            SQLITE_OK);
  {
    IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
    const auto migrated = start_and_wait(service);
    EXPECT_EQ(migrated.revision(), initial.revision());
    EXPECT_EQ(migrated.translation_units_skipped(), 3);
    EXPECT_EQ(find(service, "alphaOnly", false).symbols_size(), 2);
    EXPECT_EQ(sqlite3_exec(db, "SELECT count(*) FROM symbol; COMMIT;", nullptr,
                           nullptr, nullptr),
              SQLITE_OK);
    sqlite3_stmt *rowid = nullptr;
    ASSERT_EQ(sqlite3_prepare_v2(db, "SELECT rowid FROM symbol LIMIT 1", -1,
                                 &rowid, nullptr),
              SQLITE_OK);
    EXPECT_EQ(sqlite3_step(rowid), SQLITE_ROW);
    sqlite3_finalize(rowid);
    sqlite3_stmt *tables = nullptr;
    ASSERT_EQ(sqlite3_prepare_v2(db,
                                 "SELECT count(*) FROM sqlite_master WHERE "
                                 "type='table' AND name NOT LIKE 'sqlite_%'",
                                 -1, &tables, nullptr),
              SQLITE_OK);
    ASSERT_EQ(sqlite3_step(tables), SQLITE_ROW);
    EXPECT_EQ(sqlite3_column_int(tables, 0), 3);
    sqlite3_finalize(tables);
  }
  sqlite3_close(db);
}

TEST_F(ProjectIndexServiceTest,
       AttachedQuoteIncludePathDetectsNewHeaderShadowingExistingHeader) {
  const auto first = root / "first";
  const auto second = root / "second";
  fs::create_directories(first);
  fs::create_directories(second);
  write("one.cpp", "#include \"choice.hpp\"\nint one(){return 1;}\n");
  std::ofstream(second / "choice.hpp") << "struct OldChoice {};\n";
  write_shadow_commands("-iquote", first, second);
  IndexServiceAdapter service(storage, {}, CTK_TEST_INDEX_WORKER);
  const auto initial = start_and_wait(service);
  ASSERT_EQ(find(service, "OldChoice", false).symbols_size(), 2);

  std::ofstream(first / "choice.hpp") << "struct NewChoice {};\n";
  ProjectIndexRequest request;
  request.set_project_root(project.string());
  ProjectIndexStatus status;
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(60);
  do {
    grpc::ServerContext context;
    ASSERT_TRUE(
        service.GetProjectIndexStatus(&context, &request, &status).ok());
    if (status.state() == INDEX_STATE_COMPLETE &&
        status.revision() >= initial.revision() + 2)
      break;
    std::this_thread::sleep_for(std::chrono::milliseconds(25));
  } while (std::chrono::steady_clock::now() < deadline);
  ASSERT_EQ(status.state(), INDEX_STATE_COMPLETE) << status.error();
  EXPECT_EQ(status.revision(), initial.revision() + 2);
  EXPECT_EQ(find(service, "NewChoice", false).symbols_size(), 2);
  EXPECT_EQ(find(service, "OldChoice", false).symbols_size(), 0);
}
} // namespace
} // namespace ctk::net
