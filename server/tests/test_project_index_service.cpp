#include "ctk/net/index_service.hpp"

#include <atomic>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <gtest/gtest.h>
#include <iterator>
#include <sqlite3.h>
#include <thread>
#include <utility>

namespace ctk::net {
namespace fs = std::filesystem;
namespace {
using namespace ctk::index::v1;
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
  fs::path worker_wrapper(const fs::path &counter) {
    const auto shell_word = [](const std::string &value) {
      std::string out = "'";
      for (char c : value)
        out += c == '\'' ? "'\"'\"'" : std::string(1, c);
      return out + "'";
    };
    const auto path = root / "index-worker-wrapper";
    std::ofstream(path) << "#!/bin/sh\nprintf . >> "
                        << shell_word(counter.string()) << "\nexec "
                        << shell_word(CTK_TEST_INDEX_WORKER) << " \"$@\"\n";
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
