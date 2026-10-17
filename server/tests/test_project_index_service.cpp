#include "ctk/net/index_service.hpp"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <gtest/gtest.h>
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
} // namespace
} // namespace ctk::net
