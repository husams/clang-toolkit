#include "ctk/clang/compilation_database.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <cstdlib>
#include <fstream>
#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <gtest/gtest.h>
#include <sqlite3.h>

namespace ctk::clang_layer {
namespace {
void write_database(const std::filesystem::path &database,
                    const std::filesystem::path &directory,
                    const std::string &file,
                    const std::vector<std::string> &arguments,
                    bool shell_command = false, bool append = false) {
  google::protobuf::ListValue entries;
  if (append) {
    std::ifstream existing(database);
    std::string json((std::istreambuf_iterator<char>(existing)), {});
    ASSERT_TRUE(google::protobuf::util::JsonStringToMessage(json, &entries).ok());
  }
  auto *entry = entries.add_values()->mutable_struct_value();
  auto &fields = *entry->mutable_fields();
  fields["directory"].set_string_value(directory.string());
  fields["file"].set_string_value(file);
  if (shell_command) {
    std::string command;
    for (const auto &argument : arguments)
      command += "'" + argument + "' ";
    fields["command"].set_string_value(command);
  } else {
    auto *list = fields["arguments"].mutable_list_value();
    for (const auto &argument : arguments)
      list->add_values()->set_string_value(argument);
  }
  std::string json;
  ASSERT_TRUE(google::protobuf::util::MessageToJsonString(entries, &json).ok());
  std::ofstream(database) << json;
}

int match_count(const std::shared_ptr<IQueryEngine> &engine,
                const FileInput &file, const std::string &name) {
  int count = 0;
  const auto result = engine->match(
      file, "functionDecl(hasName(\"" + name + "\")).bind(\"f\")",
      [] { return true; }, [&](const auto &) { ++count; });
  EXPECT_TRUE(result.ok) << result.message;
  return count;
}
} // namespace

TEST(CompilationDatabase,
     AutomaticallyUsesBuildDatabaseAndCommandWorkingDirectory) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-auto"};
  std::filesystem::create_directories(project.path() /
                                      "build/include with spaces");
  std::filesystem::create_directory(project.path() / "src");
  std::ofstream(project.path() / "build/include with spaces/profile.hpp")
      << "#define PROFILE_VALUE 17\n";
  std::ofstream(project.path() / "src/file.cc")
      << "#include <profile.hpp>\nstatic_assert(PROFILE_VALUE == 17);\nint "
         "from_database(){return PROFILE_VALUE;}";
  write_database(project.path() / "build/compile_commands.json",
                 project.path() / "build", "../src/file.cc",
                 {"clang++", "-std=c++20", "-Iinclude with spaces", "-c",
                  "../src/file.cc", "-o", "file.o", "-MMD", "-MF", "file.d"},
                 true);
  FileInput input{"src/file.cc", {}, project.path().string()};
  const auto resolved = resolve_compilation_command(input);
  EXPECT_EQ(
      resolved.working_directory,
      std::filesystem::weakly_canonical(project.path() / "build").string());
  EXPECT_EQ(match_count(make_query_engine(), input, "from_database"), 1);
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/file.o"));
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/file.d"));
}

TEST(CompilationDatabase,
     ExplicitPathOverridesDiscoveryAndRequestFlagsOverrideDatabase) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-explicit"};
  std::ofstream(project.path() / "file.cc")
      << "static_assert(VALUE == 23); int selected(){return VALUE;}";
  write_database(project.path() / "compile_commands.json", project.path(),
                 "file.cc", {"clang++", "-DVALUE=1", "file.cc"});
  write_database(project.path() / "alternative.json", project.path(), "file.cc",
                 {"clang++", "-DVALUE=2", "file.cc"});
  FileInput input{"file.cc",
                  {"-UVALUE", "-DVALUE=23"},
                  project.path().string(),
                  "alternative.json"};
  EXPECT_EQ(match_count(make_query_engine(), input, "selected"), 1);
}

TEST(CompilationDatabase, DiscoversCMakePresetDatabaseFromSourceDirectory) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-preset"};
  std::filesystem::create_directories(project.path() / "build/dev/include");
  std::filesystem::create_directory(project.path() / "src");
  std::ofstream(project.path() / "build/dev/include/profile.hpp")
      << "#define PROFILE_VALUE 29\n";
  std::ofstream(project.path() / "src/file.cc")
      << "#include <profile.hpp>\nstatic_assert(PROFILE_VALUE == 29);\n"
         "int preset_profile(){return PROFILE_VALUE;}";
  write_database(
      project.path() / "build/dev/compile_commands.json",
      project.path() / "build/dev", "../../src/file.cc",
      {"clang++", "-std=c++20", "-Iinclude", "-c", "../../src/file.cc"});
  FileInput input{"file.cc", {}, (project.path() / "src").string()};
  const auto resolved = resolve_compilation_command(input);
  EXPECT_EQ(resolved.compilation_database,
            std::filesystem::weakly_canonical(project.path() /
                                              "build/dev/compile_commands.json")
                .string());
  EXPECT_EQ(match_count(make_query_engine(), input, "preset_profile"), 1);
  // Explicit selection still takes precedence over the discovered preset.
  input.compilation_database = "missing.json";
  EXPECT_THROW(resolve_compilation_command(input), std::invalid_argument);
}

TEST(CompilationDatabase, InputSeparatorDoesNotCreateExtraCompilerJobs) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-input-separator"};
  std::ofstream(project.path() / "optional")
      << "#ifndef PROFILE\n#define PROFILE 17\n#endif\n";
  std::ofstream(project.path() / "file.cc")
      << "static_assert(PROFILE == 23); int selected(){return PROFILE;}";
  write_database(
      project.path() / "compile_commands.json", project.path(), "file.cc",
      {"clang++", "-std=c++20", "-include", "optional", "-c", "--", "file.cc"});
  FileInput input{
      "file.cc", {"-UPROFILE", "-DPROFILE=23"}, project.path().string()};
  EXPECT_EQ(match_count(make_query_engine(), input, "selected"), 1);
}

TEST(CompilationDatabase, ResponseInputSeparatorPreservesOuterOverrideOptions) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-response-separator"};
  std::ofstream(project.path() / "optional") << "#define HEADER_PRESENT 1\n";
  std::ofstream(project.path() / "flags.rsp")
      << "-std=c++20 -include optional -DPROFILE=17 -c -- file.cc";
  std::ofstream(project.path() / "file.cc")
      << "static_assert(HEADER_PRESENT && PROFILE == 23); int "
         "selected(){return PROFILE;}";
  write_database(project.path() / "compile_commands.json", project.path(),
                 "file.cc", {"clang++", "@flags.rsp"});
  FileInput input{
      "file.cc", {"-UPROFILE", "-DPROFILE=23"}, project.path().string()};
  EXPECT_EQ(match_count(make_query_engine(), input, "selected"), 1);
}

TEST(CompilationDatabase, ChangedDatabaseSelectsNewAstRatherThanStaleFlags) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-refresh"};
  std::ofstream(project.path() / "file.cc")
      << "#if VALUE == 1\nint before(){return 1;}\n#else\nint after(){return "
         "2;}\n#endif\n";
  auto database = project.path() / "compile_commands.json";
  write_database(database, project.path(), "file.cc",
                 {"clang++", "-DVALUE=1", "file.cc"});
  FileInput input{"file.cc", {}, project.path().string()};
  auto engine = make_query_engine();
  EXPECT_EQ(match_count(engine, input, "before"), 1);
  EXPECT_EQ(match_count(engine, input, "before"), 1);
  write_database(database, project.path(), "file.cc",
                 {"clang++", "-DVALUE=22", "file.cc"});
  EXPECT_EQ(match_count(engine, input, "after"), 1);
  EXPECT_EQ(match_count(engine, input, "before"), 0);
  std::ofstream(database) << "[invalid JSON";
  EXPECT_THROW(resolve_compilation_command(input), std::invalid_argument);
}

TEST(CompilationDatabase,
     ExpandsResponseFilesInCommandDirectoryAndRefreshesTheirFlags) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-response"};
  std::filesystem::create_directory(project.path() / "build");
  std::ofstream(project.path() / "file.cc")
      << "#if VALUE == 1\nint before(){return 1;}\n#else\nint after(){return "
         "2;}\n#endif\n";
  auto response = project.path() / "build/flags.rsp";
  std::ofstream(response)
      << "-DVALUE=1 -c ../file.cc -o output.o -MMD -MF output.d";
  write_database(project.path() / "build/compile_commands.json",
                 project.path() / "build", "../file.cc",
                 {"clang++", "@flags.rsp"});
  FileInput input{"file.cc", {}, project.path().string()};
  auto engine = make_query_engine();
  EXPECT_EQ(match_count(engine, input, "before"), 1);
  std::ofstream(response) << "-DVALUE=22 -c ../file.cc -o output.o";
  EXPECT_EQ(match_count(engine, input, "after"), 1);
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/output.o"));
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/output.d"));
}

TEST(CompilationDatabase, ExplicitMissingFilesAndCommandsAreErrors) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-missing"};
  std::ofstream(project.path() / "file.cc") << "int value;";
  FileInput input{"file.cc", {}, project.path().string(), "absent.json"};
  EXPECT_THROW(resolve_compilation_command(input), std::invalid_argument);
  std::ofstream(project.path() / "compile_commands.json") << "[]";
  input.compilation_database = project.path().string();
  EXPECT_THROW(resolve_compilation_command(input), std::invalid_argument);
  input.compilation_database.clear();
  EXPECT_EQ(resolve_compilation_command(input).path, input.path);
}

TEST(CompilationDatabase, HeaderInheritsNearbyTuFlagsAndKeepsHeaderAsMainFile) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-header"};
  std::filesystem::create_directories(project.path() /
                                      "build/include with spaces");
  std::filesystem::create_directory(project.path() / "src");
  std::ofstream(project.path() / "build/include with spaces/profile.hpp")
      << "#define HEADER_VALUE 17\n";
  std::ofstream(project.path() / "src/profile.h")
      << "#include <profile.hpp>\nstatic_assert(HEADER_VALUE == 17 && PROFILE "
         "== 23);\n"
         "inline int from_header(){return PROFILE;}\n";
  // Clang's filename inference does not require the donor TU to be readable.
  write_database(project.path() / "build/compile_commands.json",
                 project.path() / "build", "../src/profile.cc",
                 {"clang++", "-std=c++20", "-Iinclude with spaces",
                  "-DPROFILE=1", "-c", "../src/profile.cc", "-o", "profile.o",
                  "-MMD", "-MF", "profile.d"});
  FileInput input{
      "src/profile.h", {"-UPROFILE", "-DPROFILE=23"}, project.path().string()};
  EXPECT_EQ(match_count(make_query_engine(), input, "from_header"), 1);
  input.compilation_database = "build";
  const auto resolved = resolve_compilation_command(input);
  EXPECT_EQ(resolved.path,
            std::filesystem::weakly_canonical(project.path() / "src/profile.h")
                .string());
  EXPECT_EQ(
      resolved.working_directory,
      std::filesystem::weakly_canonical(project.path() / "build").string());
  int count = 0;
  const auto result = make_query_engine()->match(
      input, "functionDecl(hasName(\"from_header\"), isExpansionInMainFile())",
      [] { return true; }, [&](const auto &) { ++count; });
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_EQ(count, 1);
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/profile.o"));
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/profile.d"));
}

TEST(CompilationDatabase,
     InferredHeaderFlagsRefreshWithDatabaseAndResponseFile) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-header-response"};
  std::filesystem::create_directory(project.path() / "build");
  std::ofstream(project.path() / "profile.hpp")
      << "#if VALUE == 1\ninline int before(){return 1;}\n"
         "#else\ninline int after(){return 2;}\n#endif\n";
  const auto response = project.path() / "build/flags.rsp";
  std::ofstream(response) << "-std=c++20 -DVALUE=1 -c -- ../profile.cc";
  const auto database = project.path() / "build/compile_commands.json";
  write_database(database, project.path() / "build", "../profile.cc",
                 {"clang++", "@flags.rsp"});
  FileInput input{"profile.hpp", {}, project.path().string()};
  auto engine = make_query_engine();
  EXPECT_EQ(match_count(engine, input, "before"), 1);
  std::ofstream(response) << "-std=c++23 -DVALUE=22 -c -- ../profile.cc";
  EXPECT_EQ(match_count(engine, input, "after"), 1);
  EXPECT_EQ(match_count(engine, input, "before"), 0);
  write_database(database, project.path() / "build", "../replacement.cc",
                 {"clang++", "-std=c++20", "-DVALUE=1", "../replacement.cc"});
  EXPECT_EQ(match_count(engine, input, "before"), 1);
  std::ofstream(database) << "[invalid JSON";
  EXPECT_THROW(resolve_compilation_command(input), std::invalid_argument);
}

TEST(CompilationDatabase, ExactHeaderEntryWinsOverInferredTu) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-exact-header"};
  const auto header = project.path() / "profile.hpp";
  std::ofstream(header)
      << "static_assert(VALUE == 23); inline int exact(){return VALUE;}";
  const auto database = project.path() / "compile_commands.json";
  write_database(database, project.path(), "profile.cc",
                 {"clang++", "-DVALUE=1", "profile.cc"});
  // Add an authoritative header entry to the same database.
  std::ifstream file(database);
  std::string json((std::istreambuf_iterator<char>(file)), {});
  google::protobuf::ListValue entries;
  ASSERT_TRUE(google::protobuf::util::JsonStringToMessage(json, &entries).ok());
  auto &fields =
      *entries.add_values()->mutable_struct_value()->mutable_fields();
  fields["directory"].set_string_value(project.path().string());
  fields["file"].set_string_value("profile.hpp");
  for (const auto *arg : {"clang++", "-std=c++20", "-DVALUE=23", "profile.hpp"})
    fields["arguments"].mutable_list_value()->add_values()->set_string_value(
        arg);
  json.clear();
  ASSERT_TRUE(google::protobuf::util::MessageToJsonString(entries, &json).ok());
  std::ofstream(database) << json;
  EXPECT_EQ(match_count(make_query_engine(),
                        {header.string(), {}, project.path().string()},
                        "exact"),
            1);
}

TEST(CompilationDatabase, MissingSourceUsesFirstCommandInSameSourceDirectory) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-sibling"};
  std::filesystem::create_directories(project.path() / "src/nested");
  std::filesystem::create_directory(project.path() / "other");
  std::filesystem::create_directories(project.path() / "build/include");
  std::ofstream(project.path() / "build/include/profile.hpp")
      << "#define INCLUDED_VALUE 17\n";
  std::ofstream(project.path() / "src/missing.cc")
      << "#include <profile.hpp>\n"
         "static_assert(INCLUDED_VALUE == 17 && VALUE == 23 && OVERRIDE == 2);\n"
         "int sibling_profile(){return VALUE;}";
  std::ofstream(project.path() / "build/flags.rsp")
      << "-std=c++20 -Iinclude -DVALUE=23 -DOVERRIDE=1 -c "
         "../src/z_first.cc -o donor.o -MMD -MF donor.d";
  const auto database = project.path() / "build/compile_commands.json";
  // Neither a matching basename elsewhere, a descendant directory nor lexical
  // filename order may displace the first entry in the same source directory.
  write_database(database, project.path() / "build", "../other/missing.cc",
                 {"clang++", "-DVALUE=0", "../other/missing.cc"});
  write_database(database, project.path() / "build", "../src/nested/missing.cc",
                 {"clang++", "-DVALUE=0", "../src/nested/missing.cc"}, false, true);
  write_database(database, project.path() / "build", "../src/z_first.cc",
                 {"clang++", "@flags.rsp"}, false, true);
  write_database(database, project.path() / "build", "../src/a_second.cc",
                 {"clang++", "-DVALUE=0", "../src/a_second.cc"}, false, true);
  FileInput input{"src/../src/missing.cc", {"-UOVERRIDE", "-DOVERRIDE=2"},
                  project.path().string(), "build"};
  auto engine = make_query_engine();
  EXPECT_EQ(match_count(engine, input, "sibling_profile"), 1);
  const auto resolved = resolve_compilation_command(input);
  EXPECT_EQ(resolved.path,
            std::filesystem::weakly_canonical(project.path() / "src/missing.cc")
                .string());
  EXPECT_EQ(resolved.working_directory,
            std::filesystem::weakly_canonical(project.path() / "build").string());
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/donor.o"));
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/donor.d"));
  input.compilation_database.clear();
  EXPECT_EQ(match_count(engine, input, "sibling_profile"), 1);
  // An exact entry must still win over the sibling fallback.
  write_database(database, project.path() / "build", "../src/z_first.cc",
                 {"clang++", "-DVALUE=0", "../src/z_first.cc"});
  write_database(database, project.path() / "build", "../src/missing.cc",
                 {"clang++", "-std=c++20", "-Iinclude", "-DVALUE=23",
                  "-DOVERRIDE=2", "../src/missing.cc"}, false, true);
  EXPECT_EQ(match_count(engine, input, "sibling_profile"), 1);
}

TEST(CompilationDatabase,
     DirectoryDonorsUpgradeLegacyCachesAndRefreshAtomically) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-donor-cache"};
  const auto database = project.path() / "compile_commands.json";
  write_database(database, project.path(), "z_first.cc",
                 {"clang++", "-DVALUE=23", "z_first.cc"});
  write_database(database, project.path(), "a_second.cc",
                 {"clang++", "-DVALUE=0", "a_second.cc"}, false, true);
  FileInput input{"missing.cc", {}, project.path().string(), database.string()};
  EXPECT_EQ(resolve_compilation_command(input).working_directory,
            std::filesystem::weakly_canonical(project.path()).string());

  std::filesystem::path storage;
  if (const char *root = std::getenv("CTK_STORAGE_ROOT"); root && *root)
    storage = root;
  else if (const char *root = std::getenv("XDG_CACHE_HOME"); root && *root)
    storage = std::filesystem::path(root) / "clang-toolkit/storage";
  else if (const char *root = std::getenv("HOME"); root && *root)
    storage = std::filesystem::path(root) / ".cache/clang-toolkit/storage";
  else
    storage = std::filesystem::temp_directory_path() / "clang-toolkit-storage";
  sqlite3 *raw = nullptr;
  ASSERT_EQ(
      sqlite3_open_v2((storage / "compile_commands.sqlite3").string().c_str(),
                      &raw, SQLITE_OPEN_READWRITE, nullptr),
      SQLITE_OK);
  std::unique_ptr<sqlite3, decltype(&sqlite3_close)> cache(raw, sqlite3_close);
  ASSERT_EQ(sqlite3_busy_timeout(cache.get(), 5000), SQLITE_OK);
  const auto cache_key = std::filesystem::weakly_canonical(database).string();
  const auto source_directory =
      std::filesystem::weakly_canonical(project.path()).string();
  auto run = [&](const char *sql) {
    sqlite3_stmt *statement = nullptr;
    EXPECT_EQ(sqlite3_prepare_v2(cache.get(), sql, -1, &statement, nullptr),
              SQLITE_OK);
    if (!statement)
      return std::string{};
    std::unique_ptr<sqlite3_stmt, decltype(&sqlite3_finalize)> query(
        statement, sqlite3_finalize);
    EXPECT_EQ(sqlite3_bind_text(statement, 1, cache_key.c_str(), -1,
                                SQLITE_TRANSIENT),
              SQLITE_OK);
    if (sqlite3_bind_parameter_count(statement) > 1)
      EXPECT_EQ(sqlite3_bind_text(statement, 2, source_directory.c_str(), -1,
                                  SQLITE_TRANSIENT),
                SQLITE_OK);
    const auto result = sqlite3_step(statement);
    EXPECT_TRUE(result == SQLITE_ROW || result == SQLITE_DONE)
        << sqlite3_errmsg(cache.get());
    EXPECT_EQ(sqlite3_stmt_status(statement, SQLITE_STMTSTATUS_FULLSCAN_STEP, 0), 0);
    EXPECT_EQ(sqlite3_stmt_status(statement, SQLITE_STMTSTATUS_SORT, 0), 0);
    if (result != SQLITE_ROW || !sqlite3_column_text(statement, 0))
      return std::string{};
    return std::string(
        reinterpret_cast<const char *>(sqlite3_column_text(statement, 0)));
  };
  const char *donor = "SELECT file FROM compilation_directory_donors WHERE "
                      "database_path=? AND source_directory=?";
  const auto first =
      (std::filesystem::path(source_directory) / "z_first.cc").string();
  EXPECT_EQ(run(donor), first);

  // An old cache has the original file stamp but no directory donor records.
  run("UPDATE compilation_sources SET "
      "signature=substr(signature,instr(signature,':')+1) WHERE path=?");
  run("DELETE FROM compilation_directory_donors WHERE database_path=?");
  EXPECT_TRUE(run(donor).empty());
  resolve_compilation_command(input);
  EXPECT_EQ(run(donor), first);

  // Failed refreshes must preserve the committed donor generation.
  std::ofstream(database) << "[invalid JSON";
  EXPECT_THROW(resolve_compilation_command(input), std::invalid_argument);
  EXPECT_EQ(run(donor), first);

  // Removing the source directory from a new generation must remove its donor.
  write_database(database, project.path(), "nested/replacement.cc",
                 {"clang++", "-DVALUE=17", "nested/replacement.cc"});
  resolve_compilation_command(input);
  EXPECT_TRUE(run(donor).empty());
}

TEST(CompilationDatabase, AmbiguousHeaderExtensionInheritsCLanguage) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-c-header"};
  std::ofstream(project.path() / "profile.h")
      << "#ifdef __cplusplus\n#error must_parse_as_c\n#endif\n"
         "_Static_assert(VALUE == 17, \"profile\");\nint c_header(void);\n";
  write_database(project.path() / "compile_commands.json", project.path(),
                 "profile.c", {"clang", "-DVALUE=17", "profile.c"});
  EXPECT_EQ(match_count(make_query_engine(),
                        {"profile.h", {}, project.path().string()}, "c_header"),
            1);
}

TEST(CompilationDatabase, CppHeaderDoesNotInheritIncompatibleCStandard) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-c-to-cpp-header"};
  std::ofstream(project.path() / "profile.hpp")
      << "template<class T> constexpr T value = T{17};\n"
         "static_assert(value<int> == VALUE);\ninline int cpp_header(){return "
         "VALUE;}\n";
  write_database(project.path() / "compile_commands.json", project.path(),
                 "profile.c", {"clang", "-std=c17", "-DVALUE=17", "profile.c"});
  EXPECT_EQ(match_count(make_query_engine(),
                        {"profile.hpp", {}, project.path().string()},
                        "cpp_header"),
            1);
}

TEST(CompilationDatabase, ParseFailureReportsMissingHeaderAndSourceLocation) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-diagnostics"};
  std::ofstream(project.path() / "file.cc")
      << "#include <ctk_missing_project_header.hpp>\nint value;\n";
  write_database(project.path() / "compile_commands.json", project.path(),
                 "file.cc", {"clang++", "-std=c++20", "file.cc"});
  FileInput input{"file.cc", {}, project.path().string()};
  auto engine = make_query_engine();
  try {
    engine->acquire_snapshot(input);
    FAIL() << "missing header must fail parsing";
  } catch (const std::exception &error) {
    const std::string message = error.what();
    EXPECT_NE(message.find("file.cc:1:10:"), std::string::npos) << message;
    EXPECT_NE(message.find("ctk_missing_project_header.hpp"), std::string::npos)
        << message;
    EXPECT_NE(message.find("file not found"), std::string::npos) << message;
  }
  // Failed snapshots must remain retryable after the build inputs are fixed.
  std::ofstream(project.path() / "file.cc") << "int recovered(){return 1;}";
  EXPECT_EQ(match_count(engine, input, "recovered"), 1);
}

TEST(CompilationDatabase, ParseFailureReportsDriverAndPreprocessorErrors) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-driver-diagnostics"};
  std::ofstream(project.path() / "file.cc")
      << "#error project_profile_missing\n";
  FileInput input{"file.cc", {}, project.path().string()};
  auto engine = make_query_engine();
  auto result = engine->match(
      input, "varDecl().bind(\"v\")", [] { return true; }, [](const auto &) {});
  EXPECT_FALSE(result.ok);
  EXPECT_NE(result.message.find("project_profile_missing"), std::string::npos)
      << result.message;
  input.compile_arguments = {"-ctk-invalid-driver-option"};
  result = engine->match(
      input, "varDecl().bind(\"v\")", [] { return true; }, [](const auto &) {});
  EXPECT_FALSE(result.ok);
  EXPECT_NE(result.message.find("-ctk-invalid-driver-option"),
            std::string::npos)
      << result.message;
  input.compile_arguments = {"-include"};
  result = engine->match(
      input, "varDecl().bind(\"v\")", [] { return true; }, [](const auto &) {});
  EXPECT_FALSE(result.ok);
  EXPECT_FALSE(result.message.empty());
}
} // namespace ctk::clang_layer
