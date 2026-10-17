#include "ctk/net/index_service.hpp"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <gtest/gtest.h>
#include <iterator>
#include <sqlite3.h>
#include <thread>

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
  // These hot-path counts must remain independent of manifest payload size.
  for (const char *query : {"EXPLAIN QUERY PLAN SELECT count(*) FROM "
                            "translation_unit WHERE indexed_at>0",
                            "EXPLAIN QUERY PLAN SELECT count(*) FROM "
                            "translation_unit WHERE status!='ready'"}) {
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
